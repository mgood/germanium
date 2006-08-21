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
    sys.exit(1)

import errno
import os.path
import time
from threading import Thread
from Queue import Queue, Empty

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.progress import BaseMeter

from emusic.decrypt import get_tracks

TITLE_COLUMN = 0
PROGRESS_COLUMN = 1
ICON_COLUMN = 2
OBJECT_COLUMN = 3

icons = {
    "new": gtk.STOCK_NEW,
    "started": gtk.STOCK_MEDIA_PLAY,
    "paused": gtk.STOCK_MEDIA_PAUSE,
    "aborted": gtk.STOCK_STOP,
    "completed": gtk.STOCK_APPLY,
}


class EmusicDownloader(object):

    max_threads = 4

    def __init__(self, files=[]):
        self.ui = gtk.glade.XML('emusic-gtk.glade', 'main-window')
        signals = ['on_open_button_clicked',
                   'on_resume_button_clicked',
                   'on_pause_button_clicked',
                   'on_stop_button_clicked',
                  ]
        handlers = dict([(s,getattr(self, s)) for s in signals])
        handlers['on_main_window_destroy'] = self.quit
        self.ui.signal_autoconnect(handlers)
        self.view = self['download-view']

        self.model = gtk.ListStore(str, int, str, object)
        self.view.set_model(self.model)

        column = gtk.TreeViewColumn('State', gtk.CellRendererPixbuf(),
                                    stock_id = ICON_COLUMN)
        self.view.append_column(column)

        column = gtk.TreeViewColumn('Title', gtk.CellRendererText(), 
                                    text=TITLE_COLUMN)
        column.set_min_width(275)
        self.view.append_column(column)

        column = gtk.TreeViewColumn('Progress Status',
                                    gtk.CellRendererProgress(), 
                                    text=PROGRESS_COLUMN,
                                    value=PROGRESS_COLUMN)
        column.set_min_width(50)
        self.view.append_column(column)
        self.view.get_selection().connect('changed', self.on_download_view_selection_changed)

        # TODO the .emp file contains the server info in the XML
        self.urlgrabber = URLGrabber(prefix='http://dl.emusic.com/dl/')
        self.track_queue = Queue(0)
        self.threads = [DownloadThread(self.track_queue, self.view, self.model,
                                       self.urlgrabber)
                        for _ in xrange(self.max_threads)]
        #self.threads = []
        for thread in self.threads:
            thread.start()

        for filename in files:
            for track in get_tracks(filename):
                self.add_track(track)

    def __getitem__(self, name):
        return self.ui.get_widget(name)

    def add_track(self, info):
        row = self.model.append(['%(artist)s %(title)s' % info, 0, icons['new'], info])
        self.track_queue.put((row, info))

    def quit(self, widget):
        for thread in self.threads:
            # TODO should also halt the current download
            # and need to unblock the Queue access
            thread.active = False
        gtk.main_quit()

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

    def on_resume_button_clicked(self, button):
        pass

    def on_pause_button_clicked(self, button):
        pass

    def on_stop_button_clicked(self, button):
        pass

    def on_download_view_selection_changed(self, selection):
        pass


class EmusicProgressMeter(BaseMeter):
    def __init__(self, thread, view, model, row):
        BaseMeter.__init__(self)
        self.thread = thread
        self.view = view
        self.model = model
        self.row = row

    def _do_start(self, now=None):
        self.model.set_value(self.row, ICON_COLUMN, icons['started'])

    def _do_update(self, amount_read, now=None):
        if not self.thread.active:
            raise URLGrabError(15, 'quitting')
        self.model.set_value(self.row, PROGRESS_COLUMN, 100*self.re.fraction_read())
        self.view.queue_draw()

    def _do_end(self, amount_read, now=None):
        self.model.set_value(self.row, PROGRESS_COLUMN, 100)
        self.model.set_value(self.row, ICON_COLUMN, icons['completed'])


class DownloadThread(Thread):
    def __init__(self, track_queue, view, model, urlgrabber):
        Thread.__init__(self)
        self.track_queue = track_queue
        self.view = view
        self.model = model
        self.urlgrabber = urlgrabber
        self.active = True
        self.setDaemon(True)

    def run(self):
        while self.active:
            row, track_info = self.track_queue.get()
            url = '%(trackid)s/%(filename)s' % track_info
            pattern = '/home/matt/Music/%(artist)s/%(album)s/%(tracknum)s-%(title)s%(format)s'
            filename = pattern % track_info
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError, e:
                if e.errno != errno.EEXIST:
                    raise
            meter = EmusicProgressMeter(self, self.view, self.model, row)
            try:
                self.urlgrabber.urlgrab(url, filename, progress_obj=meter)
            except URLGrabError, e:
                if e.errno != 15: # user error
                    pass # TODO need to display some error information


if __name__ == '__main__':
    try:
        emusic = EmusicDownloader(sys.argv[1:])
        gtk.threads_init()
        gtk.main()
    except (KeyboardInterrupt, SystemExit):
        pass
