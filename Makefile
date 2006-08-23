PACKAGE=emusic-gnome
VERSION=0.1.1

DEST=$(PACKAGE)-$(VERSION)

prefix = /usr/local
bindir = $(prefix)/bin
sharedir = $(prefix)/share
resourcedir = $(sharedir)/emusic-gnome

install:
	install -d $(DESTDIR)$(bindir) $(DESTDIR)$(resourcedir)/emusic $(DESTDIR)$(sharedir)/applications
	install -m 0644 emusic-gnome.glade $(DESTDIR)$(resourcedir)
	install -m 0644 emusic-gnome.desktop $(DESTDIR)$(sharedir)/applications
	install -m 0644 emusic/*.py $(DESTDIR)$(resourcedir)/emusic
	sed 's,^RESOURCE_DIR *=.*,RESOURCE_DIR = "$(resourcedir)",' \
	emusic-gnome > make-install-temp
	install make-install-temp $(DESTDIR)$(bindir)/emusic-gnome
	rm make-install-temp

dist:
	mkdir -p $(DEST)
	cp -a AUTHORS COPYING README emusic-gnome emusic-gnome.glade emusic-gnome.gladep emusic-gnome.desktop Makefile ChangeLog $(DEST)
	mkdir -p $(DEST)/emusic
	cp -a emusic/*.py $(DEST)/emusic
	tar czf $(DEST).tar.gz $(DEST)
	rm -rf $(DEST)

