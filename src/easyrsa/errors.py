"""Easy-RSA exception classes."""


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
