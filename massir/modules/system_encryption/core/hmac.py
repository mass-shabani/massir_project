"""
HMAC Message Authentication Module

Provides HMAC (Hash-based Message Authentication Code) for
verifying both data integrity and authenticity.
"""

import hmac
import hashlib
from enum import Enum

from .exceptions import HMACVerificationError, InvalidDataError


class HMACAlgorithm(str, Enum):
    """Supported HMAC algorithms."""
    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
    SHA3_256 = "sha3_256"
    SHA3_512 = "sha3_512"


# Map algorithm names to hashlib constructors
_HASH_ALGORITHMS = {
    HMACAlgorithm.SHA256: hashlib.sha256,
    HMACAlgorithm.SHA384: hashlib.sha384,
    HMACAlgorithm.SHA512: hashlib.sha512,
    HMACAlgorithm.SHA3_256: hashlib.sha3_256,
    HMACAlgorithm.SHA3_512: hashlib.sha3_512,
}


def sign_hmac(
    data: bytes,
    key: bytes,
    algorithm: str | HMACAlgorithm = HMACAlgorithm.SHA256,
) -> bytes:
    """
    Generate an HMAC signature for data.
    
    Args:
        data: Data to sign
        key: Secret key for HMAC (recommended: at least 32 bytes)
        algorithm: Hash algorithm to use (default: SHA-256)
    
    Returns:
        bytes: HMAC signature
        
    Raises:
        InvalidDataError: If inputs are invalid
        HMACVerificationError: If algorithm is not supported
        
    Example:
        >>> key = os.urandom(32)
        >>> signature = sign_hmac(b"message", key)
        >>> verify_hmac(b"message", signature, key)
        True
    """
    if not isinstance(data, bytes):
        raise InvalidDataError("Data must be bytes")
    if not isinstance(key, bytes):
        raise InvalidDataError("Key must be bytes")
    
    if isinstance(algorithm, str):
        try:
            algorithm = HMACAlgorithm(algorithm.lower())
        except ValueError:
            raise HMACVerificationError(
                f"Unsupported HMAC algorithm: {algorithm}. "
                f"Supported: {[a.value for a in HMACAlgorithm]}"
            )
    
    hash_func = _HASH_ALGORITHMS.get(algorithm)
    if hash_func is None:
        raise HMACVerificationError(f"No hash function for algorithm: {algorithm}")
    
    return hmac.new(key, data, hash_func).digest()


def verify_hmac(
    data: bytes,
    signature: bytes,
    key: bytes,
    algorithm: str | HMACAlgorithm = HMACAlgorithm.SHA256,
) -> bool:
    """
    Verify an HMAC signature.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        data: Original data
        signature: HMAC signature to verify
        key: Secret key (must match the key used for signing)
        algorithm: Hash algorithm (must match the algorithm used for signing)
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not isinstance(data, bytes) or not isinstance(signature, bytes):
        return False
    
    try:
        expected_signature = sign_hmac(data, key, algorithm)
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False