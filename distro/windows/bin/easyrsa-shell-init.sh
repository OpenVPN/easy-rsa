#!/bin/sh

# This script is a frontend designed to create & launch a POSIX shell
# environment suitable for use with Easy-RSA. mksh/Win32 is used with this
# project; use with other POSIX shells for Windows may require modification to
# this wrapper script.

# SC2162 - read without -r will mangle backslashes
# SC1091 - Not following source file
# SC1003 - (info): Want to escape a single quote?
# shellcheck disable=SC2162,SC1091,SC1003

# intent confirmation helper func
# modified from easyrsa
confirm() {
	prompt="$1"
	value="$2"
	msg="$3"
	input=""
	print "\
$msg

Type the word '$value' to continue, or any other input to abort."
	printf %s "  $prompt"
	# shellcheck disable=SC2162 # read without -r - confirm()
	read input
	printf '\n'
	[ "$input" = "$value" ] && return
	unset -v EASYRSA_SILENT
	notice "Aborting without confirmation."
	exit 1
} # => confirm()

# Access denied error
access_denied() {
		echo "Cannot locate or use a User-Home directory."
		echo "Press [Enter] to exit."
		read
		exit 1
} # => access_denied()

# Administrator access Required tests
admin_access() {
	mkdir "$1" 2>/dev/null || return 1
	[ -d "$1" ] || return 1
	echo 1 >"$1"/1 2>/dev/null || return 1
	[ -f "$1"/1 ] || return 1
	rm -rf "$1" 2>/dev/null || return 1
	[ ! -d "$1" ] || return 1
} # => admin_access()

# Setup "$HOMEDRIVE\$HOMEPATH\OpenVPN\easy-rsa" directory
use_home_dir() {
	if [ "$USERPROFILE" ]; then
		# Use $USERPROFILE
		user_home="$USERPROFILE"
	elif [ "$HOMEDRIVE" ]; then
		if [ "$HOMEPATH" ]; then
			# Use $HOMEDRIVE and $HOMEPATH
			user_home="${HOMEDRIVE}${HOMEPATH}"
		else
			user_home=
		fi
	else
		user_home=
	fi

	# If no $user_home was identified
	[ "$user_home" ] || access_denied

	# Use $user_home/openvpn directory
	cd "$user_home"/openvpn || access_denied

	# Create $user_home/openvpn/easy-rsa directory
	if [ ! -d easy-rsa ]; then
		mkdir easy-rsa 2>/dev/null || access_denied
		# Required test
		[ -d easy-rsa ] || access_denied
	fi

	# Use $user_home/openvpn/easy-rsa directory
	cd easy-rsa 2>/dev/null || access_denied

	export HOME="$PWD"
	export PATH="$HOME;$PATH"
	unset -v user_home
} # => use_home_dir()

# set_var is defined as any vars file needs it.
# This is the same as in easyrsa, but we _don't_ export
set_var() {
        var="$1"
        shift
        value="$*"
        eval "$var=\"\${$var-$value}\""
} #=> set_var()

########################################
# Invocation entry point:

echo "Starting Easy-RSA shell.."

setup_path="${EASYRSA:-$PWD}"
export PATH="$setup_path;$setup_path/bin;$PATH"
export HOME="$setup_path"

# This prevents reading from a user's .mkshrc if they have one.
# A user who runs mksh for other purposes might have it
export ENV="/disable-env"

# Check for broken administrator access
# https://github.com/OpenVPN/easy-rsa/issues/1072
if admin_access "$HOME"/easyrsa-write-test; then
	sec_lev='#'
else
	echo "
To use Easy-RSA in a protected system directory, you must have
full administrator privileges via Windows User Access Control."

	confirm "Continue without administrator access ? " yes "
Easy-RSA will now try to use your User-Home directory."

	use_home_dir
	sec_lev='$'
	echo "
NOTICE:
Easy-RSA has been auto-configured to run in your User-Home directory."
fi

# Verify required externals are present
extern_list="which awk cat cp mkdir printf rm grep sed"
for f in $extern_list; do
	if ! which "${f}.exe" >/dev/null 2>&1; then
		echo ""
		echo "FATAL: EasyRSA Shell init is missing a required external file:"
		echo "  ${f}.exe"
		echo "  Your installation is incomplete and cannot function without"
		echo "  the required files."
		echo ""
		echo "Press Enter to exit."
		read
		exit 1
	fi
done

# Check for a usable openssl bin, referencing vars if present
[ -r "vars" ] && EASYRSA_CALLER=1 . "vars" 2>/dev/null
if [ -z "$EASYRSA_OPENSSL" ] && ! which openssl.exe >/dev/null 2>&1; then
	echo "WARNING: openssl isn't in your system PATH. The openssl binary must be"
	echo "  available in the PATH, defined in the 'vars' file, or defined in a"
	echo "  named environment variable. See README-Windows.txt for more info."
fi

[ -f "$setup_path/easyrsa" ] || {
	echo "Missing easyrsa script. Expected to find it at: $setup_path/easyrsa"
	echo "Press Enter to exit."
	read
	exit 1
}

# Check for openvpn executable
if which openvpn.exe >/dev/null 2>&1; then
	EASYRSA_OPENVPN="$(which openvpn.exe | sed s/'\\'/'\/'/g)" || {
		echo "verify_openvpn - Failed to convert openvpn path."
		echo "Press Enter to exit."
		read
		exit 1
	}
	export EASYRSA_OPENVPN="$EASYRSA_OPENVPN"
else
	echo "WARNING: openvpn.exe is not in your system PATH."
	echo "EasyRSA will not be able to generate OpenVPN TLS keys."
fi

# Set prompt and welcome message
export PS1="$USERNAME@$COMPUTERNAME $HOME
EasyRSA-Shell: $sec_lev "

echo ""
echo "Welcome to the EasyRSA 3 Shell for Windows."
echo "Easy-RSA 3 is available under a GNU GPLv2 license."
echo ""
echo "Invoke 'easyrsa' to call the program. Without commands, help is displayed."
echo ""

# Drop to a shell and await input
sh.exe
