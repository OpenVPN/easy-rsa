Building Easy-RSA 3
===

Until a formal buildscript is available, this document serves as the build
reference. Note that Windows builds require external binary files from the
unxutils and mksh/Win32 projects which are not included in the Easy-RSA source
tree.

Basic Builds
---

This build sequence applies to all platforms, including Windows.

1. Checkout the release tag of interest

2. Create a target directory named EasyRSA-3.x.y (matching the release version)

3. Copy the `easyrsa3/*` structure to the target dir root (not named easyrsa3)

4. Copy the following files/dirs into the target dir:

   * `Licensing/`
   * `doc/`
   * `COPYING`
   * `ChangeLog`
   * `README.quickstart.md`

5. For Windows, continue to `Windows Build Extras`. Otherwise, tar up the target
   directory for release distribution.

Windows Build Extras
---

Windows has additional build steps to provide a suitable POSIX environment.
Starting with a basic build dir from earlier, proceed as follows.

1. Copy everything from `distro/windows/` into the target dir root. Make sure
   that text files follow the Windows EOL convention (CR+LF) -- a git checkout
   of the source project on Windows generally does this for you already.

2. Convert the .md readme/doc files into html for easier viewing by Windows
   clients. One option using the python3 `markdown` module is:

    find ./ -name '*.md' | while read f
    do
      python3 -m markdown "$f"  "${f/.md/.html}"
      rm "$f"
    done

3. Copy mksh.exe from the mksh/Win32 project into the target dir named exactly
   `bin/sh.exe` (note the name difference.)

4. Copy the following files from the unxutils project into the target `/bin/`
   dir. Files marked with [+] are optional in unofficial builds and serve only
   to make the shell environment more usable for users.

   * awk.exe
   * cat.exe
   * cp.exe
   * diff.exe [+]
   * grep.exe [+]
   * ls.exe [+]
   * md5sum.exe [+]
   * mkdir.exe
   * mv.exe [+]
   * printf.exe
   * rm.exe
   * sed.exe [+]
   * which.exe

5. Zip up the target directory for release distribution.
