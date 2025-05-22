[![CI](https://github.com/Openvpn/easy-rsa/actions/workflows/action.yml/badge.svg)](https://github.com/Openvpn/easy-rsa/actions/workflows/action.yml)
# Overview

easy-rsa is a CLI utility to build and manage a PKI CA. In layman's terms,
this means to create a root certificate authority, and request and sign
certificates, including intermediate CAs and certificate revocation lists (CRL).

# Installation instructions

Easy-RSA's main program is a script, supported by a couple of config files. As such, there is no formal "installation" required. Preparing to use Easy-RSA is as simple as downloading the compressed package (.tar.gz for Linux/Unix or .zip for Windows) and extract it to a location of your choosing. There is no compiling or OS-dependent setup required.

You should install and run Easy-RSA as a non-root (non-Administrator) account as root access is not required.

## *nix like OS

1. **Download** the latest tarball from the [Releases page](https://github.com/OpenVPN/easy-rsa/releases):
```bash
wget https://github.com/OpenVPN/easy-rsa/releases/download/vX.X.X/EasyRSA-X.X.X.tgz
```
or
```bash
curl -LO https://github.com/OpenVPN/easy-rsa/releases/download/v.X.Y.Z/EasyRSA-X.Y.Z.tgz
```
2. **Extract** the archive and change into the directory:
```bash
$ tar xzf EasyRSA.tgz
$ cd EasyRSA
$ ls
easyrsa  openssl-easyrsa.cnf  vars.example  x509-types
# easyrsa is the binary, invoke the binary in the following way
$ ./easyrsa help

Easy-RSA 3 usage and overview

Usage: easyrsa [ OPTIONS.. ] <COMMAND> <TARGET> [ cmd-opts.. ]

To get detailed usage and help for a command, use:
  ./easyrsa help COMMAND

For a list of global-options, use:
  ./easyrsa help options

For a list of utility commands, use:
  ./easyrsa help util

A list of commands is shown below:
  init-pki [ cmd-opts ]
  self-sign-server <file_name_base> [ cmd-opts ]
...
...
```
Further more command line options and availability can be referred from [EasyRSA-Readme.md](https://github.com/OpenVPN/easy-rsa/blob/master/doc/EasyRSA-Readme.md#configuring-easy-rsa)

## Windows 

1. **Download** the latest ZIP from the [Releases page](https://github.com/OpenVPN/easy-rsa/releases).
```bash
Example: EasyRSA-X.X.X-win64 (must have -win64)
```
2. **Extract** to a folder, e.g., `C:\EasyRSA` (right-click → Extract All...).

Invoking Easy-RSA is done through your preferred shell. Under Windows, you will use the `EasyRSA Start.bat` program to provide a POSIX-shell environment suitable for using Easy-RSA.

After clicking on `EasyRSA-Start.bat` you will see something similar below

```bash
    Easy-RSA starting..

    Welcome to the EasyRSA 3 Shell for Windows.
    Easy-RSA 3 is available under a GNU GPLv2 license.

    Invoke 'easyrsa' to call the program. Without commands, help is displayed.

    Using directory: C:/Users/mp13/Downloads/EasyRSA-3.2.2-win64/EasyRSA-3.2.2

    EasyRSA Shell
    # easyrsa help

    Easy-RSA 3 usage and overview

    Usage: easyrsa [ OPTIONS.. ] <COMMAND> <TARGET> [ cmd-opts.. ]

    To get detailed usage and help for a command, use:
      ./easyrsa help COMMAND

    For a list of global-options, use:
      ./easyrsa help options

    For a list of utility commands, use:
      ./easyrsa help util

    A list of commands is shown below:
      init-pki [ cmd-opts ]
      self-sign-server <file_name_base> [ cmd-opts ]
    ...
```

Further more command line options and availability can be referred from [EasyRSA-Readme.md](https://github.com/OpenVPN/easy-rsa/blob/master/doc/EasyRSA-Readme.md#configuring-easy-rsa) & more information for windows can be found at [README-Windows.txt](https://github.com/OpenVPN/easy-rsa/blob/master/distro/windows/README-Windows.txt)

# Documentation

For 3.x project documentation and usage, see the [README.quickstart.md](README.quickstart.md) file or
the more detailed docs under the [doc/](doc/) directory. The .md files are in Markdown
format and can be converted to html files as desired for release packages, or
read as-is in plaintext.

# Getting help using easy-rsa

Currently, Easy-RSA development co-exists with OpenVPN even though they are
separate projects. The following resources are good places as of this writing to
seek help using Easy-RSA:

The [openvpn-users mailing list](https://lists.sourceforge.net/lists/listinfo/openvpn-users)
is a good place to post usage or help questions.

Users of GitHub can report problems to the Easy-RSA `issues` list.

# Branch structure

The easy-rsa master branch is currently tracking development for the 3.x release
cycle. Please note that, at any given time, master may be broken. Feel free to
create issues against master, but have patience when using the master branch. It
is recommended to use a release, and priority will be given to bugs identified in
the most recent release.

The prior 2.x and 1.x versions are available as release branches for
tracking and possible back-porting of relevant fixes.

Branch layout is:

    master             <- Active: v3.2.x - Rolling.
    v3.<N>.<N>-<LABEL>    Active: Development branches.
    testing               Sandbox: Subject to change without notice.
    v3.1.8                Sunset: Bugfix only for v3.1.7

    The following are NOT compatible with OpenSSL version 3:

    v3.0.6                Inactive: Archived.
    v3.0.5                Inactive: Archived.
    v3.0.4                Inactive: Archived.
    release/3.0           Inactive: Archived.
    release/2.x           Inactive: Archived.
    release/1.x           Inactive: Unmaintained.

LICENSING info for 3.x is in the [COPYING.md](COPYING.md) file

## Contributing

Please refer to: [doc/EasyRSA-Contributing.md](doc/EasyRSA-Contributing.md)

# Code style, standards

We are attempting to adhere to the POSIX standard, which can be found here:

https://pubs.opengroup.org/onlinepubs/9699919799/
