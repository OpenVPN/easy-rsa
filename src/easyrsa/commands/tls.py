"""gen-tls-key command — wraps 'openvpn --genkey'."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..config import EasyRSAConfig
from ..errors import EasyRSAUserError
from ..session import Session


def gen_tls_key(
    config: EasyRSAConfig,
    session: Session,
    key_name: str = "tc",
    key_type: str = "tls-crypt-v2-server",
) -> None:
    """Generate a TLS authentication or crypt key using openvpn --genkey.

    key_type: one of tls-auth, tls-crypt, tls-crypt-v2-server, tls-crypt-v2-client
    """
    out_dir = config.pki_dir / "private"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_key = out_dir / f"{key_name}.key"

    if out_key.exists():
        raise EasyRSAUserError(
            f"TLS key already exists:\\n* {out_key}\\n"
            f"Remove it first or choose a different name."
        )

    # openvpn --genkey <type> <filename>
    cmd = ["openvpn", "--genkey", key_type, str(out_key)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise EasyRSAUserError(
            "openvpn binary not found. Please install OpenVPN to generate TLS keys."
        )

    if result.returncode != 0:
        raise EasyRSAUserError(
            f"openvpn --genkey failed (exit {result.returncode}):\\n"
            f"{result.stderr.strip()}"
        )

    # Set permissions
    out_key.chmod(0o600)

    print(f"\\nNotice: TLS key generated:\\n* {out_key}")
