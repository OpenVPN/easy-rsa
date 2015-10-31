Building Easy-RSA 3
===

This document serves as the packaging reference.

Using the buildscript
---

build/build-dist.sh prepares a release-ready tarball from the current source
tree. Ensure a clean checkout (remove your left-over temp files) and verify
release changes are in order:

 * ChangeLog updated for version, date, & feature changes
 * Release-tag prepared in git

When ready, set a match version on the tarball & inside dir with:

    ./build/build-dist.sh --version=3.2.1

For development use, omitting the --version param creates by default a
`git-development` version.

Windows Build Extras
---

When the build-script is updated to support Windows, this section will be
updated to match.

Note that Windows builds require external binary files from the unxutils and
mksh/Win32 projects which are not included in the Easy-RSA source tree. Starting
with a basic build dir from earlier, proceed as follows.

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
