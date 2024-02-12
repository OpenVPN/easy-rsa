#!/bin/sh
# shellcheck disable=SC2161,SC1091

# This script is a frontend designed to create & launch a POSIX shell
# environment suitable for use with Easy-RSA. mksh/Win32 is used with this
# project; use with other POSIX shells for Windows may require modification to
# this wrapper script.

cd easyrsa3 || { echo "ERROR: Cannot find easyrsa3 directory"; exit 1; }

setup_path="${EASYRSA:-$PWD}"
export PATH="$setup_path;$PATH"
export HOME="$setup_path"

# This prevents reading from a user's .mkshrc if they have one.
# A user who runs mksh for other purposes might have it
export ENV="/disable-env"

# set_var is defined as any vars file needs it.
# This is the same as in easyrsa, but we _don't_ export
set_var() {
        var="$1"
        shift
        value="$*"
        eval "$var=\"\${$var-$value}\""
} #=> set_var()

# Check for a usable openssl bin, referencing vars if present
[ -r "vars" ] && EASYRSA_CALLER=1 . "vars" 2>/dev/null
if [ -z "$EASYRSA_OPENSSL" ] && ! which openssl.exe >/dev/null 2>&1; then
	echo "WARNING: openssl isn't in your system PATH. The openssl binary must be"
	echo "  available in the PATH, defined in the 'vars' file, or defined in a"
	echo "  named environment variable. See README-Windows.txt for more info."
fi

[ -f "$setup_path/easyrsa" ] || {
	echo "Missing easyrsa script. Expected to find it at: $setup_path/easyrsa"
	exit 2
}

# Set prompt and welcome message
export PS1='
EasyRSA Shell
# '
echo ""
echo "Welcome to the EasyRSA 3 Shell for Windows."
echo "Easy-RSA 3 is available under a GNU GPLv2 license."
echo ""
echo "Invoke './easyrsa' to call the program. Without commands, help is displayed."

cd ..

./op-test.sh -w -p -v
