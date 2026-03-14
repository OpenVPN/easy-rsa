"""Build inline files (.inline) for Easy-RSA."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import EasyRSAConfig
from .crypto import get_cert_fingerprint, load_cert
from .errors import EasyRSAUserError


def build_inline(
    config: EasyRSAConfig,
    name: str,
    include_ca: bool = True,
    include_cert: bool = True,
    include_key: bool = True,
    include_tls: bool = False,
    tls_key_name: str = "tc",
    tls_tag: str = "tls-crypt",
) -> None:
    """Build a .inline file containing all PKI components for a client/server.

    Creates two files:
      pki/inline/<name>.inline         (public: ca, cert, optionally tls)
      pki/inline/private/<name>.inline (private: ca, cert, key, optionally tls)
    """
    pki = config.pki_dir
    ca_crt = pki / "ca.crt"
    crt_in = pki / "issued" / f"{name}.crt"
    key_in = pki / "private" / f"{name}.key"
    tls_in = pki / "private" / f"{tls_key_name}.key"

    # Verify required files
    if include_cert and not crt_in.exists():
        raise EasyRSAUserError(f"No certificate found for '{name}'")

    # Build public inline
    pub_parts = []
    if include_ca and ca_crt.exists():
        pub_parts.append(_wrap_tag("ca", ca_crt.read_text("utf-8")))
    if include_cert and crt_in.exists():
        pub_parts.append(_wrap_tag("cert", crt_in.read_text("utf-8")))
    if include_tls and tls_in.exists():
        pub_parts.append(_wrap_tag(tls_tag, tls_in.read_text("utf-8")))

    pub_content = "# Easy-RSA Inline file\n\n" + "\n".join(pub_parts) + "\n"

    pub_dir = pki / "inline"
    pub_dir.mkdir(parents=True, exist_ok=True)
    pub_out = pub_dir / f"{name}.inline"
    pub_out.write_text(pub_content, encoding="utf-8")

    # Build private inline (includes key)
    pri_parts = list(pub_parts)
    if include_key and key_in.exists():
        pri_parts.append(_wrap_tag("key", key_in.read_text("utf-8")))

    pri_content = "# Easy-RSA Inline file (private)\n\n" + "\n".join(pri_parts) + "\n"

    pri_dir = pki / "inline" / "private"
    pri_dir.mkdir(parents=True, exist_ok=True)
    pri_out = pri_dir / f"{name}.inline"
    pri_out.write_text(pri_content, encoding="utf-8")

    print(f"\nNotice: Inline file created at:\n* {pub_out}")
    print(f"\nNotice: Private inline file created at:\n* {pri_out}")


def _wrap_tag(tag: str, content: str) -> str:
    """Wrap content with XML-like <tag>...</tag> block."""
    content = content.strip()
    return f"<{tag}>\n{content}\n</{tag}>"


def build_peer_fingerprint_list(
    config: EasyRSAConfig,
    names: list,
    digest: str = "sha256",
) -> None:
    """Build a peer-fingerprint list for OpenVPN peer-fingerprint mode.

    Writes pki/pfp-list.txt with one fingerprint per line (colon-hex).
    """
    pki = config.pki_dir
    pfp_file = pki / "pfp-list.txt"

    lines = ["# Easy-RSA peer-fingerprint list\n"]
    for name in names:
        crt_in = pki / "issued" / f"{name}.crt"
        if not crt_in.exists():
            raise EasyRSAUserError(f"No certificate found for '{name}'")
        cert = load_cert(crt_in.read_bytes())
        fp = get_cert_fingerprint(cert, digest)
        lines.append(fp)

    pfp_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nNotice: Peer-fingerprint list written to:\n* {pfp_file}")


def init_peer_fingerprint_pki(config: EasyRSAConfig) -> None:
    """Initialize a peer-fingerprint PKI (no CA required)."""
    pki = config.pki_dir
    pki.mkdir(parents=True, exist_ok=True)
    mode_file = pki / "peer-fp.mode"
    if mode_file.exists():
        raise EasyRSAUserError("PKI is already in peer-fingerprint mode.")
    mode_file.write_text("peer-fingerprint\n", encoding="utf-8")
    print(f"\nNotice: PKI initialized in peer-fingerprint mode at:\n* {pki}")
