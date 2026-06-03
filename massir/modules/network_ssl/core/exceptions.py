"""
Exception hierarchy for network_ssl module.
"""


class SSLError(Exception):
    """Base exception for all SSL-related errors."""
    pass


class SSLConfigError(SSLError):
    """Raised when SSL configuration is invalid or missing."""
    pass


class CertificateError(SSLError):
    """Base exception for certificate-related errors."""
    pass


class CertificateLoadError(CertificateError):
    """Raised when a certificate cannot be loaded from disk."""
    pass


class CertificateValidationError(CertificateError):
    """Raised when a certificate fails validation checks."""
    pass


class CertificateExpiredError(CertificateValidationError):
    """Raised when a certificate has expired."""
    pass


class CertificateExpiringSoonError(CertificateValidationError):
    """Raised when a certificate will expire within the warning threshold."""
    pass


class ContextCreationError(SSLError):
    """Raised when SSLContext creation fails."""
    pass