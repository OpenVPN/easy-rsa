#!/bin/bash
#
# This script clones, switches to a tag (CLI option)
# then attempts to build openssl binaries

# make a temporary working directory
tempdir=$(mktemp -d)
cd "$tempdir" || exit 1

# clone repo
git clone https://github.com/openssl/openssl.git && cd openssl

# check out the tag from the CLI, if nothing passed, find latest
latest=$(git tag --sort=committerdate --list 'openssl-3.*' | tail -1)

# checkout that tag
git checkout "tags/$latest"

# crosscompile Windows 32
./Configure --cross-compile-prefix=i686-w64-mingw32- mingw
make

# build done, save what we want
mkdir "$tempdir/win32/"
cp libcrypto-3.dll libssl-3.dll apps/openssl.exe "$tempdir/win32"

# clean our source tree
make clean

# build 64-bit version
./Configure --cross-compile-prefix=x86_64-w64-mingw32- mingw64
make

# build done, save what we want
mkdir "$tempdir/win64/"
cp libcrypto-3-x64.dll libssl-3-x64.dll apps/openssl.exe "$tempdir/win64"

# we're done, make the zip file
cd "$tempdir"
zip "$latest.zip" win32/* win64/* && cp "$latest.zip" ~/

# remove temp dir
cd /tmp/
rm -rf "$tempdir"
