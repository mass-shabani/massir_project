"""
Data classes for certificate information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CertInfo:
    """Container for certificate information."""
    
    subject: str
    issuer: str
    serial_number: int
    not_valid_before: datetime
    not_valid_after: datetime
    days_until_expiry: int
    is_expired: bool
    san_dns_names: list[str] = field(default_factory=list)
    san_ip_addresses: list[str] = field(default_factory=list)
    signature_algorithm: str = ""
    key_size: int = 0
    version: int = 3
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "serial_number": hex(self.serial_number),
            "not_valid_before": self.not_valid_before.isoformat(),
            "not_valid_after": self.not_valid_after.isoformat(),
            "days_until_expiry": self.days_until_expiry,
            "is_expired": self.is_expired,
            "san_dns_names": self.san_dns_names,
            "san_ip_addresses": self.san_ip_addresses,
            "signature_algorithm": self.signature_algorithm,
            "key_size": self.key_size,
            "version": self.version,
        }
    
    @property
    def status(self) -> str:
        """Get human-readable status of the certificate."""
        if self.is_expired:
            return "EXPIRED"
        elif self.days_until_expiry <= 7:
            return "CRITICAL"
        elif self.days_until_expiry <= 30:
            return "WARNING"
        else:
            return "OK"


@dataclass
class CertValidationResult:
    """Result of certificate validation."""
    
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    cert_info: CertInfo | None = None
    
    def add_error(self, message: str):
        """Add an error to the validation result."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning to the validation result."""
        self.warnings.append(message)