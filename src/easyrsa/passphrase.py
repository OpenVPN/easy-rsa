"""Passphrase handling for Easy-RSA."""

from __future__ import annotations

import getpass
import os
from pathlib import Path
from typing import Optional

from .errors import EasyRSAUserError


def prompt_passphrase(prompt: str, confirm: bool = False, allow_empty: bool = False) -> bytes:
    """Prompt for a passphrase interactively.

    Enforces minimum 4-character length (unless allow_empty=True).
    If confirm=True, prompts twice and ensures they match.
    Returns the passphrase as bytes (empty bytes b"" if allowed and no input given).
    """
    while True:
        pw = getpass.getpass(prompt)
        if not allow_empty and len(pw) < 4:
            print("Passphrase must be at least 4 characters!")
            continue
        if allow_empty and pw == "":
            return b""
        if len(pw) < 4:
            print("Passphrase must be at least 4 characters!")
            continue
        if confirm:
            pw2 = getpass.getpass("Confirm passphrase: ")
            if pw != pw2:
                raise EasyRSAUserError("Passphrase mismatch!")
        return pw.encode("utf-8")


def parse_passin(passin_str: str) -> Optional[bytes]:
    """Parse a passin specifier string into password bytes.

    Supported formats:
    - "pass:PASSWORD" -> b"PASSWORD"
    - "file:/path/to/file" -> contents of file
    - "env:VAR" -> os.environ[VAR]
    - "" -> None (no password)
    """
    if not passin_str:
        return None
    if passin_str.startswith("pass:"):
        return passin_str[5:].encode("utf-8")
    if passin_str.startswith("file:"):
        fp = Path(passin_str[5:])
        if not fp.exists():
            raise EasyRSAUserError(f"Password file not found: {fp}")
        return fp.read_bytes().rstrip(b"\n\r")
    if passin_str.startswith("env:"):
        var = passin_str[4:]
        val = os.environ.get(var)
        if val is None:
            raise EasyRSAUserError(f"Environment variable not set: {var}")
        return val.encode("utf-8")
    raise EasyRSAUserError(
        f"Unknown passin format '{passin_str}'. "
        f"Use pass:PASSWORD, file:/path, or env:VAR"
    )


def parse_passout(passout_str: str) -> Optional[bytes]:
    """Parse a passout specifier string — same formats as passin."""
    return parse_passin(passout_str)


def load_key_password(passin_str: str) -> Optional[bytes]:
    """Load the key decryption password from a passin string.

    Returns bytes or None (no password required).
    """
    return parse_passin(passin_str)
