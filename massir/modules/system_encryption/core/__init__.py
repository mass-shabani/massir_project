"""
System Encryption Core Module

Provides cryptographic operations for the Massir framework:
- AES-256-GCM for symmetric encryption
- RSA-4096 for asymmetric encryption  
- HMAC-SHA256 for message authentication
"""

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
from .hmac import (
    sign_hmac,
    verify_hmac,
    HMACAlgorithm,
)
from .encryption_api import EncryptionAPI
from .exceptions import (
    EncryptionError,
    AESDecryptionError,
    RSAError,
    RSAKeyError,
    HMACVerificationError,
    EncryptionConfigError,
)

__all__ = [
    # AES
    "encrypt_aes_gcm",
    "decrypt_aes_gcm",
    "generate_aes_key",
    "AES_KEY_SIZE_BYTES",
    # RSA
    "generate_rsa_keypair",
    "encrypt_rsa",
    "decrypt_rsa",
    "sign_rsa",
    "verify_rsa",
    "serialize_public_key",
    "serialize_private_key",
    "deserialize_public_key",
    "deserialize_private_key",
    # HMAC
    "sign_hmac",
    "verify_hmac",
    "HMACAlgorithm",
    # API
    "EncryptionAPI",
    # Exceptions
    "EncryptionError",
    "AESDecryptionError",
    "RSAError",
    "RSAKeyError",
    "HMACVerificationError",
    "EncryptionConfigError",
]