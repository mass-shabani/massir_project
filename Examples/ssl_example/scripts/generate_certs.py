"""
Certificate Generation Script

Generates self-signed certificates for testing:
- CA (Certificate Authority)
- Server certificate (with SAN)
- Client certificate (for mTLS)
"""

import sys
import ipaddress  # ✅ این import اضافه شود
from pathlib import Path

# Add the main project path to sys.path
MASSIR_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


def generate_key():
    """Generate an RSA private key."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )


def generate_ca_cert(key, common_name="Massir Test CA"):
    """Generate a CA certificate."""
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Massir Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()),
            critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )
    
    return cert


def generate_server_cert(ca_key, ca_cert, common_name="localhost", san_names=None):
    """Generate a server certificate signed by the CA."""
    server_key = generate_key()
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Massir Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    # Build SAN (Subject Alternative Names)
    san_list = [x509.DNSName("localhost")]
    if san_names:
        san_list.extend([x509.DNSName(name) for name in san_names])
    san_list.append(x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")))  # ✅ حالا ipaddress در دسترس است
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))  # 1 year
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    return server_key, cert


def generate_client_cert(ca_key, ca_cert, common_name="client"):
    """Generate a client certificate signed by the CA."""
    client_key = generate_key()
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Massir Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))  # 1 year
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(client_key.public_key()),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    return client_key, cert


def save_key(key, path):
    """Save a private key to a PEM file."""
    with open(path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))


def save_cert(cert, path):
    """Save a certificate to a PEM file."""
    with open(path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def main():
    """Generate all test certificates."""
    certs_dir = Path(__file__).parent.parent / "certs"
    certs_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("🔐 Generating Test Certificates")
    print("=" * 60)
    
    # 1. Generate CA
    print("\n📜 Generating CA certificate...")
    ca_key = generate_key()
    ca_cert = generate_ca_cert(ca_key)
    save_key(ca_key, certs_dir / "ca.key")
    save_cert(ca_cert, certs_dir / "ca.crt")
    print(f"   ✅ CA certificate saved to {certs_dir / 'ca.crt'}")
    
    # 2. Generate Server certificate
    print("\n🖥️  Generating server certificate...")
    server_key, server_cert = generate_server_cert(
        ca_key, ca_cert,
        common_name="localhost",
        san_names=["massir-server", "node-01"]
    )
    save_key(server_key, certs_dir / "server.key")
    save_cert(server_cert, certs_dir / "server.crt")
    print(f"   ✅ Server certificate saved to {certs_dir / 'server.crt'}")
    
    # 3. Generate Client certificate
    print("\n👤 Generating client certificate...")
    client_key, client_cert = generate_client_cert(
        ca_key, ca_cert,
        common_name="massir-client"
    )
    save_key(client_key, certs_dir / "client.key")
    save_cert(client_cert, certs_dir / "client.crt")
    print(f"   ✅ Client certificate saved to {certs_dir / 'client.crt'}")
    
    print("\n" + "=" * 60)
    print("✅ All certificates generated successfully!")
    print("=" * 60)
    print(f"\nCertificate files are in: {certs_dir}")
    print("\nFiles created:")
    for f in sorted(certs_dir.glob("*.crt")):
        print(f"   📄 {f.name}")
    for f in sorted(certs_dir.glob("*.key")):
        print(f"   🔑 {f.name}")
    print()


if __name__ == "__main__":
    main()