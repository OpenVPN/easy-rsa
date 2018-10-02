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
	echo "$1"
	printf " y/n: "
	read r
	[ "$r" = "y" ] || die "user abort"
}

# main handling entry, run after options parsing:
main() {
	PV="$PRODUCT-$VERSION"

	dist_clean
	stage_unix
	stage_win
	make_tar
	make_zip
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
	src_files="easyrsa3/ Licensing/ COPYING.md ChangeLog README.md README.quickstart.md"
	for f in $src_files
	do
		cp -a "$SRC_ROOT/$f" "$DIST_ROOT/unix/$PV" || die "failed to copy $f"
	done
	
	cp -R "$SRC_ROOT/doc" "$DIST_ROOT/unix/$PV/" || die "failed to copy unix doc"

	sed -i "" -e "s/~VER~/$VERSION/" "$DIST_ROOT/unix/$PV/easyrsa"

	# files not included
	rm -rf "$DIST_ROOT/unix/$PV/doc/TODO" || die "failed rm TODO"
}

stage_win() {
	# make our windows stage if it doesn't exist
	mkdir -p "$DIST_ROOT/windows/$PV"
	
	# make doc dir
	mkdir -p "$DIST_ROOT/windows/$PV/doc"

	for f in $SRC_ROOT/doc/*.md;
	do
		fname=$(basename "$f" .md)
		sed -i "" -e "s/~~~/$VERSION/" "$SRC_ROOT/$f"
		python -m markdown "$f" > "$DIST_ROOT/windows/$PV/doc/$fname.html"
	done
	
	for f in "README" "README.quickstart" "COPYING"
	do
		python -m markdown $SRC_ROOT/$f.md > $DIST_ROOT/windows/$PV/$f.html
	done
	# Copy files into $PV, starting with easyrsa3 as the initial root dir
	src_files="easyrsa3/ ChangeLog COPYING.md"
	for f in $src_files
	do
		cp -a "$SRC_ROOT/$f" "$DIST_ROOT/windows/$PV" || die "failed to copy $f"
	done
	
	src_files="Licensing distro/windows/Licensing"
	for f in $src_files
	do
		cp -R "$SRC_ROOT/$f" "$DIST_ROOT/windows/$PV" || die "failed to copy $f"
	done
	src_files="README-Windows.txt EasyRSA-Start.bat"
	for f in $src_files
	do
		cp -a "$SRC_ROOT/distro/windows/$f" "$DIST_ROOT/windows/$PV" || die "failed to copy $f"
		unix2dos "$DIST_ROOT/windows/$PV/$f" || die "unix2dos conversion failed for $f"
	done
	
	# create bin dir with windows binaries
	cp -v -R "$SRC_ROOT/distro/windows/bin" "$DIST_ROOT/windows/$PV/" || die "failed to copy bin"

	# files not included
	rm -rf "$DIST_ROOT/windows/$PV/doc/TODO" || die "failed rm TODO"

}

make_tar() {
	(cd "$DIST_ROOT/unix/"; tar -czf "$BIN_DEST/${PV}.tgz" "$PV") || die "tar failed"
	note "tarball created at: $BIN_DEST/${PV}.tgz" 
}

make_zip() {
	(cd "$DIST_ROOT/windows/"; zip -qr "../../$BIN_DEST/${PV}.zip" "$PV") || die "zip failed"
	note "zip file created at: $BIN_DEST/${PV}.zip" 
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
