"""
Network Socket Module for Massir Framework

Provides async TCP/UDP socket services to all modules in the Massir framework.
"""

import json
from pathlib import Path
from typing import Optional, Any

from massir.core.interfaces import IModule

from .core.socket_api import SocketAPI
from .core.exceptions import SocketConfigError


class NetworkSocketModule(IModule):
    """
    Network Socket Module.
    
    Provides socket_api service for:
    - Async TCP servers and clients
    - Message Mode (length-prefix framing with codecs)
    - Stream Mode (zero-copy byte passthrough)
    - Connection pooling per peer
    - Auto-reconnect with exponential backoff
    - Heartbeat monitoring
    - Optional TLS via ssl_api
    - Optional encryption via encryption_api
    """
    
    def __init__(self):
        self._api: Optional[SocketAPI] = None
        self._logger: Any = None
        self._config: dict = {}
        self._module_dir: Path = Path(__file__).parent
    
    async def start(self, context):
        """
        Start the socket module.
        
        Reads configuration from:
        1. config.json (default settings)
        2. app_settings.json (user overrides)
        
        Creates and registers the SocketAPI service.
        """
        # Get framework services
        self._logger = context.services.get("core_logger")
        core_config = context.services.get("core_config")
        
        # Load default config
        self._config = self._load_default_config()
        
        # Override with user config
        if core_config:
            user_config = core_config.get("network_socket", {})
            if isinstance(user_config, dict):
                self._config = self._merge_config(self._config, user_config)
        
        # Resolve placeholders
        if hasattr(context, 'app_dir'):
            self._resolve_path_placeholders(context.app_dir)
        
        # Validate
        self._validate_config()
        
        # Create API
        self._api = SocketAPI(self._config, self._logger)
        
        # Link optional services
        ssl_api = context.services.get("ssl_api")
        if ssl_api:
            self._api.set_ssl_api(ssl_api)
            if self._logger:
                self._logger.log(
                    "SocketAPI linked with ssl_api for TLS support",
                    tag="socket"
                )
        
        encryption_api = context.services.get("encryption_api")
        if encryption_api:
            self._api.set_encryption_api(encryption_api)
            if self._logger:
                self._logger.log(
                    "SocketAPI linked with encryption_api",
                    tag="socket"
                )
        
        context.services.set("socket_api", self._api)
        
        if self._logger:
            self._logger.log(
                "NetworkSocketModule started - Message/Stream modes ready",
                tag="socket"
            )
        
        if self._api:
            await self._api.start()
        
        if self._logger:
            self._logger.log("NetworkSocketModule started", tag="socket")
    
    async def stop(self, context):
        """Stop the socket module."""
        if self._api:
            await self._api.stop()
        
        if self._logger:
            self._logger.log("NetworkSocketModule stopped", tag="socket")
        
        self._api = None
    
    def _load_default_config(self) -> dict:
        """Load default configuration from config.json."""
        config_path = self._module_dir / "config.json"
        
        default_config = {
            "server": {
                "default_host": "0.0.0.0",
                "default_port": 8443,
                "backlog": 100,
                "max_connections_per_peer": 10,
            },
            "client": {
                "connect_timeout_seconds": 10.0,
                "reconnect_enabled": True,
                "reconnect_initial_delay_seconds": 1.0,
                "reconnect_max_delay_seconds": 60.0,
                "reconnect_backoff_multiplier": 2.0,
                "reconnect_max_attempts": 0,
                "send_queue_size": 1000,
            },
            "framing": {
                "max_message_size_bytes": 16 * 1024 * 1024,
                "length_prefix_bytes": 4,
                "default_codec": "json",
            },
            "heartbeat": {
                "enabled": True,
                "interval_seconds": 30.0,
                "timeout_seconds": 90.0,
                "missed_threshold": 3,
            },
            "pool": {
                "max_connections_per_peer": 5,
                "idle_timeout_seconds": 300.0,
                "cleanup_interval_seconds": 60.0,
            },
            "ssl": {
                "enabled": True,
                "use_ssl_api": True,
            },
            "encryption": {
                "enabled": False,
                "encrypt_payload": False,
            },
            "logging": {
                "tag": "socket",
                "log_connections": True,
                "log_messages": False,
                "log_heartbeat": False,
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
                        tag="socket"
                    )
        
        return default_config
    
    def _merge_config(self, base: dict, override: dict) -> dict:
        """Deep merge configurations."""
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
        """Validate configuration."""
        # Validate server config
        server = self._config.get("server", {})
        port = server.get("default_port", 8443)
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise SocketConfigError(
                f"server.default_port must be between 1 and 65535, got {port}"
            )
        
        # Validate framing
        framing = self._config.get("framing", {})
        prefix_bytes = framing.get("length_prefix_bytes", 4)
        if prefix_bytes not in (2, 4, 8):
            raise SocketConfigError(
                f"framing.length_prefix_bytes must be 2, 4, or 8, got {prefix_bytes}"
            )
        
        max_size = framing.get("max_message_size_bytes", 16 * 1024 * 1024)
        if not isinstance(max_size, int) or max_size < 1:
            raise SocketConfigError(
                f"framing.max_message_size_bytes must be positive, got {max_size}"
            )

        # Validate heartbeat
        hb = self._config.get("heartbeat", {})
        interval = hb.get("interval_seconds", 30.0)
        timeout = hb.get("timeout_seconds", 90.0)
        if timeout <= interval:
            raise SocketConfigError(
                f"heartbeat.timeout_seconds ({timeout}) must be greater than "
                f"interval_seconds ({interval})"
            )

        # Validate pool
        pool = self._config.get("pool", {})
        max_per_peer = pool.get("max_connections_per_peer", 5)
        if not isinstance(max_per_peer, int) or max_per_peer < 1:
            raise SocketConfigError(
                f"pool.max_connections_per_peer must be at least 1, got {max_per_peer}"
            )