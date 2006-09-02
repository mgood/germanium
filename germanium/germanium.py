#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2006 Matt Good <matt@matt-good.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import sys
try:
    import pygtk
    pygtk.require("2.0")
except ImportError:
    pass
try:
    import gtk
    import gtk.glade
except ImportError:
    # FIXME
    sys.exit(1)

import os.path

current_dir = os.path.dirname(__file__)
base_dir = os.path.join(current_dir, '..')
if (os.path.isdir(base_dir)
    and os.path.isfile(os.path.join(base_dir, 'AUTHORS'))):
    sys.path.insert(0, os.path.abspath(base_dir))
else:
    sys.path.insert(0, os.path.abspath('@PYTHONDIR@'))

import gconf
import gnomevfs

from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor
from twisted.web import client

import errno
from threading import Thread
from urlparse import urlparse
import weakref

import defs
from emp import get_tracks
from progress import ProgressDownloader, format_time
from gconf_util import gconf_property, bind_file_chooser, bind_combo_box, bind_checkbox
from vfs_util import vfs_makedirs, open_for_write

TITLE_COLUMN = 0
PROGRESS_COLUMN = 1
PROGRESS_TIME_COLUMN = 2
ICON_COLUMN = 3
OBJECT_COLUMN = 4

icons = {
    'started': gtk.STOCK_MEDIA_PLAY,
    'aborted': gtk.STOCK_STOP,
    'completed': gtk.STOCK_APPLY,
    'error': gtk.STOCK_DIALOG_ERROR,
}

GLADE_FILE = os.path.join(defs.DATA_DIR, defs.PACKAGE, 'germanium.glade')

GCONF_KEY = '/apps/germanium'
gconf.client_get_default().add_dir(GCONF_KEY, gconf.CLIENT_PRELOAD_NONE)

class Germanium(object):

    max_downloads = gconf_property(GCONF_KEY+'/max_downloads', gconf.VALUE_INT)
    base_uri = gconf_property(GCONF_KEY+'/base_uri')
    path_pattern = gconf_property(GCONF_KEY+'/path_pattern')
    file_pattern = gconf_property(GCONF_KEY+'/file_pattern')
 
    # TODO
    strip_special = gconf_property(GCONF_KEY+'/strip_special', gconf.VALUE_BOOL)

    def __init__(self):
        self.ui = gtk.glade.XML(GLADE_FILE, 'main_window')
        signals = ['on_open_button_clicked',
                   'on_start_button_clicked',
                   'on_stop_button_clicked',
                   'on_clear_button_clicked',
                   'on_prefs_button_clicked',
                  ]
        handlers = dict([(s,getattr(self, s)) for s in signals])
        handlers['on_main_window_destroy'] = self.quit
        self.ui.signal_autoconnect(handlers)
        self.view = self['download_view']

        self.model = gtk.ListStore(str, int, str, str, object)
        self.view.set_model(self.model)

        column = gtk.TreeViewColumn('State', gtk.CellRendererPixbuf(),
                                    stock_id=ICON_COLUMN)
        self.view.append_column(column)

        title_renderer = gtk.CellRendererText()
        title_renderer.set_property('ellipsize', 3)
        column = gtk.TreeViewColumn('Title', title_renderer,
                                    markup=TITLE_COLUMN)
        column.set_min_width(100)
        column.set_expand(True)
        self.view.append_column(column)

        column = gtk.TreeViewColumn('Progress Status',
                                    gtk.CellRendererProgress(), 
                                    text=PROGRESS_TIME_COLUMN,
                                    value=PROGRESS_COLUMN)
        column.set_min_width(100)
        self.view.append_column(column)
        self.view.get_selection().connect('changed',
                                          self.on_track_selection_changed)

        self.selected_row = None

        Germanium.max_downloads.add_callback(self.on_max_downloads_changed)

        if self.max_downloads is None:
            self.max_downloads = 2
        self.active_downloads = 0

        self._cover_queue = set()
        self.max_cover_downloads = 1
        self.active_cover_downloads = 0

    def __getitem__(self, name):
        return self.ui.get_widget(name)

    def load_files(self, files):
        # TODO the .emp file contains the server info in the XML
        for filename in files:
            for track in get_tracks(filename):
                self.add_track(track)

    def add_track(self, info):
        import cgi
        title = '<b>%s</b>\n%s' % (cgi.escape(info['title']),
                                   cgi.escape(info['artist']))
        track = Track(info)
        row = self.model.append([title, 0, '', None, track])
        if self.active_downloads < self.max_downloads:
            self._download(row)
        if not track.cover_image.is_loaded:
            self._queue_cover_download(track.cover_image)

    def quit(self, widget):
        reactor.stop()

    def on_open_button_clicked(self, button):
        file_open = gtk.FileChooserDialog(title='Open EMP file',
                                          action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                          buttons=(gtk.STOCK_CANCEL,
                                                   gtk.RESPONSE_CANCEL,
                                                   gtk.STOCK_OPEN,
                                                   gtk.RESPONSE_OK))
        # TODO use the previously opened location
        file_open.set_select_multiple(True)

        filter = gtk.FileFilter()
        # TODO look up the description from the MIME DB
        filter.set_name('eMusic download package')
        filter.add_pattern('*.emp')
        file_open.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name('All files')
        filter.add_pattern('*')
        file_open.add_filter(filter)

        if file_open.run() == gtk.RESPONSE_OK:
            filenames = file_open.get_filenames()
        else:
            filenames = []

        file_open.destroy()

        for f in filenames:
            for track in get_tracks(f):
                self.add_track(track)

    def on_track_selection_changed(self, selection):
        model, row = selection.get_selected()
        self.selected_row = row
        if row:
            self._get_track(row).cover_image.attach(self['cover_image'])
        else:
            self['cover_image'].clear()

    def on_start_button_clicked(self, button):
        if self.selected_row is None:
            return
        track = self._get_track(self.selected_row)
        if track.status == 'started':
            return
        self._download(self.selected_row)

    def on_stop_button_clicked(self, button):
        if self.selected_row is None:
            return
        track = self._get_track(self.selected_row)
        if track.status not in ('new', 'started'):
            return
        track.abort()
        self.model.set_value(self.selected_row, ICON_COLUMN, icons['aborted'])
        self.model.set_value(self.selected_row, PROGRESS_TIME_COLUMN, '')
        self.model.set_value(self.selected_row, PROGRESS_COLUMN, 0)

    def on_clear_button_clicked(self, button):
        for row in gtk_model_iter(self.model):
            while self._get_track(row).status in ('completed', 'aborted',
                                                  'error'):
                if not self.model.remove(row):
                    break

    def on_prefs_button_clicked(self, button):
        PreferencesDialog(self)

    def on_max_downloads_changed(self, *args):
        self._check_queue()

    def _get_track(self, row):
        return self.model.get_value(row, OBJECT_COLUMN)

    def _download(self, row):
        self.active_downloads += 1
        track = self._get_track(row)

        def started():
            self.model.set_value(row, ICON_COLUMN, icons['started'])
        def progress(rate_estimator):
            self.model.set_value(row, PROGRESS_COLUMN,
                                 100*rate_estimator.fraction_read())
            self.model.set_value(row, PROGRESS_TIME_COLUMN,
                                 format_time(rate_estimator.remaining_time()))
        def complete(result):
            if track.status != 'aborted':
                self.model.set_value(row, PROGRESS_COLUMN, 100)
                self.model.set_value(row, ICON_COLUMN, icons['completed'])
                track.completed()
            self._download_done()
        def error(failure):
            print failure.getErrorMessage()
            self.model.set_value(row, ICON_COLUMN, icons['error'])
            track.error(failure)
            self._download_done()

        url = str('http://dl.emusic.com/dl/%(trackid)s/%(filename)s' % track.tags)
        if self.base_uri is None:
            dir_uri = gnomevfs.get_uri_from_local_path(os.path.expanduser('~'))
        else:
            dir_uri = self.base_uri
        pathname = track.fill_pattern(self.path_pattern, self.strip_special)
        dir_uri = gnomevfs.URI(dir_uri).append_path(pathname)

        filename = track.fill_pattern(self.file_pattern,
                                      self.strip_special) + '.mp3'

        vfs_makedirs(dir_uri)
        openfile = open_for_write(dir_uri.append_file_name(filename))

        scheme,host,path,_,_,_ = urlparse(url)
        factory = ProgressDownloader(url, openfile, started, progress)
        reactor.connectTCP(host, 80, factory)
        factory.deferred.addCallback(complete).addErrback(error)
        track.start(factory)

    def _download_done(self):
        self.active_downloads -= 1
        self._check_queue()

    def _check_queue(self):
        for row in gtk_model_iter(self.model):
            if self.active_downloads >= self.max_downloads:
                break
            track = self._get_track(row)
            if track.status == 'new':
                self._download(row)

    def _queue_cover_download(self, cover_image):
        self._cover_queue.add(cover_image)
        self._check_cover_queue()

    def _download_cover(self):
        self.active_cover_downloads += 1
        cover_image = self._cover_queue.pop()

        def complete(result):
            self._cover_done()
        def error(failure):
            cover_image.error_loading(failure)
            self._cover_done()

        url = cover_image.url
        scheme,host,path,_,_,_ = urlparse(url)
        factory = client.HTTPDownloader(url, cover_image.get_dest_file())
        reactor.connectTCP(host, 80, factory)
        factory.deferred.addCallback(complete).addErrback(error)

    def _cover_done(self):
        self.active_cover_downloads -= 1
        self._check_cover_queue()

    def _check_cover_queue(self):
        while (self._cover_queue
               and self.active_cover_downloads < self.max_cover_downloads):
            self._download_cover()


PATH_PATTERNS = [('Album Artist, Album Title', '%aa/%at'),
                 #("Album Artist (sortable), Album Title", "%as/%at"),
                 #("Track Artist, Album Title", "%ta/%at"),
                 #("Track Artist (sortable), Album Title", "%ts/%at"),
                 ("Album Title", "%at"),
                 ("Album Artist", "%aa"),
                 #("Album Artist (sortable)", "%as"),
                 ("Album Artist - Album Title", "%aa - %at"),
                 #("Album Artist (sortable) - Album Title", "%as - %at"),
                 ("[none]", ""),
                ]

FILE_PATTERNS = [("Number - Title", "%tN - %tt"),
                 ("Track Title", "%tt"),
                 ("Track Artist - Track Title", "%ta - %tt"),
                 #("Track Artist (sortable) - Track Title", "%ts - %tt"),
                 ("Number. Track Artist - Track Title", "%tN. %ta - %tt"),
                 ("Number-Track Artist-Track Title (lowercase)", "%tN-%tA-%tT"),
                ]

class PreferencesDialog(object):

    path_pattern = gconf_property(GCONF_KEY+'/path_pattern')
    file_pattern = gconf_property(GCONF_KEY+'/file_pattern')
    strip_special = gconf_property(GCONF_KEY+'/strip_special')
    label_prefs = [path_pattern, file_pattern, strip_special]

    def __init__(self, parent):
        ui = gtk.glade.XML(GLADE_FILE, 'prefs_dialog')
        dialog = ui.get_widget('prefs_dialog')
        dialog.connect('hide', self.on_dialog_hide)
        dialog.connect('response', self.on_response)

        path_chooser = ui.get_widget('path_chooser')
        bind_file_chooser(path_chooser, GCONF_KEY+'/base_uri')

        path_option = ui.get_widget('path_option')
        bind_combo_box(path_option, GCONF_KEY+'/path_pattern', PATH_PATTERNS)

        file_option = ui.get_widget('file_option')
        bind_combo_box(file_option, GCONF_KEY+'/file_pattern', FILE_PATTERNS)

        strip_option = ui.get_widget('check_strip')
        bind_checkbox(strip_option, GCONF_KEY+'/strip_special')

        self.sample_track = Track(dict(artist='Islands',
                                       album='Return to the Sea',
                                       tracknum='4',
                                       title='Rough Gem'))
        self.path_example_label = ui.get_widget('path_example_label')
        self.update_example_label()

        for pref in PreferencesDialog.label_prefs:
            pref.add_callback(self.update_example_label)

        dialog.show()

    def on_response(self, dialog, response):
        if response == gtk.RESPONSE_HELP:
            pass # TODO
        else:
            dialog.hide()

    def on_dialog_hide(self, dialog):
        dialog.destroy()
        for pref in PreferencesDialog.label_prefs:
            pref.remove_callback(self.update_example_label)

    def update_example_label(self, *args):
        pathname = self.sample_track.fill_pattern(self.path_pattern,
                                                  self.strip_special)
        filename = self.sample_track.fill_pattern(self.file_pattern,
                                                  self.strip_special)
        label = '<small><i><b>Example:</b> /%s/%s.mp3</i></small>' \
                % (pathname, filename)
        self.path_example_label.set_markup(label)


def gtk_model_iter(tree):
    iter_ = tree.get_iter_first()
    while iter_ is not None:
        yield iter_
        iter_ = tree.iter_next(iter_)


class Track(object):
    def __init__(self, tags):
        self.tags = dict([(k.encode('utf8'),v.encode('utf8'))
                          for k,v in tags.iteritems()])
        self.downloader = None
        self.status = 'new'
        self.patterns = {'%aa': self.tags['artist'],
                         '%aA': self.tags['artist'].lower(),
                         '%at': self.tags['album'],
                         '%aT': self.tags['album'].lower(),
                         '%tn': self.tags['tracknum'],
                         '%tN': self.tags['tracknum'].zfill(2),
                         '%ta': self.tags['artist'],
                         '%tA': self.tags['artist'].lower(),
                         '%tt': self.tags['title'],
                         '%tT': self.tags['title'].lower(),
                        }
        if 'albumart' in self.tags:
            self.cover_image = CoverImage(self.tags['albumart'])

    def start(self, downloader):
        self.downloader = downloader
        self.status = 'started'

    def completed(self):
        self.status = 'completed'

    def abort(self):
        self.status = 'aborted'
        if self.downloader:
            self.downloader.abort()

    def error(self, failure):
        self.status = 'error'

    def sanitize(self, string, strip_chars):
        while string.startswith('.'):
            string = string[1:]
        string = string.replace('/', '-')
        if strip_chars:
            import re
            string = re.sub(r'[\\:|]', '-', string)
            string = re.sub(r'[*?&!\'"$()`{}]', ' ', string)
            string = re.sub(r'\s', '_', string)
        return string

    def fill_pattern(self, pattern, strip_chars):
        pattern = pattern.split('/')
        for k,v in self.patterns.iteritems():
            pattern = [p.replace(k, v) for p in pattern]
        return '/'.join([self.sanitize(p, strip_chars) for p in pattern])


# TODO check that images are garbage collected when not used
class CoverImage(object):
    icon_size = 66
    _loading_icon = None
    _missing_icon = None
    _cache = weakref.WeakValueDictionary()

    def __new__(cls, url):
        try:
            return cls._cache[url]
        except KeyError:
            pass
        new_obj = object.__new__(cls, url)
        cls._cache[url] = new_obj
        return new_obj
 
    @classmethod
    def _get_icon(cls, name):
        icon_theme = gtk.icon_theme_get_default()
        loading_icon = icon_theme.lookup_icon(name, cls.icon_size,
                                              gtk.ICON_LOOKUP_FORCE_SVG)
        return loading_icon.load_icon()

    @classmethod
    def loading_icon(cls):
        if cls._loading_icon is None:
            cls._loading_icon = cls._get_icon('gnome-fs-loading-icon')
        return cls._loading_icon

    @classmethod
    def missing_icon(cls):
        if cls._missing_icon is None:
            cls._missing_icon = cls._get_icon('gtk-missing-image')
        return cls._missing_icon

    def __init__(self, url):
        self.url = url
        self.pixbuf = None
        self.attachment = None

    @property
    def is_loaded(self):
        return self.pixbuf is not None

    def get_dest_file(self):
        """Returns a file-like object to write the image data to"""
        self.loader = gtk.gdk.PixbufLoader()
        self.loader.set_size(CoverImage.icon_size, CoverImage.icon_size)
        self.loader.connect('closed', self._load_complete)
        return self.loader

    def _load_complete(self, loader):
        """Callback for `PixbufLoader` when the image has finished loading"""
        self.pixbuf = loader.get_pixbuf()
        if self.attachment:
            self.attachment.set_from_pixbuf(self.pixbuf)

    def error_loading(self, failure):
        try:
            self.loader.close()
        except:
            pass
        del self.loader

        self.pixbuf = CoverImage.missing_icon()
        if self.attachment:
            self.attachment.set_from_pixbuf(self.pixbuf)

    def attach(self, image_widget):
        """Associates this object with an image widget.  If the cover data has
        not completed loading the image will be set to a "loading" icon.  Once
        the cover data is available the image will be set to display the cover.
        """
        self.attachment = image_widget
        self.attachment.set_from_pixbuf(self.pixbuf
                                        or CoverImage.loading_icon())

    def detach(self):
        self.attachment = None


if __name__ == '__main__':
    try:
        try:
            import guniqueapp
        except ImportError:
            app = None
        else:
            app = guniqueapp.get_app('germanium')
        if app and app.is_running():
            files = [os.path.abspath(f) for f in sys.argv[1:]]
            app.custom_message('\v'.join(files))
            gtk.gdk.notify_startup_complete()
            sys.exit(1)

        germanium = Germanium()
        if app:
            def message_callback(app, flags, message, *args):
                germanium.load_files(message.split('\v'))
            app.connect('message', message_callback)
        germanium.load_files(sys.argv[1:])

        reactor.run()
    except (KeyboardInterrupt, SystemExit):
        pass
