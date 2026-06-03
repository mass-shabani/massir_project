"""
Certificate Lifecycle Manager

Handles loading, validation, expiry checking, and hot-reload
of X.509 certificates.
"""

import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Callable

from cryptography import x509
from cryptography.x509.oid import ExtensionOID
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from cryptography.hazmat.backends import default_backend

from .cert_info import CertInfo, CertValidationResult
from .exceptions import (
    CertificateLoadError,
    CertificateExpiredError,
    CertificateExpiringSoonError,
    CertificateValidationError,
)


class CertificateManager:
    """
    Manages certificate lifecycle operations.
    
    Provides methods to:
    - Load certificates from disk
    - Extract certificate information
    - Validate certificates
    - Check expiry status
    - Monitor file changes for hot-reload
    """
    
    def __init__(self):
        self._file_timestamps: dict[str, float] = {}
    
    # =========================================================================
    # Loading
    # =========================================================================
    
    def load_certificate(self, cert_path: str | Path) -> x509.Certificate:
        """
        Load an X.509 certificate from a PEM file.
        
        Args:
            cert_path: Path to PEM-encoded certificate file
        
        Returns:
            cryptography.x509.Certificate object
        
        Raises:
            CertificateLoadError: If certificate cannot be loaded
        """
        cert_path = Path(cert_path)
        
        if not cert_path.exists():
            raise CertificateLoadError(
                f"Certificate file not found: {cert_path}"
            )
        
        try:
            with open(cert_path, "rb") as f:
                pem_data = f.read()
            return x509.load_pem_x509_certificate(pem_data, default_backend())
        except ValueError as e:
            raise CertificateLoadError(
                f"Invalid PEM format in certificate file: {e}"
            ) from e
        except Exception as e:
            raise CertificateLoadError(
                f"Failed to load certificate: {e}"
            ) from e
    
    def load_certificate_chain(
        self,
        cert_path: str | Path,
    ) -> list[x509.Certificate]:
        """
        Load all certificates from a PEM chain file.
        
        Args:
            cert_path: Path to PEM file containing one or more certificates
        
        Returns:
            List of x509.Certificate objects (leaf first, then intermediates)
        """
        cert_path = Path(cert_path)
        
        if not cert_path.exists():
            raise CertificateLoadError(
                f"Certificate file not found: {cert_path}"
            )
        
        try:
            with open(cert_path, "rb") as f:
                pem_data = f.read()
            return x509.load_pem_x509_certificates(pem_data, default_backend())
        except Exception as e:
            raise CertificateLoadError(
                f"Failed to load certificate chain: {e}"
            ) from e
    
    # =========================================================================
    # Information Extraction
    # =========================================================================
    
    def get_cert_info(self, cert: x509.Certificate) -> CertInfo:
        """
        Extract comprehensive information from a certificate.
        
        Args:
            cert: X.509 certificate object
        
        Returns:
            CertInfo dataclass with all certificate details
        """
        now = datetime.now(timezone.utc)
        
        # Get validity period
        not_valid_before = cert.not_valid_before_utc
        not_valid_after = cert.not_valid_after_utc
        days_until_expiry = (not_valid_after - now).days
        is_expired = now > not_valid_after
        
        # Get Subject Alternative Names (SAN)
        san_dns_names: list[str] = []
        san_ip_addresses: list[str] = []
        
        try:
            san_ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            san_dns_names = san_ext.value.get_values_for_type(x509.DNSName)
            
            # IP addresses (as strings)
            try:
                san_ips = san_ext.value.get_values_for_type(x509.IPAddress)
                san_ip_addresses = [str(ip) for ip in san_ips]
            except Exception:
                pass
        except x509.ExtensionNotFound:
            pass
        
        # Get signature algorithm
        signature_algorithm = cert.signature_algorithm_oid._name or str(
            cert.signature_algorithm_oid
        )
        
        # Get key size
        key_size = 0
        public_key = cert.public_key()
        if isinstance(public_key, rsa.RSAPublicKey):
            key_size = public_key.key_size
        elif isinstance(public_key, ec.EllipticCurvePublicKey):
            key_size = public_key.key_size
        elif isinstance(public_key, (ed25519.Ed25519PublicKey, ed448.Ed448PublicKey)):
            key_size = 256 if isinstance(public_key, ed25519.Ed25519PublicKey) else 448
        
        return CertInfo(
            subject=cert.subject.rfc4514_string(),
            issuer=cert.issuer.rfc4514_string(),
            serial_number=cert.serial_number,
            not_valid_before=not_valid_before,
            not_valid_after=not_valid_after,
            days_until_expiry=days_until_expiry,
            is_expired=is_expired,
            san_dns_names=san_dns_names,
            san_ip_addresses=san_ip_addresses,
            signature_algorithm=signature_algorithm,
            key_size=key_size,
            version=cert.version.value,
        )
    
    def get_expiry_date(self, cert: x509.Certificate) -> datetime:
        """Get the expiry date of a certificate."""
        return cert.not_valid_after_utc
    
    def days_until_expiry(self, cert: x509.Certificate) -> int:
        """Get the number of days until certificate expiry."""
        expiry = self.get_expiry_date(cert)
        now = datetime.now(timezone.utc)
        delta = expiry - now
        return delta.days
    
    def is_expired(self, cert: x509.Certificate) -> bool:
        """Check if a certificate has expired."""
        now = datetime.now(timezone.utc)
        return now > cert.not_valid_after_utc
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    def validate_certificate(
        self,
        cert_path: str | Path,
        warning_days: int = 30,
    ) -> CertValidationResult:
        """
        Validate a certificate file.
        
        Checks:
        - File exists and is readable
        - Valid PEM format
        - Not expired
        - Not expiring soon (within warning_days)
        
        Args:
            cert_path: Path to certificate file
            warning_days: Days threshold for expiry warning
        
        Returns:
            CertValidationResult with validation status and details
        """
        result = CertValidationResult(is_valid=True)
        
        # Check file exists
        cert_path = Path(cert_path)
        if not cert_path.exists():
            result.add_error(f"Certificate file not found: {cert_path}")
            return result
        
        if not cert_path.is_file():
            result.add_error(f"Path is not a file: {cert_path}")
            return result
        
        # Try to load certificate
        try:
            cert = self.load_certificate(cert_path)
        except CertificateLoadError as e:
            result.add_error(str(e))
            return result
        
        # Get cert info
        cert_info = self.get_cert_info(cert)
        result.cert_info = cert_info
        
        # Check expiry
        if cert_info.is_expired:
            result.add_error(
                f"Certificate expired on {cert_info.not_valid_after.isoformat()}"
            )
        elif cert_info.days_until_expiry <= warning_days:
            result.add_warning(
                f"Certificate expires in {cert_info.days_until_expiry} days "
                f"(on {cert_info.not_valid_after.isoformat()})"
            )
        
        # Check key size
        if cert_info.key_size > 0:
            if cert_info.key_size < 2048 and "rsa" in cert_info.signature_algorithm.lower():
                result.add_warning(
                    f"RSA key size {cert_info.key_size} bits is considered weak. "
                    "Recommend 2048 or higher."
                )
        
        return result
    
    def assert_valid(
        self,
        cert_path: str | Path,
        warning_days: int = 30,
        raise_on_warning: bool = False,
    ) -> CertInfo:
        """
        Validate a certificate and raise exceptions on errors.
        
        Args:
            cert_path: Path to certificate file
            warning_days: Days threshold for expiry warning
            raise_on_warning: Whether to raise on warnings too
        
        Returns:
            CertInfo if validation passes
        
        Raises:
            CertificateExpiredError: If certificate has expired
            CertificateExpiringSoonError: If certificate expiring soon and raise_on_warning=True
            CertificateValidationError: If other validation errors exist
        """
        result = self.validate_certificate(cert_path, warning_days)
        
        if not result.is_valid:
            raise CertificateValidationError(
                f"Certificate validation failed: {'; '.join(result.errors)}"
            )
        
        if result.cert_info and result.cert_info.is_expired:
            raise CertificateExpiredError(
                f"Certificate expired on {result.cert_info.not_valid_after.isoformat()}"
            )
        
        if raise_on_warning and result.warnings:
            if result.cert_info and result.cert_info.days_until_expiry <= warning_days:
                raise CertificateExpiringSoonError(
                    f"Certificate expiring in {result.cert_info.days_until_expiry} days"
                )
        
        return result.cert_info
    
    # =========================================================================
    # Hot-Reload Support
    # =========================================================================
    
    def get_file_mtime(self, file_path: str | Path) -> float:
        """
        Get the modification time of a file.
        
        Args:
            file_path: Path to file
        
        Returns:
            Modification timestamp (epoch seconds)
        """
        return os.path.getmtime(file_path)
    
    def has_file_changed(self, file_path: str | Path) -> bool:
        """
        Check if a file has been modified since last check.
        
        Uses cached modification times to detect changes.
        
        Args:
            file_path: Path to file
        
        Returns:
            True if file has changed, False otherwise
        """
        file_path_str = str(file_path)
        
        try:
            current_mtime = self.get_file_mtime(file_path)
        except OSError:
            return False
        
        cached_mtime = self._file_timestamps.get(file_path_str)
        
        if cached_mtime is None:
            # First time checking
            self._file_timestamps[file_path_str] = current_mtime
            return True
        
        if current_mtime != cached_mtime:
            self._file_timestamps[file_path_str] = current_mtime
            return True
        
        return False
    
    def register_file(self, file_path: str | Path) -> None:
        """Register a file for change monitoring."""
        file_path_str = str(file_path)
        try:
            self._file_timestamps[file_path_str] = self.get_file_mtime(file_path)
        except OSError:
            pass
    
    def clear_cache(self) -> None:
        """Clear the file timestamp cache."""
        self._file_timestamps.clear()