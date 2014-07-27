Easy-RSA 3 Windows README

Easy-RSA 3 runs POSIX shell code, so use on Windows has some additional
requirements: an OpenSSL installation, and a usable shell environment.

If you don't have OpenSSL, you'll need to install an OpenSSL package (see
section 1.) The Easy-RSA Windows release includes a ready-to-use shell
environment with special thanks to the mksh/Win32 project.

Contents of this file:
  1. OpenSSL
  2. shell environment
  3. Windows paths
  4. Appendix:
   4.1: reference links
   4.2: license of included components
  5. Special Thanks
   5.1: mksh/Win32

1. Obtaining OpenSSL for use with Easy-RSA

   There are a couple of ways to do this:
   
  (A) If you are using OpenVPN, the easiest solution is to install the OpenSSL
  program components and add openvpn to the system PATH; this is offered as an
  installation option as part of OpenVPN.

  (B) Optionally, install an OpenSSL package, such as from the openssl.org
  website (see appendix.) In this case it will be required to do one of the
  following:

    (1) Add the location of openssl.exe to the system PATH

    (2) Define the EASYRSA_OPENSSL env-var to reference the full path to
    openssl.exe

    (3) Edit the vars file (copy vars.example as a starting point) as instructed
    in the comments

    NOTE: for options 2 & 3 above, see section 3 below called "Windows Paths"

2. Getting a POSIX shell

   The binary release of Easy-RSA 3 comes bundled with the mksh/Win32 shell
   environment and a handful of shell utility programs from the unxutils
   project. This is the easiest way to get a usable shell environment.

   (A) Using the mksh/Win32 shell

       With the Windows binary Easy-RSA download, all the necessary utilities
       are already present. Starting a shell environment is accomplished by
       running the `EasyRSA Start.bat` file.

       A basic collection of shell utilities is included, such as ls, cat, mv,
       and so on. Additional programs can be manually installed from the
       unxutils project (link in appendix); this is intentionally a limited set
	   of programs since most Windows users will use native methods to perform
       filesystem manipulation.

   (B) Using a full POSIX environment (Advanced users only)

       An environment such as Cygwin can provide the necessary POSIX environment
       for the Easy-RSA shell code to run. However, Cygwin paths are not usable
       by native Win32 applications. This means that the OpenSSL installation
       used must also understand Cygwin paths or command calls will fail.
       Provided this requirement is met, Cygwin can directly run the easyrsa
       script without any special interpreter or startup wrapper.

3. Windows Paths

   The provided mksh/Win32 shell understands Windows paths. However, you MUST
   either:

   * Use forward slashes instead of single backslashes, or
   * Use double-backslashes.

   This means the following path formats are accepted:

    "C:/Program Files/OpenSSL-Win32/bin/openssl.exe"
    "C:\\Program Files\\OpenSSL-Win32\\bin\\openssl.exe"

   This is primarily to reference a functioning OpenSSL installation (see
   section 1 above) but applies to any other paths used in env-vars, the `vars`
   file, or in shell commands such as ls, cd, and so on.

4. Appendix

 4.1: Reference Links

   * OpenSSL website:
     https://www.openssl.org

   * OpenSSL binary distribution links:
     https://www.openssl.org/related/binaries.html

   * OpenSSL download page, built by "Shining Light Productions"
     http://slproweb.com/products/Win32OpenSSL.html

     NOTE: if using the "Shining Light Productions" version, the "Light"
     download is fine. 32 or 64-bit is also OK (if you have a 64-bit OS.)

   * UnxUtils project:
     http://sourceforge.net/projects/unxutils

 4.2: License of included components

      Text-format copies of these licenses are available in the Licensing/
      directory.

   (A) Easy-RSA 3 is released under a GPLv2 license:
       https://www.gnu.org/licenses/gpl-2.0.html

   (B) mksh/Win32 is under a MirOS license:
       https://www.mirbsd.org/MirOS-Licence.htm

       Additional library components of mksh/Win32 are covered under additional
       licenses. See Licensing/mksh-Win32.txt for details.

   (C) unxutils is released under a GPLv2 license
       The full source for this win32 port can be found here:
       http://sourceforge.net/projects/unxutils/

5. Special Thanks

 5.1: mksh/Win32

    A special thanks is in order to the mksh/Win32 project and its primary
    maintainer, Michael Langguth <mksh-w32@gmx.net>. This shell offers featurs
    that allow Easy-RSA to run smoothly under Windows; by using mksh/Win32,
    Easy-RSA can deliver the same PKI flexibility to all major platforms.
       
vim: wrap tw=80 expandtab
