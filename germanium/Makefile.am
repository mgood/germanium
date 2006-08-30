germanium: germanium.py
	sed -e "s|\@PYTHONDIR\@|$(libdir)/germanium|" $< > $@

germaniumbindir = $(bindir)
germaniumbin_SCRIPTS = germanium

germaniumdir = $(libdir)/germanium
germanium_PYTHON = \
	defs.py \
	emp.py \
	gconf_util.py \
	__init__.py \
	progress.py \
	vfs_util.py
	
BUILT_SOURCES = \
	germanium
	
CLEANFILES = \
	$(BUILT_SOURCES)
	
DISTCLEANFILES = \
	defs.py \
	$(CLEANFILES)
	
EXTRA_DIST = \
	defs.py.in \
	germanium.py
