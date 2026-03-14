"""revoke, revoke-issued, revoke-expired, revoke-renewed commands."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import (
    cert_subject_to_dn_string,
    get_cert_serial_hex,
    load_cert,
)
from ..errors import EasyRSAUserError
from ..index import (
    IndexRecord,
    asn1_now,
    find_by_serial,
    parse_index,
    write_index,
)
from ..session import Session


# CRL reason abbreviation map
_REASON_MAP = {
    "us": "unspecified",
    "uns": "unspecified",
    "unspecified": "unspecified",
    "kc": "keyCompromise",
    "key": "keyCompromise",
    "keycompromise": "keyCompromise",
    "cc": "CACompromise",
    "ca": "CACompromise",
    "cacompromise": "CACompromise",
    "ac": "affiliationChanged",
    "aff": "affiliationChanged",
    "affiliationchanged": "affiliationChanged",
    "ss": "superseded",
    "sup": "superseded",
    "superseded": "superseded",
    "co": "cessationOfOperation",
    "ces": "cessationOfOperation",
    "cessationofoperation": "cessationOfOperation",
    "ch": "certificateHold",
    "cer": "certificateHold",
    "certificatehold": "certificateHold",
}


def _normalize_reason(reason_str: Optional[str]) -> Optional[str]:
    """Normalize a reason string to canonical form."""
    if not reason_str:
        return None
    normalized = _REASON_MAP.get(reason_str.lower())
    if normalized is None:
        raise EasyRSAUserError(
            f"Unexpected reason: '{reason_str}'. See 'help revoke' for valid reasons."
        )
    return normalized


def revoke(
    config: EasyRSAConfig,
    session: Session,
    cert_dir: str,
    name: str,
    reason: Optional[str] = None,
    move_req_and_key: bool = False,
) -> None:
    """Revoke a certificate.

    cert_dir: 'issued', 'expired', or 'renewed/issued'
    name: file_name_base
    move_req_and_key: if True, also move key and req to revoked/
    """
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    in_dir = config.pki_dir
    key_in = in_dir / "private" / f"{name}.key"
    req_in = in_dir / "reqs" / f"{name}.req"
    inline_pub = in_dir / "inline" / f"{name}.inline"
    inline_pri = in_dir / "inline" / "private" / f"{name}.inline"
    crt_in = in_dir / cert_dir / f"{name}.crt"

    crl_reason = _normalize_reason(reason)

    # Check cert exists
    if not crt_in.exists():
        raise EasyRSAUserError(
            f"Unable to revoke as no certificate was found.\n"
            f"Certificate was expected at:\n* {crt_in}"
        )

    # Load and validate cert
    try:
        cert = load_cert(crt_in.read_bytes())
    except Exception:
        raise EasyRSAUserError(
            f"Unable to revoke as the input-file is not a valid certificate.\n"
            f"Certificate was expected at:\n* {crt_in}"
        )

    cert_serial = get_cert_serial_hex(cert)
    dn = cert_subject_to_dn_string(cert)

    # Check for conflicting issued/expired/renewed certs
    if cert_dir == "issued":
        iss = in_dir / "issued" / f"{name}.crt"
        exp = in_dir / "expired" / f"{name}.crt"
        ren = in_dir / "renewed" / "issued" / f"{name}.crt"
        if iss.exists() and (exp.exists() or ren.exists()):
            if not config.batch:
                raise EasyRSAUserError(
                    f"Conflicting file(s) found.\n"
                    f"Please select which type of 'revoke' command is required:\n"
                    f"* 'revoke-issued' will revoke a current certificate.\n"
                    f"* 'revoke-expired' will revoke an old expired cert.\n"
                    f"* 'revoke-renewed' will revoke an old renewed cert."
                )

    # Set output paths
    out_dir = in_dir / "revoked"
    crt_out = out_dir / "certs_by_serial" / f"{cert_serial}.crt"
    key_out = out_dir / "private_by_serial" / f"{cert_serial}.key"
    req_out = out_dir / "reqs_by_serial" / f"{cert_serial}.req"

    # Check for conflicts
    if crt_out.exists():
        raise EasyRSAUserError(f"Cannot revoke: conflicting certificate exists:\n* {crt_out}")

    # User confirmation
    if not config.batch:
        print(f"\nWARNING: This process is destructive!")
        print(f"These files will be MOVED to the 'revoked' sub-directory:")
        print(f"* {crt_in}")
        if move_req_and_key:
            if key_in.exists():
                print(f"* {key_in}")
            if req_in.exists():
                print(f"* {req_in}")
        answer = input(
            f"\nPlease confirm revocation of certificate:\n{dn}\n"
            f"  serial-number = {cert_serial}\n"
            f"  Reason: {crl_reason or 'None given'}\n"
            f"Type 'yes' to continue with revocation: "
        ).strip()
        if answer.lower() != "yes":
            raise EasyRSAUserError("revoke aborted by user.")

    # Update index.txt: mark record as R
    index_path = in_dir / "index.txt"
    records = parse_index(index_path)
    revoke_dt = asn1_now()
    revoke_info = revoke_dt
    if crl_reason:
        revoke_info = f"{revoke_dt},{crl_reason}"

    new_records = []
    found = False
    for rec in records:
        if rec.serial.upper() == cert_serial.upper():
            found = True
            new_records.append(IndexRecord(
                status="R",
                expiry=rec.expiry,
                revoke_info=revoke_info,
                serial=rec.serial,
                unknown=rec.unknown,
                subject=rec.subject,
            ))
        else:
            new_records.append(rec)

    if not found:
        # Append new R record
        from ..crypto import get_cert_not_after
        from ..index import asn1_from_datetime
        expiry_asn1 = asn1_from_datetime(get_cert_not_after(cert))
        new_records.append(IndexRecord(
            status="R",
            expiry=expiry_asn1,
            revoke_info=revoke_info,
            serial=cert_serial,
            unknown="unknown",
            subject=dn,
        ))

    write_index(new_records, index_path)

    # Create revoke subdirs
    for sd in ["certs_by_serial", "private_by_serial", "reqs_by_serial"]:
        (out_dir / sd).mkdir(parents=True, exist_ok=True)

    # Move cert
    shutil.move(str(crt_in), str(crt_out))

    # Optionally move key and req
    if move_req_and_key:
        if req_in.exists():
            shutil.move(str(req_in), str(req_out))
        if key_in.exists():
            shutil.move(str(key_in), str(key_out))

    # Remove PKCS files
    for pkcs_ext in ("p12", "p7b", "p8", "p1"):
        for pkcs_dir in (in_dir / "issued", in_dir / "private"):
            p = pkcs_dir / f"{name}.{pkcs_ext}"
            if p.exists():
                p.unlink()

    # Remove inline files
    for f in [inline_pub, inline_pri]:
        if f.exists():
            f.unlink(missing_ok=True)

    print(f"\n                    * IMPORTANT *\n")
    print(f"Revocation was successful. You must run 'gen-crl' and upload")
    print(f"a new CRL to your infrastructure in order to prevent the revoked")
    print(f"certificate from being accepted.")
