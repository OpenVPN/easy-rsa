"""Easy-RSA x509-types file parser.

Translates OpenSSL extension string syntax into cryptography library
extension objects.
"""

from __future__ import annotations

import importlib.resources
import ipaddress
import re
from pathlib import Path
from typing import List, Optional, Tuple, Any

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from .errors import EasyRSAError, EasyRSAUserError


# Map extension name -> cryptography OID or handler
_EKU_MAP = {
    "serverAuth": ExtendedKeyUsageOID.SERVER_AUTH,
    "clientAuth": ExtendedKeyUsageOID.CLIENT_AUTH,
    "codeSigning": ExtendedKeyUsageOID.CODE_SIGNING,
    "emailProtection": ExtendedKeyUsageOID.EMAIL_PROTECTION,
    "timeStamping": ExtendedKeyUsageOID.TIME_STAMPING,
    "OCSPSigning": ExtendedKeyUsageOID.OCSP_SIGNING,
    # KDC
    "1.3.6.1.5.2.3.5": x509.ObjectIdentifier("1.3.6.1.5.2.3.5"),
}

_KU_MAP = {
    "digitalSignature": "digital_signature",
    "nonRepudiation": "content_commitment",
    "contentCommitment": "content_commitment",
    "keyEncipherment": "key_encipherment",
    "dataEncipherment": "data_encipherment",
    "keyAgreement": "key_agreement",
    "keyCertSign": "key_cert_sign",
    "cRLSign": "crl_sign",
    "encipherOnly": "encipher_only",
    "decipherOnly": "decipher_only",
}


def load_x509_type(type_name: str, pki_dir: Optional[Path], easyrsa_dir: Optional[Path]) -> str:
    """Load content of an x509-types file.

    Search order:
    1. pki_dir/x509-types/<type_name>
    2. easyrsa_dir/x509-types/<type_name>
    3. Package data fallback: src/easyrsa/data/x509-types/<type_name>
    """
    # Search filesystem locations first
    for base in [pki_dir, easyrsa_dir]:
        if base is not None:
            candidate = base / "x509-types" / type_name
            if candidate.exists():
                return candidate.read_text(encoding="utf-8")

    # Package data fallback
    try:
        pkg_data_dir = Path(__file__).parent / "data" / "x509-types"
        candidate = pkg_data_dir / type_name
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    except Exception:
        pass

    raise EasyRSAUserError(f"x509-type file not found: '{type_name}'")


def _parse_san_value(san_str: str) -> List[x509.GeneralName]:
    """Parse a SAN value string like 'DNS:foo,IP:1.2.3.4' into GeneralName objects."""
    names = []
    for part in san_str.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            continue
        prefix, value = part.split(":", 1)
        prefix = prefix.strip()
        value = value.strip()
        if prefix in ("DNS", "dns"):
            names.append(x509.DNSName(value))
        elif prefix in ("IP", "ip"):
            try:
                names.append(x509.IPAddress(ipaddress.ip_address(value)))
            except ValueError:
                try:
                    names.append(x509.IPAddress(ipaddress.ip_network(value, strict=False)))
                except ValueError:
                    raise EasyRSAUserError(f"Invalid IP SAN value: '{value}'")
        elif prefix in ("email", "EMAIL"):
            names.append(x509.RFC822Name(value))
        elif prefix in ("URI", "uri"):
            names.append(x509.UniformResourceIdentifier(value))
        elif prefix in ("otherName", "othername"):
            # Skip complex KDC otherName — requires ASN.1 encoding beyond scope
            pass
        else:
            raise EasyRSAUserError(f"Unsupported SAN type: '{prefix}'")
    return names


def _parse_extension_line(
    line: str,
    ca_cert=None,
    csr=None,
    subject_public_key=None,
) -> Optional[Tuple[x509.ExtensionType, bool]]:
    """Parse one x509-types file line into (extension_object, critical).

    Returns None if the line is a comment, blank, or unknown/unsupported.
    """
    # Strip comments and blanks
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if "=" not in line:
        return None

    name_part, value_part = line.split("=", 1)
    name_part = name_part.strip()
    value_part = value_part.strip()

    # Check for critical prefix in value
    critical = False
    if value_part.lower().startswith("critical,"):
        critical = True
        value_part = value_part[9:].strip()
    elif value_part.lower() == "critical":
        critical = True
        value_part = ""

    ext_name = name_part

    if ext_name == "basicConstraints":
        ca_flag = False
        path_len = None
        for token in value_part.split(","):
            token = token.strip()
            if token == "CA:TRUE":
                ca_flag = True
            elif token == "CA:FALSE":
                ca_flag = False
            elif token.startswith("pathlen:"):
                try:
                    path_len = int(token[8:])
                except ValueError:
                    pass
        return (x509.BasicConstraints(ca=ca_flag, path_length=path_len), critical)

    elif ext_name == "subjectKeyIdentifier":
        if value_part == "hash" and subject_public_key is not None:
            return (x509.SubjectKeyIdentifier.from_public_key(subject_public_key), False)
        elif value_part == "hash":
            # Will be resolved later with actual public key
            return None
        return None

    elif ext_name == "authorityKeyIdentifier":
        keyid = False
        issuer = False
        for token in value_part.replace(" ", "").split(","):
            if token in ("keyid", "keyid:always"):
                keyid = True
            if token in ("issuer", "issuer:always"):
                issuer = True
        if ca_cert is not None and keyid:
            try:
                issuer_public_key = ca_cert.public_key()
                aki = x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_public_key)
                return (aki, False)
            except Exception:
                pass
        # Fallback: no authority key identifier
        return None

    elif ext_name == "keyUsage":
        ku_kwargs = {v: False for v in _KU_MAP.values()}
        for token in value_part.split(","):
            token = token.strip()
            mapped = _KU_MAP.get(token)
            if mapped:
                ku_kwargs[mapped] = True
        return (x509.KeyUsage(**ku_kwargs), critical)

    elif ext_name == "extendedKeyUsage":
        eku_oids = []
        for token in value_part.split(","):
            token = token.strip()
            oid = _EKU_MAP.get(token)
            if oid is None:
                # Try as dotted OID
                try:
                    oid = x509.ObjectIdentifier(token)
                except Exception:
                    continue
            eku_oids.append(oid)
        if eku_oids:
            return (x509.ExtendedKeyUsage(eku_oids), critical)
        return None

    elif ext_name == "subjectAltName":
        names = _parse_san_value(value_part)
        if names:
            return (x509.SubjectAlternativeName(names), critical)
        return None

    elif ext_name == "crlDistributionPoints":
        # URI:http://...
        uris = []
        for token in value_part.split(","):
            token = token.strip()
            if token.startswith("URI:"):
                uris.append(token[4:])
        if uris:
            points = [
                x509.DistributionPoint(
                    full_name=[x509.UniformResourceIdentifier(u)],
                    relative_name=None,
                    reasons=None,
                    crl_issuer=None,
                )
                for u in uris
            ]
            return (x509.CRLDistributionPoints(points), critical)
        return None

    elif ext_name == "authorityInfoAccess":
        # e.g. caIssuers;URI:http://...
        descs = []
        for token in value_part.split(","):
            token = token.strip()
            if ";" in token:
                access_method_str, location_str = token.split(";", 1)
                if location_str.startswith("URI:"):
                    location = x509.UniformResourceIdentifier(location_str[4:])
                    if access_method_str.lower() == "caissuers":
                        descs.append(x509.AccessDescription(
                            x509.AuthorityInformationAccessOID.CA_ISSUERS,
                            location
                        ))
                    elif access_method_str.lower() == "ocsp":
                        descs.append(x509.AccessDescription(
                            x509.AuthorityInformationAccessOID.OCSP,
                            location
                        ))
        if descs:
            return (x509.AuthorityInformationAccess(descs), critical)
        return None

    elif ext_name in ("nsCertType", "nsComment", "issuerAltName"):
        # Deprecated / not directly supported by cryptography library as first-class
        return None

    # Unknown / unsupported extension
    return None


def build_extensions(
    cert_type: str,
    config,
    ca_cert=None,
    csr=None,
    subject_public_key=None,
    extra_exts: str = "",
) -> List[Tuple[x509.ExtensionType, bool]]:
    """Build list of (extension, critical) tuples for a certificate.

    cert_type: 'ca', 'server', 'client', 'serverClient', 'code-signing',
               'email', 'kdc', 'COMMON', 'selfsign'
    """
    pki_dir = getattr(config, "pki_dir", None)
    easyrsa_dir = getattr(config, "easyrsa_dir", None)

    # Load cert-type extensions
    type_content = load_x509_type(cert_type, pki_dir, easyrsa_dir)

    # Load COMMON extensions
    try:
        common_content = load_x509_type("COMMON", pki_dir, easyrsa_dir)
    except EasyRSAUserError:
        common_content = ""

    # Combine: cert_type + COMMON
    combined = type_content + "\n" + common_content

    # Add extra_exts from config if not already provided
    cfg_extra = getattr(config, "extra_exts", "")
    if cfg_extra and extra_exts:
        combined += "\n" + cfg_extra + "\n" + extra_exts
    elif cfg_extra:
        combined += "\n" + cfg_extra
    elif extra_exts:
        combined += "\n" + extra_exts

    # Add SAN if configured
    san = getattr(config, "san", "")
    if san:
        san_crit = getattr(config, "san_crit", False)
        crit_prefix = "critical," if san_crit else ""
        combined += f"\nsubjectAltName = {crit_prefix}{san}"

    # Parse extensions
    exts: List[Tuple[x509.ExtensionType, bool]] = []
    seen_oids = set()

    for line in combined.splitlines():
        result = _parse_extension_line(line, ca_cert=ca_cert, csr=csr,
                                        subject_public_key=subject_public_key)
        if result is None:
            continue
        ext_obj, crit = result
        # Apply config-level criticality overrides
        if isinstance(ext_obj, x509.BasicConstraints) and getattr(config, "bc_crit", False):
            crit = True
        if isinstance(ext_obj, x509.KeyUsage) and getattr(config, "ku_crit", False):
            crit = True
        if isinstance(ext_obj, x509.ExtendedKeyUsage) and getattr(config, "eku_crit", False):
            crit = True
        if isinstance(ext_obj, x509.SubjectAlternativeName) and getattr(config, "san_crit", False):
            crit = True

        oid = ext_obj.oid
        if oid in seen_oids:
            continue
        seen_oids.add(oid)
        exts.append((ext_obj, crit))

    # Add SubjectKeyIdentifier if not already present and we have the public key
    ski_oid = x509.SubjectKeyIdentifier.oid
    if subject_public_key is not None and ski_oid not in seen_oids:
        ski = x509.SubjectKeyIdentifier.from_public_key(subject_public_key)
        exts.append((ski, False))

    # Add NS extensions if configured (deprecated but supported)
    ns_support = getattr(config, "ns_support", False)
    if ns_support and cert_type in ("server", "client", "serverClient", "ca"):
        ns_comment = getattr(config, "ns_comment", "")
        # We skip nsCertType / nsComment as they're not in cryptography's first-class API

    return exts


def build_csr_extensions(config, san_override: str = "") -> List[Tuple[x509.ExtensionType, bool]]:
    """Build extensions for a CSR (gen-req).

    Only SAN is typically included in CSR extensions.
    """
    exts = []
    san = san_override or getattr(config, "san", "")
    if san:
        san_crit = getattr(config, "san_crit", False)
        names = _parse_san_value(san)
        if names:
            exts.append((x509.SubjectAlternativeName(names), san_crit))

    # extra_exts can include subjectAltName
    extra = getattr(config, "extra_exts", "")
    if extra:
        seen_oids = {e[0].oid for e in exts}
        for line in extra.splitlines():
            result = _parse_extension_line(line)
            if result is None:
                continue
            ext_obj, crit = result
            if ext_obj.oid not in seen_oids:
                exts.append((ext_obj, crit))
                seen_oids.add(ext_obj.oid)

    return exts
