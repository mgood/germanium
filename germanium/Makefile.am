germanium: germanium.py
	sed -e "s|\@PYTHONDIR\@|$(datadir)/germanium|" \
	    -e "s|\@PYTHON\@|$(PYTHON)|" $< > $@
	chmod +x $@

germaniumbindir = $(bindir)
germaniumbin_SCRIPTS = germanium

germaniumdir = $(datadir)/germanium
nodist_germanium_PYTHON = \
	defs.py
germanium_PYTHON = \
	emp.py \
	gconf_util.py \
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
	__init__.py \
	germanium.py
