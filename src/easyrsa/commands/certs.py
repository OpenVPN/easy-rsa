"""gen-req, sign-req, build-full, renew certificate commands."""

from __future__ import annotations

import ipaddress
import re
import shutil
from pathlib import Path
from typing import Optional

from ..config import EasyRSAConfig
from ..crypto import (
    build_csr,
    cert_subject_to_dn_string,
    csr_subject_to_dn_string,
    generate_key,
    generate_serial,
    get_cert_not_after,
    get_cert_serial_hex,
    hex_to_serial,
    is_ca_cert,
    load_cert,
    load_csr,
    load_private_key,
    serial_to_hex,
    serialize_cert,
    serialize_csr,
    serialize_private_key,
    sign_csr,
)
from ..errors import EasyRSAUserError
from ..index import (
    IndexRecord,
    append_record,
    asn1_from_datetime,
    find_by_serial,
    parse_index,
)
from ..passphrase import load_key_password, parse_passout, prompt_passphrase
from ..pki import read_serial, write_serial
from ..session import Session
from ..x509types import build_csr_extensions, build_extensions


def _build_subject(config: EasyRSAConfig, cn_override: str = "") -> dict:
    """Build subject attrs dict from config."""
    cn = cn_override or config.req_cn
    if config.dn_mode == "org":
        return {
            "CN": cn,
            "C": config.req_country,
            "ST": config.req_province,
            "L": config.req_city,
            "O": config.req_org,
            "OU": config.req_ou,
            "emailAddress": config.req_email,
            "serialNumber": config.req_serial,
        }
    else:
        return {"CN": cn}


def gen_req(
    config: EasyRSAConfig,
    session: Session,
    name: str,
    nopass: bool = False,
    text: bool = False,
) -> None:
    """Generate a private key and CSR.

    name: file_name_base
    """
    key_out = config.pki_dir / "private" / f"{name}.key"
    req_out = config.pki_dir / "reqs" / f"{name}.req"

    # Confirm overwrite
    if req_out.exists() and not config.batch:
        answer = input(
            f"\nWARNING: An existing request file was found at\n* {req_out}\n"
            f"Type 'yes' to overwrite: "
        ).strip()
        if answer.lower() != "yes":
            raise EasyRSAUserError("gen-req aborted by user.")
    if key_out.exists() and not config.batch:
        answer = input(
            f"\nWARNING: An existing private key was found at\n* {key_out}\n"
            f"Type 'yes' to overwrite: "
        ).strip()
        if answer.lower() != "yes":
            raise EasyRSAUserError("gen-req aborted by user.")

    # Set CN
    cn = config.req_cn if config.req_cn != "ChangeMe" else name

    # Get password
    password = _get_key_password(config, nopass)

    # Generate key
    key = generate_key(config.algo, config.key_size, config.curve)

    # Serialize key
    key_pem = serialize_private_key(key, password)

    # Build subject
    subject = _build_subject(config, cn)

    # Build CSR extensions (SAN from config or extra_exts)
    csr_exts = build_csr_extensions(config)

    # Build CSR
    csr = build_csr(
        private_key=key,
        subject_attrs=subject,
        extra_extensions=csr_exts,
        digest=config.digest,
    )
    req_pem = serialize_csr(csr)

    # Write to temp files first
    key_tmp = session.mktemp()
    req_tmp = session.mktemp()
    key_tmp.write_bytes(key_pem)
    req_tmp.write_bytes(req_pem)

    # Move to final locations
    key_out.parent.mkdir(parents=True, exist_ok=True)
    req_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(key_tmp), str(key_out))
    shutil.move(str(req_tmp), str(req_out))

    print(f"\nNotice: Private-Key and Public-Certificate-Request files created.")
    print(f"Your files are:")
    print(f"* req: {req_out}")
    print(f"* key: {key_out}")


def _get_key_password(config: EasyRSAConfig, nopass: bool = False) -> Optional[bytes]:
    """Determine key encryption password."""
    if nopass or config.no_pass:
        return None
    if config.passout:
        return parse_passout(config.passout)
    if config.batch:
        return None
    return prompt_passphrase("Enter PEM pass phrase: ", confirm=True)


def _is_unique_serial(records: list, serial_hex: str) -> bool:
    """Return True if serial is not in index.txt."""
    return find_by_serial(records, serial_hex) is None


def sign_req(
    config: EasyRSAConfig,
    session: Session,
    cert_type: str,
    name: str,
    newsubj: Optional[str] = None,
    preserve: bool = False,
    force_subj: Optional[dict] = None,
    local_request: bool = False,
) -> None:
    """Sign a CSR from pki/reqs/ and produce a cert in pki/issued/.

    cert_type: 'server', 'client', 'serverClient', 'ca', etc.
    name: file_name_base
    """
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    req_in = config.pki_dir / "reqs" / f"{name}.req"
    crt_out = config.pki_dir / "issued" / f"{name}.crt"

    if cert_type == "COMMON":
        raise EasyRSAUserError("Invalid certificate type: 'COMMON'")

    if not req_in.exists():
        raise EasyRSAUserError(
            f"No request found for the input: '{name}'\n"
            f"Expected to find the request at:\n* {req_in}"
        )
    if crt_out.exists():
        raise EasyRSAUserError(
            f"Cannot sign this request for '{name}'.\n"
            f"Conflicting certificate exists at:\n* {crt_out}"
        )

    # Load CSR
    csr_pem = req_in.read_bytes()
    try:
        csr = load_csr(csr_pem)
    except Exception as e:
        raise EasyRSAUserError(
            f"The certificate request file is not in a valid X509 format:\n* {req_in}"
        )

    # Load CA cert and key
    ca_cert_pem = (config.pki_dir / "ca.crt").read_bytes()
    ca_cert = load_cert(ca_cert_pem)

    ca_key_pem = (config.pki_dir / "private" / "ca.key").read_bytes()
    password = load_key_password(config.passin)
    ca_key = load_private_key(ca_key_pem, password)

    # Generate random serial
    index_path = config.pki_dir / "index.txt"
    records = parse_index(index_path)
    serial = _get_unique_serial(records)
    serial_hex = serial_to_hex(serial)

    # Determine subject
    csr_cn = _get_csr_cn(csr)
    if force_subj:
        final_subject = force_subj
    else:
        final_subject = None  # use CSR subject

    # Auto-SAN
    extra_exts_lines = config.extra_exts
    if not config.san and config.auto_san:
        # Determine DNS or IP
        try:
            ipaddress.ip_address(csr_cn)
            auto_san = f"IP:{csr_cn}"
        except ValueError:
            auto_san = f"DNS:{csr_cn}"
        san_crit = "critical," if config.san_crit else ""
        extra_exts_lines = (extra_exts_lines + "\n" if extra_exts_lines else "") + \
                           f"subjectAltName = {san_crit}{auto_san}"

    # Build extensions
    exts = build_extensions(
        cert_type=cert_type,
        config=config,
        ca_cert=ca_cert,
        csr=csr,
        subject_public_key=csr.public_key(),
        extra_exts=extra_exts_lines,
    )

    # Adjust basicConstraints for sub-CA path length
    if cert_type == "ca" and config.subca_len is not None:
        from cryptography import x509 as _x509
        exts = _adjust_pathlen(exts, config.subca_len)

    # Confirm with user
    if not config.batch and not local_request:
        _confirm_sign(cert_type, name, csr_cn, config, force_subj)

    # Sign
    cert = sign_csr(
        ca_cert=ca_cert,
        ca_key=ca_key,
        csr=csr,
        cert_expire_days=config.cert_expire,
        serial=serial,
        extensions=exts,
        digest=config.digest,
        force_subject=final_subject,
        preserve_dn=preserve or config.preserve_dn,
        start_date=config.start_date,
        end_date=config.end_date,
    )

    cert_pem = serialize_cert(cert)

    # Write cert to temp file then move
    cert_tmp = session.mktemp()
    cert_tmp.write_bytes(cert_pem)
    crt_out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(cert_tmp), str(crt_out))

    # Copy to certs_by_serial/
    serial_copy = config.pki_dir / "certs_by_serial" / f"{serial_hex}.pem"
    serial_copy.parent.mkdir(parents=True, exist_ok=True)
    import shutil as _shutil
    _shutil.copy2(str(crt_out), str(serial_copy))

    # Update index.txt
    expiry_dt = get_cert_not_after(cert)
    expiry_asn1 = asn1_from_datetime(expiry_dt)
    dn = cert_subject_to_dn_string(cert)
    record = IndexRecord(
        status="V",
        expiry=expiry_asn1,
        revoke_info="",
        serial=serial_hex,
        unknown="unknown",
        subject=dn,
    )
    append_record(index_path, record)

    # Update serial file for next use
    write_serial(config.pki_dir, serial_hex)

    # Build inline file if not disabled and cert_type is not 'ca'
    if not config.no_inline and cert_type != "ca":
        from ..inline import build_inline
        try:
            build_inline(config, name, "std")
        except Exception:
            pass

    print(f"\nNotice: Certificate created at:\n* {crt_out}")


def _adjust_pathlen(exts: list, path_len: int) -> list:
    """Replace basicConstraints with one that includes pathlen."""
    from cryptography import x509
    new_exts = []
    for ext_obj, crit in exts:
        if isinstance(ext_obj, x509.BasicConstraints):
            new_exts.append((x509.BasicConstraints(ca=True, path_length=path_len), crit))
        else:
            new_exts.append((ext_obj, crit))
    return new_exts


def _get_unique_serial(records: list) -> int:
    """Generate a unique 128-bit random serial not in index.txt."""
    from ..crypto import generate_serial
    for _ in range(10):
        s = generate_serial()
        sh = serial_to_hex(s)
        if _is_unique_serial(records, sh):
            return s
    raise EasyRSAUserError("Failed to generate a unique serial number after 10 attempts")


def _get_csr_cn(csr) -> str:
    """Extract commonName from a CSR subject."""
    from cryptography.x509.oid import NameOID
    attrs = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if attrs:
        return attrs[0].value
    return ""


def _confirm_sign(cert_type: str, name: str, cn: str, config: EasyRSAConfig, force_subj) -> None:
    """Prompt user to confirm certificate signing."""
    print(f"\nYou are about to sign the following certificate:")
    print(f"  Requested CN:     '{cn}'")
    print(f"  Requested type:   '{cert_type}'")
    if config.end_date:
        print(f"  Valid until:      '{config.end_date}'")
    else:
        print(f"  Valid for:        '{config.cert_expire}' days")
    if force_subj:
        print(f"  Forced Subject:   '{force_subj}'")
    answer = input("\nType 'yes' to confirm signing: ").strip()
    if answer.lower() != "yes":
        raise EasyRSAUserError("sign-req aborted by user.")


def build_full(
    config: EasyRSAConfig,
    session: Session,
    cert_type: str,
    name: str,
    nopass: bool = False,
) -> None:
    """Generate key+CSR and immediately sign it (build-*-full)."""
    req_out = config.pki_dir / "reqs" / f"{name}.req"
    key_out = config.pki_dir / "private" / f"{name}.key"
    crt_out = config.pki_dir / "issued" / f"{name}.crt"

    for label, path in [("Request", req_out), ("Key", key_out), ("Certificate", crt_out)]:
        if path.exists():
            raise EasyRSAUserError(
                f"{label} file already exists. Aborting build to avoid overwriting this file.\n"
                f"If you wish to continue, please use a different name.\n"
                f"Conflicting file found at:\n* {path}"
            )

    # Temporarily enable copy-ext for build-full
    old_cp_ext = config.cp_ext
    config.cp_ext = True

    try:
        gen_req(config, session, name, nopass=nopass, text=False)
        sign_req(config, session, cert_type, name, local_request=True)
    finally:
        config.cp_ext = old_cp_ext


def renew(config: EasyRSAConfig, session: Session, name: str) -> None:
    """Renew a certificate keeping the same key and request."""
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    req_in = config.pki_dir / "reqs" / f"{name}.req"
    inline_pub = config.pki_dir / "inline" / f"{name}.inline"
    inline_pri = config.pki_dir / "inline" / "private" / f"{name}.inline"

    if not crt_in.exists():
        raise EasyRSAUserError(f"Missing certificate file:\n* {crt_in}")
    if not req_in.exists():
        raise EasyRSAUserError(f"Missing request file:\n* {req_in}")

    # Load cert and req
    cert = load_cert(crt_in.read_bytes())
    csr = load_csr(req_in.read_bytes())

    # Verify CN matches
    from ..crypto import get_cert_subject
    cert_cn = get_cert_subject(cert).get("CN", "")
    csr_cn = _get_csr_cn(csr)
    if cert_cn != csr_cn:
        raise EasyRSAUserError("Certificate cannot be renewed due to commonName mismatch")

    # Get cert serial
    old_serial_hex = get_cert_serial_hex(cert)

    # Get cert type from existing cert EKU
    cert_type = _detect_cert_type(cert)

    # Extract digest from old cert
    try:
        sig_alg = cert.signature_hash_algorithm
        if sig_alg:
            config.digest = sig_alg.name.lower()
    except Exception:
        pass

    # Extract SAN from old cert if present
    from cryptography import x509 as _x509
    try:
        san_ext = cert.extensions.get_extension_for_class(_x509.SubjectAlternativeName)
        san_values = []
        for name_obj in san_ext.value:
            if isinstance(name_obj, _x509.DNSName):
                san_values.append(f"DNS:{name_obj.value}")
            elif isinstance(name_obj, _x509.IPAddress):
                san_values.append(f"IP:{name_obj.value}")
            elif isinstance(name_obj, _x509.RFC822Name):
                san_values.append(f"email:{name_obj.value}")
        if san_values:
            san_str = ",".join(san_values)
            san_crit = san_ext.critical
            crit_prefix = "critical," if san_crit else ""
            config.extra_exts = (config.extra_exts + "\n" if config.extra_exts else "") + \
                                 f"subjectAltName = {crit_prefix}{san_str}"
    except _x509.ExtensionNotFound:
        pass

    # Confirm
    if not config.batch:
        answer = input(
            f"\nWARNING: This process is destructive!\n"
            f"Certificate '{name}' will be moved to the 'renewed' sub-directory.\n"
            f"Type 'yes' to continue: "
        ).strip()
        if answer.lower() != "yes":
            raise EasyRSAUserError("renew aborted by user.")

    # Set unique_subject = no
    attr_file = config.pki_dir / "index.txt.attr"
    attr_file.write_text("unique_subject = no\n", encoding="utf-8")

    # Move cert to renewed/
    renewed_dir = config.pki_dir / "renewed" / "issued"
    renewed_dir.mkdir(parents=True, exist_ok=True)
    renewed_out = renewed_dir / f"{name}.crt"
    if renewed_out.exists():
        raise EasyRSAUserError(
            f"Cannot renew this certificate, a conflicting file exists:\n* {renewed_out}\n"
            f"Use command 'revoke-renewed' to revoke this certificate."
        )

    # Cleanup inline files and PKCS files
    for f in [inline_pub, inline_pri]:
        if f.exists():
            f.unlink(missing_ok=True)

    import shutil as _shutil
    _shutil.move(str(crt_in), str(renewed_out))

    try:
        # Sign new cert
        sign_req(config, session, cert_type, name, local_request=True)
    except Exception:
        # Restore cert on failure
        _shutil.move(str(renewed_out), str(crt_in))
        raise

    print(f"\nNotice: Renew was successful.")
    print(f"  To revoke the old certificate once the new one is deployed:")
    print(f"  Use command 'revoke-renewed {name}'")


def _detect_cert_type(cert) -> str:
    """Detect certificate type from EKU."""
    from ..crypto import get_cert_eku
    from cryptography.x509.oid import ExtendedKeyUsageOID
    ekus = get_cert_eku(cert)
    srv = ExtendedKeyUsageOID.SERVER_AUTH.dotted_string
    cli = ExtendedKeyUsageOID.CLIENT_AUTH.dotted_string
    cod = ExtendedKeyUsageOID.CODE_SIGNING.dotted_string
    eml = ExtendedKeyUsageOID.EMAIL_PROTECTION.dotted_string

    if srv in ekus and cli in ekus:
        return "serverClient"
    elif srv in ekus:
        return "server"
    elif cli in ekus:
        return "client"
    elif cod in ekus:
        return "codeSigning"
    elif eml in ekus:
        return "email"
    else:
        return "client"


def expire_cert(config: EasyRSAConfig, session: Session, name: str) -> None:
    """Move a certificate from issued/ to expired/."""
    from ..pki import verify_ca
    verify_ca(config.pki_dir)

    crt_in = config.pki_dir / "issued" / f"{name}.crt"
    crt_out_dir = config.pki_dir / "expired"
    crt_out = crt_out_dir / f"{name}.crt"

    if not crt_in.exists():
        raise EasyRSAUserError(f"Missing certificate file:\n* {crt_in}")
    if crt_out.exists():
        raise EasyRSAUserError(
            f"Cannot expire this certificate, a conflicting file exists:\n* {crt_out}"
        )

    # Verify it's a valid cert
    try:
        cert = load_cert(crt_in.read_bytes())
    except Exception:
        raise EasyRSAUserError(f"Input file is not a valid certificate:\n* {crt_in}")

    cert_serial = get_cert_serial_hex(cert)
    expiry = get_cert_not_after(cert)

    if not config.batch:
        dn = cert_subject_to_dn_string(cert)
        answer = input(
            f"\nPlease confirm you wish to expire the certificate:\n{dn}\n"
            f"  serial-number = {cert_serial}\n"
            f"  notAfter date = {expiry}\n"
            f"Type 'yes' to continue: "
        ).strip()
        if answer.lower() != "yes":
            raise EasyRSAUserError("expire aborted by user.")

    crt_out_dir.mkdir(parents=True, exist_ok=True)
    import shutil as _shutil
    _shutil.move(str(crt_in), str(crt_out))

    print(f"\nNotice: Certificate has been successfully moved to the expired directory.")
    print(f"* {crt_out}")
