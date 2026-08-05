"""
Multi-Node Certificate Generation Script

Generates a CA and certificates for 4 nodes in the test network.
Each node gets its own certificate with proper SAN entries.
"""

import sys
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta, timezone

MASSIR_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


# Define all nodes in the network
NODES = [
    {"id": "node1", "hostname": "node1", "ip": "192.168.1.101"},
    {"id": "node2", "hostname": "node2", "ip": "192.168.1.102"},
    {"id": "node3", "hostname": "node3", "ip": "192.168.1.103"},
    {"id": "node4", "hostname": "node4", "ip": "192.168.1.104"},
]


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
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Massir Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    return (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=3650))
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
        .sign(key, hashes.SHA256(), default_backend())
    )


def generate_node_cert(ca_key, ca_cert, node):
    """Generate a node certificate signed by the CA."""
    node_key = generate_key()
    
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Massir Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, node["id"]),
    ])
    
    # Build SAN
    san_list = [
        x509.DNSName("localhost"),
        x509.DNSName(node["hostname"]),
        x509.DNSName(node["id"]),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.IPAddress(ipaddress.IPv4Address(node["ip"])),
    ]
    
    # Add all other nodes as SAN
    for other_node in NODES:
        if other_node["id"] != node["id"]:
            san_list.append(x509.DNSName(other_node["hostname"]))
    
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(node_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
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
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )
        .add_extension(
            x509.SubjectAlternativeName(san_list),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256(), default_backend())
    )
    
    return node_key, cert


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
    """Generate all certificates for the test network."""
    certs_dir = Path(__file__).parent.parent / "certs"
    certs_dir.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("🔐 Generating Multi-Node Certificates")
    print("=" * 60)
    
    # 1. Generate CA
    print("\n📜 Generating CA certificate...")
    ca_key = generate_key()
    ca_cert = generate_ca_cert(ca_key)
    save_key(ca_key, certs_dir / "ca.key")
    save_cert(ca_cert, certs_dir / "ca.crt")
    print(f"   ✅ CA: {certs_dir / 'ca.crt'}")
    
    # 2. Generate each node certificate
    for node in NODES:
        print(f"\n🖥️  Generating certificate for {node['id']}...")
        node_key, node_cert = generate_node_cert(ca_key, ca_cert, node)
        save_key(node_key, certs_dir / f"{node['id']}.key")
        save_cert(node_cert, certs_dir / f"{node['id']}.crt")
        print(f"   ✅ {node['id']}.crt and {node['id']}.key")
        print(f"      Hostname: {node['hostname']}")
        print(f"      IP: {node['ip']}")
    
    print("\n" + "=" * 60)
    print("✅ All certificates generated successfully!")
    print("=" * 60)
    print(f"\nFiles in: {certs_dir}")
    print("\n📁 Certificate files:")
    for f in sorted(certs_dir.glob("*.crt")):
        print(f"   📄 {f.name}")
    print("\n🔑 Key files:")
    for f in sorted(certs_dir.glob("*.key")):
        print(f"   🔐 {f.name}")
    print()


if __name__ == "__main__":
    main()
