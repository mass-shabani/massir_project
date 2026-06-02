"""
RSA-4096 Asymmetric Encryption Module

Provides RSA key generation, encryption, decryption, signing, and verification.

Security notes:
- Use RSA-4096 for long-term security
- RSA can only encrypt data smaller than key size minus padding
- For large data, use hybrid encryption (RSA for key, AES for data)
"""

from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend

from .exceptions import RSAError, RSAKeyError, RSAEncryptionError

# Constants
DEFAULT_RSA_KEY_SIZE = 4096
DEFAULT_RSA_PUBLIC_EXPONENT = 65537


def generate_rsa_keypair(
    key_size: int = DEFAULT_RSA_KEY_SIZE,
) -> Tuple[rsa.RSAPublicKey, rsa.RSAPrivateKey]:
    """
    Generate an RSA key pair.
    
    Args:
        key_size: Key size in bits (default 4096, minimum 2048)
    
    Returns:
        Tuple of (public_key, private_key)
    
    Raises:
        RSAKeyError: If key size is too small
        
    Example:
        >>> pub, priv = generate_rsa_keypair()
        >>> isinstance(pub, rsa.RSAPublicKey)
        True
    """
    if key_size < 2048:
        raise RSAKeyError(
            f"RSA key size must be at least 2048 bits, got {key_size}"
        )
    
    private_key = rsa.generate_private_key(
        public_exponent=DEFAULT_RSA_PUBLIC_EXPONENT,
        key_size=key_size,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    
    return public_key, private_key


def encrypt_rsa(data: bytes, public_key: rsa.RSAPublicKey) -> bytes:
    """
    Encrypt data using RSA-OAEP with SHA-256.
    
    Args:
        data: Data to encrypt (must be smaller than key size - 66 bytes for OAEP)
        public_key: RSA public key
    
    Returns:
        bytes: Encrypted data
        
    Raises:
        RSAEncryptionError: If encryption fails (e.g., data too large)
        
    Example:
        >>> pub, priv = generate_rsa_keypair()
        >>> ciphertext = encrypt_rsa(b"secret", pub)
    """
    if not isinstance(data, bytes):
        raise RSAEncryptionError("Data must be bytes")
    
    try:
        ciphertext = public_key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return ciphertext
    except Exception as e:
        raise RSAEncryptionError(
            f"RSA encryption failed: {str(e)}. "
            "Data may be too large for the key size."
        ) from e


def decrypt_rsa(ciphertext: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    """
    Decrypt data using RSA-OAEP with SHA-256.
    
    Args:
        ciphertext: Encrypted data
        private_key: RSA private key (must match the public key used for encryption)
    
    Returns:
        bytes: Decrypted data
        
    Raises:
        RSAEncryptionError: If decryption fails (wrong key, tampered data)
    """
    if not isinstance(ciphertext, bytes):
        raise RSAEncryptionError("Ciphertext must be bytes")
    
    try:
        plaintext = private_key.decrypt(
            ciphertext,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext
    except Exception as e:
        raise RSAEncryptionError(
            f"RSA decryption failed: {str(e)}. "
            "This may indicate wrong key or tampered ciphertext."
        ) from e


def sign_rsa(data: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    """
    Sign data using RSA-PSS with SHA-256.
    
    Args:
        data: Data to sign
        private_key: RSA private key
    
    Returns:
        bytes: Digital signature
        
    Raises:
        RSAError: If signing fails
    """
    if not isinstance(data, bytes):
        raise RSAError("Data must be bytes")
    
    try:
        signature = private_key.sign(
            data,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return signature
    except Exception as e:
        raise RSAError(f"RSA signing failed: {str(e)}") from e


def verify_rsa(
    data: bytes,
    signature: bytes,
    public_key: rsa.RSAPublicKey,
) -> bool:
    """
    Verify an RSA-PSS signature.
    
    Args:
        data: Original data that was signed
        signature: Signature to verify
        public_key: RSA public key (must match the private key used for signing)
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not isinstance(data, bytes) or not isinstance(signature, bytes):
        return False
    
    try:
        public_key.verify(
            signature,
            data,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False


def serialize_public_key(
    public_key: rsa.RSAPublicKey,
    encoding: str = "PEM",
) -> bytes:
    """
    Serialize a public key to bytes for storage or transmission.
    
    Args:
        public_key: RSA public key
        encoding: "PEM" (default, text-based) or "DER" (binary)
    
    Returns:
        bytes: Serialized public key
    """
    enc = (
        serialization.Encoding.PEM
        if encoding.upper() == "PEM"
        else serialization.Encoding.DER
    )
    
    return public_key.public_bytes(
        encoding=enc,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def serialize_private_key(
    private_key: rsa.RSAPrivateKey,
    password: bytes | None = None,
    encoding: str = "PEM",
) -> bytes:
    """
    Serialize a private key to bytes for storage.
    
    Args:
        private_key: RSA private key
        password: Optional password to encrypt the key
        encoding: "PEM" (default, text-based) or "DER" (binary)
    
    Returns:
        bytes: Serialized private key
    """
    enc = (
        serialization.Encoding.PEM
        if encoding.upper() == "PEM"
        else serialization.Encoding.DER
    )
    
    encryption = (
        serialization.BestAvailableEncryption(password)
        if password
        else serialization.NoEncryption()
    )
    
    return private_key.private_bytes(
        encoding=enc,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )


def deserialize_public_key(
    data: bytes,
) -> rsa.RSAPublicKey:
    """
    Deserialize a public key from bytes.
    
    Args:
        data: Serialized public key (PEM or DER format)
    
    Returns:
        RSA public key object
        
    Raises:
        RSAKeyError: If deserialization fails
    """
    try:
        return serialization.load_pem_public_key(data, backend=default_backend())
    except Exception:
        try:
            return serialization.load_der_public_key(data, backend=default_backend())
        except Exception as e:
            raise RSAKeyError(f"Failed to deserialize public key: {str(e)}") from e


def deserialize_private_key(
    data: bytes,
    password: bytes | None = None,
) -> rsa.RSAPrivateKey:
    """
    Deserialize a private key from bytes.
    
    Args:
        data: Serialized private key (PEM or DER format)
        password: Password if the key is encrypted
    
    Returns:
        RSA private key object
        
    Raises:
        RSAKeyError: If deserialization fails
    """
    try:
        return serialization.load_pem_private_key(
            data, password=password, backend=default_backend()
        )
    except Exception:
        try:
            return serialization.load_der_private_key(
                data, password=password, backend=default_backend()
            )
        except Exception as e:
            raise RSAKeyError(f"Failed to deserialize private key: {str(e)}") from e