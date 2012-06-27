#
#  Easy-RSA -- This is a small RSA key management package, based on the openssl
#              command line tool, that can be found in the easy-rsa subdirectory
#              of the OpenVPN distribution.  While this tool is primary concerned
#              with key management for the SSL VPN application space, it can also
#              be used for building web certificates.
#
#  Copyright (C) 2002-2010 OpenVPN Technologies, Inc. <sales@openvpn.net>
#  Copyright (C) 2006-2012 Alon Bar-Lev <alon.barlev@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License version 2
#  as published by the Free Software Foundation.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program (see the file COPYING included with this
#  distribution); if not, write to the Free Software Foundation, Inc.,
#  59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

dnl Process this file with autoconf to produce a configure script.

AC_PREREQ(2.59)

AC_INIT([easy-rsa], [2.2.0_master], [openvpn-users@lists.sourceforge.net])

AC_CONFIG_SRCDIR([./easy-rsa/2.0/build-key-pass])
AM_INIT_AUTOMAKE

AC_PROG_INSTALL
AC_PROG_LN_S
AC_PROG_MAKE_SET

AC_ARG_WITH(
	[easyrsadir],
	[AS_HELP_STRING([--with-easyrsadir], [specify easyrsadir @<:@default=DATADIR/easy-rsa@:>@])],
	[easyrsadir="${withval}"],
	[easyrsadir="\$(datadir)/easy-rsa"]
)

AC_SUBST([easyrsadir])

AC_CONFIG_FILES([
	Makefile
	doc/Makefile
	distro/Makefile
	distro/rpm/Makefile
	distro/rpm/easy-rsa.spec
])
AC_OUTPUT
