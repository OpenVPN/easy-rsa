"""Core cryptographic operations for Easy-RSA.

All crypto uses the cryptography library; no openssl subprocess for crypto.
"""

from __future__ import annotations

import datetime
import secrets
from typing import List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import dh, ec, ed25519, ed448, padding, rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    pkcs12,
)
from cryptography.x509 import CertificateRevocationList, CertificateRevocationListBuilder
from cryptography.x509.oid import NameOID

from .errors import EasyRSAError, EasyRSAUserError


# ============================================================
# Digest mapping
# ============================================================

def _get_hash(digest: str, key=None):
    """Return hash algorithm object for the given digest name.

    For Ed25519/Ed448 keys, returns None (prehash not used).
    """
    if key is not None and isinstance(key, (ed25519.Ed25519PrivateKey, ed448.Ed448PrivateKey)):
        return None
    # Also check public keys
    if key is not None and isinstance(key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
        return None

    digest_map = {
        "sha256": hashes.SHA256(),
        "sha384": hashes.SHA384(),
        "sha512": hashes.SHA512(),
        "sha224": hashes.SHA224(),
        "sha1": hashes.SHA1(),
        "md5": hashes.MD5(),
    }
    h = digest_map.get(digest.lower())
    if h is None:
        raise EasyRSAUserError(f"Unknown digest algorithm: '{digest}'")
    return h


# ============================================================
# Curve name mapping
# ============================================================

def _get_ec_curve(curve_name: str):
    """Return an EC curve object from its name."""
    curve_map = {
        "secp384r1": ec.SECP384R1(),
        "secp256r1": ec.SECP256R1(),
        "prime256v1": ec.SECP256R1(),
        "secp521r1": ec.SECP521R1(),
        "secp224r1": ec.SECP224R1(),
        "secp192r1": ec.SECP192R1(),
        "brainpoolP256r1": ec.BrainpoolP256R1(),
        "brainpoolP384r1": ec.BrainpoolP384R1(),
        "brainpoolP512r1": ec.BrainpoolP512R1(),
    }
    curve = curve_map.get(curve_name.lower()) or curve_map.get(curve_name)
    if curve is None:
        raise EasyRSAUserError(f"Unknown EC curve: '{curve_name}'")
    return curve


# ============================================================
# Key generation
# ============================================================

def generate_key(algo: str, key_size: int = 2048, curve: str = "secp384r1"):
    """Generate a private key.

    algo: 'rsa', 'ec', 'ed'
    Returns a private key object.
    """
    algo = algo.lower()
    if algo == "rsa":
        return rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
    elif algo == "ec":
        ec_curve = _get_ec_curve(curve)
        return ec.generate_private_key(ec_curve)
    elif algo == "ed":
        curve_lower = curve.lower()
        if curve_lower == "ed25519":
            return ed25519.Ed25519PrivateKey.generate()
        elif curve_lower == "ed448":
            return ed448.Ed448PrivateKey.generate()
        else:
            raise EasyRSAUserError(f"Unknown Edwards curve: '{curve}'")
    else:
        raise EasyRSAUserError(f"Unknown algorithm: '{algo}'. Must be rsa, ec, or ed")


# ============================================================
# Key serialization
# ============================================================

def serialize_private_key(key, password: Optional[bytes] = None) -> bytes:
    """Serialize private key to PEM.

    Uses TraditionalOpenSSL format for compatibility with shell version.
    If password is provided, encrypts with BestAvailableEncryption.
    """
    encryption = BestAvailableEncryption(password) if password else NoEncryption()
    # Use TraditionalOpenSSL format for RSA/EC to match shell easyrsa behavior
    if isinstance(key, rsa.RSAPrivateKey):
        fmt = PrivateFormat.TraditionalOpenSSL
    elif isinstance(key, ec.EllipticCurvePrivateKey):
        fmt = PrivateFormat.TraditionalOpenSSL
    else:
        # Ed25519/Ed448 only support PKCS8
        fmt = PrivateFormat.PKCS8
    return key.private_bytes(Encoding.PEM, fmt, encryption)


def load_private_key(pem_data: bytes, password: Optional[bytes] = None):
    """Load a private key from PEM data."""
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    return load_pem_private_key(pem_data, password=password)


def serialize_public_key(key) -> bytes:
    """Serialize public key to PEM."""
    pub = key.public_key() if hasattr(key, "public_key") else key
    return pub.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)


# ============================================================
# CSR operations
# ============================================================

def _build_name(subject_attrs: dict) -> x509.Name:
    """Build an x509.Name from a dict of OID-name -> value."""
    oid_map = {
        "CN": NameOID.COMMON_NAME,
        "C": NameOID.COUNTRY_NAME,
        "ST": NameOID.STATE_OR_PROVINCE_NAME,
        "L": NameOID.LOCALITY_NAME,
        "O": NameOID.ORGANIZATION_NAME,
        "OU": NameOID.ORGANIZATIONAL_UNIT_NAME,
        "emailAddress": NameOID.EMAIL_ADDRESS,
        "serialNumber": NameOID.SERIAL_NUMBER,
        "GN": NameOID.GIVEN_NAME,
        "SN": NameOID.SURNAME,
    }
    attrs = []
    for key, value in subject_attrs.items():
        if not value:
            continue
        oid = oid_map.get(key)
        if oid is None:
            continue
        attrs.append(x509.NameAttribute(oid, value))
    return x509.Name(attrs)


def build_csr(
    private_key,
    subject_attrs: dict,
    san_ext=None,
    extra_extensions=None,
    digest: str = "sha256",
) -> x509.CertificateSigningRequest:
    """Build a CSR.

    subject_attrs: {'CN': ..., 'C': ..., etc.}
    san_ext: optional SubjectAlternativeName extension
    extra_extensions: optional list of (ExtensionType, critical) tuples
    """
    name = _build_name(subject_attrs)
    builder = x509.CertificateSigningRequestBuilder().subject_name(name)

    if san_ext is not None:
        ext_obj, critical = san_ext
        builder = builder.add_extension(ext_obj, critical=critical)

    if extra_extensions:
        for ext_obj, critical in extra_extensions:
            try:
                builder = builder.add_extension(ext_obj, critical=critical)
            except Exception:
                pass

    hash_alg = _get_hash(digest, private_key)
    return builder.sign(private_key, hash_alg)


def serialize_csr(csr: x509.CertificateSigningRequest) -> bytes:
    """Serialize CSR to PEM."""
    return csr.public_bytes(Encoding.PEM)


def load_csr(pem_data: bytes) -> x509.CertificateSigningRequest:
    """Load CSR from PEM data."""
    from cryptography.x509 import load_pem_x509_csr
    return load_pem_x509_csr(pem_data)


# ============================================================
# Certificate operations
# ============================================================

def _make_validity(
    expire_days: int,
    start_date=None,
    end_date=None,
) -> Tuple[datetime.datetime, datetime.datetime]:
    """Compute (not_valid_before, not_valid_after) datetimes."""
    now = datetime.datetime.utcnow().replace(microsecond=0)

    if start_date:
        not_before = _parse_date_string(start_date)
    else:
        not_before = now

    if end_date:
        not_after = _parse_date_string(end_date)
    else:
        not_after = not_before + datetime.timedelta(days=expire_days)

    return not_before, not_after


def _parse_date_string(s: str) -> datetime.datetime:
    """Parse [YY]YYMMDDhhmmssZ date string."""
    s = s.rstrip("Z")
    if len(s) == 12:
        # YYMMDDHHMMSS
        yy = int(s[0:2])
        year = (2000 + yy) if yy < 70 else (1900 + yy)
        month, day = int(s[2:4]), int(s[4:6])
        hour, minute, second = int(s[6:8]), int(s[8:10]), int(s[10:12])
    elif len(s) == 14:
        year = int(s[0:4])
        month, day = int(s[4:6]), int(s[6:8])
        hour, minute, second = int(s[8:10]), int(s[10:12]), int(s[12:14])
    else:
        raise EasyRSAUserError(f"Cannot parse date string: '{s}Z'")
    return datetime.datetime(year, month, day, hour, minute, second)


def build_ca_cert(
    private_key,
    subject_attrs: dict,
    ca_expire_days: int,
    extensions: list,
    serial: Optional[int] = None,
    digest: str = "sha256",
    start_date: str = "",
    end_date: str = "",
) -> x509.Certificate:
    """Build a self-signed CA certificate."""
    name = _build_name(subject_attrs)
    not_before, not_after = _make_validity(ca_expire_days, start_date or None, end_date or None)

    if serial is None:
        serial = generate_serial()

    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(serial)
        .not_valid_before(not_before)
        .not_valid_after(not_after)
    )

    for ext_obj, critical in extensions:
        try:
            builder = builder.add_extension(ext_obj, critical=critical)
        except Exception:
            pass

    hash_alg = _get_hash(digest, private_key)
    return builder.sign(private_key, hash_alg)


def sign_csr(
    ca_cert: x509.Certificate,
    ca_key,
    csr: x509.CertificateSigningRequest,
    cert_expire_days: int,
    serial: int,
    extensions: list,
    digest: str = "sha256",
    force_subject: Optional[dict] = None,
    preserve_dn: bool = False,
    start_date: str = "",
    end_date: str = "",
) -> x509.Certificate:
    """Sign a CSR with a CA cert+key. Returns a Certificate."""
    if force_subject:
        subject_name = _build_name(force_subject)
    elif preserve_dn:
        subject_name = csr.subject
    else:
        subject_name = csr.subject

    not_before, not_after = _make_validity(cert_expire_days, start_date or None, end_date or None)

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject_name)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(serial)
        .not_valid_before(not_before)
        .not_valid_after(not_after)
    )

    for ext_obj, critical in extensions:
        try:
            builder = builder.add_extension(ext_obj, critical=critical)
        except Exception:
            pass

    hash_alg = _get_hash(digest, ca_key)
    return builder.sign(ca_key, hash_alg)


def serialize_cert(cert: x509.Certificate) -> bytes:
    """Serialize certificate to PEM."""
    return cert.public_bytes(Encoding.PEM)


def load_cert(pem_data: bytes) -> x509.Certificate:
    """Load certificate from PEM data."""
    from cryptography.x509 import load_pem_x509_certificate
    return load_pem_x509_certificate(pem_data)


# ============================================================
# Serial number handling
# ============================================================

def generate_serial() -> int:
    """Generate a 128-bit random serial number.

    Ensures no leading zeros in hex representation (first nibble >= 1).
    """
    while True:
        # 16 random bytes = 128 bits
        raw = secrets.token_bytes(16)
        serial = int.from_bytes(raw, "big")
        # Ensure the hex representation doesn't have leading zeros (first byte >= 1)
        hex_str = format(serial, "032X")
        if not hex_str.startswith("00"):
            return serial


def serial_to_hex(serial: int) -> str:
    """Convert serial int to uppercase hex without leading zeros."""
    return format(serial, "X").upper()


def hex_to_serial(hex_str: str) -> int:
    """Convert hex string to serial integer."""
    return int(hex_str, 16)


# ============================================================
# CRL operations
# ============================================================

_REASON_MAP = {
    "unspecified": x509.ReasonFlags.unspecified,
    "keyCompromise": x509.ReasonFlags.key_compromise,
    "CACompromise": x509.ReasonFlags.ca_compromise,
    "affiliationChanged": x509.ReasonFlags.affiliation_changed,
    "superseded": x509.ReasonFlags.superseded,
    "cessationOfOperation": x509.ReasonFlags.cessation_of_operation,
    "certificateHold": x509.ReasonFlags.certificate_hold,
    "privilegeWithdrawn": x509.ReasonFlags.privilege_withdrawn,
    "aACompromise": x509.ReasonFlags.aa_compromise,
}


def build_crl(
    ca_cert: x509.Certificate,
    ca_key,
    revoked_certs: list,
    crl_days: int,
    digest: str = "sha256",
) -> x509.CertificateRevocationList:
    """Build a CRL.

    revoked_certs: list of (serial_int, revoke_datetime, reason_str_or_None)
    """
    now = datetime.datetime.utcnow().replace(microsecond=0)
    next_update = now + datetime.timedelta(days=crl_days)

    builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(ca_cert.subject)
        .last_update(now)
        .next_update(next_update)
    )

    # Add AKI extension
    try:
        aki = x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_cert.public_key())
        builder = builder.add_extension(aki, critical=False)
    except Exception:
        pass

    for serial_int, revoke_dt, reason_str in revoked_certs:
        revoked_builder = x509.RevokedCertificateBuilder()
        revoked_builder = revoked_builder.serial_number(serial_int)
        revoked_builder = revoked_builder.revocation_date(revoke_dt)
        if reason_str and reason_str != "None given":
            reason_flag = _REASON_MAP.get(reason_str)
            if reason_flag is not None:
                revoked_builder = revoked_builder.add_extension(
                    x509.CRLReason(reason_flag), critical=False
                )
        builder = builder.add_revoked_certificate(revoked_builder.build())

    hash_alg = _get_hash(digest, ca_key)
    return builder.sign(ca_key, hash_alg)


def serialize_crl(crl: x509.CertificateRevocationList) -> bytes:
    """Serialize CRL to PEM."""
    return crl.public_bytes(Encoding.PEM)


# ============================================================
# DH parameters
# ============================================================

def generate_dh_params(key_size: int) -> bytes:
    """Generate DH parameters and return PEM bytes."""
    parameters = dh.generate_parameters(generator=2, key_size=key_size)
    return parameters.parameter_bytes(Encoding.PEM, serialization.ParameterFormat.PKCS3)


# ============================================================
# PKCS#12 export
# ============================================================

def export_pkcs12(
    cert: x509.Certificate,
    private_key,
    ca_certs: list,
    friendly_name: bytes,
    password: Optional[bytes] = None,
    legacy: bool = False,
) -> bytes:
    """Export a PKCS#12 file.

    Returns raw bytes of the .p12 file.
    """
    if legacy:
        # Use legacy RC2/3DES encryption
        encryption = (
            pkcs12.PKCS12Encryption()
            if hasattr(pkcs12, "PKCS12Encryption")
            else serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()
        )
    else:
        encryption = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()

    return pkcs12.serialize_key_and_certificates(
        name=friendly_name,
        key=private_key,
        cert=cert,
        cas=ca_certs if ca_certs else None,
        encryption_algorithm=encryption,
    )


# ============================================================
# Certificate info
# ============================================================

def get_cert_subject(cert: x509.Certificate) -> dict:
    """Return subject as ordered dict {short_name: value}."""
    oid_to_short = {
        NameOID.COMMON_NAME: "CN",
        NameOID.COUNTRY_NAME: "C",
        NameOID.STATE_OR_PROVINCE_NAME: "ST",
        NameOID.LOCALITY_NAME: "L",
        NameOID.ORGANIZATION_NAME: "O",
        NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
        NameOID.EMAIL_ADDRESS: "emailAddress",
        NameOID.SERIAL_NUMBER: "serialNumber",
    }
    result = {}
    for attr in cert.subject:
        short = oid_to_short.get(attr.oid, attr.oid.dotted_string)
        result[short] = attr.value
    return result


def get_cert_serial_hex(cert: x509.Certificate) -> str:
    """Return cert serial as uppercase hex string."""
    return serial_to_hex(cert.serial_number)


def get_cert_fingerprint(cert: x509.Certificate, algorithm: str = "sha256") -> str:
    """Return fingerprint as 'AA:BB:CC:...' colon-separated uppercase hex string."""
    alg_map = {
        "sha256": hashes.SHA256(),
        "sha1": hashes.SHA1(),
        "md5": hashes.MD5(),
    }
    alg = alg_map.get(algorithm.lower(), hashes.SHA256())
    fp_bytes = cert.fingerprint(alg)
    return ":".join(f"{b:02X}" for b in fp_bytes)


def get_cert_not_after(cert: x509.Certificate) -> datetime.datetime:
    """Return certificate expiry datetime (UTC)."""
    # Handle both old and new cryptography API
    try:
        return cert.not_valid_after_utc.replace(tzinfo=None)
    except AttributeError:
        return cert.not_valid_after


def verify_cert_signature(cert: x509.Certificate, ca_cert: x509.Certificate) -> bool:
    """Verify that cert was signed by ca_cert. Returns True/False."""
    try:
        ca_public_key = ca_cert.public_key()
        if isinstance(ca_public_key, rsa.RSAPublicKey):
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                padding.PKCS1v15(),
                cert.signature_hash_algorithm,
            )
        elif isinstance(ca_public_key, ec.EllipticCurvePublicKey):
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                ec.ECDSA(cert.signature_hash_algorithm),
            )
        elif isinstance(ca_public_key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
            ca_public_key.verify(cert.signature, cert.tbs_certificate_bytes)
        else:
            return False
        return True
    except Exception:
        return False


def get_cert_eku(cert: x509.Certificate) -> list:
    """Return list of EKU OID dotted strings."""
    try:
        ext = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        return [oid.dotted_string for oid in ext.value]
    except x509.ExtensionNotFound:
        return []


def is_ca_cert(cert: x509.Certificate) -> bool:
    """Return True if cert has basicConstraints CA:TRUE."""
    try:
        ext = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        return ext.value.ca
    except x509.ExtensionNotFound:
        return False


def cert_subject_to_dn_string(cert: x509.Certificate) -> str:
    """Convert cert subject to OpenSSL-style /CN=.../O=... string."""
    oid_to_short = {
        NameOID.COMMON_NAME: "CN",
        NameOID.COUNTRY_NAME: "C",
        NameOID.STATE_OR_PROVINCE_NAME: "ST",
        NameOID.LOCALITY_NAME: "L",
        NameOID.ORGANIZATION_NAME: "O",
        NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
        NameOID.EMAIL_ADDRESS: "emailAddress",
        NameOID.SERIAL_NUMBER: "serialNumber",
    }
    parts = []
    for attr in cert.subject:
        short = oid_to_short.get(attr.oid, attr.oid.dotted_string)
        parts.append(f"{short}={attr.value}")
    return "/" + "/".join(parts)


def csr_subject_to_dn_string(csr: x509.CertificateSigningRequest) -> str:
    """Convert CSR subject to OpenSSL-style /CN=... string."""
    oid_to_short = {
        NameOID.COMMON_NAME: "CN",
        NameOID.COUNTRY_NAME: "C",
        NameOID.STATE_OR_PROVINCE_NAME: "ST",
        NameOID.LOCALITY_NAME: "L",
        NameOID.ORGANIZATION_NAME: "O",
        NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
        NameOID.EMAIL_ADDRESS: "emailAddress",
        NameOID.SERIAL_NUMBER: "serialNumber",
    }
    parts = []
    for attr in csr.subject:
        short = oid_to_short.get(attr.oid, attr.oid.dotted_string)
        parts.append(f"{short}={attr.value}")
    return "/" + "/".join(parts)
