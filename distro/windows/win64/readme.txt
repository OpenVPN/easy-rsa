-----------------------------------------------------------------------
OpenSSL v1.1.0j Win64 for ICS, http://www.overbyte.be
-----------------------------------------------------------------------

Built with:
                  Visual Studio Build Tools 2017
                  The Netwide Assembler (NASM) v2.11.05
                  Strawberry Perl v5.20.3.1

Build Commands:
                  perl configure VC-WIN64A-rtt
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