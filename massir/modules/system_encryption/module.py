"""
System Encryption Module for Massir Framework

Provides cryptographic services (AES, RSA, HMAC) to all modules
in the Massir framework. This module is stateless and does not
store any keys or sensitive data.
"""

import json
from pathlib import Path
from typing import Optional

from massir.core.interfaces import IModule

from .core.encryption_api import EncryptionAPI
from .core.exceptions import EncryptionConfigError


class EncryptionModule(IModule):
    """
    System Encryption Module.
    
    Provides encryption_api service for:
    - AES-256-GCM symmetric encryption
    - RSA-4096 asymmetric encryption and signing
    - HMAC-SHA256 message authentication
    
    This module is stateless - it does not store any keys.
    Keys must be managed by consuming modules or provided at runtime.
    """
    
    def __init__(self):
        self._api: Optional[EncryptionAPI] = None
        self._logger = None
        self._config: dict = {}
        self._module_dir: Path = Path(__file__).parent
    
    async def load(self, context):
        """
        Load the encryption module.
        
        Reads configuration from:
        1. config.json (default settings in module directory)
        2. app_settings.json (user overrides via core_config)
        
        Creates and registers the EncryptionAPI service.
        """
        # Get framework services
        self._logger = context.services.get("core_logger")
        core_config = context.services.get("core_config")
        
        # Load default config from module's config.json
        self._config = self._load_default_config()
        
        # Override with user config from app_settings.json
        if core_config:
            user_config = core_config.get("system_encryption", {})
            if isinstance(user_config, dict):
                self._config = self._merge_config(self._config, user_config)
        
        # Validate configuration
        self._validate_config()
        
        # Create and register the API
        self._api = EncryptionAPI(self._config)
        context.services.set("encryption_api", self._api)
        
        if self._logger:
            self._logger.log(
                "EncryptionModule loaded - AES-256-GCM, RSA-4096, HMAC-SHA256 ready",
                tag="encryption"
            )
    
    async def start(self, context):
        """Start the encryption module (no-op for stateless module)."""
        if self._logger:
            log_ops = self._config.get("logging", {}).get("log_operations", False)
            if log_ops:
                self._logger.log(
                    "EncryptionModule started - ready to serve requests",
                    tag="encryption"
                )
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self._logger:
            self._logger.log(
                "EncryptionModule is ready",
                tag="encryption"
            )
    
    async def stop(self, context):
        """Stop the encryption module."""
        if self._logger:
            self._logger.log(
                "EncryptionModule stopped",
                tag="encryption"
            )
        # Clear references
        self._api = None
    
    def _load_default_config(self) -> dict:
        """Load default configuration from config.json in module directory."""
        config_path = self._module_dir / "config.json"
        
        default_config = {
            "default_algorithm": "aes-256-gcm",
            "rsa_key_size": 4096,
            "hmac_algorithm": "sha256",
            "auto_generate_keys_on_startup": False,
            "key_storage": {
                "enabled": False,
                "path": "{app_dir}/keys",
                "auto_create_dir": True,
            },
            "logging": {
                "tag": "encryption",
                "log_operations": False,
                "log_key_generation": True,
            },
        }
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                    if isinstance(file_config, dict):
                        default_config = self._merge_config(
                            default_config, file_config
                        )
            except (json.JSONDecodeError, IOError) as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to load config.json: {e}",
                        level="WARNING",
                        tag="encryption"
                    )
        
        return default_config
    
    def _merge_config(self, base: dict, override: dict) -> dict:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _validate_config(self):
        """Validate configuration values."""
        rsa_key_size = self._config.get("rsa_key_size", 4096)
        if not isinstance(rsa_key_size, int) or rsa_key_size < 2048:
            raise EncryptionConfigError(
                f"rsa_key_size must be an integer >= 2048, got {rsa_key_size}"
            )
        
        default_algo = self._config.get("default_algorithm", "aes-256-gcm")
        valid_algos = ["aes-256-gcm", "aes-128-gcm"]
        if default_algo not in valid_algos:
            raise EncryptionConfigError(
                f"default_algorithm must be one of {valid_algos}, got {default_algo}"
            )
        
        hmac_algo = self._config.get("hmac_algorithm", "sha256")
        valid_hmac = ["sha256", "sha384", "sha512", "sha3_256", "sha3_512"]
        if hmac_algo not in valid_hmac:
            raise EncryptionConfigError(
                f"hmac_algorithm must be one of {valid_hmac}, got {hmac_algo}"
            )