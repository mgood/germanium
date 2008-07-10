resourcesdir = $(pkgdatadir)
resources_DATA = germanium.glade

applicationsdir = $(datadir)/application-registry
applications_DATA = germanium.applications

desktopdir = $(datadir)/applications
desktop_DATA = germanium.desktop

mimedir = $(datadir)/mime/packages
mime_DATA = emusic.xml

schemadir = $(GCONF_SCHEMA_FILE_DIR)
schema_DATA = germanium.schemas

install-data-hook:
if HAVE_FDO_MIME
	$(UPDATE_MIME_DATABASE) "$(datadir)/mime"
endif

if HAVE_FDO_DESKTOP
	$(UPDATE_DESKTOP_DATABASE)
endif

germaniumbindir = $(libdir)/germanium

# ******************************************************************************
# Build rules
# ******************************************************************************
if GCONF_SCHEMAS_INSTALL
install-data-local: install-schemas
install-schemas:
	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
		$(GCONFTOOL) --makefile-install-rule `for schema in $(schema_DATA); do \
		if test -f "$$schema"; then dir=""; \
		elif test -f "$(srcdir)/$$schema"; then dir="$(srcdir)/"; \
		else dir=""; fi; \
		echo "$${dir}$${schema}"; done`
endif

#DISTCLEANFILES = \
#	$(schema_DATA)

EXTRA_DIST = \
	$(resources_DATA) \
	$(applications_DATA) \
	$(desktop_DATA) \
	$(mime_DATA) \
	$(schema_DATA)
	
	
