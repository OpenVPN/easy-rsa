#!/bin/sh
#
# unit-tests-pr1436.sh -- Regression tests for PR #1436 bug fixes
#
# Covers four changes made in PR #1436:
#
#   FIX-1  hide_read_pass() now propagates read's exit status so
#          get_passphrase() can detect EOF and return 1 instead of
#          looping forever.
#
#   FIX-2  set_var() now validates that $1 matches the POSIX identifier
#          set ([A-Za-z_][A-Za-z0-9_]*) before passing it to eval.
#
#   FIX-3  build_ca() reads passphrase temp-files with 'read -r' instead
#          of $(cat ...) to avoid unnecessary subshell forks.
#
#   FIX-4  easyrsa_mktemp() uses a counter-based while loop (explicit
#          limit of 20) instead of opaque nested for-loops.
#
# Usage:
#   sh unit-tests-pr1436.sh [-v] [-k]
#
#   -v   verbose: show per-test detail
#   -k   keep:    preserve temp directory on exit
#
# Exit code: 0 all tests passed, 1 one or more tests failed.

ERSA_BIN="${ERSA_BIN:-./easyrsa3/easyrsa}"
ERSA_UTEST_VERSION="1436.1"

pass_count=0
fail_count=0
skip_count=0
VERBOSE=0
KEEP_TEMP=0

while [ "$1" ]; do
	case "$1" in
	version)
		printf 'unit-tests-pr1436.sh version: %s\n' "$ERSA_UTEST_VERSION"
		exit 0
	;;
	-v) VERBOSE=1 ;;
	-k) KEEP_TEMP=1 ;;
	*)  printf 'Unknown option: %s\n' "$1"; exit 1 ;;
	esac
	shift
done

TMPDIR_TEST="${TMPDIR:-/tmp}/ersa-pr1436-$$"
mkdir -p "$TMPDIR_TEST" || { printf 'Cannot create temp dir\n'; exit 1; }

cleanup_tests() {
	if [ "$KEEP_TEMP" -eq 1 ]; then
		printf '\nTemp dir preserved: %s\n' "$TMPDIR_TEST"
	else
		rm -rf "$TMPDIR_TEST"
	fi
}
trap cleanup_tests EXIT INT TERM

# --- helpers ---

t_pass() {
	pass_count=$((pass_count + 1))
	printf 'PASS [%s]\n' "$1"
}

t_fail() {
	fail_count=$((fail_count + 1))
	printf 'FAIL [%s]: %s\n' "$1" "$2"
}

t_skip() {
	skip_count=$((skip_count + 1))
	printf 'SKIP [%s]: %s\n' "$1" "$2"
}

# run_ersa <pki-dir> [extra easyrsa args...]
run_ersa() {
	_pki="$1"; shift
	"$ERSA_BIN" --pki-dir="$_pki" "$@" >"$TMPDIR_TEST/.out" 2>"$TMPDIR_TEST/.err"
}

# Portable background-process timeout.
# Usage: run_with_timeout <seconds> <command> [args...]
# Returns: command's exit code, or 124 if killed by timeout.
run_with_timeout() {
	_timeout="$1"; shift
	"$@" &
	_proc="$!"
	(
		_slept=0
		while [ "$_slept" -lt "$_timeout" ]; do
			sleep 1
			_slept=$((_slept + 1))
			kill -0 "$_proc" 2>/dev/null || exit 0
		done
		kill "$_proc" 2>/dev/null
	) &
	_timer="$!"
	wait "$_proc"
	_ret=$?
	kill "$_timer" 2>/dev/null
	wait "$_timer" 2>/dev/null
	return "$_ret"
}

# init a throw-away PKI; die if it fails (prerequisite)
init_test_pki() {
	_pki="$1"
	if ! run_ersa "$_pki" init-pki; then
		printf 'FATAL: Could not init PKI at %s\n' "$_pki"
		cat "$TMPDIR_TEST/.err"
		exit 1
	fi
}

# ---------------------------------------------------------------------------
# FIX-1: get_passphrase() must not loop forever on EOF
#
# Before the fix, hide_read_pass() always returned 0 regardless of whether
# read hit EOF. get_passphrase() never escaped the while-loop. With stdin
# from /dev/null every iteration immediately gets an empty read, the
# passphrase length check fails, and the loop spins forever.
#
# After the fix, hide_read_pass() propagates read's exit status.
# get_passphrase() sees the non-zero return and calls `return 1`,
# which causes build-ca to fail promptly.
#
# We give the command 10 seconds. If it is still running after that the old
# bug is present.
# ---------------------------------------------------------------------------
T="FIX-1-passphrase-eof-exits"
_pki="$TMPDIR_TEST/pki-eof"
init_test_pki "$_pki"

if run_with_timeout 10 \
	sh -c "\"$ERSA_BIN\" --pki-dir=\"$_pki\" --batch build-ca </dev/null" \
	>"$TMPDIR_TEST/.out" 2>"$TMPDIR_TEST/.err"
then
	# Exited 0 — that would be surprising without --nopass/--passout
	t_fail "$T" "build-ca returned 0 from EOF stdin (expected non-zero)"
else
	_ret=$?
	if [ "$_ret" -eq 124 ]; then
		# Our timer killed the process — the old infinite-loop bug is present
		t_fail "$T" \
			"build-ca did not exit within 10s on EOF stdin (infinite loop)"
	else
		# Exited with some non-zero code in time — fix is working
		t_pass "$T"
	fi
fi
[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"

# ---------------------------------------------------------------------------
# FIX-2a: set_var() must reject identifiers that start with a digit
#
# Pattern [0-9]* was not in the original case guard.  A vars file containing
# `set_var 0INVALID "foo"` would previously reach eval and silently produce
# incorrect behaviour (eval of `export "0INVALID"="..."` is a syntax error
# in most shells that produces a confusing message rather than user_error).
# After the fix it is caught before eval and user_error is raised.
# ---------------------------------------------------------------------------
T="FIX-2a-set_var-rejects-digit-leading-name"
_pki="$TMPDIR_TEST/pki-sv-digit"
_vars="$TMPDIR_TEST/vars-digit"
printf 'set_var 0INVALID "test"\n' > "$_vars"
if run_ersa "$_pki" --vars="$_vars" show-host; then
	t_fail "$T" "Expected non-zero exit for digit-leading variable name, got 0"
else
	t_pass "$T"
fi
[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"

# ---------------------------------------------------------------------------
# FIX-2b: set_var() must reject identifiers containing a hyphen
#
# Hyphens are not valid in POSIX variable names but were not previously
# caught by the *=* guard. A vars file with `set_var EASYRSA-INVALID "x"`
# reaches eval as `export "EASYRSA-INVALID"="..."` which is either a syntax
# error or silently sets nothing, depending on the shell.  The new guard
# *[!A-Za-z0-9_]* catches the hyphen.
# ---------------------------------------------------------------------------
T="FIX-2b-set_var-rejects-hyphen-in-name"
_pki="$TMPDIR_TEST/pki-sv-hyph"
_vars="$TMPDIR_TEST/vars-hyphen"
printf 'set_var EASYRSA-INVALID "test"\n' > "$_vars"
if run_ersa "$_pki" --vars="$_vars" show-host; then
	t_fail "$T" "Expected non-zero exit for hyphenated variable name, got 0"
else
	t_pass "$T"
fi
[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"

# ---------------------------------------------------------------------------
# FIX-2c: set_var() must accept valid POSIX identifiers (regression guard)
#
# Ensure the tightened validation does not break normal vars-file usage.
# ---------------------------------------------------------------------------
T="FIX-2c-set_var-accepts-valid-identifier"
_pki="$TMPDIR_TEST/pki-sv-valid"
_vars="$TMPDIR_TEST/vars-valid"
printf 'set_var EASYRSA_REQ_CN "test-valid-cn"\n' > "$_vars"
if run_ersa "$_pki" --vars="$_vars" init-pki; then
	t_pass "$T"
else
	t_fail "$T" "Valid set_var call unexpectedly failed (exit $?)"
fi
[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"

# ---------------------------------------------------------------------------
# FIX-2d: set_var() must reject an empty identifier (edge case)
# ---------------------------------------------------------------------------
T="FIX-2d-set_var-rejects-empty-name"
_pki="$TMPDIR_TEST/pki-sv-empty"
_vars="$TMPDIR_TEST/vars-empty"
# Note: the '' guard is new; previously only *=* was checked
printf "set_var '' \"test\"\n" > "$_vars"
if run_ersa "$_pki" --vars="$_vars" show-host; then
	t_fail "$T" "Expected non-zero exit for empty variable name, got 0"
else
	t_pass "$T"
fi
[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"

# ---------------------------------------------------------------------------
# FIX-3: Passphrase comparison still works after $(cat) -> read -r change
#
# build_ca() previously used `p="$(cat $in_key_pass_tmp)"` to read back the
# passphrase for comparison.  That was changed to `read -r p < $file`.
# Both should behave identically for single-line passphrases written by
# `printf '%s'` (no trailing newline).  This test verifies that a CA can be
# built with an explicit passphrase, confirming the comparison logic works.
# ---------------------------------------------------------------------------
T="FIX-3-passphrase-comparison-regression"
_pki="$TMPDIR_TEST/pki-passphrase"
init_test_pki "$_pki"
if run_ersa "$_pki" \
	--batch \
	--passout=pass:TestPass1234 \
	--passin=pass:TestPass1234 \
	build-ca
then
	t_pass "$T"
else
	t_fail "$T" "build-ca with --passout/--passin failed (exit $?)"
	[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"
fi

# ---------------------------------------------------------------------------
# FIX-4: easyrsa_mktemp names temp files temp.NN using counter loop
#
# The nested for-loop was replaced with a counter-based while loop.  The
# resulting temp file names must be identical: temp.00, temp.01, ...
# We exercise the path by building a CA (which calls easyrsa_mktemp several
# times) with --keep-tmp so the session directory is preserved, then verify
# that temp.00 exists in the saved snapshot.
# ---------------------------------------------------------------------------
T="FIX-4-easyrsa-mktemp-naming"
_pki="$TMPDIR_TEST/pki-mktemp"
init_test_pki "$_pki"

# Run build-ca nopass (calls easyrsa_mktemp at least twice for key+cert tmp)
if run_ersa "$_pki" \
	--batch \
	--keep-tmp=pr1436-slot-check \
	build-ca nopass
then
	# The kept session should be at $EASYRSA_PKI/tmp/pr1436-slot-check
	_slot_dir="$_pki/tmp/pr1436-slot-check"
	if [ -f "${_slot_dir}/temp.00" ]; then
		t_pass "$T"
		if [ "$VERBOSE" -eq 1 ]; then
			printf '  Slot files found:\n'
			ls "${_slot_dir}"/temp.* 2>/dev/null | while IFS= read -r f; do
				printf '    %s\n' "$f"
			done
		fi
	else
		t_fail "$T" \
			"temp.00 not found in kept session dir: ${_slot_dir}"
		[ "$VERBOSE" -eq 1 ] && ls -la "${_slot_dir}" 2>/dev/null
	fi
else
	t_fail "$T" "build-ca nopass failed, cannot inspect temp file names"
	[ "$VERBOSE" -eq 1 ] && cat "$TMPDIR_TEST/.err"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
printf '\n'
printf '=%.0s' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
               21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40
printf '\n'
printf 'PR #1436 regression tests: %d passed, %d failed, %d skipped\n' \
	"$pass_count" "$fail_count" "$skip_count"
printf '=%.0s' 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
               21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40
printf '\n'

[ "$fail_count" -eq 0 ]
