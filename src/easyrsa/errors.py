"""Easy-RSA exception classes."""

import re

_SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9_.-]+$')


class EasyRSAError(Exception):
    """Base exception for Easy-RSA errors."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class EasyRSAUserError(EasyRSAError):
    """User-facing errors (bad input, missing files, etc.)."""

    pass


class EasyRSALockError(EasyRSAError):
    """Lock file errors."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=17)


def validate_name(name: str) -> None:
    """Raise EasyRSAUserError if name is unsafe as a filename."""
    if not name or name in ('.', '..') or '/' in name or '\\' in name:
        raise EasyRSAUserError(f"Invalid name: '{name}'")
    if not _SAFE_NAME_RE.match(name):
        raise EasyRSAUserError(
            f"Invalid name '{name}': only alphanumeric, hyphen, underscore, and dot are allowed"
        )
