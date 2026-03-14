"""Easy-RSA session management: temp dir, lock file."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from .errors import EasyRSALockError, EasyRSAError


class Session:
    """Manages a temp directory and PKI lock file for an Easy-RSA operation."""

    def __init__(self, pki_dir: Path, no_lockfile: bool = False):
        self.pki_dir = pki_dir
        self.no_lockfile = no_lockfile
        self._tmp_dir: Optional[Path] = None
        self._lock_file: Optional[Path] = None
        self._lock_acquired = False
        self._counter = 0

    def __enter__(self) -> "Session":
        self._setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
        return False

    def _setup(self) -> None:
        """Create temp directory and acquire lock file."""
        # Create tmp dir under pki_dir/tmp/
        tmp_base = self.pki_dir / "tmp"
        tmp_base.mkdir(parents=True, exist_ok=True)
        self._tmp_dir = Path(tempfile.mkdtemp(dir=str(tmp_base)))

        # Acquire lock file
        if not self.no_lockfile and self.pki_dir.exists():
            self._acquire_lock()

    def _acquire_lock(self) -> None:
        """Acquire PKI lock file using O_CREAT|O_EXCL (atomic)."""
        lock_path = self.pki_dir / "lock.file"
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(fd, str(os.getpid()).encode())
            finally:
                os.close(fd)
            self._lock_file = lock_path
            self._lock_acquired = True
        except FileExistsError:
            raise EasyRSALockError(
                f"PKI is locked by another process.\n"
                f"Lock file: {lock_path}\n"
                f"If no other easyrsa process is running, remove the lock file and retry."
            )

    def mktemp(self) -> Path:
        """Return path to a new exclusive temp file in the session dir."""
        if self._tmp_dir is None:
            raise EasyRSAError("Session not started; call __enter__ or _setup() first")
        for _ in range(100):
            path = self._tmp_dir / f"temp.{self._counter:02d}"
            self._counter += 1
            try:
                # Exclusive create
                fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                return path
            except FileExistsError:
                continue
        raise EasyRSAError("Session temp file slots exhausted")

    def cleanup(self, keep_name: Optional[str] = None) -> None:
        """Clean up temp dir and release lock file.

        If keep_name is given, rename the session dir to pki_dir/tmp/<keep_name>.
        """
        if self._tmp_dir and self._tmp_dir.exists():
            if keep_name:
                dest = self.pki_dir / "tmp" / keep_name
                if dest.exists():
                    shutil.rmtree(dest, ignore_errors=True)
                try:
                    shutil.move(str(self._tmp_dir), str(dest))
                except OSError:
                    shutil.rmtree(self._tmp_dir, ignore_errors=True)
            else:
                shutil.rmtree(self._tmp_dir, ignore_errors=True)
            self._tmp_dir = None

        if self._lock_file and self._lock_acquired:
            try:
                self._lock_file.unlink()
            except OSError:
                pass
            self._lock_acquired = False
            self._lock_file = None
