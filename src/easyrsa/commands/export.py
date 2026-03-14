"""export-p12, export-p7, export-p8, export-p1 commands."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import (
    export_pkcs12,
    load_cert,
    load_private_key,
    serialize_private_key,
)
from ..errors import EasyRSAUserError
from ..passphrase import load_key_password, parse_passin, parse_passout, prompt_passphrase
from ..session import Session


def export_p12(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    nopass: bool = False,
    noca: bool = False,
    nokey: bool = False,
    nofn: bool = False,
    legacy: bool = False,
) -> None:
    """Export a PKCS#12 file."""
    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    key_in = config.pki_dir / "private" / f"{name}.key"
    ca_crt = config.pki_dir / "ca.crt"
    pkcs_out = config.pki_dir / "private" / f"{name}.p12"

    if not crt_in.exists():
        raise EasyRSAUserError(f"Missing User Certificate:\n* {crt_in}")

    cert = load_cert(crt_in.read_bytes())

    # Load CA cert if needed
    ca_certs = []
    if not noca and ca_crt.exists():
        ca_certs = [load_cert(ca_crt.read_bytes())]
    elif not noca and not ca_crt.exists():
        if not config.batch:
            answer = input(
                f"\nMissing CA Certificate. Continue without CA? (type 'yes'): "
            ).strip()
            if answer.lower() != "yes":
                raise EasyRSAUserError("export-p12: Missing CA")

    # Load private key if needed
    private_key = None
    if not nokey:
        if not key_in.exists():
            if not config.batch:
                answer = input(
                    f"\nMissing Private Key. Continue without key? (type 'yes'): "
                ).strip()
                if answer.lower() != "yes":
                    raise EasyRSAUserError("export-p12: Missing key")
        else:
            key_pem = key_in.read_bytes()
            key_password = load_key_password(config.passin)
            private_key = load_private_key(key_pem, key_password)

    # Determine friendly name
    friendly_name = b"" if nofn else name.encode("utf-8")

    # Output password
    if nopass or config.no_pass:
        out_password = None
    elif config.passout:
        out_password = parse_passout(config.passout)
    else:
        out_password = prompt_passphrase(
            f"Enter Export Password for {name}.p12: ", confirm=True
        )

    p12_bytes = export_pkcs12(
        cert=cert,
        private_key=private_key,
        ca_certs=ca_certs,
        friendly_name=friendly_name,
        password=out_password,
        legacy=legacy,
    )

    pkcs_out.parent.mkdir(parents=True, exist_ok=True)
    pkcs_out.write_bytes(p12_bytes)

    # Also create inline p12 file (base64)
    _create_p12_inline(config, name, pkcs_out, cert)

    print(f"\nNotice: Successful export of p12 file. Your exported file is at:\n* {pkcs_out}")


def _create_p12_inline(config: EasyRSAConfig, name: str, p12_path: Path, cert) -> None:
    """Create a base64-encoded inline file for the p12."""
    from ..crypto import get_cert_subject
    inline_dir = config.pki_dir / "inline" / "private"
    inline_dir.mkdir(parents=True, exist_ok=True)
    inline_out = inline_dir / f"{name}.p12-inline"

    cn_dict = get_cert_subject(cert)
    cn = cn_dict.get("CN", name)

    p12_bytes = p12_path.read_bytes()
    b64 = base64.b64encode(p12_bytes).decode("ascii")

    content = (
        f"# Easy-RSA Inline file\n"
        f"# Inline type: BASE64 pkcs12\n"
        f"# commonName: {cn}\n\n"
        f"<pkcs12>\n{b64}\n</pkcs12>\n"
    )
    inline_out.write_text(content, encoding="utf-8")


def export_p7(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    noca: bool = False,
) -> None:
    """Export a PKCS#7 (cert chain) file using cryptography or openssl fallback."""
    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    ca_crt = config.pki_dir / "ca.crt"
    pkcs_out = config.pki_dir / "issued" / f"{name}.p7b"

    if not crt_in.exists():
        raise EasyRSAUserError(f"Missing User Certificate:\n* {crt_in}")

    # Use cryptography library PKCS7 builder
    try:
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.hazmat.primitives.serialization import Encoding

        cert = load_cert(crt_in.read_bytes())
        builder = pkcs7.PKCS7SignatureBuilder()

        # PKCS7 cert-only (no signatures) — use openssl as fallback if not available
        # The cryptography library PKCS7 signing is complex; use openssl for cert chain
        raise ImportError("Use openssl fallback for PKCS7 cert-only")
    except (ImportError, AttributeError):
        # Fallback to openssl subprocess for PKCS#7
        import subprocess
        cmd = ["openssl", "crl2pkcs7", "-nocrl", "-certfile", str(crt_in), "-out", str(pkcs_out)]
        if not noca and ca_crt.exists():
            cmd += ["-certfile", str(ca_crt)]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            raise EasyRSAUserError(f"Failed to export PKCS#7:\n{result.stderr.decode()}")

    print(f"\nNotice: Successful export of p7 file. Your exported file is at:\n* {pkcs_out}")


def export_p8(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    nopass: bool = False,
) -> None:
    """Export private key as PKCS#8."""
    key_in = config.pki_dir / "private" / f"{name}.key"
    pkcs_out = config.pki_dir / "private" / f"{name}.p8"

    if not key_in.exists():
        raise EasyRSAUserError(f"Missing Private Key:\n* {key_in}")

    key_pem = key_in.read_bytes()
    in_password = load_key_password(config.passin)
    key = load_private_key(key_pem, in_password)

    if nopass or config.no_pass:
        out_password = None
    elif config.passout:
        out_password = parse_passout(config.passout)
    else:
        out_password = prompt_passphrase(f"Enter Export Password for {name}.p8: ", confirm=True)

    from cryptography.hazmat.primitives.serialization import (
        BestAvailableEncryption, Encoding, NoEncryption, PrivateFormat
    )
    encryption = BestAvailableEncryption(out_password) if out_password else NoEncryption()
    p8_bytes = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, encryption)

    pkcs_out.write_bytes(p8_bytes)
    print(f"\nNotice: Successful export of p8 file. Your exported file is at:\n* {pkcs_out}")


def export_p1(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    nopass: bool = False,
) -> None:
    """Export RSA private key in PKCS#1 (TraditionalOpenSSL) format."""
    key_in = config.pki_dir / "private" / f"{name}.key"
    pkcs_out = config.pki_dir / "private" / f"{name}.p1"

    if not key_in.exists():
        raise EasyRSAUserError(f"Missing Private Key:\n* {key_in}")

    key_pem = key_in.read_bytes()
    in_password = load_key_password(config.passin)
    key = load_private_key(key_pem, in_password)

    if nopass or config.no_pass:
        out_password = None
    elif config.passout:
        out_password = parse_passout(config.passout)
    else:
        out_password = prompt_passphrase(f"Enter Export Password for {name}.p1: ", confirm=True)

    from cryptography.hazmat.primitives.serialization import (
        BestAvailableEncryption, Encoding, NoEncryption, PrivateFormat
    )
    encryption = BestAvailableEncryption(out_password) if out_password else NoEncryption()
    p1_bytes = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, encryption)

    pkcs_out.write_bytes(p1_bytes)
    print(f"\nNotice: Successful export of p1 file. Your exported file is at:\n* {pkcs_out}")
