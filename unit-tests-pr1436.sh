#!/bin/sh
#
# unit-tests-pr1436.sh -- Regression tests for PR #1436 bug fixes
#
# Portable design constraints
# ---------------------------
# Requires ONLY:
#   - A POSIX sh-compatible shell  (mksh/Win32, dash, bash, ksh)
#   - The easyrsa script itself
#   - openssl (used internally by easyrsa)
#
# Deliberately avoids all bundled GNU-tool binaries (awk, cat, ls, sed,
# grep, sleep, ...) so the suite runs correctly on Windows with mksh/Win32
# without depending on the outdated GNU-for-Windows binaries that ship with
# the EasyRSA Windows distribution.
#
# How each constraint is met
# --------------------------
#   cat   -> print_file() reads with 'while IFS= read -r'
#   ls    -> glob expansion in a for-loop
#   sleep -> detected at startup; falls back to SECONDS busy-wait (mksh/bash)
#            or the timed test is skipped if neither is available (dash/ash)
#   mkdir -> single-level mkdir only (no -p); falls back to CWD if mkdir fails
#   rm -rf-> best-effort in cleanup(); not required for correctness
#   /tmp  -> TMPDIR with TEMP/TMP/CWD fallback chain for Windows
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
#   -k   keep:    preserve test directory on exit
#
# Exit code: 0 all tests passed, 1 one or more tests failed.

ERSA_BIN="${ERSA_BIN:-./easyrsa3/easyrsa}"
ERSA_UTEST_VERSION="1436.2"

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

# ---------------------------------------------------------------------------
# Portable helpers -- no external binaries beyond the shell itself
# ---------------------------------------------------------------------------

# Print every line of a file without using cat
# Usage: print_file <path>
print_file() {
	while IFS= read -r _pf_line; do
		printf '%s\n' "$_pf_line"
	done < "$1"
}

# Print a horizontal separator line (40 chars) without relying on
# printf '=%.0s' tricks that may fail in busybox printf.
print_sep() {
	printf '%s\n' "========================================"
}

# ---------------------------------------------------------------------------
# Temp directory setup
#
# Strategy: try each candidate in order; if none succeed, fall back to CWD.
# No 'mkdir -p' -- a single-level mkdir is sufficient.
# No '/tmp' hard-coded -- use the platform's temp env vars.
# ---------------------------------------------------------------------------
_mk_tests_base() {
	# Prefer explicit TMPDIR (Unix), then Windows TEMP/TMP, then CWD
	for _base in \
		"${TMPDIR:+${TMPDIR}/ersa-pr1436-$$}" \
		"${TEMP:+${TEMP}/ersa-pr1436-$$}" \
		"${TMP:+${TMP}/ersa-pr1436-$$}" \
		"./ersa-pr1436-$$"
	do
		[ -z "$_base" ] && continue
		mkdir "$_base" 2>/dev/null && { printf '%s' "$_base"; return 0; }
	done
	# If the CWD candidate also failed (e.g. already exists from a previous
	# interrupted run), just use CWD directly.
	printf '%s' "."
}

TESTS_BASE="$(_mk_tests_base)"

cleanup_tests() {
	if [ "$KEEP_TEMP" -eq 1 ]; then
		printf '\nTest artifacts preserved: %s\n' "$TESTS_BASE"
		return
	fi
	# Best-effort removal; not required for correctness.
	# On Windows without rm.exe this will silently fail.
	rm -rf "$TESTS_BASE" 2>/dev/null
	# If rm is unavailable or failed, note what was left behind.
	[ -d "$TESTS_BASE" ] && \
		printf 'NOTE: could not remove test dir: %s\n' "$TESTS_BASE"
}
trap cleanup_tests EXIT INT TERM

# Per-test output/error capture files inside the tests base
_OUT="${TESTS_BASE}/.ersa-out"
_ERR="${TESTS_BASE}/.ersa-err"

# ---------------------------------------------------------------------------
# Timeout capability detection (no external 'timeout' binary required)
#
# Three modes, tried in order:
#   sleep   -- background timer sub-shell using sleep; works on any Unix
#   seconds -- SECONDS busy-wait; works in mksh and bash (not dash/ash)
#   none    -- skip tests that require a timeout
# ---------------------------------------------------------------------------
_timeout_mode=none

if ( sleep 0 ) >/dev/null 2>&1; then
	_timeout_mode=sleep
else
	# Check for SECONDS without causing errors in strict shells
	# ${SECONDS+x} expands to 'x' if SECONDS is set, '' otherwise
	case "${SECONDS+x}" in
	x) _timeout_mode=seconds ;;
	esac
fi

# run_with_timeout <seconds> <func_or_cmd> [args...]
#
# Runs the command in the background.  Returns its exit code, or 124 if the
# command is still running after <seconds>.
#
# The stdin of the calling shell is inherited by the background process.
# If you need a specific stdin (e.g. /dev/null), wrap the command in a
# shell function that does the redirection itself.
run_with_timeout() {
	_rwt_limit="$1"; shift

	case "$_timeout_mode" in

	sleep)
		# Start the command, then a self-destructing timer sub-shell
		"$@" &
		_rwt_pid="$!"
		(
			sleep "$_rwt_limit" 2>/dev/null
			kill "$_rwt_pid" 2>/dev/null
		) &
		_rwt_timer="$!"
		wait "$_rwt_pid"
		_rwt_ret=$?
		kill "$_rwt_timer" 2>/dev/null
		wait "$_rwt_timer" 2>/dev/null
		return "$_rwt_ret"
	;;

	seconds)
		# Busy-wait using the SECONDS built-in (mksh, bash, ksh93)
		# No sleep needed; CPU usage is acceptable for a short-lived test.
		"$@" &
		_rwt_pid="$!"
		_rwt_start=$SECONDS
		while kill -0 "$_rwt_pid" 2>/dev/null; do
			if [ $(( SECONDS - _rwt_start )) -ge "$_rwt_limit" ]; then
				kill "$_rwt_pid" 2>/dev/null
				wait "$_rwt_pid" 2>/dev/null
				return 124
			fi
		done
		wait "$_rwt_pid"
		return $?
	;;

	none)
		# Neither sleep nor SECONDS available -- cannot enforce a timeout.
		# Run the command directly and hope for the best.
		# The caller checks the return and will report SKIP if needed.
		"$@"
		return $?
	;;

	esac
}

# ---------------------------------------------------------------------------
# Test accounting
# ---------------------------------------------------------------------------
_pass=0
_fail=0
_skip=0

t_pass() { _pass=$((_pass+1)); printf 'PASS [%s]\n' "$1"; }
t_fail() { _fail=$((_fail+1)); printf 'FAIL [%s]: %s\n' "$1" "$2"; }
t_skip() { _skip=$((_skip+1)); printf 'SKIP [%s]: %s\n' "$1" "$2"; }

# ---------------------------------------------------------------------------
# easyrsa runner
# ---------------------------------------------------------------------------

# run_ersa <pki-dir> [easyrsa-args...]
# Captures stdout/stderr to $_OUT/$_ERR; returns easyrsa's exit code.
run_ersa() {
	_re_pki="$1"; shift
	"$ERSA_BIN" --pki-dir="$_re_pki" "$@" >"$_OUT" 2>"$_ERR"
}

# init_test_pki <pki-dir>
# Bootstraps a PKI; aborts the entire test suite if it fails.
init_test_pki() {
	if ! run_ersa "$1" init-pki; then
		printf 'FATAL: Could not init PKI at %s\n' "$1"
		[ -f "$_ERR" ] && print_file "$_ERR"
		exit 1
	fi
}

# ---------------------------------------------------------------------------
# FIX-1 helper
#
# A named function is used instead of an inline `sh -c "..."` string so that
# quoting is unambiguous across all shells and on Windows paths with spaces.
# The function redirects its own stdin from /dev/null so the background job
# inherits that redirection correctly.
# ---------------------------------------------------------------------------
_run_build_ca_eof() {
	"$ERSA_BIN" --pki-dir="$1" --batch build-ca \
		< /dev/null > "$_OUT" 2>"$_ERR"
}

# ---------------------------------------------------------------------------
# FIX-1: get_passphrase() must not loop forever on EOF
#
# Before: hide_read_pass() discarded read's exit status (always returned 0).
#         get_passphrase() spun in its while-loop forever on EOF stdin.
#         The `return 1` after `done` was unreachable dead code.
#
# After:  hide_read_pass() captures and returns read's exit code.
#         get_passphrase() breaks on `hide_read_pass r || return 1`.
#
# Test:   Build a CA (which calls get_passphrase) with stdin from /dev/null.
#         The fixed code exits with non-zero within the timeout.
#         The old code hangs and is killed after 10 seconds (exit 124).
# ---------------------------------------------------------------------------
T="FIX-1-passphrase-eof-exits"
_pki="${TESTS_BASE}/pki-eof"
init_test_pki "$_pki"

if [ "$_timeout_mode" = none ]; then
	t_skip "$T" "no timeout mechanism available (neither sleep nor SECONDS)"
else
	if run_with_timeout 10 _run_build_ca_eof "$_pki"; then
		# Unexpected success without --nopass/--passout — investigate
		t_fail "$T" "build-ca returned 0 from EOF stdin (expected non-zero)"
	else
		_r=$?
		if [ "$_r" -eq 124 ]; then
			t_fail "$T" \
				"build-ca did not exit within 10s on EOF stdin (infinite loop)"
		else
			t_pass "$T"
		fi
	fi
	[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"
fi

# ---------------------------------------------------------------------------
# FIX-2a: set_var() must reject identifiers that start with a digit
#
# Before: only `*=*` was guarded; `0INVALID` reached eval producing a shell
#         syntax error or silent misbehaviour depending on the shell.
# After:  `[0-9]*` pattern triggers user_error before eval.
# ---------------------------------------------------------------------------
T="FIX-2a-set_var-rejects-digit-leading-name"
_pki="${TESTS_BASE}/pki-sv-digit"
_vars="${TESTS_BASE}/vars-digit"
printf 'set_var 0INVALID "test"\n' > "$_vars"
if run_ersa "$_pki" --vars="$_vars" show-host; then
	t_fail "$T" "Expected non-zero exit for digit-leading name, got 0"
else
	t_pass "$T"
fi
[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"

# ---------------------------------------------------------------------------
# FIX-2b: set_var() must reject identifiers containing a hyphen
#
# Before: `EASYRSA-INVALID` slipped past the `*=*` guard and reached eval.
# After:  `*[!A-Za-z0-9_]*` catches the hyphen.
# ---------------------------------------------------------------------------
T="FIX-2b-set_var-rejects-hyphen-in-name"
_pki="${TESTS_BASE}/pki-sv-hyph"
_vars="${TESTS_BASE}/vars-hyphen"
printf 'set_var EASYRSA-INVALID "test"\n' > "$_vars"
if run_ersa "$_pki" --vars="$_vars" show-host; then
	t_fail "$T" "Expected non-zero exit for hyphenated name, got 0"
else
	t_pass "$T"
fi
[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"

# ---------------------------------------------------------------------------
# FIX-2c: set_var() must still accept valid POSIX identifiers (regression)
# ---------------------------------------------------------------------------
T="FIX-2c-set_var-accepts-valid-identifier"
_pki="${TESTS_BASE}/pki-sv-valid"
_vars="${TESTS_BASE}/vars-valid"
printf 'set_var EASYRSA_REQ_CN "test-valid-cn"\n' > "$_vars"
if run_ersa "$_pki" --vars="$_vars" init-pki; then
	t_pass "$T"
else
	t_fail "$T" "Valid set_var call unexpectedly failed"
	[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"
fi

# ---------------------------------------------------------------------------
# FIX-2d: set_var() must reject an empty identifier
#
# The '' arm of the case guard is new in PR #1436.
# ---------------------------------------------------------------------------
T="FIX-2d-set_var-rejects-empty-name"
_pki="${TESTS_BASE}/pki-sv-empty"
_vars="${TESTS_BASE}/vars-empty"
printf "set_var '' \"test\"\n" > "$_vars"
if run_ersa "$_pki" --vars="$_vars" show-host; then
	t_fail "$T" "Expected non-zero exit for empty name, got 0"
else
	t_pass "$T"
fi
[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"

# ---------------------------------------------------------------------------
# FIX-3: Passphrase comparison still works after $(cat) -> read -r change
#
# build_ca() previously read passphrase temp-files with `p="$(cat $f)"`.
# Changed to `read -r p < $f`.  Both are equivalent for single-line values
# written by `printf '%s'` (no trailing newline).  This test confirms that
# a CA can be built with an explicit passphrase via --passout/--passin.
# ---------------------------------------------------------------------------
T="FIX-3-passphrase-comparison-regression"
_pki="${TESTS_BASE}/pki-passphrase"
init_test_pki "$_pki"
if run_ersa "$_pki" \
	--batch \
	--passout=pass:TestPass1234 \
	--passin=pass:TestPass1234 \
	build-ca
then
	t_pass "$T"
else
	t_fail "$T" "build-ca with --passout/--passin failed"
	[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"
fi

# ---------------------------------------------------------------------------
# FIX-4: easyrsa_mktemp counter loop produces temp.NN names correctly
#
# The nested for-loop was replaced with a counter-based while loop.
# Slot names must remain identical: temp.00, temp.01, ...
#
# Verified by running build-ca with --keep-tmp, then checking that
# temp.00 exists in the preserved session snapshot.
# Verbose mode lists all temp.* files using a glob for-loop (no ls).
# ---------------------------------------------------------------------------
T="FIX-4-easyrsa-mktemp-naming"
_pki="${TESTS_BASE}/pki-mktemp"
init_test_pki "$_pki"

if run_ersa "$_pki" --batch --keep-tmp=pr1436-slot-check build-ca nopass; then
	_slot_dir="${_pki}/tmp/pr1436-slot-check"
	if [ -f "${_slot_dir}/temp.00" ]; then
		t_pass "$T"
		if [ "$VERBOSE" -eq 1 ]; then
			printf '  Slot files in kept session:\n'
			for _f in "${_slot_dir}"/temp.*; do
				[ -f "$_f" ] && printf '    %s\n' "$_f"
			done
		fi
	else
		t_fail "$T" "temp.00 not found in: ${_slot_dir}"
		if [ "$VERBOSE" -eq 1 ]; then
			printf '  Contents of %s:\n' "$_slot_dir"
			for _f in "${_slot_dir}"/*; do
				[ -e "$_f" ] && printf '    %s\n' "$_f"
			done
		fi
	fi
else
	t_fail "$T" "build-ca nopass failed; cannot inspect temp file names"
	[ "$VERBOSE" -eq 1 ] && [ -f "$_ERR" ] && print_file "$_ERR"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
printf '\n'
print_sep
printf 'PR #1436 regression tests: %d passed, %d failed, %d skipped\n' \
	"$_pass" "$_fail" "$_skip"
print_sep

[ "$_fail" -eq 0 ]
