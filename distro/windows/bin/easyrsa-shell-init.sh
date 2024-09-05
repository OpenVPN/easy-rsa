#!/bin/sh
# shellcheck disable=SC2161,SC1091,SC2028

# This script is a frontend designed to create & launch a POSIX shell
# environment suitable for use with Easy-RSA. mksh/Win32 is used with this
# project; use with other POSIX shells for Windows may require modification to
# this wrapper script.

echo "Easy-RSA starting.."

setup_path="${EASYRSA:-$PWD}"
export PATH="$setup_path;$setup_path/bin;$PATH"
export HOME="$setup_path"

# This prevents reading from a user's .mkshrc if they have one.
# A user who runs mksh for other purposes might have it
export ENV="/disable-env"

# Verify required externals are present
extern_list="which awk cat cp mkdir printf rm"
for f in $extern_list; do
	if ! which "${f}.exe" >/dev/null 2>&1; then
		echo ""
		echo "FATAL: EasyRSA Shell init is missing a required external file:"
		echo "  ${f}.exe"
		echo "  Your installation is incomplete and cannot function without the required"
		echo "  files."
		echo ""
		#shellcheck disable=SC2162
		read -p "Press Enter or CTRL-C to exit."
		exit 1
	fi
done

# Allow options
non_admin=""
while [ "$1" ]; do
	case "$1" in
		/[Nn][Aa]|/no-adm*|--no-adm*)
			non_admin=1
			echo "Using no-admin mode"
		;;
		*)
			echo "Ignoring unknown option: '$1'"
	esac
	shift
done

# Access denied
access_denied() {
	echo "Access error: $1"
	echo "\
To use Easy-RSA in a protected system directory, you must have
full administrator privileges via Windows User Access Control."
	echo ""

	#shellcheck disable=SC2162
	read -p "Press Enter or CTRL-C to exit."
	exit 1
}

# Use home directory/easy-rsa
if [ "$non_admin" ]; then
	[ "${HOMEDRIVE}" ] || \
		access_denied "Undefined: HOMEDRIVE"
	user_home_drv="${HOMEDRIVE}"

	[ "${HOMEPATH}" ] || \
		access_denied "Undefined: HOMEPATH"
	eval "user_home_dir='\\${HOMEPATH}'"

	# shellcheck disable=SC2154 # user_home_dir is not assigned
	user_home="${user_home_drv}${user_home_dir}"

	[ -d "$user_home" ] || \
		access_denied "Missing: $user_home"

	cd "$user_home" 2>/dev/null || \
		access_denied "Access: $user_home"

	if [ ! -d easy-rsa ]; then
		mkdir easy-rsa 2>/dev/null || \
			access_denied "mkdir: easy-rsa"
		# Required test
		[ -d easy-rsa ] || \
			access_denied "Missing: easy-rsa"
	fi

	cd easy-rsa 2>/dev/null || \
		access_denied "Access: easy-rsa"

	export HOME="$PWD"
	export PATH="$HOME;$PATH"
	unset -v user_home_drv user_home_dir user_home
fi

# Check for broken administrator access
# https://github.com/OpenVPN/easy-rsa/issues/1072
[ -d "$HOME" ] || access_denied "-d HOME"
win_tst_d="$HOME"/easyrsa-write-test

# Required tests
mkdir "$win_tst_d" 2>/dev/null || access_denied "mkdir"
[ -d "$win_tst_d" ] || access_denied "-d"
echo 1 >"$win_tst_d"/1 2>/dev/null || access_denied "write"
[ -f "$win_tst_d"/1 ] || access_denied "-f"
rm -rf "$win_tst_d" 2>/dev/null || access_denied "rm"
[ ! -d "$win_tst_d" ] || access_denied "! -d"
unset -v win_tst_d
unset -f access_denied

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
	read -p "Press Enter or CTRL-C to exit."
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
echo "Invoke 'easyrsa' to call the program. Without commands, help is displayed."
echo ""
echo "Using directory: $HOME"
echo ""

# Drop to a shell and await input
sh.exe
