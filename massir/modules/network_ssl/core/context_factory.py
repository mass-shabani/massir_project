"""
SSL Context Factory

Creates SSLContext objects for servers and clients with proper
security hardening and TLS version configuration.
"""

import ssl
from pathlib import Path
from typing import Optional

from .exceptions import SSLConfigError, ContextCreationError


# TLS version mapping
_TLS_VERSIONS = {
    "1.2": ssl.TLSVersion.TLSv1_2,
    "1.3": ssl.TLSVersion.TLSv1_3,
}


def get_minimum_tls_version(version: str = "1.3") -> ssl.TLSVersion:
    """
    Get the ssl.TLSVersion enum value for a given version string.
    
    Args:
        version: TLS version string ("1.2" or "1.3")
    
    Returns:
        ssl.TLSVersion enum value
    
    Raises:
        SSLConfigError: If version is not supported
    """
    version_normalized = version.strip()
    if version_normalized not in _TLS_VERSIONS:
        raise SSLConfigError(
            f"Unsupported TLS version: {version}. "
            f"Supported: {list(_TLS_VERSIONS.keys())}"
        )
    return _TLS_VERSIONS[version_normalized]


def _apply_security_options(
    context: ssl.SSLContext,
    cipher_suites: str = "HIGH:!aNULL:!MD5:!3DES:!RC4",
    security_options: dict | None = None,
) -> None:
    """
    Apply security hardening options to SSLContext.
    
    Args:
        context: SSLContext to configure
        cipher_suites: Cipher suite string
        security_options: Dictionary of security flags
    """
    options = security_options or {
        "no_compression": True,
        "no_ticket": True,
        "single_dh_use": True,
        "single_ecdh_use": True,
    }
    
    try:
        context.set_ciphers(cipher_suites)
    except ssl.SSLError as e:
        raise SSLConfigError(f"Failed to set cipher suites: {e}") from e
    
    if options.get("no_compression", True):
        context.options |= ssl.OP_NO_COMPRESSION
    if options.get("no_ticket", True):
        context.options |= ssl.OP_NO_TICKET
    if options.get("single_dh_use", True):
        context.options |= ssl.OP_SINGLE_DH_USE
    if options.get("single_ecdh_use", True):
        context.options |= ssl.OP_SINGLE_ECDH_USE


def build_server_context(
    cert_path: str | Path,
    key_path: str | Path,
    ca_path: str | Path | None = None,
    verify_client: bool = False,
    tls_version: str = "1.3",
    cipher_suites: str = "HIGH:!aNULL:!MD5:!3DES:!RC4",
    security_options: dict | None = None,
) -> ssl.SSLContext:
    """
    Build an SSLContext configured for TLS server.
    
    Args:
        cert_path: Path to server certificate (PEM format)
        key_path: Path to server private key (PEM format)
        ca_path: Optional path to CA certificate for client verification
        verify_client: Whether to require client certificates (mTLS)
        tls_version: Minimum TLS version ("1.2" or "1.3")
        cipher_suites: OpenSSL cipher suite string
        security_options: Additional security flags
    
    Returns:
        Configured ssl.SSLContext for server use
    
    Raises:
        SSLConfigError: If configuration is invalid
        ContextCreationError: If context creation fails
        CertificateLoadError: If certificates cannot be loaded
    
    Example:
        >>> ctx = build_server_context(
        ...     cert_path="/etc/ssl/server.crt",
        ...     key_path="/etc/ssl/server.key",
        ...     verify_client=True,
        ... )
    """
    cert_path = Path(cert_path)
    key_path = Path(key_path)
    
    # Validate paths exist
    if not cert_path.exists():
        raise SSLConfigError(f"Certificate file not found: {cert_path}")
    if not key_path.exists():
        raise SSLConfigError(f"Key file not found: {key_path}")
    
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    except Exception as e:
        raise ContextCreationError(f"Failed to create TLS server context: {e}") from e
    
    # Set minimum TLS version
    min_version = get_minimum_tls_version(tls_version)
    context.minimum_version = min_version
    
    # Load server certificate and key
    try:
        context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
        )
    except ssl.SSLError as e:
        from .exceptions import CertificateLoadError
        raise CertificateLoadError(
            f"Failed to load server certificate/key: {e}"
        ) from e
    except Exception as e:
        from .exceptions import CertificateLoadError
        raise CertificateLoadError(
            f"Unexpected error loading certificates: {e}"
        ) from e
    
    # Load CA certificate for client verification if provided
    if ca_path:
        ca_path = Path(ca_path)
        if not ca_path.exists():
            raise SSLConfigError(f"CA certificate file not found: {ca_path}")
        
        try:
            context.load_verify_locations(cafile=str(ca_path))
        except ssl.SSLError as e:
            from .exceptions import CertificateLoadError
            raise CertificateLoadError(
                f"Failed to load CA certificate: {e}"
            ) from e
    
    # Set client verification mode
    if verify_client:
        if not ca_path:
            raise SSLConfigError(
                "Client verification enabled but no CA certificate provided"
            )
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.verify_mode = ssl.CERT_NONE
    
    # Apply security hardening
    _apply_security_options(context, cipher_suites, security_options)
    
    return context


def build_client_context(
    cert_path: str | Path | None = None,
    key_path: str | Path | None = None,
    ca_path: str | Path | None = None,
    verify_server: bool = True,
    check_hostname: bool = True,
    tls_version: str = "1.3",
    cipher_suites: str = "HIGH:!aNULL:!MD5:!3DES:!RC4",
    security_options: dict | None = None,
    sni_hostname: str | None = None,
) -> ssl.SSLContext:
    """
    Build an SSLContext configured for TLS client.
    
    Args:
        cert_path: Optional path to client certificate (for mTLS)
        key_path: Optional path to client private key (for mTLS)
        ca_path: Optional path to CA certificate for server verification
        verify_server: Whether to verify server certificate
        check_hostname: Whether to verify server hostname matches certificate
        tls_version: Minimum TLS version ("1.2" or "1.3")
        cipher_suites: OpenSSL cipher suite string
        security_options: Additional security flags
        sni_hostname: Optional SNI hostname to send during handshake
    
    Returns:
        Configured ssl.SSLContext for client use
    
    Raises:
        SSLConfigError: If configuration is invalid
        ContextCreationError: If context creation fails
        CertificateLoadError: If certificates cannot be loaded
    
    Example:
        >>> ctx = build_client_context(
        ...     ca_path="/etc/ssl/ca.crt",
        ...     verify_server=True,
        ...     sni_hostname="api.example.com",
        ... )
    """
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception as e:
        raise ContextCreationError(f"Failed to create TLS client context: {e}") from e
    
    # Set minimum TLS version
    min_version = get_minimum_tls_version(tls_version)
    context.minimum_version = min_version
    
    # Load client certificate and key if provided (for mTLS)
    if cert_path and key_path:
        cert_path = Path(cert_path)
        key_path = Path(key_path)
        
        if not cert_path.exists():
            raise SSLConfigError(f"Client certificate file not found: {cert_path}")
        if not key_path.exists():
            raise SSLConfigError(f"Client key file not found: {key_path}")
        
        try:
            context.load_cert_chain(
                certfile=str(cert_path),
                keyfile=str(key_path),
            )
        except ssl.SSLError as e:
            from .exceptions import CertificateLoadError
            raise CertificateLoadError(
                f"Failed to load client certificate/key: {e}"
            ) from e
    
    # Load CA certificate for server verification
    if ca_path:
        ca_path = Path(ca_path)
        if not ca_path.exists():
            raise SSLConfigError(f"CA certificate file not found: {ca_path}")
        
        try:
            context.load_verify_locations(cafile=str(ca_path))
        except ssl.SSLError as e:
            from .exceptions import CertificateLoadError
            raise CertificateLoadError(
                f"Failed to load CA certificate: {e}"
            ) from e
    
    # Set server verification mode
    if verify_server:
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = check_hostname
    else:
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
    
    # Apply security hardening
    _apply_security_options(context, cipher_suites, security_options)
    
    # SNI is typically handled per-connection via ssl.SSLObject.server_hostname
    # but we store it in context for reference if needed
    if sni_hostname:
        context.sni_hostname = sni_hostname  # Custom attribute for reference
    
    return context