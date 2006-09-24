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

from cStringIO import StringIO

import gnomevfs

def open_for_write(filename, mode=0666):
    try:
        return gnomevfs.create(filename, gnomevfs.OPEN_WRITE, mode)
    except gnomevfs.FileExistsError:
        return gnomevfs.Handle(filename, gnomevfs.OPEN_WRITE)

class HandleWrapper(gnomevfs.Handle):
    def read(self, size=-1):
        if size == -1:
            buff = StringIO()
            try:
                while True:
                    buff.write(gnomevfs.Handle.read(self, 512))
            except gnomevfs.EOFError:
                pass
            return buff.getvalue()
        return gnomevfs.Handle.read(self, size)

# Copyright 2005-2006 Gautier Portet
def vfs_makedirs(uri, mode=0777):
    """Similar to os.makedirs, but with gnomevfs"""

    if isinstance(uri, basestring):
        uri = gnomevfs.URI(uri)
    path = uri.path

    # start at root
    uri =  uri.resolve_relative("/")
    
    for folder in path.split("/"):
        if not folder:
            continue
        uri = uri.append_string(folder)
        try:
            gnomevfs.make_directory(uri, mode)
        except gnomevfs.FileExistsError:
            pass
