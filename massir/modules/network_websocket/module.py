"""
Network WebSocket Module for Massir Framework

Provides WebSocket transport services optimized for cloud-friendly deployments.
Designed to work through Cloudflare, CDNs, reverse proxies, and environments
with restricted ports (only 80/443).

Unlike network_socket which provides raw TCP/TLS, this module uses WebSocket
protocol which is HTTP-compatible and widely supported.
"""

import json
from pathlib import Path
from typing import Optional, Any

from massir.core.interfaces import IModule

from .core.websocket_api import WebSocketAPI
from .core.exceptions import WebSocketConfigError


class NetworkWebSocketModule(IModule):
    """
    Network WebSocket Module.
    
    Provides websocket_api service with WebSocket-specific features:
    - URL-based and path-based connections
    - Subprotocol negotiation
    - Custom HTTP headers (auth, cookies)
    - Native ping/pong heartbeat
    - Close codes with reasons
    - Built-in compression
    
    For unified transport management across multiple protocols, use the
    system_network module which adapts both socket_api and websocket_api
    to a common network_api interface.
    """
    
    def __init__(self):
        self._api: Optional[WebSocketAPI] = None
        self._logger: Any = None
        self._config: dict = {}
        self._module_dir: Path = Path(__file__).parent
    
    async def start(self, context):
        """Load config, create API, register service, and start the WebSocket module."""
        self._logger = context.services.get("core_logger")
        core_config = context.services.get("core_config")
        
        self._config = self._load_default_config()
        
        if core_config:
            user_config = core_config.get("network_websocket", {})
            if isinstance(user_config, dict):
                self._config = self._merge_config(self._config, user_config)
        
        if hasattr(context, 'app_dir'):
            self._resolve_path_placeholders(context.app_dir)
        
        self._validate_config()

        # Create API
        self._api = WebSocketAPI(self._config, self._logger)
        
        # Link optional services
        ssl_api = context.services.get("ssl_api")
        if ssl_api:
            self._api.set_ssl_api(ssl_api)
            if self._logger:
                self._logger.log(
                    "WebSocketAPI linked with ssl_api for WSS support",
                    tag="websocket"
                )
        
        encryption_api = context.services.get("encryption_api")
        if encryption_api:
            self._api.set_encryption_api(encryption_api)
            if self._logger:
                self._logger.log(
                    "WebSocketAPI linked with encryption_api",
                    tag="websocket"
                )
        
        context.services.set("websocket_api", self._api)
        
        if self._logger:
            self._logger.log(
                "NetworkWebSocketModule started - WebSocket transport ready",
                tag="websocket"
            )
        
        if self._api:
            await self._api.start()
        
        if self._logger:
            self._logger.log("NetworkWebSocketModule started", tag="websocket")
    
    async def stop(self, context):
        """Stop the WebSocket module."""
        if self._api:
            await self._api.stop()
        
        if self._logger:
            self._logger.log("NetworkWebSocketModule stopped", tag="websocket")
        
        self._api = None
    
    def _load_default_config(self) -> dict:
        """Load default configuration from config.json."""
        config_path = self._module_dir / "config.json"
        
        default_config = {
            "server": {
                "default_host": "0.0.0.0",
                "default_port": 443,
                "default_path": "/ws",
                "max_size_bytes": 16 * 1024 * 1024,
                "compression_enabled": True,
                "allowed_origins": ["*"],
            },
            "client": {
                "connect_timeout_seconds": 10.0,
                "reconnect_enabled": True,
                "reconnect_initial_delay_seconds": 2.0,
                "reconnect_max_delay_seconds": 60.0,
                "reconnect_backoff_multiplier": 2.0,
                "reconnect_max_attempts": 0,
                "send_queue_size": 1000,
                "default_path": "/ws",
                "subprotocol": "massir.v1",
                "additional_headers": {},
                "compression_enabled": True,
            },
            "heartbeat": {
                "enabled": True,
                "interval_seconds": 20.0,
                "timeout_seconds": 60.0,
            },
            "pool": {
                "max_connections_per_peer": 3,
                "idle_timeout_seconds": 300.0,
                "cleanup_interval_seconds": 60.0,
            },
            "ssl": {
                "enabled": True,
                "use_ssl_api": True,
            },
            "logging": {
                "tag": "websocket",
                "log_connections": True,
                "log_messages": False,
                "log_frames": False,
            },
        }
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                    if isinstance(file_config, dict):
                        default_config = self._merge_config(default_config, file_config)
            except (json.JSONDecodeError, IOError) as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to load config.json: {e}",
                        level="WARNING",
                        tag="websocket"
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
    
    def _resolve_path_placeholders(self, app_dir) -> None:
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
        server = self._config.get("server", {})
        port = server.get("default_port", 443)
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise WebSocketConfigError(
                f"server.default_port must be 1-65535, got {port}"
            )
        
        hb = self._config.get("heartbeat", {})
        interval = hb.get("interval_seconds", 20.0)
        timeout = hb.get("timeout_seconds", 60.0)
        if timeout <= interval:
            raise WebSocketConfigError(
                f"heartbeat.timeout_seconds ({timeout}) must be greater than "
                f"interval_seconds ({interval})"
            )
