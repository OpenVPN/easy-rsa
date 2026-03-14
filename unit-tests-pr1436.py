#!/usr/bin/env python3
"""
unit-tests-pr1436.py -- Regression tests for PR #1436 bug fixes

Requirements
------------
Python >= 3.6 (stdlib only -- no third-party packages).
The easyrsa shell script and openssl must be available; everything else
is handled by Python natively.

Why Python instead of shell
---------------------------
The shell version (unit-tests-pr1436.sh) works around the absence of
several POSIX utilities on Windows by using only shell built-ins.
Those workarounds are non-trivial.  Python gives us:

  * subprocess.run(timeout=N)          -- no background-process gymnastics
  * subprocess.DEVNULL                 -- /dev/null on every platform
  * tempfile.mkdtemp()                 -- portable temp dir, no mkdir needed
  * shutil.rmtree()                    -- portable recursive delete
  * pathlib.Path                       -- portable path manipulation
  * TimeoutExpired                     -- clean, typed exception for FIX-1

On Windows the easyrsa script is invoked through 'sh' explicitly (see
_easyrsa_cmd()) because the OS does not process POSIX shebangs.

Usage
-----
    python3 unit-tests-pr1436.py [-v] [-k]
    python3 unit-tests-pr1436.py version

    -v / --verbose  Print captured stderr/stdout for each test.
    -k / --keep     Do not delete the temp directory on exit.

Exit code: 0 if all tests passed, 1 if any failed.
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

VERSION = "1436.1"

# ---------------------------------------------------------------------------
# Locate easyrsa
# ---------------------------------------------------------------------------

def _find_easyrsa() -> pathlib.Path:
    """Return a Path to the easyrsa script.

    Search order:
      1. ERSA_BIN environment variable
      2. easyrsa3/easyrsa  relative to this file
      3. easyrsa           relative to this file
      4. 'easyrsa'         bare name (relies on PATH)
    """
    env = os.environ.get("ERSA_BIN", "")
    if env:
        p = pathlib.Path(env)
        if p.is_file():
            return p

    here = pathlib.Path(__file__).resolve().parent
    for rel in ("easyrsa3/easyrsa", "easyrsa"):
        p = here / rel
        if p.is_file():
            return p

    return pathlib.Path("easyrsa")


def _easyrsa_cmd(easyrsa_path: pathlib.Path) -> list:
    """Return the argv prefix used to invoke easyrsa.

    On Windows the kernel does not process POSIX shebangs, so we
    prepend 'sh'.  On every other platform the shebang line in the
    easyrsa script is sufficient.
    """
    if sys.platform == "win32":
        return ["sh", str(easyrsa_path)]
    return [str(easyrsa_path)]


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

class Runner:
    """Manages temp storage, runs easyrsa sub-processes, and counts results."""

    def __init__(self, easyrsa_path: pathlib.Path, *, verbose: bool, keep: bool):
        self._prefix = _easyrsa_cmd(easyrsa_path)
        self.verbose = verbose
        self.keep = keep
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.tmpdir = pathlib.Path(tempfile.mkdtemp(prefix="ersa-pr1436-"))

    # --- result accounting ---

    def t_pass(self, name: str) -> None:
        self.passed += 1
        print(f"PASS [{name}]")

    def t_fail(self, name: str, reason: str = "") -> None:
        self.failed += 1
        msg = f"FAIL [{name}]"
        if reason:
            msg += f": {reason}"
        print(msg)

    def t_skip(self, name: str, reason: str = "") -> None:
        self.skipped += 1
        msg = f"SKIP [{name}]"
        if reason:
            msg += f": {reason}"
        print(msg)

    # --- subprocess helpers ---

    def run(
        self,
        pki_dir: str,
        *args: str,
        stdin=None,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """Run easyrsa with the given PKI dir and extra args.

        Use as_posix() for the PKI path so mksh on Windows receives
        forward-slash separators.
        """
        cmd = self._prefix + [f"--pki-dir={pathlib.Path(pki_dir).as_posix()}"] + list(args)
        return subprocess.run(
            cmd,
            stdin=stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )

    def show(self, result: subprocess.CompletedProcess) -> None:
        """Print captured output when verbose mode is active."""
        if not self.verbose:
            return
        for data, label in ((result.stderr, "stderr"), (result.stdout, "stdout")):
            if data:
                text = data.decode(errors="replace").rstrip()
                if text:
                    print(f"  [{label}]\n{text}")

    def init_pki(self, pki_dir: str) -> None:
        """Run init-pki; abort the entire suite if it fails."""
        result = self.run(pki_dir, "init-pki")
        if result.returncode != 0:
            print(f"FATAL: Could not init PKI at {pki_dir}")
            self.show(result)
            sys.exit(1)

    def write_vars(self, filename: str, content: str) -> str:
        """Write a vars file and return its path as a posix string."""
        p = self.tmpdir / filename
        p.write_text(content, encoding="utf-8")
        return p.as_posix()

    # --- lifecycle ---

    def cleanup(self) -> None:
        if self.keep:
            print(f"\nTest artifacts preserved: {self.tmpdir}")
        else:
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def summary(self) -> None:
        sep = "=" * 40
        print(f"\n{sep}")
        print(
            f"PR #1436 regression tests: "
            f"{self.passed} passed, {self.failed} failed, {self.skipped} skipped"
        )
        print(sep)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_fix1_passphrase_eof_exits(r: Runner) -> None:
    """FIX-1: get_passphrase() must not loop forever when stdin is EOF.

    Before the fix, hide_read_pass() discarded the return value of
    'read -r', always returning 0.  get_passphrase() therefore never
    detected EOF and kept looping.  The 'return 1' after the while-loop
    was dead, unreachable code.

    After the fix, each branch of hide_read_pass() captures 'ret=$?'
    and does 'return $ret'.  get_passphrase() breaks with
    'hide_read_pass r || return 1'.

    Verification: run build-ca (which calls get_passphrase) with stdin
    wired to /dev/null and a 10-second timeout.  subprocess.run() kills
    the process and raises TimeoutExpired if it hasn't returned by then.
    """
    name = "FIX-1-passphrase-eof-exits"
    pki = str(r.tmpdir / "pki-eof")
    r.init_pki(pki)
    try:
        result = r.run(
            pki, "--batch", "build-ca",
            stdin=subprocess.DEVNULL,
            timeout=10,
        )
        if result.returncode == 0:
            r.t_fail(name, "build-ca returned 0 from EOF stdin (expected non-zero)")
        else:
            r.t_pass(name)
        r.show(result)
    except subprocess.TimeoutExpired:
        r.t_fail(
            name,
            "build-ca did not exit within 10 s with EOF stdin "
            "(infinite-loop bug still present)",
        )


def test_fix2a_set_var_digit_leading(r: Runner) -> None:
    """FIX-2a: set_var() rejects identifiers that start with a digit.

    Before: only *=* was guarded; '0INVALID' reached eval and produced
            a shell syntax error or silent misbehaviour.
    After:  [0-9]* triggers user_error before eval is reached.
    """
    name = "FIX-2a-set_var-rejects-digit-leading-name"
    pki = str(r.tmpdir / "pki-sv-digit")
    vars_file = r.write_vars("vars-digit", 'set_var 0INVALID "test"\n')
    result = r.run(pki, f"--vars={vars_file}", "show-host")
    if result.returncode == 0:
        r.t_fail(name, "Expected non-zero exit for digit-leading name, got 0")
    else:
        r.t_pass(name)
    r.show(result)


def test_fix2b_set_var_hyphen(r: Runner) -> None:
    """FIX-2b: set_var() rejects identifiers containing a hyphen.

    Before: 'EASYRSA-INVALID' passed the *=* guard and reached eval.
    After:  *[!A-Za-z0-9_]* catches the hyphen.
    """
    name = "FIX-2b-set_var-rejects-hyphen-in-name"
    pki = str(r.tmpdir / "pki-sv-hyph")
    vars_file = r.write_vars("vars-hyphen", 'set_var EASYRSA-INVALID "test"\n')
    result = r.run(pki, f"--vars={vars_file}", "show-host")
    if result.returncode == 0:
        r.t_fail(name, "Expected non-zero exit for hyphenated name, got 0")
    else:
        r.t_pass(name)
    r.show(result)


def test_fix2c_set_var_valid(r: Runner) -> None:
    """FIX-2c: set_var() still accepts valid POSIX identifiers (regression guard).

    Tightened validation must not break legitimate vars-file usage.
    """
    name = "FIX-2c-set_var-accepts-valid-identifier"
    pki = str(r.tmpdir / "pki-sv-valid")
    vars_file = r.write_vars("vars-valid", 'set_var EASYRSA_REQ_CN "test-valid-cn"\n')
    result = r.run(pki, f"--vars={vars_file}", "init-pki")
    if result.returncode != 0:
        r.t_fail(name, f"Valid set_var call failed (exit {result.returncode})")
        r.show(result)
    else:
        r.t_pass(name)


def test_fix2d_set_var_empty(r: Runner) -> None:
    """FIX-2d: set_var() rejects an empty identifier.

    The '' arm of the case guard is new in PR #1436.
    """
    name = "FIX-2d-set_var-rejects-empty-name"
    pki = str(r.tmpdir / "pki-sv-empty")
    vars_file = r.write_vars("vars-empty", "set_var '' \"test\"\n")
    result = r.run(pki, f"--vars={vars_file}", "show-host")
    if result.returncode == 0:
        r.t_fail(name, "Expected non-zero exit for empty name, got 0")
    else:
        r.t_pass(name)
    r.show(result)


def test_fix3_passphrase_comparison(r: Runner) -> None:
    """FIX-3: Passphrase comparison works after $(cat) -> read -r change.

    build_ca() previously read passphrase temp-files with:
        p="$(cat "$in_key_pass_tmp")"
    Changed to:
        read -r p < "$in_key_pass_tmp"

    Both are equivalent for single-line values written by 'printf %s'
    (no trailing newline).  This test confirms that a CA can still be
    built with an explicit passphrase via --passout/--passin.
    """
    name = "FIX-3-passphrase-comparison-regression"
    pki = str(r.tmpdir / "pki-passphrase")
    r.init_pki(pki)
    result = r.run(
        pki,
        "--batch",
        "--passout=pass:TestPass1234",
        "--passin=pass:TestPass1234",
        "build-ca",
    )
    if result.returncode != 0:
        r.t_fail(name, f"build-ca with --passout/--passin failed (exit {result.returncode})")
        r.show(result)
    else:
        r.t_pass(name)


def test_fix4_mktemp_naming(r: Runner) -> None:
    """FIX-4: easyrsa_mktemp counter loop produces temp.NN names correctly.

    The nested for-loop ('for high in 0 1; for low in 0..9') was
    replaced with a single counter-based while loop.  Slot names must
    remain identical: temp.00, temp.01, ...

    Verification: build a CA with --keep-tmp so the session directory is
    preserved, then check that temp.00 exists in the saved snapshot.
    """
    name = "FIX-4-easyrsa-mktemp-naming"
    pki = str(r.tmpdir / "pki-mktemp")
    r.init_pki(pki)
    result = r.run(
        pki, "--batch", "--keep-tmp=pr1436-slot-check", "build-ca", "nopass"
    )
    if result.returncode != 0:
        r.t_fail(name, "build-ca nopass failed; cannot inspect temp file names")
        r.show(result)
        return

    slot_dir = r.tmpdir / "pki-mktemp" / "tmp" / "pr1436-slot-check"
    if (slot_dir / "temp.00").exists():
        r.t_pass(name)
        if r.verbose:
            slots = sorted(slot_dir.glob("temp.*"))
            print("  Slot files in kept session:")
            for s in slots:
                print(f"    {s}")
    else:
        r.t_fail(name, f"temp.00 not found in: {slot_dir}")
        if r.verbose and slot_dir.exists():
            print(f"  Contents of {slot_dir}:")
            for f in sorted(slot_dir.iterdir()):
                print(f"    {f}")


# ---------------------------------------------------------------------------
# Test registry
# ---------------------------------------------------------------------------

TESTS = [
    test_fix1_passphrase_eof_exits,
    test_fix2a_set_var_digit_leading,
    test_fix2b_set_var_hyphen,
    test_fix2c_set_var_valid,
    test_fix2d_set_var_empty,
    test_fix3_passphrase_comparison,
    test_fix4_mktemp_naming,
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regression tests for EasyRSA PR #1436.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        help="'version' prints version string and exits",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="print captured stderr/stdout for each test",
    )
    parser.add_argument(
        "-k", "--keep",
        action="store_true",
        help="preserve the temp directory after the run",
    )
    args = parser.parse_args()

    if args.command == "version":
        print(f"unit-tests-pr1436.py version: {VERSION}")
        sys.exit(0)

    if args.command not in ("run", None):
        parser.error(f"unknown command: {args.command!r}")

    easyrsa = _find_easyrsa()
    runner = Runner(easyrsa, verbose=args.verbose, keep=args.keep)

    try:
        for fn in TESTS:
            fn(runner)
    finally:
        runner.summary()
        runner.cleanup()

    sys.exit(0 if runner.failed == 0 else 1)


if __name__ == "__main__":
    main()
