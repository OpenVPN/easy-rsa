"""show-cert, show-req, show-ca, show-crl, verify-cert, show-expire, show-revoke,
show-renew, display-dn, show-eku commands."""

from __future__ import annotations

import datetime
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import (
    get_cert_not_after,
    get_cert_serial_hex,
    load_cert,
)
from ..errors import EasyRSAUserError
from ..index import parse_index, datetime_from_asn1
from ..session import Session


def _cert_text(cert) -> str:
    """Return human-readable text for a certificate (using cryptography library)."""
    from cryptography.hazmat.primitives import serialization
    lines = []
    lines.append(f"Certificate:")
    lines.append(f"  Serial Number: {get_cert_serial_hex(cert)}")
    lines.append(f"  Subject: {cert.subject.rfc4514_string()}")
    lines.append(f"  Issuer: {cert.issuer.rfc4514_string()}")
    lines.append(f"  Not Before: {cert.not_valid_before_utc if hasattr(cert, 'not_valid_before_utc') else cert.not_valid_before}")
    lines.append(f"  Not After : {cert.not_valid_after_utc if hasattr(cert, 'not_valid_after_utc') else cert.not_valid_after}")
    # Extensions
    try:
        for ext in cert.extensions:
            lines.append(f"  Extension: {ext.oid.dotted_string} critical={ext.critical}")
            lines.append(f"    {ext.value}")
    except Exception:
        pass
    return "\n".join(lines)


def _csr_text(csr) -> str:
    """Return human-readable text for a CSR."""
    lines = []
    lines.append(f"Certificate Request:")
    lines.append(f"  Subject: {csr.subject.rfc4514_string()}")
    try:
        for ext in csr.extensions:
            lines.append(f"  Extension: {ext.oid.dotted_string} critical={ext.critical}")
            lines.append(f"    {ext.value}")
    except Exception:
        pass
    return "\n".join(lines)


def show_cert(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    notext: bool = False,
) -> None:
    """Display a certificate."""
    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    if not crt_in.exists():
        # Check revoked and expired
        for subdir in ("revoked/certs_by_serial", "expired", "renewed/issued"):
            alt = config.pki_dir / subdir / f"{name}.crt"
            if alt.exists():
                crt_in = alt
                break
        else:
            raise EasyRSAUserError(f"No certificate found for '{name}'")

    cert_pem = crt_in.read_bytes()
    cert = load_cert(cert_pem)

    if not notext:
        print(_cert_text(cert))
    print(cert_pem.decode("utf-8", errors="replace"))


def show_req(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    notext: bool = False,
) -> None:
    """Display a certificate request."""
    from cryptography import x509 as cx509
    req_in = config.pki_dir / "reqs" / f"{name}.req"
    if not req_in.exists():
        raise EasyRSAUserError(f"No request found for '{name}':\\n* {req_in}")

    req_pem = req_in.read_bytes()
    try:
        from cryptography.hazmat.primitives.serialization import Encoding
        csr = cx509.load_pem_x509_csr(req_pem)
    except Exception as e:
        raise EasyRSAUserError(f"Failed to parse request: {e}")

    if not notext:
        print(_csr_text(csr))
    print(req_pem.decode("utf-8", errors="replace"))


def show_ca(
    config: EasyRSAConfig,
    session: Session,
    notext: bool = False,
) -> None:
    """Display the CA certificate."""
    ca_crt = config.pki_dir / "ca.crt"
    if not ca_crt.exists():
        raise EasyRSAUserError("No CA certificate found.")

    cert_pem = ca_crt.read_bytes()
    cert = load_cert(cert_pem)

    if not notext:
        print(_cert_text(cert))
    print(cert_pem.decode("utf-8", errors="replace"))


def show_crl(
    config: EasyRSAConfig,
    session: Session,
    notext: bool = False,
) -> None:
    """Display the CRL."""
    crl_file = config.pki_dir / "crl.pem"
    if not crl_file.exists():
        raise EasyRSAUserError("No CRL found. Run 'gen-crl' first.")

    from cryptography import x509 as cx509
    crl_pem = crl_file.read_bytes()
    try:
        crl = cx509.load_pem_x509_crl(crl_pem)
    except Exception as e:
        raise EasyRSAUserError(f"Failed to parse CRL: {e}")

    if not notext:
        lines = []
        lines.append("Certificate Revocation List (CRL):")
        lines.append(f"  Issuer: {crl.issuer.rfc4514_string()}")
        nbu = crl.last_update_utc if hasattr(crl, 'last_update_utc') else crl.last_update
        nau = crl.next_update_utc if hasattr(crl, 'next_update_utc') else crl.next_update
        lines.append(f"  Last Update: {nbu}")
        lines.append(f"  Next Update: {nau}")
        lines.append(f"  Revoked Certificates: {len(list(crl))}")
        for rev in crl:
            lines.append(f"    Serial: {format(rev.serial_number, 'X').upper()}")
            lines.append(f"    Revocation Date: {rev.revocation_date_utc if hasattr(rev, 'revocation_date_utc') else rev.revocation_date}")
        print("\n".join(lines))

    print(crl_pem.decode("utf-8", errors="replace"))


def verify_cert(
    config: EasyRSAConfig,
    session: Session,
    name: str,
) -> None:
    """Verify a certificate against the CA."""
    from cryptography.hazmat.primitives.asymmetric import padding as apadding
    from cryptography import x509 as cx509

    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    ca_crt = config.pki_dir / "ca.crt"

    if not crt_in.exists():
        raise EasyRSAUserError(f"No certificate found for '{name}'")
    if not ca_crt.exists():
        raise EasyRSAUserError("No CA certificate found.")

    cert = load_cert(crt_in.read_bytes())
    ca_cert = load_cert(ca_crt.read_bytes())

    try:
        from ..crypto import verify_cert_signature
        verify_cert_signature(cert, ca_cert)
        print(f"\nNotice: Certificate '{name}' verified OK against CA.")
    except Exception as e:
        raise EasyRSAUserError(f"Certificate verification failed: {e}")


def show_expire(
    config: EasyRSAConfig,
    session: Session,
    days: int = 0,
) -> None:
    """Show certificates that will expire within <days> days (or all if 0)."""
    index_path = config.pki_dir / "index.txt"
    if not index_path.exists():
        raise EasyRSAUserError("No index.txt found. PKI not initialized?")

    records = parse_index(index_path)
    now = datetime.datetime.utcnow()
    cutoff = now + datetime.timedelta(days=days) if days > 0 else None

    found = False
    for rec in records:
        if rec.status not in ("V", "E"):
            continue
        try:
            exp_dt = datetime_from_asn1(rec.expiry)
        except Exception:
            continue

        if cutoff is None or exp_dt <= cutoff:
            remaining = (exp_dt - now).days
            status_str = "EXPIRED" if exp_dt <= now else f"expires in {remaining} days"
            print(f"  {rec.serial}  {rec.subject}  [{status_str}]")
            found = True

    if not found:
        print(f"\nNotice: No certificates found expiring within {days} days.")


def show_revoke(
    config: EasyRSAConfig,
    session: Session,
) -> None:
    """Show revoked certificates from index.txt."""
    index_path = config.pki_dir / "index.txt"
    if not index_path.exists():
        raise EasyRSAUserError("No index.txt found. PKI not initialized?")

    records = parse_index(index_path)
    found = False
    for rec in records:
        if rec.status != "R":
            continue
        reason = ""
        if "," in rec.revoke_info:
            _, reason = rec.revoke_info.split(",", 1)
            reason = f"  reason={reason}"
        print(f"  Serial: {rec.serial}  {rec.subject}  revoked={rec.revoke_info}{reason}")
        found = True

    if not found:
        print("\nNotice: No revoked certificates found.")


def show_renew(
    config: EasyRSAConfig,
    session: Session,
) -> None:
    """Show renewed certificates."""
    renewed_dir = config.pki_dir / "renewed" / "issued"
    if not renewed_dir.exists():
        print("\nNotice: No renewed certificates directory found.")
        return

    certs = list(renewed_dir.glob("*.crt"))
    if not certs:
        print("\nNotice: No renewed certificates found.")
        return

    for crt_path in sorted(certs):
        try:
            cert = load_cert(crt_path.read_bytes())
            serial = get_cert_serial_hex(cert)
            not_after = get_cert_not_after(cert)
            name = crt_path.stem
            print(f"  {name}  serial={serial}  expires={not_after.date()}")
        except Exception:
            print(f"  {crt_path.name} (unreadable)")


def display_dn(
    config: EasyRSAConfig,
    session: Session,
    name: str,
) -> None:
    """Display the DN of a certificate or request."""
    # Try cert first
    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    req_in = config.pki_dir / "reqs" / f"{name}.req"

    if crt_in.exists():
        from ..crypto import cert_subject_to_dn_string
        cert = load_cert(crt_in.read_bytes())
        print(cert_subject_to_dn_string(cert))
    elif req_in.exists():
        from cryptography import x509 as cx509
        from ..crypto import csr_subject_to_dn_string
        csr = cx509.load_pem_x509_csr(req_in.read_bytes())
        print(csr_subject_to_dn_string(csr))
    else:
        raise EasyRSAUserError(f"No certificate or request found for '{name}'")


def show_eku(
    config: EasyRSAConfig,
    session: Session,
    name: str,
) -> None:
    """Show Extended Key Usage of a certificate."""
    from cryptography import x509 as cx509

    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    if not crt_in.exists():
        raise EasyRSAUserError(f"No certificate found for '{name}'")

    cert = load_cert(crt_in.read_bytes())

    try:
        eku = cert.extensions.get_extension_for_class(cx509.ExtendedKeyUsage)
        oid_names = []
        for oid in eku.value:
            oid_names.append(getattr(oid, "_name", oid.dotted_string))
        print(f"Extended Key Usage for '{name}':")
        for n in oid_names:
            print(f"  {n}")
    except cx509.ExtensionNotFound:
        print(f"No Extended Key Usage extension found for '{name}'.")
