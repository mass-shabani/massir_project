"""
AES-256-GCM Encryption Module

Provides authenticated symmetric encryption using AES-256-GCM.
GCM mode provides both confidentiality and integrity (authentication).

Security notes:
- Always use a unique nonce for each encryption with the same key
- Nonce must be 12 bytes (96 bits) for GCM
- Key must be 32 bytes (256 bits) for AES-256
"""

import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import padding

from .exceptions import AESDecryptionError, InvalidDataError

# Constants
AES_KEY_SIZE_BITS = 256
AES_KEY_SIZE_BYTES = AES_KEY_SIZE_BITS // 8  # 32 bytes
AES_NONCE_SIZE_BYTES = 12  # 96 bits - recommended for GCM
AES_TAG_SIZE_BYTES = 16  # 128 bits - authentication tag


def generate_aes_key() -> bytes:
    """
    Generate a cryptographically secure random AES-256 key.
    
    Returns:
        bytes: 32-byte random key suitable for AES-256
        
    Example:
        >>> key = generate_aes_key()
        >>> len(key)
        32
    """
    return os.urandom(AES_KEY_SIZE_BYTES)


def encrypt_aes_gcm(
    plaintext: bytes,
    key: bytes,
    nonce: bytes | None = None,
    associated_data: bytes | None = None,
) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        plaintext: Data to encrypt
        key: 32-byte AES-256 key
        nonce: Optional 12-byte nonce. If None, a random nonce is generated.
        associated_data: Optional additional authenticated data (AAD)
                        This data is authenticated but not encrypted.
    
    Returns:
        Tuple of (ciphertext, nonce, tag)
        - ciphertext: Encrypted data (same length as plaintext)
        - nonce: 12-byte nonce used (needed for decryption)
        - tag: 16-byte authentication tag (needed for decryption)
    
    Raises:
        InvalidDataError: If key or nonce size is invalid
        EncryptionError: If encryption fails
        
    Example:
        >>> key = generate_aes_key()
        >>> ciphertext, nonce, tag = encrypt_aes_gcm(b"secret", key)
        >>> plaintext = decrypt_aes_gcm(ciphertext, key, nonce, tag)
    """
    if not isinstance(plaintext, bytes):
        raise InvalidDataError("Plaintext must be bytes")
    
    if len(key) != AES_KEY_SIZE_BYTES:
        raise InvalidDataError(
            f"Key must be {AES_KEY_SIZE_BYTES} bytes for AES-256, "
            f"got {len(key)} bytes"
        )
    
    if nonce is None:
        nonce = os.urandom(AES_NONCE_SIZE_BYTES)
    elif len(nonce) != AES_NONCE_SIZE_BYTES:
        raise InvalidDataError(
            f"Nonce must be {AES_NONCE_SIZE_BYTES} bytes for GCM, "
            f"got {len(nonce)} bytes"
        )
    
    aesgcm = AESGCM(key)
    
    # AESGCM.encrypt returns ciphertext + tag concatenated
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    # Split ciphertext and tag
    ciphertext = ciphertext_with_tag[:-AES_TAG_SIZE_BYTES]
    tag = ciphertext_with_tag[-AES_TAG_SIZE_BYTES:]
    
    return ciphertext, nonce, tag


def decrypt_aes_gcm(
    ciphertext: bytes,
    key: bytes,
    nonce: bytes,
    tag: bytes,
    associated_data: bytes | None = None,
) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        ciphertext: Encrypted data
        key: 32-byte AES-256 key (must match encryption key)
        nonce: 12-byte nonce used during encryption
        tag: 16-byte authentication tag from encryption
        associated_data: Optional AAD (must match encryption AAD)
    
    Returns:
        bytes: Decrypted plaintext
    
    Raises:
        AESDecryptionError: If decryption fails (wrong key, tampered data, etc.)
        InvalidDataError: If input sizes are invalid
        
    Example:
        >>> key = generate_aes_key()
        >>> ct, nonce, tag = encrypt_aes_gcm(b"hello", key)
        >>> decrypt_aes_gcm(ct, key, nonce, tag)
        b'hello'
    """
    if not isinstance(ciphertext, bytes):
        raise InvalidDataError("Ciphertext must be bytes")
    
    if len(key) != AES_KEY_SIZE_BYTES:
        raise InvalidDataError(
            f"Key must be {AES_KEY_SIZE_BYTES} bytes for AES-256"
        )
    
    if len(nonce) != AES_NONCE_SIZE_BYTES:
        raise InvalidDataError(
            f"Nonce must be {AES_NONCE_SIZE_BYTES} bytes for GCM"
        )
    
    if len(tag) != AES_TAG_SIZE_BYTES:
        raise InvalidDataError(
            f"Tag must be {AES_TAG_SIZE_BYTES} bytes for GCM"
        )
    
    aesgcm = AESGCM(key)
    
    # Reconstruct ciphertext + tag for AESGCM.decrypt
    ciphertext_with_tag = ciphertext + tag
    
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
        return plaintext
    except Exception as e:
        raise AESDecryptionError(
            f"AES-GCM decryption failed: {str(e)}. "
            "This may indicate wrong key, tampered data, or incorrect nonce/tag."
        ) from e