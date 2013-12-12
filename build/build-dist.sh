#!/bin/sh

# Easy-RSA 3 distribution packager:
# creates ready-to-use tarball files for Unixes

# operational defaults (CLI processing overrides)
VERSION="git-development"
PRODUCT="EasyRSA"
DIST_ROOT="dist-staging"
SRC_ROOT="."
BIN_DEST="."

usage() {
	echo "build-dist options:"
	echo
	echo " --version=X	set version string, default=git-development"
	echo " --dist-root=X	set DIST_ROOT, default=dist-staging"
	echo " --src-root=X	set SRC_ROOT for git src dir, default=."
	echo " --bin-dest=X	set BIN_DEST where to put tar/zip, default=."
	echo
	echo " --dist-clean	rm -rf the DIST_ROOT w/out prompts"

	exit
}

die() {
	echo "build-dist ERROR:"
	echo "$1"
	exit "${2:-1}"
}

note() { echo "build-dist NOTE: $1"; }

# ask before dangerous things
confirm() {
	[ "$2" ] && return
	echo "$1"
	printf " y/n: "
	read r
	[ "$r" = "y" ] || die "user abort"
}

# main handling entry, run after options parsing:
main() {
	PV="$PRODUCT-$VERSION"

	dist_clean
	stage_files
	make_tar
}

# prep DIST_ROOT
dist_clean() {
	if [ -e "$DIST_ROOT" ]; then
		confirm "Remove existing DIST_ROOT at: '$DIST_ROOT' ?" \
			"$DISTCLEAN"
		rm -rf "$DIST_ROOT" || die "dist_clean failed to rm"
	fi
	mkdir -p "$DIST_ROOT" || die "dist_clean failed to mkdir"
}

# file stager
stage_files() {
	# Copy files into $PV, starting with easyrsa3 as the initial root dir
	src_files="easyrsa3/ Licensing/ doc/ COPYING ChangeLog README.quickstart.md"
	for f in $src_files
	do
		cp -a "$SRC_ROOT/$f" "$DIST_ROOT/$PV" || die "failed to copy $f"
	done

	# files not included
	rm "$DIST_ROOT/$PV/doc/TODO" || die "failed rm TODO"
}

make_tar() {
	(cd "$DIST_ROOT"; tar cz "$PV") > "$BIN_DEST/${PV}.tgz" || die "tar failed"
	note "tarball created at: $BIN_DEST/${PV}.tgz" 
}

# parse CLI options:
while [ -n "$1" ]
do
	cmd="${1%%=*}"
	val="${1#*=}"
	[ "$1" = "$cmd" ] && val=
	case "$cmd" in
		--version)
			[ -z "$val" ] && die "empty $cmd not allowed"
			VERSION="$val"
			;;
		--dist-root)
			[ -z "$val" ] && die "empty $cmd not allowed"
			DIST_ROOT="$val"
			;;
		--src-root)
			[ -z "$val" ] && die "empty $cmd not allowed"
			SRC_ROOT="$val"
			;;
		--bin-dest)
			[ -z "$val" ] && die "empty $cmd not allowed"
			BIN_DEST="$val"
			;;
		--dist-clean)
			DISTCLEAN=1
			;;
		help|-h|--help|-help)
			usage
			;;
		*)
			die "Unknown option: $1"
			;;
	esac
	shift
done

main
