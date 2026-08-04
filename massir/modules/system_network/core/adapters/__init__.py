"""
Transport Adapters package.

Provides adapters for different transport layers, allowing the
system_network module to work uniformly with socket, websocket,
and future transports.
"""

from .base import (
    TransportAdapter,
    MessageCallback,
    BytesCallback,
    ConnectionCallback,
)
from .socket_adapter import SocketAdapter
from .websocket_adapter import WebSocketAdapter

__all__ = [
    "TransportAdapter",
    "MessageCallback",
    "BytesCallback",
    "ConnectionCallback",
    "SocketAdapter",
    "WebSocketAdapter",
]