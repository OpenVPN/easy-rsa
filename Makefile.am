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

AUTOMAKE_OPTIONS = foreign 1.9

MAINTAINERCLEANFILES = \
	config.log config.status \
	$(srcdir)/Makefile.in \
	$(srcdir)/configure \
	$(srcdir)/missing $(srcdir)/install-sh \
	$(srcdir)/depcomp $(srcdir)/aclocal.m4 \
	$(srcdir)/config.guess $(srcdir)/config.sub

EXTRA_DIST = easy-rsa

SUBDIRS = doc distro

dist_doc_DATA = \
	COPYRIGHT.GPL \
	COPYING

dist_easyrsa_DATA =

install-data-local:	install-dist_easyrsaDATA
	cp "$(srcdir)/easy-rsa/2.0"/* "$(DESTDIR)$(easyrsadir)"

uninstall-local:
	-rm -fr "$(DESTDIR)$(easyrsadir)"
