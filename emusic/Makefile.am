emusic-gnome: emusic-gnome.py
	sed -e "s|\@PYTHONDIR\@|$(libdir)/emusic-gnome|" $< > $@

emusicbindir = $(bindir)
emusicbin_SCRIPTS = emusic-gnome

emusicdir = $(libdir)/emusic-gnome
emusic_PYTHON = \
	defs.py \
	emp.py \
	gconf_util.py \
	__init__.py \
	progress.py \
	vfs_util.py
	
BUILT_SOURCES = \
	emusic-gnome
	
CLEANFILES = \
	$(BUILT_SOURCES)
	
DISTCLEANFILES = \
	defs.py \
	$(CLEANFILES)
	
EXTRA_DIST = \
	defs.py.in \
	emusic-gnome.py
