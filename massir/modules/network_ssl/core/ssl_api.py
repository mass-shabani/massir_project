"""
Unified SSL API

Provides a high-level interface for SSL/TLS operations including
context creation, certificate management, and hot-reload.
"""

import ssl
import asyncio
from pathlib import Path
from typing import Callable, Any, Optional
from datetime import datetime

from .context_factory import build_server_context, build_client_context
from .cert_manager import CertificateManager
from .cert_info import CertInfo, CertValidationResult
from .exceptions import (
    SSLError,
    SSLConfigError,
    CertificateLoadError,
)


class SSLAPI:
    """
    Unified API for SSL/TLS operations.
    
    Provides methods to:
    - Create server SSL contexts
    - Create client ssl contexts
    - Manage certificates
    - Check certificate expiry
    - Hot-reload certificates
    
    Example:
        >>> api = SSLAPI(config)
        >>> server_ctx = api.get_server_context()
        >>> client_ctx = api.get_client_context(peer_id="node-02")
        >>> info = api.get_cert_info()
    """
    
    def __init__(self, config: dict | None = None, logger: Any = None):
        """
        Initialize the SSL API.
        
        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        self._config = config or {}
        self._logger = logger
        self._cert_manager = CertificateManager()
        
        # Cache for contexts and cert info
        self._server_contexts: dict[str, ssl.SSLContext] = {}
        self._client_contexts: dict[str, ssl.SSLContext] = {}
        self._cert_info_cache: dict[str, CertInfo] = {}
        
        # Expiry callbacks
        self._expiry_callbacks: list[Callable[[str, CertInfo], Any]] = []
        
        # Background tasks
        self._reload_task: Optional[asyncio.Task] = None
        self._running = False
    
    # =========================================================================
    # Context Management
    # =========================================================================
    
    def get_server_context(
        self,
        node_id: str = "default",
        force_reload: bool = False,
    ) -> ssl.SSLContext:
        """
        Get or create an SSLContext for TLS server.
        
        Args:
            node_id: Node identifier to use specific certificates
            force_reload: Force reload from disk
        
        Returns:
            Configured ssl.SSLContext for server use
        """
        cache_key = f"server_{node_id}"
        
        if cache_key in self._server_contexts and not force_reload:
            return self._server_contexts[cache_key]
        
        # Get certificate paths from config
        node_config = self._get_node_config(node_id)
        certs_path = self._resolve_certs_path()
        
        cert_path = certs_path / node_config.get("cert_file", "server.crt")
        key_path = certs_path / node_config.get("key_file", "server.key")
        ca_path_str = node_config.get("ca_file")
        ca_path = certs_path / ca_path_str if ca_path_str else None
        
        # Build context
        context = build_server_context(
            cert_path=cert_path,
            key_path=key_path,
            ca_path=ca_path,
            verify_client=self._config.get("verify_client_certs", False),
            tls_version=self._config.get("tls_version", "1.3"),
            cipher_suites=self._config.get(
                "cipher_suites", "HIGH:!aNULL:!MD5:!3DES:!RC4"
            ),
            security_options=self._config.get("security_options"),
        )
        
        self._server_contexts[cache_key] = context
        
        # Cache cert info
        try:
            cert = self._cert_manager.load_certificate(cert_path)
            self._cert_info_cache[cache_key] = self._cert_manager.get_cert_info(cert)
            self._cert_manager.register_file(cert_path)
            
            if self._logger and self._config.get("logging", {}).get("log_cert_info"):
                info = self._cert_info_cache[cache_key]
                self._logger.log(
                    f"Server cert loaded: {info.subject} "
                    f"(expires in {info.days_until_expiry} days)",
                    tag="ssl"
                )
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to load cert info for server: {e}",
                    level="WARNING",
                    tag="ssl"
                )
        
        return context
    
    def get_client_context(
        self,
        peer_id: str = "default",
        sni_hostname: str | None = None,
        force_reload: bool = False,
    ) -> ssl.SSLContext:
        """
        Get or create an SSLContext for TLS client.
        
        Args:
            peer_id: Peer identifier to use specific certificates
            sni_hostname: Optional SNI hostname for the connection
            force_reload: Force reload from disk
        
        Returns:
            Configured ssl.SSLContext for client use
        """
        cache_key = f"client_{peer_id}_{sni_hostname or 'no_sni'}"
        
        if cache_key in self._client_contexts and not force_reload:
            return self._client_contexts[cache_key]
        
        # Get certificate paths from config
        node_config = self._get_node_config(peer_id)
        certs_path = self._resolve_certs_path()
        
        cert_path_str = node_config.get("cert_file")
        key_path_str = node_config.get("key_file")
        ca_path_str = node_config.get("ca_file")
        
        cert_path = certs_path / cert_path_str if cert_path_str else None
        key_path = certs_path / key_path_str if key_path_str else None
        ca_path = certs_path / ca_path_str if ca_path_str else None
        
        # Build context
        context = build_client_context(
            cert_path=cert_path,
            key_path=key_path,
            ca_path=ca_path,
            verify_server=self._config.get("verify_server_certs", True),
            check_hostname=self._config.get("check_hostname", True),
            tls_version=self._config.get("tls_version", "1.3"),
            cipher_suites=self._config.get(
                "cipher_suites", "HIGH:!aNULL:!MD5:!3DES:!RC4"
            ),
            security_options=self._config.get("security_options"),
            sni_hostname=sni_hostname,
        )
        
        self._client_contexts[cache_key] = context
        return context
    
    # =========================================================================
    # Certificate Information
    # =========================================================================
    
    def get_cert_info(
        self,
        node_id: str = "default",
    ) -> CertInfo | None:
        """
        Get certificate information for a node.
        
        Args:
            node_id: Node identifier
        
        Returns:
            CertInfo or None if not available
        """
        cache_key = f"server_{node_id}"
        
        if cache_key in self._cert_info_cache:
            return self._cert_info_cache[cache_key]
        
        # Try to load cert info
        try:
            node_config = self._get_node_config(node_id)
            certs_path = self._resolve_certs_path()
            cert_path = certs_path / node_config.get("cert_file", "server.crt")
            
            cert = self._cert_manager.load_certificate(cert_path)
            info = self._cert_manager.get_cert_info(cert)
            self._cert_info_cache[cache_key] = info
            return info
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to get cert info: {e}",
                    level="WARNING",
                    tag="ssl"
                )
            return None
    
    def validate_certificate(
        self,
        cert_path: str | Path,
        warning_days: int | None = None,
    ) -> CertValidationResult:
        """
        Validate a certificate file.
        
        Args:
            cert_path: Path to certificate file
            warning_days: Days threshold for expiry warning
        
        Returns:
            CertValidationResult with validation status
        """
        if warning_days is None:
            warning_days = self._config.get("expiry_warning_days", 30)
        
        return self._cert_manager.validate_certificate(cert_path, warning_days)
    
    # =========================================================================
    # Hot-Reload
    # =========================================================================
    
    def reload_certs(
        self,
        node_id: str = "default",
    ) -> bool:
        """
        Reload certificates from disk.
        
        Args:
            node_id: Node identifier
        
        Returns:
            True if certificates were reloaded, False if no changes
        """
        node_config = self._get_node_config(node_id)
        certs_path = self._resolve_certs_path()
        cert_path = certs_path / node_config.get("cert_file", "server.crt")
        
        if not self._cert_manager.has_file_changed(cert_path):
            return False
        
        # Clear caches for this node
        cache_key = f"server_{node_id}"
        if cache_key in self._server_contexts:
            del self._server_contexts[cache_key]
        if cache_key in self._cert_info_cache:
            del self._cert_info_cache[cache_key]
        
        # Rebuild context
        try:
            self.get_server_context(node_id, force_reload=True)
            if self._logger:
                self._logger.log(
                    f"Certificates reloaded for node '{node_id}'",
                    tag="ssl"
                )
            return True
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to reload certificates: {e}",
                    level="ERROR",
                    tag="ssl"
                )
            return False
    
    async def start_auto_reload(self) -> None:
        """
        Start automatic certificate reload monitoring.
        
        Checks certificates periodically and reloads if changed.
        """
        if not self._config.get("auto_reload", True):
            return
        
        if self._reload_task is not None:
            return
        
        self._running = True
        self._reload_task = asyncio.create_task(self._auto_reload_loop())
        
        if self._logger:
            interval = self._config.get("reload_check_interval_seconds", 3600)
            self._logger.log(
                f"Auto-reload started (checking every {interval}s)",
                tag="ssl"
            )
    
    async def stop_auto_reload(self) -> None:
        """Stop automatic certificate reload monitoring."""
        self._running = False
        
        if self._reload_task is not None:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass
            self._reload_task = None
    
    async def _auto_reload_loop(self) -> None:
        """Background loop for auto-reload."""
        interval = self._config.get("reload_check_interval_seconds", 3600)
        warning_days = self._config.get("expiry_warning_days", 30)
        
        while self._running:
            try:
                await asyncio.sleep(interval)
                
                # Check all registered nodes
                for node_id in list(self._get_all_node_ids()):
                    try:
                        self._check_and_reload(node_id, warning_days)
                    except Exception as e:
                        if self._logger:
                            self._logger.log(
                                f"Auto-reload error for node '{node_id}': {e}",
                                level="ERROR",
                                tag="ssl"
                            )
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Auto-reload loop error: {e}",
                        level="ERROR",
                        tag="ssl"
                    )
    
    def _check_and_reload(
        self,
        node_id: str,
        warning_days: int,
    ) -> None:
        """Check and reload a node's certificates if needed."""
        node_config = self._get_node_config(node_id)
        certs_path = self._resolve_certs_path()
        cert_path = certs_path / node_config.get("cert_file", "server.crt")
        
        if not cert_path.exists():
            return
        
        # Check for file changes
        if self._cert_manager.has_file_changed(cert_path):
            self.reload_certs(node_id)
        
        # Check expiry
        info = self.get_cert_info(node_id)
        if info:
            if info.is_expired:
                if self._logger:
                    self._logger.log(
                        f"Certificate for '{node_id}' has EXPIRED!",
                        level="ERROR",
                        tag="ssl"
                    )
                self._notify_expiry_callbacks(node_id, info)
            elif info.days_until_expiry <= warning_days:
                if self._logger:
                    self._logger.log(
                        f"Certificate for '{node_id}' expires in "
                        f"{info.days_until_expiry} days",
                        level="WARNING",
                        tag="ssl"
                    )
                self._notify_expiry_callbacks(node_id, info)
    
    # =========================================================================
    # Expiry Callbacks
    # =========================================================================
    
    def register_expiry_callback(
        self,
        callback: Callable[[str, CertInfo], Any],
    ) -> None:
        """
        Register a callback to be notified about certificate expiry.
        
        The callback will be called with (node_id, cert_info) when a
        certificate is expired or expiring soon.
        
        Args:
            callback: Function to call on expiry events
        """
        self._expiry_callbacks.append(callback)
    
    def unregister_expiry_callback(
        self,
        callback: Callable[[str, CertInfo], Any],
    ) -> None:
        """Remove an expiry callback."""
        if callback in self._expiry_callbacks:
            self._expiry_callbacks.remove(callback)
    
    def _notify_expiry_callbacks(
        self,
        node_id: str,
        cert_info: CertInfo,
    ) -> None:
        """Notify all registered callbacks about expiry events."""
        for callback in self._expiry_callbacks:
            try:
                result = callback(node_id, cert_info)
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Expiry callback error: {e}",
                        level="ERROR",
                        tag="ssl"
                    )
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_info(self) -> dict[str, Any]:
        """Get information about the SSL module."""
        return {
            "module": "network_ssl",
            "version": "1.0.0",
            "tls_version": self._config.get("tls_version", "1.3"),
            "verify_client_certs": self._config.get("verify_client_certs", False),
            "verify_server_certs": self._config.get("verify_server_certs", True),
            "auto_reload": self._config.get("auto_reload", True),
            "expiry_warning_days": self._config.get("expiry_warning_days", 30),
            "cached_contexts": {
                "server": len(self._server_contexts),
                "client": len(self._client_contexts),
            },
            "registered_callbacks": len(self._expiry_callbacks),
        }
    
    def clear_cache(self) -> None:
        """Clear all cached contexts and cert info."""
        self._server_contexts.clear()
        self._client_contexts.clear()
        self._cert_info_cache.clear()
        self._cert_manager.clear_cache()
    
    # =========================================================================
    # Internal Helpers
    # =========================================================================
    
    def _get_node_config(self, node_id: str) -> dict:
        """Get configuration for a specific node."""
        nodes = self._config.get("nodes", {})
        return nodes.get(node_id, nodes.get("default", {}))
    
    def _resolve_certs_path(self) -> Path:
        """Resolve the certificates directory path."""
        certs_path = self._config.get(
            "default_certs_path", "{app_dir}/certs"
        )
        
        # Replace placeholders
        if "{app_dir}" in certs_path:
            # Use current working directory as fallback
            certs_path = certs_path.replace("{app_dir}", str(Path.cwd()))
        
        return Path(certs_path)
    
    def _get_all_node_ids(self) -> list[str]:
        """Get all configured node IDs."""
        nodes = self._config.get("nodes", {})
        node_ids = list(nodes.keys())
        if "default" not in node_ids and node_ids:
            node_ids.append("default")
        return node_ids or ["default"]