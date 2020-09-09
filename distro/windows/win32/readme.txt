-----------------------------------------------------------------------
OpenSSL v1.1.1g Win32 for ICS, http://www.overbyte.be
-----------------------------------------------------------------------

Only supports Windows Vista/Server 2008, and later, not Windows XP.

The OpenSSL DLLs and EXE files are digitally code signed 'Open Source
Developer, François PIETTE', the lead developer for ICS.  ICS V8.38 and
later check the DLLs are correctly signed when opening them.  Beware
that Windows needs recent root certificates to check newly signed code,
and may give an error if the root store has not been kept current by
Windows Update, particularly on older versions of Windows such as Vista,
7 and Windows 2008.

Built with:
                  Visual Studio Build Tools 2017
                  The Netwide Assembler (NASM) v2.14.02
                  Strawberry Perl v5.20.3.1

Build Commands:
                  perl configure VC-WIN32-rtt
                  nmake

Custom configuration file (.conf file at the "Configurations" folder):

## -*- mode: perl; -*-
## Personal configuration targets

%targets = (
    "VC-WIN32-rtt" => {
        inherit_from     => [ "VC-WIN32" ],
        cflags           => sub{my $v=pop; $v=~ s/\/MD/\/MT/ig; return $v},
        lflags           => "/nologo /release",
    },
    "VC-WIN64A-rtt" => {
        inherit_from     => [ "VC-WIN64A" ],
        cflags           => sub{my $v=pop; $v=~ s/\/MD/\/MT/ig; return $v},
        lflags           => "/nologo /release",
    },
);
