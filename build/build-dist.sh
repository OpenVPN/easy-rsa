#!/bin/sh
# shellcheck disable=SC2162

# Easy-RSA 3 distribution packager:
# creates ready-to-use tarball files for Unixes and a zip file for windows

# operational defaults (CLI processing overrides)
VERSION="git-development"
PRODUCT="EasyRSA"
DIST_ROOT="dist-staging"
SRC_ROOT="."
BIN_DEST="."

usage() {
	cat << __EOF__
build-dist options:

 --version=X	set version string, default=git-development
 --dist-root=X	set DIST_ROOT, default=dist-staging
 --src-root=X	set SRC_ROOT for git src dir, default=.
 --bin-dest=X	set BIN_DEST where to put tar/zip, default=.
 --no-windows	do not build for Windows
 --no-unix	do not build for UNIX
 --no-compress  do not create zip/tar

 --dist-clean	rm -rf the DIST_ROOT w/out prompts
__EOF__

	exit
}

die() {
	echo "build-dist ERROR:" >&2
	echo "$1" >&2
	exit "${2:-1}"
}

note() { echo "build-dist NOTE: $1"; }

# ask before dangerous things
confirm() {
	[ "$2" ] && return
	printf "%s y/n: " "$1"
	read r
	[ "$r" = "y" ] || die "user abort"
}

# main handling entry, run after options parsing:
main() {
	PV="$PRODUCT-$VERSION"

	dist_clean
	$SKIP_UNIX || stage_unix
	$SKIP_WIN || stage_win
	$SKIP_TAR || make_tar
	$SKIP_ZIP || make_zip
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

# stage unix files
stage_unix() {
	# make our unix stage if it doesn't exist
	mkdir -p "$DIST_ROOT/unix/$PV"
	
	# Copy files into $PV, starting with easyrsa3 as the initial root dir
	src_files="easyrsa3/. Licensing/. COPYING.md ChangeLog README.md README.quickstart.md doc"
	for f in $src_files
	do
		cp -R "$SRC_ROOT/$f" "$DIST_ROOT/unix/$PV/" || die "failed to copy $f"
	done
	
	# FreeBSD does not accept -i without argument in a way also acceptable by GNU sed
	sed -i.tmp -e "s/~VER~/$VERSION/" "$DIST_ROOT/unix/$PV/easyrsa" || die "Cannot update easyrsa version"
	rm -f "$DIST_ROOT/unix/$PV/easyrsa.tmp"

	# files not included
	rm -rf "$DIST_ROOT/unix/$PV/doc/TODO" || die "failed rm TODO"
}

stage_win() {
	for win in win32 win64;
	do
		# make our windows stage if it doesn't exist
		mkdir -p "$DIST_ROOT/$win/$PV"
	
		# make doc dir
		mkdir -p "$DIST_ROOT/$win/$PV/doc"

		for f in doc/*.md README.md README.quickstart.md COPYING.md;
		do
			# FreeBSD does not accept -i without argument in a way also acceptable by GNU sed
			sed -i.tmp -e "s/~~~/$VERSION/" "$SRC_ROOT/$f" || die "Cannot update easyrsa version"
			rm -f "$SRC_ROOT/$f.tmp"
			python -m markdown "$SRC_ROOT/$f" > "$DIST_ROOT/$win/$PV/${f%.md}.html" || die "Failed to convert markdown to HTML"
		done
	
		# Copy files into $PV, starting with easyrsa3 as the initial root dir
		src_files="easyrsa3/. ChangeLog COPYING.md Licensing distro/windows/Licensing distro/windows/bin distro/windows/$win/lib* distro/windows/$win/openssl.exe"
		for f in $src_files
		do
			cp -R "$SRC_ROOT/$f" "$DIST_ROOT/$win/$PV/" || die "failed to copy $f"
		done
		
		src_files="README-Windows.txt EasyRSA-Start.bat"
		for f in $src_files
		do
			cp -R "$SRC_ROOT/distro/windows/$f" "$DIST_ROOT/$win/$PV/" || die "failed to copy $f"
			unix2dos "$DIST_ROOT/$win/$PV/$f" || die "unix2dos conversion failed for $f"
		done
		
		# files not included
		rm -rf "$DIST_ROOT/$win/$PV/doc/TODO" || die "failed rm TODO"
	done
}

make_tar() {
	(cd "$DIST_ROOT/unix/"; tar -czf "../${PV}.tgz" "$PV") || die "tar failed"
	note "tarball created at: $DIST_ROOT/${PV}.tgz" 
}

make_zip() {
	for win in win32 win64;
	do
		(cd "$DIST_ROOT/$win/"; zip -qr "../${PV}-$win.zip" "$PV") || die "zip failed"
		note "zip file created at: $DIST_ROOT/${PV}-$win.zip" 
	done
}

SKIP_WIN=false
SKIP_UNIX=false
SKIP_ZIP=false
SKIP_TAR=false
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
			# shellcheck disable=SC2034
			BIN_DEST="$val"
			;;
		--dist-clean)
			DISTCLEAN=1
			;;
		--no-windows)
			SKIP_WIN=true
			SKIP_ZIP=true
			;;
		--no-unix)
			SKIP_UNIX=true
			SKIP_TAR=true
			;;
		--no-compress)
			SKIP_ZIP=true
			SKIP_TAR=true
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
