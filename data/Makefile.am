# ******************************************************************************
# GConf Schemas
# ******************************************************************************
# GConf Preference Schemas
#schemadir = $(GCONF_SCHEMA_FILE_DIR)
#schema_in_files = emusic-gnome.schemas.in
#schema_DATA = $(schema_in_files:.schemas.in=.schemas)

# ******************************************************************************
# Misc data
# ******************************************************************************
resourcesdir = $(pkgdatadir)
resources_DATA = emusic-gnome.glade

desktopdir = $(datadir)/applications
desktop_DATA = emusic-gnome.desktop

mimedir = $(datadir)/mime/packages
mime_DATA = emusic.xml

install-data-hook:
if HAVE_FDO_MIME
	$(UPDATE_MIME_DATABASE) "$(datadir)/mime"
endif

if HAVE_FDO_DESKTOP
	$(UPDATE_DESKTOP_DATABASE)
endif

emusicbindir = $(libdir)/emusic-gnome

# ******************************************************************************
# Build rules
# ******************************************************************************
#if GCONF_SCHEMAS_INSTALL
#install-data-local: install-schemas
#install-schemas:
#	GCONF_CONFIG_SOURCE=$(GCONF_SCHEMA_CONFIG_SOURCE) \
#		$(GCONFTOOL) --makefile-install-rule $(schema_DATA)
#endif

#DISTCLEANFILES = \
#	$(schema_DATA)

EXTRA_DIST = \
	$(resources_DATA) \
	$(deskbar_PYTHON) \
	$(mime_DATA)
#	$(schema_in_files)
	
	
