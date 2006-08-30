AC_INIT(germanium, 0.2.0, matt@matt-good.net)
AC_CONFIG_SRCDIR(germanium/__init__.py)
AC_CONFIG_MACRO_DIR([m4])

AM_INIT_AUTOMAKE
GNOME_COMMON_INIT

AM_MAINTAINER_MODE
AM_DISABLE_STATIC
AM_PROG_LIBTOOL
AC_SUBST(ACLOCAL_AMFLAGS, "$ACLOCAL_FLAGS -I m4")
AC_PROG_CC
AC_PROG_INSTALL

dnl ****************************************************************************
dnl * Pkg-Config
dnl ****************************************************************************
AC_CHECK_PROG(HAVE_PKGCONFIG, pkg-config, yes, no)
if test "x$HAVE_PKGCONFIG" = "xno"; then
  AC_MSG_ERROR(you need to have pkgconfig installed !)
fi

dnl ****************************************************************************
dnl * Translation & i18n
dnl ****************************************************************************
dnl ALL_LINGUAS="bg ca cs cy da de dz el en_CA en_GB es et fi fr gl gu he hi hu id it ja ka ko ku lt mk nb ne nl pa pl pt pt_BR ru sk sq sr sr@Latn sv th vi uk zh_CN zh_HK zh_TW"

dnl GETTEXT_PACKAGE="deskbar-applet"
dnl AC_PROG_INTLTOOL([0.33])
dnl AC_SUBST(GETTEXT_PACKAGE)
dnl AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [The gettext package])
dnl AM_GLIB_GNU_GETTEXT

dnl ****************************************************************************
dnl * GConf support
dnl ****************************************************************************
AC_PATH_PROG(GCONFTOOL, gconftool-2)
AM_GCONF_SOURCE_2

dnl ****************************************************************************
dnl * Python 2.3
dnl ****************************************************************************
AM_PATH_PYTHON(2.3)
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

dnl ****************************************************************************
dnl * Write the values of various paths in defs.py
dnl ****************************************************************************
AC_SUBST(VERSION)
AC_SUBST(PACKAGE)

AS_AC_EXPAND(DATADIR, $datadir)
AC_SUBST(DATADIR)

AS_AC_EXPAND(LIBDIR, $libdir)
AC_SUBST(LIBDIR)

AS_AC_EXPAND(PYTHONDIR, $pythondir)
AC_SUBST(PYTHONDIR)
		
PKG_CHECK_MODULES(EMUSIC_GNOME,
	gtk+-2.0				>= 2.6
	pygtk-2.0				>= 2.6
	pygobject-2.0			>= 2.6
)

AC_PATH_PROG(UPDATE_DESKTOP_DATABASE, update-desktop-database, no)
AC_PATH_PROG(UPDATE_MIME_DATABASE, update-mime-database, no)

AC_ARG_ENABLE(desktop-update, [AC_HELP_STRING(--disable-desktop-update, Disable the MIME desktop database update)], disable_desktop=yes, disable_desktop=no)
AC_ARG_ENABLE(mime-update, [AC_HELP_STRING(--disable-mime-update, Disable the MIME database update)], disable_mime=yes, disable_mime=no)

AM_CONDITIONAL(HAVE_FDO_DESKTOP, test "x$UPDATE_DESKTOP_DATABASE" != "xno" -a "x$disable_desktop" = "xno")
AM_CONDITIONAL(HAVE_FDO_MIME, test "x$UPDATE_MIME_DATABASE" != "xno" -a "x$disable_mime" = "xno")

AC_SUBST(EMUSIC_GNOME_CFLAGS)
AC_SUBST(EMUSIC_GNOME_LIBS)

AC_OUTPUT([
Makefile
germanium/Makefile
germanium/defs.py
data/Makefile
])

echo
echo $PACKAGE v$VERSION
echo

echo Prefix............... : $prefix

echo
echo "Now type make to compile"
echo "Then su to root and type: make install"
echo
