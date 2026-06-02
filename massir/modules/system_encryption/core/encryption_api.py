"""
Unified Encryption API

Provides a high-level interface for all cryptographic operations.
This API is stateless and can be safely used by any module in the framework.
"""

import os
from typing import Any
from dataclasses import dataclass, asdict

from .aes import (
    encrypt_aes_gcm,
    decrypt_aes_gcm,
    generate_aes_key,
    AES_KEY_SIZE_BYTES,
)
from .rsa import (
    generate_rsa_keypair,
    encrypt_rsa,
    decrypt_rsa,
    sign_rsa,
    verify_rsa,
    serialize_public_key,
    serialize_private_key,
    deserialize_public_key,
    deserialize_private_key,
)
from .hmac import sign_hmac, verify_hmac, HMACAlgorithm
from .exceptions import EncryptionConfigError


@dataclass
class EncryptedData:
    """Container for encrypted data with metadata."""
    algorithm: str
    ciphertext: bytes
    nonce: bytes | None = None
    tag: bytes | None = None
    associated_data: bytes | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "algorithm": self.algorithm,
            "ciphertext": self.ciphertext.hex(),
            "nonce": self.nonce.hex() if self.nonce else None,
            "tag": self.tag.hex() if self.tag else None,
            "associated_data": (
                self.associated_data.hex() if self.associated_data else None
            ),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EncryptedData":
        """Create from dictionary."""
        return cls(
            algorithm=data["algorithm"],
            ciphertext=bytes.fromhex(data["ciphertext"]),
            nonce=(
                bytes.fromhex(data["nonce"]) if data.get("nonce") else None
            ),
            tag=(
                bytes.fromhex(data["tag"]) if data.get("tag") else None
            ),
            associated_data=(
                bytes.fromhex(data["associated_data"])
                if data.get("associated_data")
                else None
            ),
        )


class EncryptionAPI:
    """
    Unified API for cryptographic operations.
    
    This class is stateless - it does not store any keys or sensitive data.
    All keys must be provided explicitly for each operation.
    
    Example:
        >>> api = EncryptionAPI()
        >>> key = api.generate_symmetric_key()
        >>> encrypted = api.encrypt(b"secret data", key)
        >>> decrypted = api.decrypt(encrypted, key)
        >>> assert decrypted == b"secret data"
    """
    
    def __init__(self, config: dict | None = None):
        """
        Initialize the Encryption API.
        
        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}
    
    # =========================================================================
    # Symmetric Encryption (AES-256-GCM)
    # =========================================================================
    
    def generate_symmetric_key(self) -> bytes:
        """
        Generate a random AES-256 key.
        
        Returns:
            bytes: 32-byte random key
        """
        return generate_aes_key()
    
    def encrypt(
        self,
        plaintext: bytes,
        key: bytes,
        associated_data: bytes | None = None,
    ) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: Data to encrypt
            key: 32-byte AES key
            associated_data: Optional AAD for authentication
        
        Returns:
            EncryptedData: Container with ciphertext, nonce, and tag
        """
        ciphertext, nonce, tag = encrypt_aes_gcm(
            plaintext, key, associated_data=associated_data
        )
        return EncryptedData(
            algorithm="aes-256-gcm",
            ciphertext=ciphertext,
            nonce=nonce,
            tag=tag,
            associated_data=associated_data,
        )
    
    def decrypt(
        self,
        encrypted: EncryptedData,
        key: bytes,
    ) -> bytes:
        """
        Decrypt AES-256-GCM encrypted data.
        
        Args:
            encrypted: EncryptedData container from encrypt()
            key: 32-byte AES key (must match encryption key)
        
        Returns:
            bytes: Decrypted plaintext
        """
        if encrypted.algorithm != "aes-256-gcm":
            raise EncryptionConfigError(
                f"Unsupported algorithm: {encrypted.algorithm}. "
                "Expected 'aes-256-gcm'"
            )
        
        if encrypted.nonce is None or encrypted.tag is None:
            raise EncryptionConfigError(
                "EncryptedData must contain nonce and tag for AES-GCM"
            )
        
        return decrypt_aes_gcm(
            encrypted.ciphertext,
            key,
            encrypted.nonce,
            encrypted.tag,
            encrypted.associated_data,
        )
    
    # =========================================================================
    # Asymmetric Encryption (RSA)
    # =========================================================================
    
    def generate_keypair(
        self,
        key_size: int | None = None,
    ) -> tuple:
        """
        Generate an RSA key pair.
        
        Args:
            key_size: Key size in bits (default from config, usually 4096)
        
        Returns:
            Tuple of (public_key, private_key)
        """
        size = key_size or self._config.get("rsa_key_size", 4096)
        return generate_rsa_keypair(size)
    
    def encrypt_with_public(
        self,
        plaintext: bytes,
        public_key: Any,
    ) -> bytes:
        """
        Encrypt data with an RSA public key.
        
        Args:
            plaintext: Data to encrypt
            public_key: RSA public key
        
        Returns:
            bytes: Encrypted data
        """
        return encrypt_rsa(plaintext, public_key)
    
    def decrypt_with_private(
        self,
        ciphertext: bytes,
        private_key: Any,
    ) -> bytes:
        """
        Decrypt data with an RSA private key.
        
        Args:
            ciphertext: Encrypted data
            private_key: RSA private key
        
        Returns:
            bytes: Decrypted data
        """
        return decrypt_rsa(ciphertext, private_key)
    
    def sign(
        self,
        data: bytes,
        private_key: Any,
    ) -> bytes:
        """
        Sign data with an RSA private key.
        
        Args:
            data: Data to sign
            private_key: RSA private key
        
        Returns:
            bytes: Digital signature
        """
        return sign_rsa(data, private_key)
    
    def verify(
        self,
        data: bytes,
        signature: bytes,
        public_key: Any,
    ) -> bool:
        """
        Verify an RSA signature.
        
        Args:
            data: Original data
            signature: Signature to verify
            public_key: RSA public key
        
        Returns:
            bool: True if signature is valid
        """
        return verify_rsa(data, signature, public_key)
    
    # =========================================================================
    # Key Serialization
    # =========================================================================
    
    def export_public_key(
        self,
        public_key: Any,
        encoding: str = "PEM",
    ) -> bytes:
        """Export public key to bytes."""
        return serialize_public_key(public_key, encoding)
    
    def export_private_key(
        self,
        private_key: Any,
        password: bytes | None = None,
        encoding: str = "PEM",
    ) -> bytes:
        """Export private key to bytes."""
        return serialize_private_key(private_key, password, encoding)
    
    def import_public_key(self, data: bytes) -> Any:
        """Import public key from bytes."""
        return deserialize_public_key(data)
    
    def import_private_key(
        self,
        data: bytes,
        password: bytes | None = None,
    ) -> Any:
        """Import private key from bytes."""
        return deserialize_private_key(data, password)
    
    # =========================================================================
    # Message Authentication (HMAC)
    # =========================================================================
    
    def generate_hmac_key(self, size: int = 32) -> bytes:
        """Generate a random key for HMAC."""
        return os.urandom(size)
    
    def create_hmac(
        self,
        data: bytes,
        key: bytes,
        algorithm: str = "sha256",
    ) -> bytes:
        """Create an HMAC signature."""
        return sign_hmac(data, key, algorithm)
    
    def verify_hmac(
        self,
        data: bytes,
        signature: bytes,
        key: bytes,
        algorithm: str = "sha256",
    ) -> bool:
        """Verify an HMAC signature."""
        return verify_hmac(data, signature, key, algorithm)
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def generate_random_bytes(self, size: int = 32) -> bytes:
        """Generate cryptographically secure random bytes."""
        return os.urandom(size)
    
    def get_info(self) -> dict[str, Any]:
        """Get information about the encryption module."""
        return {
            "module": "system_encryption",
            "version": "1.0.0",
            "algorithms": {
                "symmetric": "AES-256-GCM",
                "asymmetric": "RSA-4096",
                "hash": "SHA-256/384/512",
                "hmac": ["SHA-256", "SHA-384", "SHA-512", "SHA3-256", "SHA3-512"],
            },
            "key_sizes": {
                "aes": AES_KEY_SIZE_BYTES,
                "rsa_default": self._config.get("rsa_key_size", 4096),
            },
        }