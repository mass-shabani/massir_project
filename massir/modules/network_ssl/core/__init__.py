"""
Network SSL Core Module

Provides TLS/SSL management for the Massir framework:
- SSLContext creation for servers and clients
- Certificate lifecycle management
- mTLS (mutual TLS) support
- SNI (Server Name Indication) support
- Hot-reload of certificates
- Expiry monitoring
"""

from .ssl_api import SSLAPI
from .cert_info import CertInfo, CertValidationResult
from .context_factory import (
    build_server_context,
    build_client_context,
    get_minimum_tls_version,
)
from .cert_manager import CertificateManager
from .exceptions import (
    SSLError,
    SSLConfigError,
    CertificateError,
    CertificateExpiredError,
    CertificateExpiringSoonError,
    CertificateLoadError,
    CertificateValidationError,
)

__all__ = [
    # API
    "SSLAPI",
    # Data classes
    "CertInfo",
    "CertValidationResult",
    # Context factory
    "build_server_context",
    "build_client_context",
    "get_minimum_tls_version",
    # Manager
    "CertificateManager",
    # Exceptions
    "SSLError",
    "SSLConfigError",
    "CertificateError",
    "CertificateExpiredError",
    "CertificateExpiringSoonError",
    "CertificateLoadError",
    "CertificateValidationError",
]