"""
Network SSL Module for Massir Framework

Provides SSL/TLS services (context creation, certificate management)
to all modules in the Massir framework.
"""

import json
from pathlib import Path
from typing import Optional, Any

from massir.core.interfaces import IModule

from .core.ssl_api import SSLAPI
from .core.exceptions import SSLConfigError


class NetworkSSLModule(IModule):
    """
    Network SSL Module.
    
    Provides ssl_api service for:
    - TLS 1.3 server and client contexts
    - mTLS (mutual TLS) support
    - Certificate lifecycle management
    - Hot-reload of certificates
    - Expiry monitoring and warnings
    
    This module manages SSLContext objects which can be shared across
    multiple connections to the same peer.
    """
    
    name = "network_ssl"
    provides = ["ssl_api"]
    
    def __init__(self):
        self._api: Optional[SSLAPI] = None
        self._logger: Any = None
        self._config: dict = {}
        self._module_dir: Path = Path(__file__).parent
    
    async def load(self, context):
        """
        Load the SSL module.
        
        Reads configuration from:
        1. config.json (default settings in module directory)
        2. app_settings.json (user overrides via core_config)
        
        Creates and registers the SSLAPI service.
        """
        # Get framework services
        self._logger = context.services.get("core_logger")
        core_config = context.services.get("core_config")
        
        # Load default config from module's config.json
        self._config = self._load_default_config()
        
        # Override with user config from app_settings.json
        if core_config:
            user_config = core_config.get("network_ssl", {})
            if isinstance(user_config, dict):
                self._config = self._merge_config(self._config, user_config)
        
        # Resolve cert paths placeholders with app_dir from context
        if hasattr(context, 'app_dir'):
            self._resolve_path_placeholders(context.app_dir)
        
        # Validate configuration
        self._validate_config()
        
        # Create and register the API
        self._api = SSLAPI(self._config, self._logger)
        context.services.set("ssl_api", self._api)
        
        if self._logger:
            self._logger.log(
                f"NetworkSSLModule loaded - TLS {self._config.get('tls_version', '1.3')} ready",
                tag="ssl"
            )
    
    async def start(self, context):
        """Start the SSL module and begin auto-reload monitoring."""
        if self._api:
            # Pre-load server context to catch certificate issues early
            try:
                self._api.get_server_context("default")
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to pre-load server context: {e}",
                        level="WARNING",
                        tag="ssl"
                    )
            
            # Start auto-reload if enabled
            if self._config.get("auto_reload", True):
                await self._api.start_auto_reload()
        
        if self._logger:
            self._logger.log(
                "NetworkSSLModule started",
                tag="ssl"
            )
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self._logger:
            info = self._api.get_info() if self._api else {}
            self._logger.log(
                f"NetworkSSLModule ready - "
                f"{info.get('cached_contexts', {}).get('server', 0)} server context(s) cached",
                tag="ssl"
            )
    
    async def stop(self, context):
        """Stop the SSL module and cleanup."""
        if self._api:
            await self._api.stop_auto_reload()
            self._api.clear_cache()
        
        if self._logger:
            self._logger.log(
                "NetworkSSLModule stopped",
                tag="ssl"
            )
        
        self._api = None
    
    def _load_default_config(self) -> dict:
        """Load default configuration from config.json in module directory."""
        config_path = self._module_dir / "config.json"
        
        default_config = {
            "tls_version": "1.3",
            "default_certs_path": "{app_dir}/certs",
            "verify_client_certs": False,
            "verify_server_certs": True,
            "check_hostname": True,
            "expiry_warning_days": 30,
            "auto_reload": True,
            "reload_check_interval_seconds": 3600,
            "cipher_suites": "HIGH:!aNULL:!MD5:!3DES:!RC4",
            "security_options": {
                "no_compression": True,
                "no_ticket": True,
                "single_dh_use": True,
                "single_ecdh_use": True,
            },
            "nodes": {
                "default": {
                    "cert_file": "server.crt",
                    "key_file": "server.key",
                    "ca_file": "ca.crt",
                }
            },
            "logging": {
                "tag": "ssl",
                "log_handshakes": False,
                "log_cert_info": True,
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
                        tag="ssl"
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
    
    def _resolve_path_placeholders(self, app_dir: str | Path) -> None:
        """Resolve {app_dir} placeholders in configuration."""
        app_dir_str = str(app_dir)
        
        def resolve(obj):
            if isinstance(obj, str):
                return obj.replace("{app_dir}", app_dir_str)
            elif isinstance(obj, dict):
                return {k: resolve(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve(item) for item in obj]
            return obj
        
        self._config = resolve(self._config)
    
    def _validate_config(self):
        """Validate configuration values."""
        tls_version = self._config.get("tls_version", "1.3")
        if tls_version not in ["1.2", "1.3"]:
            raise SSLConfigError(
                f"tls_version must be '1.2' or '1.3', got '{tls_version}'"
            )
        
        warning_days = self._config.get("expiry_warning_days", 30)
        if not isinstance(warning_days, int) or warning_days < 0:
            raise SSLConfigError(
                f"expiry_warning_days must be a non-negative integer, got {warning_days}"
            )
        
        reload_interval = self._config.get("reload_check_interval_seconds", 3600)
        if not isinstance(reload_interval, int) or reload_interval < 60:
            raise SSLConfigError(
                f"reload_check_interval_seconds must be at least 60, got {reload_interval}"
            )
        
        # Validate nodes configuration
        nodes = self._config.get("nodes", {})
        if not isinstance(nodes, dict):
            raise SSLConfigError("nodes must be a dictionary")
        
        for node_id, node_config in nodes.items():
            if not isinstance(node_config, dict):
                raise SSLConfigError(
                    f"Node '{node_id}' configuration must be a dictionary"
                )