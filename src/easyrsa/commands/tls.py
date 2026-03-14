"""gen-tls-key command — pure-Python TLS key generation.

All three OpenVPN key types are generated using only the Python standard
library (secrets) and the cryptography package.  No openvpn binary needed.

Key formats are derived directly from the OpenVPN source (src/openvpn/tls_crypt.c
and src/openvpn/crypto.c):

  tls-auth / tls-crypt (v1)
    256 bytes of OS random, hex-encoded, 16 bytes per line.
    Header: "-----BEGIN OpenVPN Static key V1-----"
    Both key types share the same on-disk format; OpenVPN uses different
    sub-slices at runtime (HMAC-SHA1 for tls-auth, AES-256-CTR +
    HMAC-SHA256 for tls-crypt).

  tls-crypt-v2 server
    128 bytes of OS random, base64 PEM, 64 chars per line.
    Header: "-----BEGIN OpenVPN tls-crypt-v2 server key-----"

  tls-crypt-v2 client  (requires existing server key)
    256 bytes of OS random (the client key Kc), SIV-wrapped with the
    server key (AES-256-CTR encrypt + HMAC-SHA256 tag) plus a 9-byte
    timestamp metadata block.  Total payload = 555 bytes, base64 PEM.
    Header: "-----BEGIN OpenVPN tls-crypt-v2 client key-----"
"""

from __future__ import annotations

import base64
import re
import secrets
import struct
import time
from pathlib import Path

from ..config import EasyRSAConfig
from ..errors import EasyRSAError, EasyRSAUserError
from ..session import Session


# ---------------------------------------------------------------------------
# Internal key-generation helpers
# ---------------------------------------------------------------------------

def _gen_static_key() -> str:
    """256 bytes OS random → OpenVPN Static key V1 (hex, 16 bytes/line)."""
    raw = secrets.token_bytes(256)
    lines = [
        "#",
        "# 2048 bit OpenVPN static key",
        "#",
        "-----BEGIN OpenVPN Static key V1-----",
    ]
    for i in range(0, 256, 16):
        lines.append(raw[i:i + 16].hex())
    lines.append("-----END OpenVPN Static key V1-----")
    return "\n".join(lines) + "\n"


def _gen_tls_crypt_v2_server_key() -> tuple[str, bytes]:
    """128 bytes OS random → PEM + raw bytes (needed for client wrap)."""
    raw = secrets.token_bytes(128)
    b64 = base64.b64encode(raw).decode()
    lines = ["-----BEGIN OpenVPN tls-crypt-v2 server key-----"]
    for i in range(0, len(b64), 64):
        lines.append(b64[i:i + 64])
    lines.append("-----END OpenVPN tls-crypt-v2 server key-----")
    return "\n".join(lines) + "\n", raw


def _load_tls_crypt_v2_server_key(path: Path) -> bytes:
    """Read a tls-crypt-v2 server key PEM file and return the 128 raw bytes."""
    text = path.read_text(encoding="utf-8")
    # Extract base64 payload between PEM header and footer
    m = re.search(
        r"-----BEGIN OpenVPN tls-crypt-v2 server key-----\s+"
        r"([A-Za-z0-9+/=\s]+?)"
        r"-----END OpenVPN tls-crypt-v2 server key-----",
        text,
    )
    if not m:
        raise EasyRSAError(f"Not a valid tls-crypt-v2 server key file: {path}")
    raw = base64.b64decode(m.group(1).replace("\n", "").strip())
    if len(raw) != 128:
        raise EasyRSAError(
            f"tls-crypt-v2 server key has unexpected length {len(raw)} (expected 128)"
        )
    return raw


def _gen_tls_crypt_v2_client_key(
    server_key_raw: bytes,
    metadata: bytes | None = None,
) -> str:
    """Wrap a fresh 256-byte client key with the server key (SIV construction).

    Implements tls_crypt_v2_write_client_key_file() from OpenVPN source:
      - tag  = HMAC-SHA256(server_hmac_key, net_len || Kc || metadata)
      - IV   = tag[0:16]
      - enc  = AES-256-CTR(server_cipher_key, IV, Kc || metadata)
      - WKc  = tag || enc || net_len_be          (299 bytes)
      - file = base64(Kc || WKc)                 (555 bytes)
    """
    from cryptography.hazmat.primitives import hmac as crypto_hmac, hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend

    assert len(server_key_raw) == 128

    # Key layout inside struct key (cipher[64] then hmac[64]):
    server_cipher_key = server_key_raw[0:32]   # AES-256-CTR key
    server_hmac_key   = server_key_raw[64:96]  # HMAC-SHA256 key

    # 1. Client key material: sizeof(key2.keys) = 2 × 128 = 256 bytes
    kc = secrets.token_bytes(256)

    # 2. Metadata: type=0x01 (timestamp) + 8-byte big-endian int64 unix timestamp
    if metadata is None:
        metadata = bytes([0x01]) + struct.pack(">q", int(time.time()))

    # 3. net_len = sizeof(tag=32) + sizeof(kc) + sizeof(metadata) + sizeof(uint16=2)
    tagged_len = 32 + len(kc) + len(metadata) + 2
    net_len_be = struct.pack(">H", tagged_len)

    # 4. tag = HMAC-SHA256(server_hmac_key, net_len || Kc || metadata)
    h = crypto_hmac.HMAC(server_hmac_key, hashes.SHA256(), backend=default_backend())
    h.update(net_len_be)
    h.update(kc)
    h.update(metadata)
    tag = h.finalize()  # 32 bytes

    # 5. Encrypt Kc || metadata with AES-256-CTR, IV = tag[0:16]
    cipher = Cipher(
        algorithms.AES(server_cipher_key),
        modes.CTR(tag[:16]),
        backend=default_backend(),
    )
    enc = cipher.encryptor()
    ciphertext = enc.update(kc + metadata) + enc.finalize()

    # 6. WKc = tag || ciphertext || net_len_be
    wkc = tag + ciphertext + net_len_be

    # 7. PEM-encode Kc || WKc
    payload = kc + wkc
    b64 = base64.b64encode(payload).decode()
    lines = ["-----BEGIN OpenVPN tls-crypt-v2 client key-----"]
    for i in range(0, len(b64), 64):
        lines.append(b64[i:i + 64])
    lines.append("-----END OpenVPN tls-crypt-v2 client key-----")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Public command
# ---------------------------------------------------------------------------

_STATIC_TYPES = {"tls-auth", "tls-crypt"}
_V2_SERVER    = "tls-crypt-v2-server"
_V2_CLIENT    = "tls-crypt-v2-client"

# Label written as the first comment line, matching what openvpn writes.
_LABEL = {
    "tls-auth":  "# Easy-RSA TLS-AUTH key\n",
    "tls-crypt": "# Easy-RSA TLS-CRYPT key\n",
}


def gen_tls_key(
    config: EasyRSAConfig,
    session: Session,
    key_type: str = "tls-crypt",
    server_key_path: Path | None = None,
) -> None:
    """Generate a TLS authentication or crypt key using pure Python.

    key_type: one of 'tls-auth', 'tls-crypt', 'tls-crypt-v2-server',
              or 'tls-crypt-v2-client' (requires server_key_path).

    Output always goes to pki/private/easyrsa-tls.key (the fixed path that
    inline_file() looks for).
    """
    out_dir = config.pki_dir / "private"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_key = out_dir / "easyrsa-tls.key"

    # Generate key material (before any unlink, so server key can be read
    # even when server_key_path == out_key)
    if key_type in _STATIC_TYPES:
        content = _LABEL.get(key_type, "") + _gen_static_key()

    elif key_type == _V2_SERVER:
        pem, _ = _gen_tls_crypt_v2_server_key()
        content = pem

    elif key_type == _V2_CLIENT:
        if server_key_path is None:
            # Default: look for the server key in the same PKI
            server_key_path = out_dir / "easyrsa-tls.key"
        if not server_key_path.exists():
            raise EasyRSAUserError(
                f"tls-crypt-v2 server key not found at:\n* {server_key_path}\n"
                f"Generate one first with: gen-tls-key tls-crypt-v2-server"
            )
        server_raw = _load_tls_crypt_v2_server_key(server_key_path)
        content = _gen_tls_crypt_v2_client_key(server_raw)

    else:
        raise EasyRSAUserError(
            f"Unknown TLS key type: '{key_type}'\n"
            f"Valid types: tls-auth, tls-crypt, tls-crypt-v2-server, tls-crypt-v2-client"
        )

    if out_key.exists():
        if not config.batch:
            answer = input(
                f"\nWARNING: TLS key already exists at:\n  {out_key}\n"
                f"Type 'yes' to overwrite: "
            ).strip()
            if answer.lower() != "yes":
                raise EasyRSAUserError("Aborted: TLS key not overwritten.")
        out_key.unlink()

    # Write atomically with restricted permissions
    tmp = session.mktemp()
    tmp.write_text(content, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.rename(out_key)

    print(f"\nNotice: TLS {key_type} key generated:\n* {out_key}")
