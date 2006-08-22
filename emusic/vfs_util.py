import gnomevfs

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

def open_for_write(filename, mode=0666):
    try:
        return gnomevfs.create(filename, gnomevfs.OPEN_WRITE, mode)
    except gnomevfs.FileExistsError:
        return gnomevfs.Handle(filename, gnomevfs.OPEN_WRITE)
