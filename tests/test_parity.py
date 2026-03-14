"""Parity tests: run both shell and Python Easy-RSA and compare PKI output.

These tests require:
- bash with the original easyrsa shell script available
- Python easyrsa package installed (or accessible via sys.path)
- The 'cryptography' package installed
- openssl in PATH

Tests are skipped if the shell script is not found.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
SHELL_SCRIPT = REPO_ROOT / "easyrsa3" / "easyrsa"
SRC_DIR = str(REPO_ROOT / "src")
PYTHON_EASYRSA = [sys.executable, "-m", "easyrsa"]

BATCH_ENV = {
    **os.environ,
    "EASYRSA_BATCH": "1",
    "EASYRSA_NO_PASS": "1",
    "EASYRSA_REQ_CN": "TestCA",
    "EASYRSA_CALLER": "test",  # Required by shell script vars guard
}


def shell_available() -> bool:
    return SHELL_SCRIPT.exists() and shutil.which("bash") is not None


def run_shell(args: list, pki_dir: Path, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run the shell easyrsa script with given args."""
    cmd = ["bash", str(SHELL_SCRIPT), f"--pki-dir={pki_dir}"] + args
    e = {**BATCH_ENV, **(env or {})}
    return subprocess.run(cmd, capture_output=True, text=True, env=e)


def run_python(args: list, pki_dir: Path, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run the Python easyrsa with given args."""
    cmd = PYTHON_EASYRSA + [f"--pki-dir={pki_dir}", "--batch", "--no-pass"] + args
    # Inject src/ onto PYTHONPATH so the package is importable without installation
    e = {**os.environ, "PYTHONPATH": SRC_DIR + os.pathsep + os.environ.get("PYTHONPATH", ""), **(env or {})}
    return subprocess.run(cmd, capture_output=True, text=True, env=e)


def load_cert(pem_bytes: bytes):
    """Load an X.509 certificate from PEM bytes."""
    from cryptography import x509
    return x509.load_pem_x509_certificate(pem_bytes)


def load_csr(pem_bytes: bytes):
    """Load a CSR from PEM bytes."""
    from cryptography import x509
    return x509.load_pem_x509_csr(pem_bytes)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def shell_pki(tmp_path):
    """Initialize a shell-based PKI in a temp directory."""
    if not shell_available():
        pytest.skip("Shell script or bash not available")
    pki_dir = tmp_path / "shell_pki"
    result = run_shell(["init-pki"], pki_dir)
    assert result.returncode == 0, f"Shell init-pki failed:\n{result.stderr}"
    result = run_shell(["build-ca", "nopass"], pki_dir,
                       env={"EASYRSA_REQ_CN": "ShellTestCA"})
    assert result.returncode == 0, f"Shell build-ca failed:\n{result.stderr}"
    return pki_dir


@pytest.fixture
def python_pki(tmp_path):
    """Initialize a Python-based PKI in a temp directory."""
    pki_dir = tmp_path / "python_pki"
    result = run_python(["init-pki"], pki_dir)
    assert result.returncode == 0, f"Python init-pki failed:\n{result.stderr}"
    result = run_python(["build-ca"], pki_dir,
                        env={"EASYRSA_REQ_CN": "PythonTestCA"})
    assert result.returncode == 0, f"Python build-ca failed:\n{result.stderr}"
    return pki_dir


# ---------------------------------------------------------------------------
# Unit tests (Python-only, no shell required)
# ---------------------------------------------------------------------------

class TestPythonInit:
    """Test Python PKI initialization creates expected files/dirs."""

    def test_init_pki_creates_dirs(self, tmp_path):
        pki_dir = tmp_path / "pki"
        result = run_python(["init-pki"], pki_dir)
        assert result.returncode == 0
        assert (pki_dir / "reqs").is_dir()
        assert (pki_dir / "private").is_dir()
        assert (pki_dir / "issued").is_dir()

    def test_build_ca_creates_cert(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        result = run_python(["build-ca"], pki_dir,
                            env={"EASYRSA_REQ_CN": "TestCA"})
        assert result.returncode == 0
        ca_crt = pki_dir / "ca.crt"
        assert ca_crt.exists()
        # Validate it's a real X.509 cert
        cert = load_cert(ca_crt.read_bytes())
        assert cert is not None

    def test_build_ca_is_self_signed(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        cert = load_cert((pki_dir / "ca.crt").read_bytes())
        # For a self-signed cert, subject == issuer
        assert cert.subject == cert.issuer

    def test_build_ca_has_basic_constraints(self, tmp_path):
        from cryptography import x509
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        cert = load_cert((pki_dir / "ca.crt").read_bytes())
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.value.ca is True

    def test_gen_req_creates_files(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        result = run_python(["gen-req", "testclient"], pki_dir,
                            env={"EASYRSA_REQ_CN": "testclient"})
        assert result.returncode == 0
        assert (pki_dir / "reqs" / "testclient.req").exists()
        assert (pki_dir / "private" / "testclient.key").exists()

    def test_sign_req_creates_cert(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["gen-req", "testclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "testclient"})
        result = run_python(["sign-req", "client", "testclient"], pki_dir)
        assert result.returncode == 0
        assert (pki_dir / "issued" / "testclient.crt").exists()

    def test_signed_cert_not_ca(self, tmp_path):
        from cryptography import x509
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["gen-req", "testclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "testclient"})
        run_python(["sign-req", "client", "testclient"], pki_dir)
        cert = load_cert((pki_dir / "issued" / "testclient.crt").read_bytes())
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.value.ca is False

    def test_signed_cert_has_client_eku(self, tmp_path):
        from cryptography import x509
        from cryptography.x509.oid import ExtendedKeyUsageOID
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["gen-req", "testclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "testclient"})
        run_python(["sign-req", "client", "testclient"], pki_dir)
        cert = load_cert((pki_dir / "issued" / "testclient.crt").read_bytes())
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        oid_list = list(eku.value)
        assert ExtendedKeyUsageOID.CLIENT_AUTH in oid_list

    def test_build_client_full(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        result = run_python(["build-client-full", "myclient"], pki_dir,
                            env={"EASYRSA_REQ_CN": "myclient"})
        assert result.returncode == 0
        assert (pki_dir / "issued" / "myclient.crt").exists()
        assert (pki_dir / "private" / "myclient.key").exists()

    def test_revoke_moves_cert(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["build-client-full", "myclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "myclient"})
        result = run_python(["revoke", "myclient"], pki_dir)
        assert result.returncode == 0
        # Certificate should no longer be in issued/
        assert not (pki_dir / "issued" / "myclient.crt").exists()

    def test_gen_crl_creates_crl(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        result = run_python(["gen-crl"], pki_dir)
        assert result.returncode == 0
        assert (pki_dir / "crl.pem").exists()

    def test_index_txt_updated_after_sign(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["build-client-full", "myclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "myclient"})
        index = (pki_dir / "index.txt").read_text()
        assert "V" in index
        assert "myclient" in index

    def test_index_txt_revoke_status(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["build-client-full", "myclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "myclient"})
        run_python(["revoke", "myclient"], pki_dir)
        index = (pki_dir / "index.txt").read_text()
        # At least one line should start with R
        assert any(line.startswith("R") for line in index.splitlines())

    def test_ec_key_generation(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        result = run_python(
            ["build-ca"],
            pki_dir,
            env={"EASYRSA_REQ_CN": "ECTestCA", "EASYRSA_ALGO": "ec",
                 "EASYRSA_CURVE": "secp384r1"},
        )
        assert result.returncode == 0
        ca_crt = pki_dir / "ca.crt"
        cert = load_cert(ca_crt.read_bytes())
        from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
        assert isinstance(cert.public_key(), EllipticCurvePublicKey)

    def test_export_p12(self, tmp_path):
        pki_dir = tmp_path / "pki"
        run_python(["init-pki"], pki_dir)
        run_python(["build-ca"], pki_dir, env={"EASYRSA_REQ_CN": "TestCA"})
        run_python(["build-client-full", "myclient"], pki_dir,
                   env={"EASYRSA_REQ_CN": "myclient"})
        result = run_python(["export-p12", "myclient", "nopass"], pki_dir)
        assert result.returncode == 0
        assert (pki_dir / "private" / "myclient.p12").exists()


# ---------------------------------------------------------------------------
# Parity tests (require shell script)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shell_available(), reason="Shell script not available")
class TestParity:
    """Verify that Python and shell versions produce equivalent PKI structures."""

    def test_pki_dir_structure_parity(self, shell_pki, python_pki):
        """Both PKIs should have the same top-level directory structure."""
        shell_dirs = {p.name for p in shell_pki.iterdir() if p.is_dir()}
        python_dirs = {p.name for p in python_pki.iterdir() if p.is_dir()}
        # Both should have at minimum these directories
        required = {"reqs", "private", "issued"}
        assert required.issubset(shell_dirs), f"Shell PKI missing dirs: {required - shell_dirs}"
        assert required.issubset(python_dirs), f"Python PKI missing dirs: {required - python_dirs}"

    def test_ca_cert_is_x509_parity(self, shell_pki, python_pki):
        """Both CA certs should be valid X.509 certificates."""
        shell_cert = load_cert((shell_pki / "ca.crt").read_bytes())
        python_cert = load_cert((python_pki / "ca.crt").read_bytes())
        assert shell_cert is not None
        assert python_cert is not None

    def test_ca_cert_basic_constraints_parity(self, shell_pki, python_pki):
        """Both CA certs should have CA:TRUE basic constraints."""
        from cryptography import x509
        for pki_dir in (shell_pki, python_pki):
            cert = load_cert((pki_dir / "ca.crt").read_bytes())
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            assert bc.value.ca is True, f"CA cert in {pki_dir} does not have CA:TRUE"

    def test_client_cert_parity(self, shell_pki, python_pki):
        """Both client certs should have equivalent extensions."""
        from cryptography import x509
        from cryptography.x509.oid import ExtendedKeyUsageOID

        # Generate client cert in both PKIs
        run_shell(["build-client-full", "parityclient", "nopass"], shell_pki,
                  env={"EASYRSA_REQ_CN": "parityclient"})
        run_python(["build-client-full", "parityclient"], python_pki,
                   env={"EASYRSA_REQ_CN": "parityclient"})

        for pki_dir in (shell_pki, python_pki):
            crt = pki_dir / "issued" / "parityclient.crt"
            assert crt.exists(), f"Client cert not found in {pki_dir}"
            cert = load_cert(crt.read_bytes())
            # Must have CA:FALSE
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            assert bc.value.ca is False
            # Must have clientAuth EKU
            eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
            assert ExtendedKeyUsageOID.CLIENT_AUTH in list(eku.value)

    def test_server_cert_parity(self, shell_pki, python_pki):
        """Both server certs should have serverAuth EKU."""
        from cryptography import x509
        from cryptography.x509.oid import ExtendedKeyUsageOID

        run_shell(["build-server-full", "parityserver", "nopass"], shell_pki,
                  env={"EASYRSA_REQ_CN": "parityserver"})
        run_python(["build-server-full", "parityserver"], python_pki,
                   env={"EASYRSA_REQ_CN": "parityserver"})

        for pki_dir in (shell_pki, python_pki):
            cert = load_cert((pki_dir / "issued" / "parityserver.crt").read_bytes())
            eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
            assert ExtendedKeyUsageOID.SERVER_AUTH in list(eku.value)

    def test_index_txt_format_parity(self, shell_pki, python_pki):
        """Both index.txt files should have the same tab-separated format."""
        # Build a client cert in both
        run_shell(["build-client-full", "indexclient", "nopass"], shell_pki,
                  env={"EASYRSA_REQ_CN": "indexclient"})
        run_python(["build-client-full", "indexclient"], python_pki,
                   env={"EASYRSA_REQ_CN": "indexclient"})

        for pki_dir in (shell_pki, python_pki):
            index = (pki_dir / "index.txt").read_text()
            for line in index.strip().splitlines():
                if not line:
                    continue
                fields = line.split("\t")
                assert len(fields) >= 5, (
                    f"index.txt line in {pki_dir} has fewer than 5 tab-separated fields: {line!r}"
                )
                # First field is status
                assert fields[0] in ("V", "R", "E"), (
                    f"Unexpected status in {pki_dir}: {fields[0]!r}"
                )

    def test_crl_parity(self, shell_pki, python_pki):
        """Both should generate valid CRLs."""
        from cryptography import x509

        run_shell(["gen-crl"], shell_pki)
        run_python(["gen-crl"], python_pki)

        for pki_dir in (shell_pki, python_pki):
            crl_pem = (pki_dir / "crl.pem").read_bytes()
            crl = x509.load_pem_x509_crl(crl_pem)
            assert crl is not None, f"CRL in {pki_dir} is not valid"

    def test_revoke_parity(self, shell_pki, python_pki):
        """After revocation and CRL gen, revoked cert should appear in CRL."""
        from cryptography import x509

        # Build and revoke in both
        for run_fn, pki_dir in [(run_shell, shell_pki), (run_python, python_pki)]:
            extra_env = {"EASYRSA_REQ_CN": "revokeclient"}
            if run_fn is run_shell:
                run_fn(["build-client-full", "revokeclient", "nopass"], pki_dir, env=extra_env)
                run_fn(["revoke", "revokeclient"], pki_dir)
            else:
                run_fn(["build-client-full", "revokeclient"], pki_dir, env=extra_env)
                run_fn(["revoke", "revokeclient"], pki_dir)
            run_fn(["gen-crl"], pki_dir)

        # Verify CRLs have revoked entries
        for pki_dir in (shell_pki, python_pki):
            crl_pem = (pki_dir / "crl.pem").read_bytes()
            crl = x509.load_pem_x509_crl(crl_pem)
            revoked = list(crl)
            assert len(revoked) > 0, f"CRL in {pki_dir} has no revoked certificates"


# ---------------------------------------------------------------------------
# TLS key generation tests (Python-only, no openvpn binary required)
# ---------------------------------------------------------------------------

class TestTLSKeyGen:
    """Tests for pure-Python TLS key generation (no openvpn binary)."""

    def _init_pki(self, tmp_path):
        pki_dir = tmp_path / "pki"
        result = run_python(["init-pki"], pki_dir)
        assert result.returncode == 0
        return pki_dir

    def test_gen_tls_auth_creates_file(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        result = run_python(["gen-tls-key", "tls-auth"], pki_dir)
        assert result.returncode == 0, f"gen-tls-key tls-auth failed:\n{result.stderr}"
        key_file = pki_dir / "private" / "easyrsa-tls.key"
        assert key_file.exists()

    def test_gen_tls_auth_format(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        run_python(["gen-tls-key", "tls-auth"], pki_dir)
        key_file = pki_dir / "private" / "easyrsa-tls.key"
        content = key_file.read_text()
        assert "-----BEGIN OpenVPN Static key V1-----" in content
        assert "-----END OpenVPN Static key V1-----" in content
        # Verify hex lines (16 bytes = 32 hex chars each)
        lines = content.splitlines()
        hex_lines = [l for l in lines if l and not l.startswith("#") and not l.startswith("---")]
        assert len(hex_lines) == 16, f"Expected 16 hex lines, got {len(hex_lines)}"
        for line in hex_lines:
            assert len(line) == 32, f"Hex line wrong length: {line!r}"
            int(line, 16)  # must be valid hex

    def test_gen_tls_crypt_creates_file(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        result = run_python(["gen-tls-key", "tls-crypt"], pki_dir)
        assert result.returncode == 0, f"gen-tls-key tls-crypt failed:\n{result.stderr}"
        key_file = pki_dir / "private" / "easyrsa-tls.key"
        assert key_file.exists()

    def test_gen_tls_crypt_format(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        run_python(["gen-tls-key", "tls-crypt"], pki_dir)
        content = (pki_dir / "private" / "easyrsa-tls.key").read_text()
        assert "-----BEGIN OpenVPN Static key V1-----" in content
        assert "-----END OpenVPN Static key V1-----" in content

    def test_gen_tls_crypt_v2_server_creates_file(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        result = run_python(["gen-tls-key", "tls-crypt-v2-server"], pki_dir)
        assert result.returncode == 0, f"gen-tls-key tls-crypt-v2-server failed:\n{result.stderr}"
        key_file = pki_dir / "private" / "easyrsa-tls.key"
        assert key_file.exists()

    def test_gen_tls_crypt_v2_server_format(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        run_python(["gen-tls-key", "tls-crypt-v2-server"], pki_dir)
        content = (pki_dir / "private" / "easyrsa-tls.key").read_text()
        assert "-----BEGIN OpenVPN tls-crypt-v2 server key-----" in content
        assert "-----END OpenVPN tls-crypt-v2 server key-----" in content
        # Decode payload and verify 128 bytes
        import base64, re
        m = re.search(
            r"-----BEGIN OpenVPN tls-crypt-v2 server key-----\s+([A-Za-z0-9+/=\s]+?)\s*-----END",
            content,
        )
        assert m, "Could not extract base64 payload"
        raw = base64.b64decode(m.group(1).replace("\n", ""))
        assert len(raw) == 128, f"Server key payload should be 128 bytes, got {len(raw)}"

    def test_gen_tls_crypt_v2_client_creates_file(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        run_python(["gen-tls-key", "tls-crypt-v2-server"], pki_dir)
        result = run_python(["gen-tls-key", "tls-crypt-v2-client"], pki_dir)
        # Client key goes to a different path; but command succeeds
        assert result.returncode == 0, f"gen-tls-key tls-crypt-v2-client failed:\n{result.stderr}"

    def test_gen_tls_crypt_v2_client_format(self, tmp_path):
        import base64, re
        pki_dir = self._init_pki(tmp_path)
        run_python(["gen-tls-key", "tls-crypt-v2-server"], pki_dir)
        # Rename server key so we can generate client key
        server_key = pki_dir / "private" / "easyrsa-tls.key"
        server_backup = pki_dir / "private" / "server.key"
        server_key.rename(server_backup)
        result = run_python(
            ["gen-tls-key", "tls-crypt-v2-client", str(server_backup)], pki_dir
        )
        assert result.returncode == 0, f"gen-tls-key tls-crypt-v2-client failed:\n{result.stderr}"
        client_key = pki_dir / "private" / "easyrsa-tls.key"
        content = client_key.read_text()
        assert "-----BEGIN OpenVPN tls-crypt-v2 client key-----" in content
        assert "-----END OpenVPN tls-crypt-v2 client key-----" in content
        # Decode and verify 555-byte payload (256 Kc + 299 WKc)
        m = re.search(
            r"-----BEGIN OpenVPN tls-crypt-v2 client key-----\s+([A-Za-z0-9+/=\s]+?)\s*-----END",
            content,
        )
        assert m, "Could not extract base64 payload"
        raw = base64.b64decode(m.group(1).replace("\n", ""))
        assert len(raw) == 555, f"Client key payload should be 555 bytes, got {len(raw)}"

    def test_gen_tls_crypt_v2_client_requires_server_key(self, tmp_path):
        """Generating a client key without a server key should fail gracefully."""
        pki_dir = self._init_pki(tmp_path)
        result = run_python(["gen-tls-key", "tls-crypt-v2-client"], pki_dir)
        assert result.returncode != 0

    def test_gen_tls_key_permissions(self, tmp_path):
        import stat
        pki_dir = self._init_pki(tmp_path)
        run_python(["gen-tls-key", "tls-auth"], pki_dir)
        key_file = pki_dir / "private" / "easyrsa-tls.key"
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600, f"Key file permissions should be 0o600, got {oct(mode)}"

    def test_gen_tls_key_invalid_type(self, tmp_path):
        pki_dir = self._init_pki(tmp_path)
        result = run_python(["gen-tls-key", "invalid-type"], pki_dir)
        assert result.returncode != 0
