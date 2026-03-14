"""Easy-RSA PKI directory layout and management."""

from __future__ import annotations

import importlib.resources
import os
import shutil
from pathlib import Path
from typing import Optional

from .errors import EasyRSAUserError


# Required PKI subdirectories
_PKI_DIRS = ["private", "reqs", "issued", "certs_by_serial"]
_CA_DIRS = ["issued", "certs_by_serial"]
_REVOKE_DIRS = [
    "revoked/certs_by_serial",
    "revoked/private_by_serial",
    "revoked/reqs_by_serial",
]


def init_pki(pki_dir: Path, algo: str = "rsa", curve: str = "", batch: bool = False) -> None:
    """Initialise a new PKI directory structure.

    Creates required dirs and writes vars.example.
    If pki_dir already exists, requires confirmation (or batch=True).
    """
    if pki_dir.exists():
        if not batch:
            answer = input(
                f"\nWARNING: This will remove the existing PKI at:\n"
                f"  {pki_dir}\n"
                f"Type 'yes' to confirm removal: "
            ).strip()
            if answer.lower() != "yes":
                raise EasyRSAUserError("init-pki aborted by user.")
        shutil.rmtree(pki_dir)

    # Create required directories
    for subdir in _PKI_DIRS:
        (pki_dir / subdir).mkdir(parents=True, exist_ok=True)

    # Write vars.example from package data
    _write_vars_example(pki_dir)

    # For ec/ed, auto-configure pki/vars
    if algo in ("ec", "ed"):
        _write_auto_vars(pki_dir, algo, curve)


def _write_vars_example(pki_dir: Path) -> None:
    """Write vars.example from the package data file."""
    pkg_data = Path(__file__).parent / "data" / "vars.example"
    dest = pki_dir / "vars.example"
    if pkg_data.exists():
        shutil.copy2(str(pkg_data), str(dest))
    else:
        # Write minimal vars.example inline
        dest.write_text(
            "# Easy-RSA vars file\n"
            "# Copy to 'vars' and customize.\n"
            "#set_var EASYRSA_DN\t\t\"cn_only\"\n"
            "#set_var EASYRSA_REQ_COUNTRY\t\"US\"\n"
            "#set_var EASYRSA_REQ_PROVINCE\t\"California\"\n"
            "#set_var EASYRSA_REQ_CITY\t\"San Francisco\"\n"
            "#set_var EASYRSA_REQ_ORG\t\"Copyleft Certificate Co\"\n"
            "#set_var EASYRSA_REQ_EMAIL\t\"me@example.net\"\n"
            "#set_var EASYRSA_ALGO\t\trsa\n"
            "#set_var EASYRSA_KEY_SIZE\t2048\n"
            "#set_var EASYRSA_CURVE\t\tsecp384r1\n"
            "#set_var EASYRSA_CA_EXPIRE\t3650\n"
            "#set_var EASYRSA_CERT_EXPIRE\t825\n"
            "#set_var EASYRSA_CRL_DAYS\t180\n"
            "#set_var EASYRSA_RAND_SN\t\"yes\"\n",
            encoding="utf-8",
        )


def _write_auto_vars(pki_dir: Path, algo: str, curve: str) -> None:
    """Write pki/vars with auto-configuration for ec/ed."""
    vars_path = pki_dir / "vars"
    lines = [
        "# Easy-RSA auto-configured vars\n",
        f"set_var EASYRSA_ALGO\t\t{algo}\n",
    ]
    if curve:
        lines.append(f"set_var EASYRSA_CURVE\t\t{curve}\n")
    vars_path.write_text("".join(lines), encoding="utf-8")


def verify_pki(pki_dir: Path) -> None:
    """Verify the PKI directory is properly initialised."""
    if not pki_dir.exists():
        raise EasyRSAUserError(
            f"PKI directory does not exist (run init-pki first):\n* {pki_dir}"
        )
    for subdir in ["private", "reqs"]:
        if not (pki_dir / subdir).is_dir():
            raise EasyRSAUserError(
                f"Missing expected PKI directory: {subdir}\n"
                f"(run init-pki first)"
            )


def verify_ca(pki_dir: Path) -> None:
    """Verify the CA is properly initialised."""
    for fname in ["ca.crt", "private/ca.key", "index.txt", "serial"]:
        fpath = pki_dir / fname
        if not fpath.exists():
            raise EasyRSAUserError(
                f"Missing expected CA file: {fname}\n"
                f"(run build-ca first)"
            )
    for subdir in ["issued", "certs_by_serial"]:
        if not (pki_dir / subdir).is_dir():
            raise EasyRSAUserError(
                f"Missing expected CA directory: {subdir}\n"
                f"(run build-ca first)"
            )


def read_serial(pki_dir: Path) -> str:
    """Read the current serial from pki/serial. Returns uppercase hex string."""
    serial_file = pki_dir / "serial"
    if not serial_file.exists():
        raise EasyRSAUserError(f"Serial file not found: {serial_file}")
    return serial_file.read_text(encoding="utf-8").strip().upper()


def write_serial(pki_dir: Path, serial_hex: str) -> None:
    """Write serial + newline to pki/serial atomically."""
    serial_file = pki_dir / "serial"
    tmp = serial_file.parent / (serial_file.name + ".tmp")
    tmp.write_text(serial_hex.upper() + "\n", encoding="utf-8")
    os.replace(str(tmp), str(serial_file))


def get_cert_by_serial(pki_dir: Path, serial_hex: str) -> Optional[Path]:
    """Find a cert file by serial number.

    Checks certs_by_serial/, then issued/, then revoked/.
    """
    serial_upper = serial_hex.upper()

    # Check certs_by_serial/
    p = pki_dir / "certs_by_serial" / f"{serial_upper}.pem"
    if p.exists():
        return p

    # Check revoked/certs_by_serial/
    p = pki_dir / "revoked" / "certs_by_serial" / f"{serial_upper}.crt"
    if p.exists():
        return p

    return None


def create_ca_dirs(pki_dir: Path) -> None:
    """Create the CA-specific subdirectories."""
    for subdir in ["certs_by_serial", "revoked/certs_by_serial",
                   "revoked/private_by_serial", "revoked/reqs_by_serial"]:
        (pki_dir / subdir).mkdir(parents=True, exist_ok=True)


def init_ca_files(pki_dir: Path) -> None:
    """Initialise index.txt, index.txt.attr, and serial=01."""
    index = pki_dir / "index.txt"
    if not index.exists():
        index.write_text("", encoding="utf-8")

    attr = pki_dir / "index.txt.attr"
    attr.write_text("unique_subject = no\n", encoding="utf-8")

    serial = pki_dir / "serial"
    if not serial.exists():
        serial.write_text("01\n", encoding="utf-8")
