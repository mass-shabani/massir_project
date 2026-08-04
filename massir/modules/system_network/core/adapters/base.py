"""
Base Transport Adapter interface.

Defines the contract that all transport adapters must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable, Optional


# Callback types
MessageCallback = Callable[[str, dict, Any], Awaitable[None] | None]
BytesCallback = Callable[[str, bytes, Any], Awaitable[None] | None]
ConnectionCallback = Callable[[str, Any], Awaitable[None] | None]


class TransportAdapter(ABC):
    """
    Abstract base class for transport adapters.
    
    Each transport (socket, websocket, etc.) implements this interface
    to provide a uniform way of communicating across different protocols.
    """
    
    @property
    @abstractmethod
    def transport_name(self) -> str:
        """Name of this transport (e.g., 'socket', 'websocket')."""
        pass
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    @abstractmethod
    async def connect(self, peer_id: str, endpoint: dict) -> bool:
        """
        Connect to a peer.
        
        Args:
            peer_id: Unique peer identifier
            endpoint: Transport-specific endpoint configuration
        
        Returns:
            True if connection established, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self, peer_id: str) -> bool:
        """
        Disconnect from a peer.
        
        Returns:
            True if disconnection succeeded
        """
        pass
    
    @abstractmethod
    def is_connected(self, peer_id: str) -> bool:
        """Check if currently connected to a peer."""
        pass
    
    @abstractmethod
    def get_connected_peers(self) -> list[str]:
        """Get list of connected peer IDs."""
        pass
    
    # =========================================================================
    # Sending
    # =========================================================================
    
    @abstractmethod
    async def send_message(self, peer_id: str, message: dict) -> bool:
        """
        Send a dictionary message to a peer.
        
        The adapter is responsible for converting the dict to the
        transport's native format (e.g., JSON for WebSocket).
        
        Returns:
            True if sent successfully
        """
        pass
    
    @abstractmethod
    async def send_bytes(self, peer_id: str, data: bytes) -> bool:
        """
        Send raw bytes to a peer.
        
        Returns:
            True if sent successfully
        """
        pass
    
    # =========================================================================
    # Receiving (Callbacks)
    # =========================================================================
    
    @abstractmethod
    def on_message(self, callback: MessageCallback) -> None:
        """
        Register callback for incoming messages.
        
        Callback signature: async def handler(peer_id, message_dict, connection)
        """
        pass
    
    @abstractmethod
    def on_bytes(self, callback: BytesCallback) -> None:
        """
        Register callback for incoming bytes.
        
        Callback signature: async def handler(peer_id, bytes, connection)
        """
        pass
    
    @abstractmethod
    def on_connection(self, callback: ConnectionCallback) -> None:
        """Register callback for new connections (inbound)."""
        pass
    
    @abstractmethod
    def on_disconnection(self, callback: ConnectionCallback) -> None:
        """Register callback for disconnections."""
        pass
    
    # =========================================================================
    # Server (Optional)
    # =========================================================================
    
    async def start_server(self, config: dict) -> bool:
        """
        Start a server to accept inbound connections.
        
        Not all transports support this. Default implementation returns False.
        """
        return False
    
    async def stop_server(self) -> None:
        """Stop the server if running."""
        pass
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self) -> None:
        """Start the adapter (background tasks, etc.)."""
        pass
    
    async def stop(self) -> None:
        """Stop the adapter and cleanup."""
        pass
    
    def get_info(self) -> dict:
        """Get adapter information and statistics."""
        return {
            "transport": self.transport_name,
            "connected_peers": len(self.get_connected_peers()),
        }