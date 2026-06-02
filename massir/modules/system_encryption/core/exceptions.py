"""
Exception hierarchy for system_encryption module.

Each exception is specific to a cryptographic operation,
allowing fine-grained error handling by consuming modules.
"""


class EncryptionError(Exception):
    """Base exception for all encryption-related errors."""
    pass


class EncryptionConfigError(EncryptionError):
    """Raised when encryption configuration is invalid or missing."""
    pass


class AESDecryptionError(EncryptionError):
    """Raised when AES-GCM decryption fails (e.g., wrong key, tampered data)."""
    pass


class RSAError(EncryptionError):
    """Base exception for RSA-related errors."""
    pass


class RSAKeyError(RSAError):
    """Raised when RSA key operations fail (e.g., invalid key format)."""
    pass


class RSAEncryptionError(RSAError):
    """Raised when RSA encryption/decryption fails."""
    pass


class HMACVerificationError(EncryptionError):
    """Raised when HMAC signature verification fails."""
    pass


class InvalidDataError(EncryptionError):
    """Raised when input data is invalid for the operation."""
    pass