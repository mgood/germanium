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

from twisted.internet import gtk2reactor
gtk2reactor.install()
from twisted.internet import reactor

import errno
import os.path
import time
from threading import Thread
from Queue import Queue, Empty

from urlgrabber.grabber import URLGrabber, URLGrabError
from urlgrabber.progress import BaseMeter

from twisted.web import client

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
    "error": gtk.STOCK_STOP, # FIXME
}


class EmusicDownloader(object):

    max_downloads = 2

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
                                    stock_id=ICON_COLUMN)
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

        self.active_downloads = set()

        # TODO the .emp file contains the server info in the XML
        for filename in files:
            for track in get_tracks(filename):
                self.add_track(track)

    def __getitem__(self, name):
        return self.ui.get_widget(name)

    def add_track(self, info):
        row = self.model.append(['%(artist)s - %(title)s' % info, 0, icons['new'], info])
        if len(self.active_downloads) < self.max_downloads:
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

    def on_resume_button_clicked(self, button):
        pass

    def on_pause_button_clicked(self, button):
        pass

    def on_stop_button_clicked(self, button):
        pass

    def on_download_view_selection_changed(self, selection):
        pass

    def _download(self, row):
        self.active_downloads.add(row)

        def started():
            self.model.set_value(row, ICON_COLUMN, icons['started'])
        def progress(fraction):
            # TODO only update the progress periodically
            self.model.set_value(row, PROGRESS_COLUMN, 100*fraction)
        def complete(result):
            self.model.set_value(row, PROGRESS_COLUMN, 100)
            self.model.set_value(row, ICON_COLUMN, icons['completed'])
            self._download_done(row)
        def error(failure):
            # failure.getErrorMessage()
            self.model.set_value(row, ICON_COLUMN, icons['error'])
            self._download_done(row)

        track_info = self.model.get_value(row, OBJECT_COLUMN)
        url = str('http://dl.emusic.com/dl/%(trackid)s/%(filename)s' % track_info)
        pattern = '/home/matt/Music/%(artist)s/%(album)s/%(tracknum)s-%(title)s%(format)s'
        filename = str(pattern % track_info)

        scheme,host,port,path = client._parse(url)
        factory = ProgressDownloader(url, filename, started, progress)
        reactor.connectTCP(host, port, factory)
        factory.deferred.addCallback(complete).addErrback(error)

    def _download_done(self, row):
        return
        self.active_downloads.remove(row)
        for sibling in row:
            if len(self.active_downloads) >= self.active_downloads:
                break
            if sibling not in self.active_downloads:
                self._download(sibling)


class ProgressDownloader(client.HTTPDownloader):
    def __init__(self, url, file, started_callback, progress_callback,
                 granularity=0.3):
        client.HTTPDownloader.__init__(self, url, file)
        self.started_callback = started_callback
        self.progress_callback = progress_callback
        self.granularity = granularity
        self.next_update = None
        self.re = RateEstimator()

    def gotHeaders(self, headers):
        if self.status == '200':
            self.total_length = int(headers.get('content-length', [0])[0])
            self.re.start(self.total_length)
            self.current_length = 0.0
        return client.HTTPDownloader.gotHeaders(self, headers)

    def pageStart(self, data):
        self.started_callback()
        return client.HTTPDownloader.pageStart(self, data)

    def pagePart(self, data):
        if self.status == '200':
            self.current_length += len(data)
            if self.total_length:
                now = time.time()
                if not self.next_update or now >= self.next_update:
                    self.re.update(len(data), now)
                    self.next_update = now + self.granularity
                    self.progress_callback(self.current_length / self.total_length)
        return client.HTTPDownloader.pagePart(self, data)


class RateEstimator:
    def __init__(self, timescale=5.0):
        self.timescale = timescale

    def start(self, total=None, now=None):
        if now is None: now = time.time()
        self.total = total
        self.start_time = now
        self.last_update_time = now
        self.last_amount_read = 0
        self.ave_rate = None
        
    def update(self, amount_read, now=None):
        if now is None: now = time.time()
        if amount_read == 0:
            # if we just started this file, all bets are off
            self.last_update_time = now
            self.last_amount_read = 0
            self.ave_rate = None
            return

        #print 'times', now, self.last_update_time
        time_diff = now         - self.last_update_time
        read_diff = amount_read - self.last_amount_read
        self.last_update_time = now
        self.last_amount_read = amount_read
        self.ave_rate = self._temporal_rolling_ave(\
            time_diff, read_diff, self.ave_rate, self.timescale)
        #print 'results', time_diff, read_diff, self.ave_rate
        
    #####################################################################
    # result methods
    def average_rate(self):
        "get the average transfer rate (in bytes/second)"
        return self.ave_rate

    def elapsed_time(self):
        "the time between the start of the transfer and the most recent update"
        return self.last_update_time - self.start_time

    def remaining_time(self):
        "estimated time remaining"
        if not self.ave_rate or not self.total: return None
        return (self.total - self.last_amount_read) / self.ave_rate

    def fraction_read(self):
        """the fraction of the data that has been read
        (can be None for unknown transfer size)"""
        if self.total is None: return None
        elif self.total == 0: return 1.0
        else: return float(self.last_amount_read)/self.total

    #########################################################################
    # support methods
    def _temporal_rolling_ave(self, time_diff, read_diff, last_ave, timescale):
        """a temporal rolling average performs smooth averaging even when
        updates come at irregular intervals.  This is performed by scaling
        the "epsilon" according to the time since the last update.
        Specifically, epsilon = time_diff / timescale

        As a general rule, the average will take on a completely new value
        after 'timescale' seconds."""
        epsilon = time_diff / timescale
        if epsilon > 1: epsilon = 1.0
        return self._rolling_ave(time_diff, read_diff, last_ave, epsilon)
    
    def _rolling_ave(self, time_diff, read_diff, last_ave, epsilon):
        """perform a "rolling average" iteration
        a rolling average "folds" new data into an existing average with
        some weight, epsilon.  epsilon must be between 0.0 and 1.0 (inclusive)
        a value of 0.0 means only the old value (initial value) counts,
        and a value of 1.0 means only the newest value is considered."""
        
        try:
            recent_rate = read_diff / time_diff
        except ZeroDivisionError:
            recent_rate = None
        if last_ave is None: return recent_rate
        elif recent_rate is None: return last_ave

        # at this point, both last_ave and recent_rate are numbers
        return epsilon * recent_rate  +  (1 - epsilon) * last_ave

    def _round_remaining_time(self, rt, start_time=15.0):
        """round the remaining time, depending on its size
        If rt is between n*start_time and (n+1)*start_time round downward
        to the nearest multiple of n (for any counting number n).
        If rt < start_time, round down to the nearest 1.
        For example (for start_time = 15.0):
         2.7  -> 2.0
         25.2 -> 25.0
         26.4 -> 26.0
         35.3 -> 34.0
         63.6 -> 60.0
        """

        if rt < 0: return 0.0
        shift = int(math.log(rt/start_time)/math.log(2))
        rt = int(rt)
        if shift <= 0: return rt
        return float(int(rt) >> shift << shift)


if __name__ == '__main__':
    try:
        emusic = EmusicDownloader(sys.argv[1:])
        reactor.run()
    except (KeyboardInterrupt, SystemExit):
        pass
