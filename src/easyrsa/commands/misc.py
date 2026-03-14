"""gen-dh, rand, set-pass, check-serial, self-sign commands."""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import (
    generate_dh_params,
    load_cert,
    load_private_key,
    serialize_private_key,
)
from ..errors import EasyRSAUserError
from ..passphrase import load_key_password, parse_passout, prompt_passphrase
from ..session import Session


def gen_dh(config: EasyRSAConfig, session: Session) -> None:
    """Generate Diffie-Hellman parameters."""
    out_file = config.pki_dir / "dh.pem"

    key_size = config.key_size if config.algo == "rsa" else 2048
    print(f"\nNotice: Generating DH parameters ({key_size} bit). This may take a while...")

    dh_pem = generate_dh_params(key_size)

    tmp = session.mktemp()
    tmp.write_bytes(dh_pem)
    import shutil
    shutil.move(str(tmp), str(out_file))

    print(f"\nNotice: DH parameters of size {key_size} created at:\\n* {out_file}")


def rand(config: EasyRSAConfig, session: Session, num_bytes: int = 16) -> None:
    """Generate random bytes (hex-encoded)."""
    data = secrets.token_bytes(num_bytes)
    print(data.hex())


def set_pass(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    cert_type: str = "issued",
) -> None:
    """Change (or remove) the passphrase on a private key."""
    key_in = config.pki_dir / "private" / f"{name}.key"

    if not key_in.exists():
        raise EasyRSAUserError(f"No private key found:\\n* {key_in}")

    key_pem = key_in.read_bytes()
    in_password = load_key_password(config.passin)
    key = load_private_key(key_pem, in_password)

    if config.no_pass:
        out_password = None
    elif config.passout:
        out_password = parse_passout(config.passout)
    else:
        out_password = prompt_passphrase(
            f"Enter new passphrase for {name}.key (empty for no passphrase): ",
            confirm=True,
            allow_empty=True,
        )
        if out_password == b"":
            out_password = None

    new_pem = serialize_private_key(key, out_password)

    # Write atomically
    tmp = session.mktemp()
    tmp.write_bytes(new_pem)
    import shutil
    shutil.move(str(tmp), str(key_in))

    if out_password:
        print(f"\nNotice: Passphrase updated for {name}.key")
    else:
        print(f"\nNotice: Passphrase removed from {name}.key")


def check_serial(
    config: EasyRSAConfig,
    session: Session,
    name: str,
) -> None:
    """Check whether a serial number is present in index.txt."""
    from ..index import parse_index, find_by_serial

    index_path = config.pki_dir / "index.txt"
    if not index_path.exists():
        raise EasyRSAUserError("No index.txt found. PKI not initialized?")

    # If name looks like a serial (hex string), use it directly
    serial = name.upper()
    rec = find_by_serial(parse_index(index_path), serial)
    if rec:
        print(f"\nNotice: Serial {serial} found in index.txt:")
        print(f"  Status: {rec.status}")
        print(f"  Subject: {rec.subject}")
        print(f"  Expiry: {rec.expiry}")
    else:
        print(f"\nNotice: Serial {serial} NOT found in index.txt.")


def self_sign(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    cert_type: str = "server",
) -> None:
    """Self-sign a CSR (without a CA) — generates a self-signed certificate."""
    from cryptography import x509 as cx509
    from ..crypto import (
        build_ca_cert,
        generate_serial,
        serialize_cert,
    )
    from ..x509types import build_extensions

    req_in = config.pki_dir / "reqs" / f"{name}.req"
    key_in = config.pki_dir / "private" / f"{name}.key"
    out_crt = config.pki_dir / "issued" / f"{name}.crt"

    if not req_in.exists():
        raise EasyRSAUserError(f"No request found:\\n* {req_in}")
    if not key_in.exists():
        raise EasyRSAUserError(f"No private key found:\\n* {key_in}")

    csr = cx509.load_pem_x509_csr(req_in.read_bytes())
    password = load_key_password(config.passin)
    key = load_private_key(key_in.read_bytes(), password)

    subject_attrs = {}
    for attr in csr.subject:
        subject_attrs[attr.oid._name] = attr.value

    exts = build_extensions(
        cert_type=cert_type,
        config=config,
        subject_public_key=key.public_key(),
    )

    serial = generate_serial()
    cert = build_ca_cert(
        private_key=key,
        subject_attrs=subject_attrs,
        ca_expire_days=config.ca_expire,
        extensions=exts,
        serial=serial,
        digest=config.digest,
    )

    out_crt.parent.mkdir(parents=True, exist_ok=True)
    out_crt.write_bytes(serialize_cert(cert))
    print(f"\nNotice: Self-signed certificate created:\\n* {out_crt}")
