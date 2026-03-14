"""Easy-RSA configuration management.

Implements layered config: defaults -> vars-file -> env vars -> CLI flags.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .errors import EasyRSAUserError


# Valid identifier: no leading digits, no hyphens, alphanumeric + underscore only
_IDENT_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def _validate_identifier(name: str) -> None:
    """Raise EasyRSAUserError if name is not a valid variable identifier."""
    if not name:
        raise EasyRSAUserError("Variable name cannot be empty")
    if not _IDENT_RE.match(name):
        raise EasyRSAUserError(
            f"Invalid variable name '{name}': must start with letter/underscore "
            f"and contain only alphanumeric characters and underscores"
        )


def _parse_vars_file(path: Path) -> dict:
    """Parse a vars file using set_var KEY "value" syntax.

    Returns a dict of {KEY: value}. Uses shlex for safe parsing (no exec/eval).
    """
    result = {}
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            # Skip blank lines and comments
            if not stripped or stripped.startswith("#"):
                continue
            # Skip the shell guard block (if/return)
            if stripped.startswith("if ") or stripped.startswith("fi") or stripped == "return 1":
                continue
            # Only process set_var lines
            if not stripped.startswith("set_var"):
                continue
            try:
                tokens = shlex.split(stripped)
            except ValueError as e:
                raise EasyRSAUserError(
                    f"vars file parse error at line {lineno}: {e}\n* {path}"
                )
            if len(tokens) < 2:
                continue
            if tokens[0] != "set_var":
                continue
            if len(tokens) < 3:
                # set_var KEY  (no value) -- treat as empty string
                key = tokens[1]
                value = ""
            else:
                key = tokens[1]
                value = tokens[2]
            _validate_identifier(key)
            result[key] = value
    return result


def _truthy(value: str) -> bool:
    """Return True if value is a non-empty, non-zero, non-'no'/'false' string."""
    if not value:
        return False
    return value.lower() not in ("0", "no", "false", "")


@dataclass
class EasyRSAConfig:
    """All Easy-RSA configuration variables.

    Layered: defaults -> vars-file -> env vars -> CLI flags.
    """

    # PKI directory
    pki_dir: Path = field(default_factory=lambda: Path("pki"))

    # Crypto algorithm
    algo: str = "rsa"
    key_size: int = 2048
    curve: str = ""

    # Certificate validity
    ca_expire: int = 3650
    cert_expire: int = 825
    crl_days: int = 180

    # Digest
    digest: str = "sha256"

    # Serial number
    rand_sn: str = "yes"

    # DN mode: "cn_only" or "org"
    dn_mode: str = "cn_only"

    # Request fields
    req_cn: str = "ChangeMe"
    req_country: str = "US"
    req_province: str = "California"
    req_city: str = "San Francisco"
    req_org: str = "Copyleft Certificate Co"
    req_email: str = "me@example.net"
    req_ou: str = ""
    req_serial: str = ""

    # Sub-CA path length
    subca_len: Optional[int] = None

    # Extensions
    extra_exts: str = ""
    san: str = ""
    san_crit: bool = False
    bc_crit: bool = False
    ku_crit: bool = False
    eku_crit: bool = False
    cp_ext: bool = False
    auto_san: bool = False

    # Operation flags
    batch: bool = False
    silent: bool = False
    verbose: bool = False
    no_pass: bool = False

    # Passphrase inputs
    passin: str = ""
    passout: str = ""

    # Inline/lock
    no_inline: bool = False
    no_lockfile: bool = False

    # Temp dir
    keep_tmp: str = ""
    temp_dir: Optional[Path] = None

    # Pre-expiry window (days)
    pre_expiry_window: int = 90

    # Subject override
    preserve_dn: bool = False
    new_subject: str = ""

    # PKCS#12 friendly name
    p12_fr_name: str = ""

    # Date overrides
    start_date: str = ""
    end_date: str = ""
    alias_days: Optional[int] = None

    # Netscape (deprecated) extensions
    ns_support: bool = False
    ns_comment: str = ""

    # Text output
    text_on: bool = False
    text_off: bool = False

    # Raw CA mode
    raw_ca: bool = False

    # vars-file path (loaded from)
    vars_file: Optional[Path] = None

    # EasyRSA install dir (for x509-types lookup)
    easyrsa_dir: Optional[Path] = None

    def __post_init__(self):
        # Set default curve based on algo if not specified
        if not self.curve:
            if self.algo == "ec":
                self.curve = "secp384r1"
            elif self.algo == "ed":
                self.curve = "ed25519"

    @classmethod
    def from_env_and_args(
        cls,
        vars_file: Optional[Path] = None,
        cli_overrides: Optional[dict] = None,
        easyrsa_dir: Optional[Path] = None,
        pki_dir: Optional[Path] = None,
    ) -> "EasyRSAConfig":
        """Build config from defaults -> vars file -> env vars -> CLI overrides."""
        # Start with defaults
        cfg = cls()

        if easyrsa_dir:
            cfg.easyrsa_dir = easyrsa_dir
        if pki_dir:
            cfg.pki_dir = pki_dir

        # Load vars file if provided or auto-detected
        vf = vars_file
        if vf is None:
            # Auto-detect: look for pki/vars, then ./vars
            pki = cfg.pki_dir
            if (pki / "vars").exists():
                vf = pki / "vars"
            elif Path("vars").exists():
                vf = Path("vars")

        if vf is not None and vf.exists():
            cfg.vars_file = vf
            vars_data = _parse_vars_file(vf)
            cfg._apply_vars_dict(vars_data)

        # Apply environment variables
        cfg._apply_env()

        # Apply CLI overrides last
        if cli_overrides:
            cfg._apply_dict(cli_overrides)

        cfg.__post_init__()
        return cfg

    def _apply_vars_dict(self, d: dict) -> None:
        """Apply parsed vars dict to config fields."""
        mapping = {
            "EASYRSA_PKI": ("pki_dir", Path),
            "EASYRSA_ALGO": ("algo", str),
            "EASYRSA_KEY_SIZE": ("key_size", int),
            "EASYRSA_CURVE": ("curve", str),
            "EASYRSA_CA_EXPIRE": ("ca_expire", int),
            "EASYRSA_CERT_EXPIRE": ("cert_expire", int),
            "EASYRSA_CRL_DAYS": ("crl_days", int),
            "EASYRSA_DIGEST": ("digest", str),
            "EASYRSA_RAND_SN": ("rand_sn", str),
            "EASYRSA_DN": ("dn_mode", str),
            "EASYRSA_REQ_CN": ("req_cn", str),
            "EASYRSA_REQ_COUNTRY": ("req_country", str),
            "EASYRSA_REQ_PROVINCE": ("req_province", str),
            "EASYRSA_REQ_CITY": ("req_city", str),
            "EASYRSA_REQ_ORG": ("req_org", str),
            "EASYRSA_REQ_EMAIL": ("req_email", str),
            "EASYRSA_REQ_OU": ("req_ou", str),
            "EASYRSA_REQ_SERIAL": ("req_serial", str),
            "EASYRSA_SUBCA_LEN": ("subca_len", lambda v: int(v) if v else None),
            "EASYRSA_EXTRA_EXTS": ("extra_exts", str),
            "EASYRSA_SAN": ("san", str),
            "EASYRSA_SAN_CRIT": ("san_crit", _truthy),
            "EASYRSA_BC_CRIT": ("bc_crit", _truthy),
            "EASYRSA_KU_CRIT": ("ku_crit", _truthy),
            "EASYRSA_EKU_CRIT": ("eku_crit", _truthy),
            "EASYRSA_CP_EXT": ("cp_ext", _truthy),
            "EASYRSA_AUTO_SAN": ("auto_san", _truthy),
            "EASYRSA_BATCH": ("batch", _truthy),
            "EASYRSA_SILENT": ("silent", _truthy),
            "EASYRSA_VERBOSE": ("verbose", _truthy),
            "EASYRSA_NO_PASS": ("no_pass", _truthy),
            "EASYRSA_PASSIN": ("passin", str),
            "EASYRSA_PASSOUT": ("passout", str),
            "EASYRSA_NO_INLINE": ("no_inline", _truthy),
            "EASYRSA_NO_LOCKFILE": ("no_lockfile", _truthy),
            "EASYRSA_KEEP_TEMP": ("keep_tmp", str),
            "EASYRSA_PRE_EXPIRY_WINDOW": ("pre_expiry_window", int),
            "EASYRSA_PRESERVE_DN": ("preserve_dn", _truthy),
            "EASYRSA_NEW_SUBJECT": ("new_subject", str),
            "EASYRSA_P12_FR_NAME": ("p12_fr_name", str),
            "EASYRSA_START_DATE": ("start_date", str),
            "EASYRSA_END_DATE": ("end_date", str),
            "EASYRSA_NS_SUPPORT": ("ns_support", lambda v: v.lower() in ("yes", "1", "true")),
            "EASYRSA_NS_COMMENT": ("ns_comment", str),
            "EASYRSA_TEXT_ON": ("text_on", _truthy),
            "EASYRSA_TEXT_OFF": ("text_off", _truthy),
            "EASYRSA_RAW_CA": ("raw_ca", _truthy),
        }
        for env_key, (attr, converter) in mapping.items():
            if env_key in d:
                try:
                    setattr(self, attr, converter(d[env_key]))
                except (ValueError, TypeError) as e:
                    raise EasyRSAUserError(
                        f"Invalid value for {env_key}='{d[env_key]}': {e}"
                    )

    def _apply_env(self) -> None:
        """Apply EASYRSA_* environment variables."""
        env_dict = {k: v for k, v in os.environ.items() if k.startswith("EASYRSA_")}
        self._apply_vars_dict(env_dict)

    def _apply_dict(self, d: dict) -> None:
        """Apply a dict of {attr_name: value} directly to config."""
        for attr, value in d.items():
            if hasattr(self, attr) and value is not None:
                setattr(self, attr, value)

    def get_san_critical_prefix(self) -> str:
        """Return 'critical,' if san_crit is set, else ''."""
        return "critical," if self.san_crit else ""
