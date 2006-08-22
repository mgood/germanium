#!/usr/bin/env python
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

from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor

import errno
import os.path
from threading import Thread
from urlparse import urlparse
from Queue import Queue, Empty

from emusic.emp import get_tracks
from emusic.progress import ProgressDownloader, format_time

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

GLADE_FILE = 'emusic-gtk.glade'

class EmusicDownloader(object):

    max_downloads = 2

    def __init__(self, files=[]):
        self.ui = gtk.glade.XML(GLADE_FILE, 'main_window')
        signals = ['on_open_button_clicked',
                   'on_start_button_clicked',
                   'on_stop_button_clicked',
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

        column = gtk.TreeViewColumn('Title', gtk.CellRendererText(), 
                                    text=TITLE_COLUMN)
        column.set_min_width(275)
        self.view.append_column(column)

        column = gtk.TreeViewColumn('Progress Status',
                                    gtk.CellRendererProgress(), 
                                    text=PROGRESS_TIME_COLUMN,
                                    value=PROGRESS_COLUMN)
        column.set_min_width(50)
        self.view.append_column(column)
        self.view.get_selection().connect('changed', self.on_track_selection_changed)

        self.selected_row = None

        self.active_downloads = 0

        # TODO the .emp file contains the server info in the XML
        for filename in files:
            for track in get_tracks(filename):
                self.add_track(track)

    def __getitem__(self, name):
        return self.ui.get_widget(name)

    def add_track(self, info):
        row = self.model.append(['%(artist)s - %(title)s' % info, 0, '',
                                 None, Track(info)])
        if self.active_downloads < self.max_downloads:
            self._download(row)

    def quit(self, widget):
        #gtk.main_quit()
        reactor.stop()

    def on_open_button_clicked(self, button):
        file_open = gtk.FileChooserDialog(title='Open EMP file',
                                          action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                          buttons=(gtk.STOCK_CANCEL,
                                                   gtk.RESPONSE_CANCEL,
                                                   gtk.STOCK_OPEN,
                                                   gtk.RESPONSE_OK))
        filter = gtk.FileFilter()
        filter.set_name('eMusic download file')
        filter.add_pattern('*.emp')
        file_open.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name('All files')
        filter.add_pattern('*')
        file_open.add_filter(filter)

        filename = None
        if file_open.run() == gtk.RESPONSE_OK:
            filename = file_open.get_filename()

        file_open.destroy()

        # TODO should use GnomeVFS in case file is not on local FS
        if filename is not None:
            for track in get_tracks(filename):
                self.add_track(track)

    def on_track_selection_changed(self, selection):
        model, row = selection.get_selected()
        self.selected_row = row

    def on_start_button_clicked(self, button):
        if self.selected_row is None:
            return
        track = self.model.get_value(self.selected_row, OBJECT_COLUMN)
        if track.status == 'started':
            return
        self._download(self.selected_row)

    def on_stop_button_clicked(self, button):
        if self.selected_row is None:
            return
        track = self.model.get_value(self.selected_row, OBJECT_COLUMN)
        if track.status not in ('new', 'started'):
            return
        track.abort()
        self.model.set_value(self.selected_row, ICON_COLUMN, icons['aborted'])
        self.model.set_value(self.selected_row, PROGRESS_TIME_COLUMN, '')
        self.model.set_value(self.selected_row, PROGRESS_COLUMN, 0)

    def _download(self, row):
        self.active_downloads += 1
        track = self.model.get_value(row, OBJECT_COLUMN)

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
        pattern = '/home/matt/Music/%(artist)s/%(album)s/%(tracknum)s-%(title)s%(format)s'
        filename = str(pattern % track.tags)

        try:
            os.makedirs(os.path.dirname(filename))
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

        scheme,host,path,_,_,_ = urlparse(url)
        factory = ProgressDownloader(url, filename, started, progress)
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
            track = self.model.get_value(row, OBJECT_COLUMN)
            if track.status == 'new':
                self._download(row)


def gtk_model_iter(tree):
    iter_ = tree.get_iter_first()
    while iter_ is not None:
        yield iter_
        iter_ = tree.iter_next(iter_)


class Track(object):
    def __init__(self, tags):
        self.tags = tags
        self.downloader = None
        self.status = 'new'

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


if __name__ == '__main__':
    try:
        emusic = EmusicDownloader(sys.argv[1:])
        reactor.run()
    except (KeyboardInterrupt, SystemExit):
        pass
