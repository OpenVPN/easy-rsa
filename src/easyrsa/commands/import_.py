"""import-req, import-ca, import-tls-key commands."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import load_cert, load_private_key
from ..errors import EasyRSAUserError
from ..session import Session


def import_req(
    config: EasyRSAConfig,
    session: Session,
    req_file: str,
    short_name: str,
) -> None:
    """Import an external certificate request (CSR) into the PKI."""
    from cryptography import x509 as cx509

    req_path = Path(req_file)
    if not req_path.exists():
        raise EasyRSAUserError(f"CSR file not found:\\n* {req_path}")

    # Validate it's a real CSR
    req_pem = req_path.read_bytes()
    try:
        csr = cx509.load_pem_x509_csr(req_pem)
    except Exception:
        try:
            csr = cx509.load_der_x509_csr(req_pem)
            # Convert to PEM for storage
            from cryptography.hazmat.primitives.serialization import Encoding
            req_pem = csr.public_bytes(Encoding.PEM)
        except Exception as e:
            raise EasyRSAUserError(f"Failed to parse CSR: {e}")

    out_req = config.pki_dir / "reqs" / f"{short_name}.req"
    if out_req.exists():
        raise EasyRSAUserError(
            f"Cannot import: request already exists:\\n* {out_req}\\n"
            f"Use a different short-name."
        )

    out_req.parent.mkdir(parents=True, exist_ok=True)
    out_req.write_bytes(req_pem)

    print(f"\\nNotice: Request file imported successfully.\\n* {out_req}")
    print(f"\\nYou may sign this request with:")
    print(f"  easyrsa sign-req <type> {short_name}")


def import_ca(
    config: EasyRSAConfig,
    session: Session,
    ca_file: str,
    copy_ext: bool = False,
    sub_ca: bool = False,
) -> None:
    """Import a CA certificate (for intermediate/sub-CA scenarios)."""
    ca_path = Path(ca_file)
    if not ca_path.exists():
        raise EasyRSAUserError(f"CA certificate file not found:\\n* {ca_path}")

    # Validate it's a real certificate
    ca_pem = ca_path.read_bytes()
    try:
        cert = load_cert(ca_pem)
    except Exception as e:
        raise EasyRSAUserError(f"Failed to parse CA certificate: {e}")

    out_ca = config.pki_dir / "ca.crt"
    if out_ca.exists():
        raise EasyRSAUserError(
            f"Cannot import: CA certificate already exists:\\n* {out_ca}\\n"
            f"Run 'init-pki' to start fresh if needed."
        )

    out_ca.parent.mkdir(parents=True, exist_ok=True)
    out_ca.write_bytes(ca_pem)

    print(f"\\nNotice: CA certificate imported successfully:\\n* {out_ca}")


def import_tls_key(
    config: EasyRSAConfig,
    session: Session,
    tls_key_file: str,
    key_name: str = "tc",
) -> None:
    """Import a TLS authentication/crypt key (ta.key / tc.key) into the PKI."""
    tls_path = Path(tls_key_file)
    if not tls_path.exists():
        raise EasyRSAUserError(f"TLS key file not found:\\n* {tls_path}")

    # Read and do basic validation — should be OpenVPN static key
    tls_data = tls_path.read_bytes()
    tls_text = tls_data.decode("utf-8", errors="replace")

    # OpenVPN static keys contain a BEGIN/END block
    if "BEGIN OpenVPN Static key" not in tls_text and "BEGIN OpenVPN tls-auth key" not in tls_text:
        # May still be a valid raw key file; warn but allow
        if not config.batch:
            answer = input(
                "\\nFile does not appear to be an OpenVPN static key. Import anyway? (type 'yes'): "
            ).strip()
            if answer.lower() != "yes":
                raise EasyRSAUserError("import-tls-key: aborted by user.")

    # Determine output path: pki/private/<key_name>.key
    out_dir = config.pki_dir / "private"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_key = out_dir / f"{key_name}.key"

    # Honor no-clobber: do not overwrite existing key
    if out_key.exists():
        raise EasyRSAUserError(
            f"Cannot import: TLS key already exists:\\n* {out_key}\\n"
            f"Remove or rename the existing file first."
        )

    shutil.copy2(str(tls_path), str(out_key))
    # Set permissions to 0600
    out_key.chmod(0o600)

    print(f"\\nNotice: TLS key imported successfully:\\n* {out_key}")
