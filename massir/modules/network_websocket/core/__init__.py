"""
Network WebSocket Core Module

Provides a WebSocket transport layer optimized for cloud-friendly deployments:
- WebSocket (ws://) and Secure WebSocket (wss://)
- URL-based and path-based routing
- Subprotocol negotiation (massir.v1, custom, etc.)
- Native WebSocket ping/pong for heartbeat
- HTTP headers for authentication (Bearer tokens, cookies)
- Compression (permessage-deflate)
- Close codes (RFC 6455) for precise disconnect reasons
- Compatible with Cloudflare, CDN, reverse proxies

This module provides a WebSocket-specific API. For unified transport
management across multiple protocols, use the system_network module.
"""

from .websocket_api import WebSocketAPI
from .connection import WebSocketConnection
from .server import WebSocketServer
from .client import WebSocketClient
from .pool import WebSocketConnectionPool
from .heartbeat import WebSocketHeartbeatMonitor
from .types import (
    WebSocketConfig,
    WebSocketCloseCode,
    WebSocketConnectionInfo,
    WebSocketFrameType,
)
from .exceptions import (
    WebSocketError,
    WebSocketConfigError,
    WebSocketConnectionError,
    WebSocketConnectionTimeoutError,
    WebSocketConnectionClosedError,
    WebSocketProtocolError,
    WebSocketHandshakeError,
    PoolError,
)

__all__ = [
    "WebSocketAPI",
    "WebSocketConnection",
    "WebSocketServer",
    "WebSocketClient",
    "WebSocketConnectionPool",
    "WebSocketHeartbeatMonitor",
    "WebSocketConfig",
    "WebSocketCloseCode",
    "WebSocketConnectionInfo",
    "WebSocketFrameType",
    "WebSocketError",
    "WebSocketConfigError",
    "WebSocketConnectionError",
    "WebSocketConnectionTimeoutError",
    "WebSocketConnectionClosedError",
    "WebSocketProtocolError",
    "WebSocketHandshakeError",
    "PoolError",
]