"""
Connection Manager for high-level connection lifecycle.

Coordinates transport adapters to maintain required connections
based on topology and node registry state.
"""

import asyncio
from typing import Any, Callable, Awaitable, Optional

from .types import NodeEntry, PeerStatus
from .registry import NodeRegistry
from .topology import TopologyManager
from .adapters.base import TransportAdapter
from .exceptions import TransportNotAvailableError


# Callback types
ConnectionCallback = Callable[[str, NodeEntry], Awaitable[None] | None]
DisconnectionCallback = Callable[[str, NodeEntry], Awaitable[None] | None]


class ConnectionManager:
    """
    Manages high-level connection lifecycle.
    
    Responsibilities:
    - Maintain connections to required peers based on topology
    - Coordinate transport adapters for different transport types
    - Track connection state at network level (above transport layer)
    - Trigger reconnection on failures
    """
    
    def __init__(
        self,
        self_node_id: str,
        registry: NodeRegistry,
        topology: TopologyManager,
        logger: Any = None,
    ):
        self._self_node_id = self_node_id
        self._registry = registry
        self._topology = topology
        self._logger = logger
        
        # Registered transport adapters: {"socket": adapter, "websocket": adapter}
        self._adapters: dict[str, TransportAdapter] = {}
        
        # Track active connections at network level
        self._active_connections: set[str] = set()
        
        # Callbacks
        self._on_connect: Optional[ConnectionCallback] = None
        self._on_disconnect: Optional[DisconnectionCallback] = None
    
    # =========================================================================
    # Adapter Registration
    # =========================================================================
    
    def register_adapter(
        self,
        transport: str,
        adapter: TransportAdapter,
    ) -> None:
        """
        Register a transport adapter.
        
        Args:
            transport: Transport name (e.g., "socket", "websocket")
            adapter: TransportAdapter implementation
        """
        self._adapters[transport] = adapter
        if self._logger:
            self._logger.log(
                f"Registered transport adapter: {transport}",
                tag="network"
            )
    
    def get_adapter(self, transport: str) -> TransportAdapter:
        """
        Get adapter for a transport type.
        
        Raises:
            TransportNotAvailableError: If adapter not registered
        """
        adapter = self._adapters.get(transport)
        if adapter is None:
            raise TransportNotAvailableError(transport)
        return adapter
    
    def get_available_transports(self) -> list[str]:
        """Get list of available transport types."""
        return list(self._adapters.keys())
    
    def has_transport(self, transport: str) -> bool:
        """Check if a transport is available."""
        return transport in self._adapters
    
    # =========================================================================
    # Callbacks
    # =========================================================================
    
    def on_connect(self, callback: ConnectionCallback) -> None:
        """Register callback for successful connections."""
        self._on_connect = callback
    
    def on_disconnect(self, callback: DisconnectionCallback) -> None:
        """Register callback for disconnections."""
        self._on_disconnect = callback
    
    async def _invoke_on_connect(self, peer_id: str, entry: NodeEntry) -> None:
        """Invoke connect callback safely."""
        if self._on_connect:
            try:
                result = self._on_connect(peer_id, entry)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in on_connect callback: {e}",
                        level="ERROR",
                        tag="network"
                    )
    
    async def _invoke_on_disconnect(
        self,
        peer_id: str,
        entry: NodeEntry,
    ) -> None:
        """Invoke disconnect callback safely."""
        if self._on_disconnect:
            try:
                result = self._on_disconnect(peer_id, entry)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error in on_disconnect callback: {e}",
                        level="ERROR",
                        tag="network"
                    )
    
    # =========================================================================
    # Connection Operations
    # =========================================================================
    
    async def connect_to(self, peer_id: str) -> bool:
        """
        Connect to a specific peer.
        
        Returns True if connection was established, False otherwise.
        """
        entry = self._registry.get(peer_id)
        if not entry:
            if self._logger:
                self._logger.log(
                    f"Cannot connect: peer '{peer_id}' not in registry",
                    level="WARNING",
                    tag="network"
                )
            return False
        
        if peer_id == self._self_node_id:
            return False
        
        if peer_id in self._active_connections:
            return True
        
        try:
            adapter = self.get_adapter(entry.transport)
        except TransportNotAvailableError as e:
            if self._logger:
                self._logger.log(
                    f"Cannot connect to '{peer_id}': {e}",
                    level="ERROR",
                    tag="network"
                )
            self._registry.update_status(peer_id, PeerStatus.FAILED)
            return False
        
        self._registry.update_status(peer_id, PeerStatus.CONNECTING)
        
        try:
            success = await adapter.connect(peer_id, entry.endpoint)
            if success:
                self._active_connections.add(peer_id)
                self._registry.update_status(peer_id, PeerStatus.CONNECTED)
                await self._invoke_on_connect(peer_id, entry)
                return True
            else:
                self._registry.update_status(peer_id, PeerStatus.FAILED)
                return False
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to connect to '{peer_id}': {e}",
                    level="ERROR",
                    tag="network"
                )
            self._registry.update_status(peer_id, PeerStatus.FAILED)
            return False
    
    async def disconnect_from(self, peer_id: str) -> bool:
        """
        Disconnect from a specific peer.
        
        Returns True if disconnection succeeded.
        """
        entry = self._registry.get(peer_id)
        if not entry:
            return False
        
        try:
            adapter = self.get_adapter(entry.transport)
            await adapter.disconnect(peer_id)
        except TransportNotAvailableError:
            pass
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Error disconnecting from '{peer_id}': {e}",
                    level="WARNING",
                    tag="network"
                )
        
        was_connected = peer_id in self._active_connections
        self._active_connections.discard(peer_id)
        self._registry.update_status(peer_id, PeerStatus.DISCONNECTED)
        
        if was_connected:
            await self._invoke_on_disconnect(peer_id, entry)
        
        return True
    
    async def connect_to_required_peers(self) -> dict[str, bool]:
        """
        Connect to all peers required by the current topology.
        
        Returns:
            Dictionary mapping peer_id to connection success
        """
        all_nodes = self._registry.get_all_ids()
        required = self._topology.get_required_connections(all_nodes)
        
        results = {}
        for peer_id in required:
            if peer_id == self._self_node_id:
                continue
            results[peer_id] = await self.connect_to(peer_id)
        
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all peers."""
        peers = list(self._active_connections)
        for peer_id in peers:
            await self.disconnect_from(peer_id)
    
    # =========================================================================
    # Status Queries
    # =========================================================================
    
    def is_connected_to(self, peer_id: str) -> bool:
        """Check if currently connected to a peer."""
        return peer_id in self._active_connections
    
    def get_connected_peers(self) -> list[str]:
        """Get list of connected peer IDs."""
        return list(self._active_connections)
    
    def get_missing_connections(self) -> list[str]:
        """Get peers that should be connected but aren't."""
        all_nodes = self._registry.get_all_ids()
        required = set(self._topology.get_required_connections(all_nodes))
        return list(required - self._active_connections - {self._self_node_id})
    
    def get_status(self) -> dict:
        """Get connection manager status."""
        all_nodes = self._registry.get_all_ids()
        required = self._topology.get_required_connections(all_nodes)
        required = [n for n in required if n != self._self_node_id]
        
        return {
            "self_node_id": self._self_node_id,
            "total_nodes": len(all_nodes),
            "required_peers": len(required),
            "connected_peers": len(self._active_connections),
            "missing_connections": self.get_missing_connections(),
            "available_transports": self.get_available_transports(),
        }