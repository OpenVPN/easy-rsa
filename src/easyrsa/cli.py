"""Command-line interface for Easy-RSA Python rewrite."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .config import EasyRSAConfig
from .errors import EasyRSAError, EasyRSAUserError
from .session import Session


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easyrsa",
        description=f"Easy-RSA {__version__} — PKI management tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    # Global options
    parser.add_argument("--version", action="version", version=f"Easy-RSA {__version__}")
    parser.add_argument("--pki-dir", dest="pki_dir", metavar="DIR",
                        help="Path to PKI directory (default: ./pki)")
    parser.add_argument("--vars", dest="vars_file", metavar="FILE",
                        help="Path to vars file")
    parser.add_argument("--batch", action="store_true", default=None,
                        help="Enable batch mode (no interactive prompts)")
    parser.add_argument("--silent", action="store_true", default=None,
                        help="Suppress non-error output")
    parser.add_argument("--verbose", action="store_true", default=None,
                        help="Enable verbose output")
    parser.add_argument("--no-pass", dest="no_pass", action="store_true", default=None,
                        help="Do not use a passphrase for private keys")
    parser.add_argument("--passin", metavar="SPEC",
                        help="Input passphrase specifier (pass:, file:, env:)")
    parser.add_argument("--passout", metavar="SPEC",
                        help="Output passphrase specifier (pass:, file:, env:)")
    parser.add_argument("--algo", choices=["rsa", "ec", "ed"],
                        help="Crypto algorithm")
    parser.add_argument("--curve", metavar="CURVE",
                        help="EC/Ed curve name (e.g. secp384r1, ed25519)")
    parser.add_argument("--key-size", dest="key_size", type=int, metavar="BITS",
                        help="RSA key size in bits")
    parser.add_argument("--digest", metavar="DIGEST",
                        help="Digest algorithm (sha256, sha384, sha512, ...)")
    parser.add_argument("--dn-mode", dest="dn_mode", choices=["cn_only", "org"],
                        help="Distinguished Name mode")
    parser.add_argument("--req-cn", dest="req_cn", metavar="CN",
                        help="Common Name for the request")
    parser.add_argument("--days", dest="cert_expire", type=int, metavar="N",
                        help="Certificate validity in days")
    parser.add_argument("--ca-expire", dest="ca_expire", type=int, metavar="N",
                        help="CA certificate validity in days")
    parser.add_argument("--crl-days", dest="crl_days", type=int, metavar="N",
                        help="CRL validity in days")
    parser.add_argument("--san", metavar="SAN",
                        help="subjectAltName (e.g. DNS:host.example.com,IP:1.2.3.4)")
    parser.add_argument("--extra-exts", dest="extra_exts", metavar="EXTS",
                        help="Extra X509 extensions (OpenSSL-style)")
    parser.add_argument("--subca-len", dest="subca_len", type=int, metavar="N",
                        help="Path length constraint for sub-CA")
    parser.add_argument("--start-date", dest="start_date", metavar="DATE",
                        help="Certificate start date (YYYYMMDDHHMMSSZ)")
    parser.add_argument("--end-date", dest="end_date", metavar="DATE",
                        help="Certificate end date (YYYYMMDDHHMMSSZ)")
    parser.add_argument("--no-inline", dest="no_inline", action="store_true", default=None,
                        help="Do not create inline files")

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- init-pki ---
    p_init = subparsers.add_parser("init-pki", help="Initialize a new PKI")
    p_init.add_argument("--no-ansi", dest="no_ansi", action="store_true", default=False)

    # --- build-ca ---
    p_bca = subparsers.add_parser("build-ca", help="Build a Certificate Authority")
    p_bca.add_argument("nopass", nargs="?", default=None,
                       help="Pass 'nopass' to skip CA key passphrase")

    # --- build-client-full ---
    p_bcf = subparsers.add_parser("build-client-full",
                                   help="Generate and sign a client certificate in one step")
    p_bcf.add_argument("name", help="Client name")
    p_bcf.add_argument("nopass", nargs="?", default=None)
    p_bcf.add_argument("inline", nargs="?", default=None)

    # --- build-server-full ---
    p_bsf = subparsers.add_parser("build-server-full",
                                   help="Generate and sign a server certificate in one step")
    p_bsf.add_argument("name", help="Server name")
    p_bsf.add_argument("nopass", nargs="?", default=None)
    p_bsf.add_argument("inline", nargs="?", default=None)

    # --- build-serverClient-full ---
    p_bscf = subparsers.add_parser("build-serverClient-full",
                                    help="Generate and sign a serverClient certificate")
    p_bscf.add_argument("name", help="Name")
    p_bscf.add_argument("nopass", nargs="?", default=None)
    p_bscf.add_argument("inline", nargs="?", default=None)

    # --- gen-req ---
    p_gr = subparsers.add_parser("gen-req", help="Generate a certificate request")
    p_gr.add_argument("name", help="Name for the request")
    p_gr.add_argument("nopass", nargs="?", default=None)

    # --- sign-req ---
    p_sr = subparsers.add_parser("sign-req", help="Sign a certificate request")
    p_sr.add_argument("cert_type", metavar="TYPE",
                      help="Certificate type: client, server, ca, serverClient, etc.")
    p_sr.add_argument("name", help="Name of the request to sign")
    p_sr.add_argument("nopass", nargs="?", default=None)
    p_sr.add_argument("inline", nargs="?", default=None)

    # --- import-req ---
    p_ir = subparsers.add_parser("import-req", help="Import an external CSR")
    p_ir.add_argument("req_file", metavar="REQFILE", help="Path to the CSR file")
    p_ir.add_argument("short_name", metavar="NAME", help="Short name for the request")

    # --- import-ca ---
    p_ica = subparsers.add_parser("import-ca", help="Import a CA certificate")
    p_ica.add_argument("ca_file", metavar="CAFILE", help="Path to the CA certificate")
    p_ica.add_argument("--copy-ext", dest="copy_ext", action="store_true", default=False)

    # --- import-tls-key / import-key-tls ---
    p_itk = subparsers.add_parser("import-tls-key", help="Import a TLS static key")
    p_itk.add_argument("tls_key_file", metavar="KEYFILE", help="Path to the TLS key file")
    p_itk.add_argument("key_name", metavar="NAME", nargs="?", default="tc",
                        help="Name for the imported key (default: tc)")

    # --- gen-tls-key ---
    p_gtk = subparsers.add_parser("gen-tls-key", help="Generate a TLS authentication/crypt key")
    p_gtk.add_argument("key_name", metavar="NAME", nargs="?", default="tc",
                        help="Name for the key (default: tc)")
    p_gtk.add_argument("--type", dest="key_type", default="tls-crypt-v2-server",
                        choices=["tls-auth", "tls-crypt", "tls-crypt-v2-server",
                                 "tls-crypt-v2-client"],
                        help="Key type (default: tls-crypt-v2-server)")

    # --- revoke ---
    p_rev = subparsers.add_parser("revoke", help="Revoke a certificate")
    p_rev.add_argument("name", help="Name of the certificate to revoke")
    p_rev.add_argument("reason", nargs="?", default=None,
                       help="Revocation reason")

    # --- revoke-issued ---
    p_ri = subparsers.add_parser("revoke-issued", help="Revoke a current (issued) certificate")
    p_ri.add_argument("name")
    p_ri.add_argument("reason", nargs="?", default=None)

    # --- revoke-expired ---
    p_re = subparsers.add_parser("revoke-expired", help="Revoke an expired certificate")
    p_re.add_argument("name")
    p_re.add_argument("reason", nargs="?", default=None)

    # --- revoke-renewed ---
    p_rr = subparsers.add_parser("revoke-renewed", help="Revoke a renewed (old) certificate")
    p_rr.add_argument("name")
    p_rr.add_argument("reason", nargs="?", default=None)

    # --- gen-crl ---
    subparsers.add_parser("gen-crl", help="Generate a Certificate Revocation List")

    # --- update-db ---
    subparsers.add_parser("update-db", help="Update index.txt with expired certificate status")

    # --- renew ---
    p_renew = subparsers.add_parser("renew", help="Renew a certificate")
    p_renew.add_argument("name", help="Name of the certificate to renew")
    p_renew.add_argument("nopass", nargs="?", default=None)
    p_renew.add_argument("inline", nargs="?", default=None)

    # --- expire ---
    p_exp = subparsers.add_parser("expire", help="Move a certificate to expired/")
    p_exp.add_argument("name", help="Name of the certificate to expire")

    # --- renew-ca ---
    subparsers.add_parser("renew-ca", help="Renew the CA certificate (keeps the same key)")

    # --- export-p12 ---
    p_ep12 = subparsers.add_parser("export-p12", help="Export a PKCS#12 file")
    p_ep12.add_argument("name", help="Name of the certificate to export")
    p_ep12.add_argument("nopass", nargs="?", default=None)
    p_ep12.add_argument("noca", nargs="?", default=None)
    p_ep12.add_argument("nokey", nargs="?", default=None)
    p_ep12.add_argument("nofn", nargs="?", default=None)
    p_ep12.add_argument("legacy", nargs="?", default=None)

    # --- export-p7 ---
    p_ep7 = subparsers.add_parser("export-p7", help="Export a PKCS#7 certificate chain")
    p_ep7.add_argument("name", help="Name of the certificate to export")
    p_ep7.add_argument("noca", nargs="?", default=None)

    # --- export-p8 ---
    p_ep8 = subparsers.add_parser("export-p8", help="Export a private key as PKCS#8")
    p_ep8.add_argument("name", help="Name")
    p_ep8.add_argument("nopass", nargs="?", default=None)

    # --- export-p1 ---
    p_ep1 = subparsers.add_parser("export-p1", help="Export a private key in PKCS#1 format")
    p_ep1.add_argument("name", help="Name")
    p_ep1.add_argument("nopass", nargs="?", default=None)

    # --- gen-dh ---
    subparsers.add_parser("gen-dh", help="Generate Diffie-Hellman parameters")

    # --- show-cert ---
    p_sc = subparsers.add_parser("show-cert", help="Display a certificate")
    p_sc.add_argument("name", help="Certificate name")
    p_sc.add_argument("--notext", action="store_true", default=False)

    # --- show-req ---
    p_sreq = subparsers.add_parser("show-req", help="Display a certificate request")
    p_sreq.add_argument("name", help="Request name")
    p_sreq.add_argument("--notext", action="store_true", default=False)

    # --- show-ca ---
    p_sca = subparsers.add_parser("show-ca", help="Display the CA certificate")
    p_sca.add_argument("--notext", action="store_true", default=False)

    # --- show-crl ---
    p_scrl = subparsers.add_parser("show-crl", help="Display the CRL")
    p_scrl.add_argument("--notext", action="store_true", default=False)

    # --- verify-cert ---
    p_vc = subparsers.add_parser("verify-cert", help="Verify a certificate against the CA")
    p_vc.add_argument("name", help="Certificate name")

    # --- show-expire ---
    p_se = subparsers.add_parser("show-expire", help="Show certificates expiring soon")
    p_se.add_argument("days", nargs="?", type=int, default=0,
                      help="Show certs expiring within N days (0 = all)")

    # --- show-revoke ---
    subparsers.add_parser("show-revoke", help="Show revoked certificates")

    # --- show-renew ---
    subparsers.add_parser("show-renew", help="Show renewed certificates")

    # --- display-dn ---
    p_dn = subparsers.add_parser("display-dn", help="Display the DN of a certificate or request")
    p_dn.add_argument("name", help="Name")

    # --- show-eku ---
    p_eku = subparsers.add_parser("show-eku", help="Show Extended Key Usage")
    p_eku.add_argument("name", help="Certificate name")

    # --- set-pass ---
    p_sp = subparsers.add_parser("set-pass", help="Change private key passphrase")
    p_sp.add_argument("name", help="Key name")

    # --- check-serial ---
    p_cs = subparsers.add_parser("check-serial", help="Check a serial number in index.txt")
    p_cs.add_argument("serial", metavar="SERIAL", help="Serial number (hex)")

    # --- rand ---
    p_rand = subparsers.add_parser("rand", help="Generate random bytes (hex output)")
    p_rand.add_argument("num_bytes", type=int, nargs="?", default=16,
                         metavar="BYTES", help="Number of bytes (default: 16)")

    # --- build-inline ---
    p_bi = subparsers.add_parser("build-inline", help="Build a .inline file")
    p_bi.add_argument("name", help="Certificate/key name")
    p_bi.add_argument("--no-ca", dest="no_ca", action="store_true", default=False)
    p_bi.add_argument("--no-cert", dest="no_cert", action="store_true", default=False)
    p_bi.add_argument("--no-key", dest="no_key", action="store_true", default=False)
    p_bi.add_argument("--tls-key", dest="tls_key", metavar="NAME", default=None,
                      help="Include TLS key with given name")
    p_bi.add_argument("--tls-tag", dest="tls_tag", default="tls-crypt",
                      help="XML tag for TLS key (default: tls-crypt)")

    # --- init-pfp ---
    subparsers.add_parser("init-pfp", help="Initialize peer-fingerprint PKI")

    # --- help ---
    p_help = subparsers.add_parser("help", help="Show help for a command")
    p_help.add_argument("topic", nargs="?", default=None)

    return parser


# ---------------------------------------------------------------------------
# Config builder from parsed args
# ---------------------------------------------------------------------------

def _config_from_args(args: argparse.Namespace) -> EasyRSAConfig:
    """Build EasyRSAConfig from parsed CLI arguments."""
    cli_overrides = {}

    if args.batch is not None and args.batch:
        cli_overrides["batch"] = True
    if args.silent is not None and args.silent:
        cli_overrides["silent"] = True
    if args.verbose is not None and args.verbose:
        cli_overrides["verbose"] = True
    if args.no_pass is not None and args.no_pass:
        cli_overrides["no_pass"] = True
    if getattr(args, "no_inline", None):
        cli_overrides["no_inline"] = True
    if getattr(args, "passin", None):
        cli_overrides["passin"] = args.passin
    if getattr(args, "passout", None):
        cli_overrides["passout"] = args.passout
    if getattr(args, "algo", None):
        cli_overrides["algo"] = args.algo
    if getattr(args, "curve", None):
        cli_overrides["curve"] = args.curve
    if getattr(args, "key_size", None):
        cli_overrides["key_size"] = args.key_size
    if getattr(args, "digest", None):
        cli_overrides["digest"] = args.digest
    if getattr(args, "dn_mode", None):
        cli_overrides["dn_mode"] = args.dn_mode
    if getattr(args, "req_cn", None):
        cli_overrides["req_cn"] = args.req_cn
    if getattr(args, "cert_expire", None):
        cli_overrides["cert_expire"] = args.cert_expire
    if getattr(args, "ca_expire", None):
        cli_overrides["ca_expire"] = args.ca_expire
    if getattr(args, "crl_days", None):
        cli_overrides["crl_days"] = args.crl_days
    if getattr(args, "san", None):
        cli_overrides["san"] = args.san
    if getattr(args, "extra_exts", None):
        cli_overrides["extra_exts"] = args.extra_exts
    if getattr(args, "subca_len", None) is not None:
        cli_overrides["subca_len"] = args.subca_len
    if getattr(args, "start_date", None):
        cli_overrides["start_date"] = args.start_date
    if getattr(args, "end_date", None):
        cli_overrides["end_date"] = args.end_date

    pki_dir = Path(args.pki_dir) if getattr(args, "pki_dir", None) else None
    vars_file = Path(args.vars_file) if getattr(args, "vars_file", None) else None

    # Determine easyrsa_dir = directory containing this package's data
    import importlib.resources as pkg_resources
    try:
        from importlib.resources import files
        data_dir = files("easyrsa") / "data"
        easyrsa_dir = Path(str(data_dir))
    except Exception:
        easyrsa_dir = Path(__file__).parent / "data"

    return EasyRSAConfig.from_env_and_args(
        vars_file=vars_file,
        cli_overrides=cli_overrides,
        easyrsa_dir=easyrsa_dir,
        pki_dir=pki_dir,
    )


# ---------------------------------------------------------------------------
# Command dispatcher
# ---------------------------------------------------------------------------

def _dispatch(args: argparse.Namespace, config: EasyRSAConfig, session: Session) -> int:
    """Dispatch parsed args to the appropriate command handler."""
    cmd = args.command

    if cmd == "init-pki":
        from .pki import init_pki
        init_pki(config.pki_dir, algo=config.algo, curve=config.curve, batch=config.batch)
        return 0

    elif cmd == "build-ca":
        from .commands.ca import build_ca
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        build_ca(config, session, sub_ca=False)
        return 0

    elif cmd == "build-sub-ca":
        from .commands.ca import build_ca
        build_ca(config, session, sub_ca=True)
        return 0

    elif cmd == "renew-ca":
        from .commands.ca import renew_ca_cert
        renew_ca_cert(config, session)
        return 0

    elif cmd in ("build-client-full", "build-server-full", "build-serverClient-full"):
        from .commands.certs import build_full
        type_map = {
            "build-client-full": "client",
            "build-server-full": "server",
            "build-serverClient-full": "serverClient",
        }
        cert_type = type_map[cmd]
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        inline = getattr(args, "inline", None) == "inline"
        build_full(config, session, cert_type, args.name, nopass=nopass)
        if inline and not config.no_inline:
            from .inline import build_inline
            build_inline(config, args.name)
        return 0

    elif cmd == "gen-req":
        from .commands.certs import gen_req
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        gen_req(config, session, args.name, nopass=nopass)
        return 0

    elif cmd == "sign-req":
        from .commands.certs import sign_req
        inline = getattr(args, "inline", None) == "inline"
        sign_req(config, session, args.cert_type, args.name)
        if inline and not config.no_inline:
            from .inline import build_inline
            build_inline(config, args.name)
        return 0

    elif cmd == "import-req":
        from .commands.import_ import import_req
        import_req(config, session, args.req_file, args.short_name)
        return 0

    elif cmd == "import-ca":
        from .commands.import_ import import_ca
        import_ca(config, session, args.ca_file)
        return 0

    elif cmd == "import-tls-key":
        from .commands.import_ import import_tls_key
        import_tls_key(config, session, args.tls_key_file, args.key_name)
        return 0

    elif cmd == "gen-tls-key":
        from .commands.tls import gen_tls_key
        gen_tls_key(config, session, args.key_name, args.key_type)
        return 0

    elif cmd == "revoke":
        from .commands.revoke import revoke
        revoke(config, session, "issued", args.name, args.reason, move_req_and_key=True)
        return 0

    elif cmd == "revoke-issued":
        from .commands.revoke import revoke
        revoke(config, session, "issued", args.name, args.reason)
        return 0

    elif cmd == "revoke-expired":
        from .commands.revoke import revoke
        revoke(config, session, "expired", args.name, args.reason)
        return 0

    elif cmd == "revoke-renewed":
        from .commands.revoke import revoke
        revoke(config, session, "renewed/issued", args.name, args.reason)
        return 0

    elif cmd == "gen-crl":
        from .commands.crl import gen_crl
        gen_crl(config, session)
        return 0

    elif cmd == "update-db":
        from .commands.crl import update_db
        update_db(config, session)
        return 0

    elif cmd == "renew":
        from .commands.certs import renew
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        inline = getattr(args, "inline", None) == "inline"
        renew(config, session, args.name, nopass=nopass)
        if inline and not config.no_inline:
            from .inline import build_inline
            build_inline(config, args.name)
        return 0

    elif cmd == "expire":
        from .commands.certs import expire_cert
        expire_cert(config, session, args.name)
        return 0

    elif cmd == "export-p12":
        from .commands.export import export_p12
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        noca = getattr(args, "noca", None) == "noca"
        nokey = getattr(args, "nokey", None) == "nokey"
        nofn = getattr(args, "nofn", None) == "nofn"
        legacy = getattr(args, "legacy", None) == "legacy"
        export_p12(config, session, args.name, nopass=nopass, noca=noca,
                   nokey=nokey, nofn=nofn, legacy=legacy)
        return 0

    elif cmd == "export-p7":
        from .commands.export import export_p7
        noca = getattr(args, "noca", None) == "noca"
        export_p7(config, session, args.name, noca=noca)
        return 0

    elif cmd == "export-p8":
        from .commands.export import export_p8
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        export_p8(config, session, args.name, nopass=nopass)
        return 0

    elif cmd == "export-p1":
        from .commands.export import export_p1
        nopass = getattr(args, "nopass", None) == "nopass" or config.no_pass
        export_p1(config, session, args.name, nopass=nopass)
        return 0

    elif cmd == "gen-dh":
        from .commands.misc import gen_dh
        gen_dh(config, session)
        return 0

    elif cmd == "rand":
        from .commands.misc import rand
        rand(config, session, args.num_bytes)
        return 0

    elif cmd == "set-pass":
        from .commands.misc import set_pass
        set_pass(config, session, args.name)
        return 0

    elif cmd == "check-serial":
        from .commands.misc import check_serial
        check_serial(config, session, args.serial)
        return 0

    elif cmd == "show-cert":
        from .commands.inspect import show_cert
        show_cert(config, session, args.name, notext=args.notext)
        return 0

    elif cmd == "show-req":
        from .commands.inspect import show_req
        show_req(config, session, args.name, notext=args.notext)
        return 0

    elif cmd == "show-ca":
        from .commands.inspect import show_ca
        show_ca(config, session, notext=args.notext)
        return 0

    elif cmd == "show-crl":
        from .commands.inspect import show_crl
        show_crl(config, session, notext=args.notext)
        return 0

    elif cmd == "verify-cert":
        from .commands.inspect import verify_cert
        verify_cert(config, session, args.name)
        return 0

    elif cmd == "show-expire":
        from .commands.inspect import show_expire
        show_expire(config, session, days=args.days)
        return 0

    elif cmd == "show-revoke":
        from .commands.inspect import show_revoke
        show_revoke(config, session)
        return 0

    elif cmd == "show-renew":
        from .commands.inspect import show_renew
        show_renew(config, session)
        return 0

    elif cmd == "display-dn":
        from .commands.inspect import display_dn
        display_dn(config, session, args.name)
        return 0

    elif cmd == "show-eku":
        from .commands.inspect import show_eku
        show_eku(config, session, args.name)
        return 0

    elif cmd == "build-inline":
        from .inline import build_inline
        include_tls = args.tls_key is not None
        build_inline(
            config, args.name,
            include_ca=not args.no_ca,
            include_cert=not args.no_cert,
            include_key=not args.no_key,
            include_tls=include_tls,
            tls_key_name=args.tls_key or "tc",
            tls_tag=args.tls_tag,
        )
        return 0

    elif cmd == "init-pfp":
        from .inline import init_peer_fingerprint_pki
        init_peer_fingerprint_pki(config)
        return 0

    elif cmd == "help" or cmd is None:
        topic = getattr(args, "topic", None)
        if topic:
            # Try to get subparser help
            parser = _build_parser()
            if topic in parser._subparsers._group_actions[0].choices:
                parser._subparsers._group_actions[0].choices[topic].print_help()
            else:
                print(f"No help available for '{topic}'")
        else:
            _build_parser().print_help()
        return 0

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        _build_parser().print_help()
        return 1


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[list] = None) -> int:
    """Main entry point for the easyrsa CLI."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        config = _config_from_args(args)
    except EasyRSAUserError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return e.exit_code

    try:
        with Session(config.pki_dir, no_lockfile=config.no_lockfile) as session:
            return _dispatch(args, config, session)
    except EasyRSAError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return e.exit_code
    except KeyboardInterrupt:
        print("\nAborted.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
