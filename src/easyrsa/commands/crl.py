"""gen-crl and update-db commands."""

from __future__ import annotations

import datetime
import shutil
from pathlib import Path

from ..config import EasyRSAConfig
from ..crypto import (
    build_crl,
    get_cert_not_after,
    get_cert_serial_hex,
    hex_to_serial,
    load_cert,
    load_private_key,
    serialize_crl,
)
from ..errors import EasyRSAUserError
from ..index import (
    IndexRecord,
    asn1_now,
    datetime_from_asn1,
    parse_index,
    write_index,
)
from ..passphrase import load_key_password
from ..session import Session


def gen_crl(config: EasyRSAConfig, session: Session) -> None:
    """Generate a new CRL from the index.txt R records."""
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    out_file = config.pki_dir / "crl.pem"

    # Load CA cert and key
    ca_cert_pem = (config.pki_dir / "ca.crt").read_bytes()
    ca_cert = load_cert(ca_cert_pem)

    ca_key_pem = (config.pki_dir / "private" / "ca.key").read_bytes()
    password = load_key_password(config.passin)
    ca_key = load_private_key(ca_key_pem, password)

    # Collect revoked certs from index.txt
    index_path = config.pki_dir / "index.txt"
    records = parse_index(index_path)

    revoked_entries = []
    for rec in records:
        if rec.status != "R":
            continue
        try:
            serial_int = hex_to_serial(rec.serial)
        except ValueError:
            continue

        # Parse revoke_info: "YYMMDDHHMMSSZ[,reason]"
        revoke_info = rec.revoke_info
        reason_str = None
        if "," in revoke_info:
            date_part, reason_str = revoke_info.split(",", 1)
        else:
            date_part = revoke_info

        try:
            revoke_dt = datetime_from_asn1(date_part)
        except Exception:
            revoke_dt = datetime.datetime.utcnow().replace(microsecond=0)

        revoked_entries.append((serial_int, revoke_dt, reason_str))

    # Build CRL
    crl = build_crl(
        ca_cert=ca_cert,
        ca_key=ca_key,
        revoked_certs=revoked_entries,
        crl_days=config.crl_days,
        digest=config.digest,
    )

    crl_pem = serialize_crl(crl)

    # Write to temp then move
    tmp = session.mktemp()
    tmp.write_bytes(crl_pem)
    shutil.copy2(str(tmp), str(out_file))

    # Write DER version
    try:
        crl_der = crl.public_bytes(
            __import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.DER
        )
        der_file = config.pki_dir / "crl.der"
        der_file.write_bytes(crl_der)
        print(f"\nNotice: An updated CRL DER copy has been created:\n* {der_file}")
    except Exception:
        pass

    print(f"\nNotice: An updated CRL has been created:\n* {out_file}")
    print(f"\nIMPORTANT: When the CRL expires, an OpenVPN Server which uses a")
    print(f"CRL will reject ALL new connections, until the CRL is replaced.")


def update_db(config: EasyRSAConfig, session: Session) -> None:
    """Check index.txt for expired certs and update E status."""
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    index_path = config.pki_dir / "index.txt"
    records = parse_index(index_path)
    now = datetime.datetime.utcnow()

    changed = False
    new_records = []
    for rec in records:
        if rec.status == "V":
            try:
                expiry = datetime_from_asn1(rec.expiry)
            except Exception:
                new_records.append(rec)
                continue
            if expiry <= now:
                new_records.append(IndexRecord(
                    status="E",
                    expiry=rec.expiry,
                    revoke_info="",
                    serial=rec.serial,
                    unknown=rec.unknown,
                    subject=rec.subject,
                ))
                changed = True
            else:
                new_records.append(rec)
        else:
            new_records.append(rec)

    if changed:
        write_index(new_records, index_path)
        print("\nNotice: Database updated.")
    else:
        print("\nNotice: No changes needed.")
