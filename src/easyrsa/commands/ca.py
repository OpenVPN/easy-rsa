"""build-ca and renew-ca commands."""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import (
    build_ca_cert,
    build_csr,
    cert_subject_to_dn_string,
    generate_key,
    generate_serial,
    get_cert_serial_hex,
    load_cert,
    load_private_key,
    serialize_cert,
    serialize_csr,
    serialize_private_key,
    serial_to_hex,
)
from ..errors import EasyRSAUserError
from ..index import asn1_from_datetime, parse_index
from ..passphrase import load_key_password, parse_passout, prompt_passphrase
from ..pki import create_ca_dirs, init_ca_files, verify_pki
from ..session import Session
from ..x509types import build_extensions


def _build_subject(config: EasyRSAConfig, cn_override: str = "") -> dict:
    """Build subject attrs dict from config."""
    cn = cn_override or config.req_cn
    if config.dn_mode == "org":
        return {
            "CN": cn,
            "C": config.req_country,
            "ST": config.req_province,
            "L": config.req_city,
            "O": config.req_org,
            "OU": config.req_ou,
            "emailAddress": config.req_email,
            "serialNumber": config.req_serial,
        }
    else:
        return {"CN": cn}


def build_ca(config: EasyRSAConfig, session: Session, sub_ca: bool = False) -> None:
    """Build a new CA or sub-CA CSR.

    sub_ca=True: generate CSR for intermediate CA instead of self-signed cert.
    """
    # Check for peer-fingerprint mode
    if (config.pki_dir / "peer-fp.mode").exists():
        raise EasyRSAUserError("Cannot create CA in a peer-fingerprint PKI")

    # Check for existing CA
    out_key = config.pki_dir / "private" / "ca.key"
    out_cert = config.pki_dir / "ca.crt"
    out_req = config.pki_dir / "reqs" / "ca.req"

    if out_cert.exists() and not sub_ca:
        raise EasyRSAUserError(
            "Unable to create a CA as you already seem to have one set up.\n"
            "If you intended to start a new CA, run init-pki first."
        )
    if out_key.exists():
        raise EasyRSAUserError(
            "A CA private key exists but no ca.crt is found in your PKI.\n"
            "Refusing to create a new CA as this would overwrite your\n"
            "current CA. To start a new CA, run init-pki first."
        )

    # Determine CN
    cn = config.req_cn
    if cn == "ChangeMe":
        cn = "Easy-RSA Sub-CA" if sub_ca else "Easy-RSA CA"

    # Create CA dirs and init files
    verify_pki(config.pki_dir)
    create_ca_dirs(config.pki_dir)
    init_ca_files(config.pki_dir)

    # Get passphrase
    password = _get_ca_password(config)

    # Generate key
    key = generate_key(config.algo, config.key_size, config.curve)

    # Write key to temp file
    key_tmp = session.mktemp()
    key_pem = serialize_private_key(key, password)
    key_tmp.write_bytes(key_pem)

    if sub_ca:
        # Generate CSR for sub-CA
        subject = _build_subject(config, cn)
        csr = build_csr(subject_attrs=subject, private_key=key, digest=config.digest)
        req_pem = serialize_csr(csr)
        req_tmp = session.mktemp()
        req_tmp.write_bytes(req_pem)
        # Move to final location
        _move_file(key_tmp, out_key)
        _move_file(req_tmp, out_req)
        print(f"\nNotice: Your intermediate CA request is at:\n* {out_req}")
        print(f"  Sign it with your parent CA and place the result at:\n* {out_cert}")
    else:
        # Build self-signed CA certificate
        subject = _build_subject(config, cn)

        # Build extensions
        exts = build_extensions(
            cert_type="ca",
            config=config,
            subject_public_key=key.public_key(),
        )

        serial = generate_serial()
        cert = build_ca_cert(
            private_key=key,
            subject_attrs=subject,
            ca_expire_days=config.ca_expire,
            extensions=exts,
            serial=serial,
            digest=config.digest,
            start_date=config.start_date,
            end_date=config.end_date,
        )

        cert_tmp = session.mktemp()
        cert_tmp.write_bytes(serialize_cert(cert))

        # Move to final locations
        _move_file(key_tmp, out_key)
        _move_file(cert_tmp, out_cert)

        print(f"\nNotice: CA creation complete. Your new CA certificate is at:\n* {out_cert}")
        print("Build-ca completed successfully.")


def _get_ca_password(config: EasyRSAConfig) -> Optional[bytes]:
    """Determine CA key password based on config."""
    if config.no_pass:
        return None
    if config.passout:
        return parse_passout(config.passout)
    if config.batch:
        return None
    # Interactive
    return prompt_passphrase("Enter New CA Key Passphrase: ", confirm=True)


def _move_file(src: Path, dst: Path) -> None:
    """Move src to dst, creating parent dirs as needed."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def renew_ca_cert(config: EasyRSAConfig, session: Session) -> None:
    """Renew CA certificate keeping the same key."""
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    ca_key_file = config.pki_dir / "private" / "ca.key"
    ca_cert_file = config.pki_dir / "ca.crt"
    exp_ca_list = config.pki_dir / "expired-ca.list"

    # Load existing key and cert
    password = load_key_password(config.passin)
    key_pem = ca_key_file.read_bytes()
    ca_key = load_private_key(key_pem, password)

    old_cert_pem = ca_cert_file.read_bytes()
    old_cert = load_cert(old_cert_pem)

    # Get CN from old cert
    cn = old_cert.subject.get_attributes_for_oid(
        __import__("cryptography.x509.oid", fromlist=["NameOID"]).NameOID.COMMON_NAME
    )[0].value

    # Build new cert
    subject = {"CN": cn}
    if config.dn_mode == "org":
        subject = _build_subject(config, cn)

    exts = build_extensions(
        cert_type="ca",
        config=config,
        subject_public_key=ca_key.public_key(),
    )

    serial = generate_serial()
    new_cert = build_ca_cert(
        private_key=ca_key,
        subject_attrs=subject,
        ca_expire_days=config.ca_expire,
        extensions=exts,
        serial=serial,
        digest=config.digest,
    )

    # Confirm
    if not config.batch:
        print("\nNEW CA CERTIFICATE:")
        print(f"  Serial: {serial_to_hex(serial)}")
        answer = input("\nInstall the new CA certificate? (type 'yes' to confirm): ").strip()
        if answer.lower() != "yes":
            raise EasyRSAUserError("Renewal aborted by user.")

    # Archive old cert
    old_serial = get_cert_serial_hex(old_cert)
    _append_old_ca_to_list(old_cert_pem, exp_ca_list)

    # Write new cert
    new_pem = serialize_cert(new_cert)
    tmp = session.mktemp()
    tmp.write_bytes(new_pem)
    _move_file(tmp, ca_cert_file)

    print(f"\nNotice: CA certificate has been successfully renewed.")
    print(f"  Old CA archived to: {exp_ca_list}")
    print(f"  Renewed CA at: {ca_cert_file}")


def _append_old_ca_to_list(old_cert_pem: bytes, list_file: Path) -> None:
    """Append old CA cert PEM to the expired CA list."""
    list_file.parent.mkdir(parents=True, exist_ok=True)
    header = "# Easy-RSA expired CA certificate list:\n"
    sep = "# =====================================\n"
    mode = "a" if list_file.exists() else "w"
    with open(list_file, mode, encoding="utf-8") as f:
        if mode == "w":
            f.write(header)
            f.write(sep + "\n")
        f.write(old_cert_pem.decode("utf-8"))
        f.write("\n")
