"""
Unified Network API.

The high-level interface that application modules use to interact
with the network. Hides transport details and provides transport-agnostic
messaging, routing, and topology management.
"""

import asyncio
import time
from typing import Any, Callable, Awaitable, Optional

from .types import NodeEntry, NetworkStatus, PeerStatus
from .registry import NodeRegistry
from .topology import TopologyManager, TopologyType
from .router import Router, Route
from .connection_manager import ConnectionManager
from .envelope import MessageEnvelope
from .adapters.base import TransportAdapter
from .exceptions import (
    NetworkError,
    NodeNotFoundError,
    NoRouteError,
    EnvelopeExpiredError,
)


# Event callback types
MessageEventCallback = Callable[
    [MessageEnvelope, str, Any],
    Awaitable[None] | None,
]
PeerEventCallback = Callable[
    [str, NodeEntry],
    Awaitable[None] | None,
]


class NetworkAPI:
    """
    High-level, transport-agnostic network API.
    
    This is the main interface application modules use to:
    - Register and discover nodes
    - Configure topology
    - Send messages (direct or multi-hop)
    - Broadcast to groups
    - Monitor network health
    
    The API hides all transport details - applications don't need to
    know whether communication uses sockets or WebSockets.
    """
    
    def __init__(
        self,
        self_node_id: str,
        registry: NodeRegistry,
        topology: TopologyManager,
        router: Router,
        connection_manager: ConnectionManager,
        config: dict,
        logger: Any = None,
    ):
        self._self_node_id = self_node_id
        self._registry = registry
        self._topology = topology
        self._router = router
        self._connection_manager = connection_manager
        self._config = config
        self._logger = logger
        
        # Event callbacks
        self._on_message: Optional[MessageEventCallback] = None
        self._on_peer_connected: Optional[PeerEventCallback] = None
        self._on_peer_disconnected: Optional[PeerEventCallback] = None
        
        # Wire up internal handlers
        self._setup_internal_handlers()
    
    def _setup_internal_handlers(self) -> None:
        """Wire up internal message routing handler."""
        
        async def internal_message_handler(
            peer_id: str,
            message_dict: dict,
            connection: Any,
        ):
            """Route incoming messages through envelope logic."""
            try:
                # Check if this is an envelope
                if MessageEnvelope.is_envelope(message_dict):
                    envelope = MessageEnvelope.from_dict(message_dict)
                    await self._handle_envelope(envelope, peer_id, connection)
                else:
                    # Raw message - deliver to application
                    if self._on_message:
                        # Wrap as envelope for consistent API
                        synthetic = MessageEnvelope(
                            source=peer_id,
                            destination=self._self_node_id,
                            route=[peer_id, self._self_node_id],
                            current_hop=1,
                            payload=message_dict,
                        )
                        result = self._on_message(synthetic, peer_id, connection)
                        if hasattr(result, '__await__'):
                            await result
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Error processing inbound message: {e}",
                        level="ERROR",
                        tag="network"
                    )
        
        async def internal_connect_handler(peer_id: str, connection: Any):
            """Handle peer connection events."""
            entry = self._registry.get(peer_id)
            if entry and self._on_peer_connected:
                try:
                    result = self._on_peer_connected(peer_id, entry)
                    if hasattr(result, '__await__'):
                        await result
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error in on_peer_connected callback: {e}",
                            level="ERROR",
                            tag="network"
                        )
        
        async def internal_disconnect_handler(peer_id: str, connection: Any):
            """Handle peer disconnection events."""
            entry = self._registry.get(peer_id)
            if entry and self._on_peer_disconnected:
                try:
                    result = self._on_peer_disconnected(peer_id, entry)
                    if hasattr(result, '__await__'):
                        await result
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error in on_peer_disconnected callback: {e}",
                            level="ERROR",
                            tag="network"
                        )
        
        # Register handlers on all adapters
        for adapter in self._get_all_adapters():
            adapter.on_message(internal_message_handler)
            adapter.on_connection(internal_connect_handler)
            adapter.on_disconnection(internal_disconnect_handler)
    
    def _get_all_adapters(self) -> list[TransportAdapter]:
        """Get all registered adapters from connection manager."""
        adapters = []
        for transport in self._connection_manager.get_available_transports():
            try:
                adapters.append(self._connection_manager.get_adapter(transport))
            except Exception:
                pass
        return adapters
    
    async def _handle_envelope(
        self,
        envelope: MessageEnvelope,
        from_peer: str,
        connection: Any,
    ) -> None:
        """
        Handle an incoming envelope - either deliver locally or forward.
        """
        # Check TTL
        if envelope.is_expired():
            if self._logger:
                self._logger.log(
                    f"Envelope {envelope.message_id[:8]} expired, dropping",
                    level="WARNING",
                    tag="network"
                )
            return
        
        # If this envelope is for me, deliver to application
        if envelope.is_for_me(self._self_node_id):
            if self._on_message:
                try:
                    result = self._on_message(envelope, from_peer, connection)
                    if hasattr(result, '__await__'):
                        await result
                except Exception as e:
                    if self._logger:
                        self._logger.log(
                            f"Error delivering envelope to app: {e}",
                            level="ERROR",
                            tag="network"
                        )
            return
        
        # Not for me - forward to next hop (multi-hop routing)
        if not self._config.get("routing", {}).get("enable_multi_hop", True):
            if self._logger:
                self._logger.log(
                    f"Multi-hop disabled, dropping envelope for {envelope.destination}",
                    level="WARNING",
                    tag="network"
                )
            return
        
        next_hop = envelope.next_hop()
        if not next_hop:
            return
        
        try:
            envelope.advance_hop()
            await self._send_envelope(next_hop, envelope)
        except EnvelopeExpiredError:
            if self._logger:
                self._logger.log(
                    f"Envelope {envelope.message_id[:8]} TTL expired, dropping",
                    level="WARNING",
                    tag="network"
                )
    
    async def _send_envelope(
        self,
        next_hop: str,
        envelope: MessageEnvelope,
    ) -> bool:
        """Send an envelope to the next hop via appropriate adapter."""
        entry = self._registry.get(next_hop)
        if not entry:
            if self._logger:
                self._logger.log(
                    f"Cannot forward: next_hop '{next_hop}' not in registry",
                    level="ERROR",
                    tag="network"
                )
            return False
        
        if not self._connection_manager.is_connected_to(next_hop):
            if self._logger:
                self._logger.log(
                    f"Cannot forward: not connected to '{next_hop}'",
                    level="WARNING",
                    tag="network"
                )
            return False
        
        try:
            adapter = self._connection_manager.get_adapter(entry.transport)
            return await adapter.send_message(next_hop, envelope.to_dict())
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to forward envelope to '{next_hop}': {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    # =========================================================================
    # Node Management
    # =========================================================================
    
    def register_node(
        self,
        node_id: str,
        transport: str,
        endpoint: dict,
        metadata: Optional[dict] = None,
        capabilities: Optional[list[str]] = None,
    ) -> NodeEntry:
        """
        Register a node in the network.
        
        Args:
            node_id: Unique node identifier
            transport: Transport type ("socket" or "websocket")
            endpoint: Transport-specific endpoint configuration
            metadata: Optional metadata dict
            capabilities: Optional list of capabilities
        
        Returns:
            The registered NodeEntry
        """
        return self._registry.register(
            node_id=node_id,
            transport=transport,
            endpoint=endpoint,
            metadata=metadata,
            capabilities=capabilities,
        )
    
    def unregister_node(self, node_id: str) -> bool:
        """Remove a node from the registry."""
        return self._registry.unregister(node_id)
    
    def get_node(self, node_id: str) -> Optional[NodeEntry]:
        """Get information about a specific node."""
        return self._registry.get(node_id)
    
    def get_all_nodes(self) -> list[NodeEntry]:
        """Get all registered nodes."""
        return self._registry.get_all()
    
    def get_nodes_by_capability(self, capability: str) -> list[NodeEntry]:
        """Get all nodes with a specific capability."""
        return self._registry.get_by_capability(capability)
    
    # =========================================================================
    # Topology
    # =========================================================================
    
    def set_topology(
        self,
        topology: str | TopologyType,
        hub_node: Optional[str] = None,
        parent_node: Optional[str] = None,
        custom_edges: Optional[list] = None,
    ) -> None:
        """
        Configure the network topology.
        
        Args:
            topology: Topology type
            hub_node: Hub node ID for STAR topology
            parent_node: Parent node ID for TREE topology
            custom_edges: Edge list for CUSTOM topology
        """
        self._topology.set_topology(
            topology,
            hub_node=hub_node,
            parent_node=parent_node,
            custom_edges=custom_edges,
        )
    
    def get_topology(self) -> dict:
        """Get current topology information."""
        return self._topology.get_info()
    
    # =========================================================================
    # Connectivity
    # =========================================================================
    
    async def connect_all(self) -> dict[str, bool]:
        """
        Connect to all peers required by the current topology.
        
        Returns:
            Dictionary mapping peer_id to connection success
        """
        return await self._connection_manager.connect_to_required_peers()
    
    async def connect_to(self, node_id: str) -> bool:
        """Connect to a specific node."""
        return await self._connection_manager.connect_to(node_id)
    
    async def disconnect_from(self, node_id: str) -> bool:
        """Disconnect from a specific node."""
        return await self._connection_manager.disconnect_from(node_id)
    
    async def disconnect_all(self) -> None:
        """Disconnect from all peers."""
        await self._connection_manager.disconnect_all()
    
    def is_connected_to(self, node_id: str) -> bool:
        """Check if currently connected to a node."""
        return self._connection_manager.is_connected_to(node_id)
    
    def get_connected_peers(self) -> list[str]:
        """Get list of currently connected peers."""
        return self._connection_manager.get_connected_peers()
    
    # =========================================================================
    # Routing
    # =========================================================================
    
    def get_route(self, destination: str) -> Optional[Route]:
        """
        Get the route to a destination.
        
        Returns None if no route exists.
        """
        return self._router.find_route(destination)
    
    def get_routing_table(self) -> dict[str, Route]:
        """Get the full routing table."""
        return self._router.get_routing_table()
    
    # =========================================================================
    # Messaging
    # =========================================================================
    
    async def send(
        self,
        destination: str,
        payload: Any,
        payload_type: str = "data",
        ttl: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> bool:
        """
        Send a message to a destination (with automatic routing).
        
        If directly connected, sends directly. Otherwise routes through
        intermediate hops based on current topology.
        
        Args:
            destination: Target node ID
            payload: Message payload (any JSON-serializable data)
            payload_type: Type label for the payload
            ttl: Time-to-live (max hops), None = use default
            trace_id: Optional trace ID for distributed tracing
        
        Returns:
            True if message was sent to the next hop successfully
        """
        if destination == self._self_node_id:
            if self._logger:
                self._logger.log(
                    "Cannot send message to self",
                    level="WARNING",
                    tag="network"
                )
            return False
        
        # Find route
        route = self._router.find_route(destination)
        if not route:
            if self._logger:
                self._logger.log(
                    f"No route to '{destination}'",
                    level="ERROR",
                    tag="network"
                )
            return False
        
        # Build envelope
        default_ttl = self._config.get("routing", {}).get("default_ttl", 10)
        envelope = MessageEnvelope(
            source=self._self_node_id,
            destination=destination,
            route=route.hops,
            payload=payload,
            payload_type=payload_type,
            ttl=ttl or default_ttl,
            trace_id=trace_id or "",
        )
        
        # Send to next hop
        success = await self._send_envelope(route.next_hop, envelope)
        
        if success and self._logger and self._config.get("logging", {}).get("log_routing"):
            self._logger.log(
                f"Sent envelope {envelope.message_id[:8]} to '{destination}' "
                f"via '{route.next_hop}' ({route.hop_count} hops)",
                tag="network"
            )
        
        return success
    
    async def broadcast(
        self,
        payload: Any,
        payload_type: str = "data",
        exclude_self: bool = True,
    ) -> dict[str, bool]:
        """
        Broadcast a message to all nodes.
        
        Args:
            payload: Message payload
            payload_type: Type label
            exclude_self: If True, don't send to self (default)
        
        Returns:
            Dictionary mapping node_id to send success
        """
        results = {}
        for entry in self._registry.get_all():
            if exclude_self and entry.node_id == self._self_node_id:
                continue
            results[entry.node_id] = await self.send(
                entry.node_id,
                payload,
                payload_type,
            )
        return results
    
    async def send_to_capability(
        self,
        capability: str,
        payload: Any,
        payload_type: str = "data",
    ) -> dict[str, bool]:
        """Send a message to all nodes with a specific capability."""
        results = {}
        for entry in self._registry.get_by_capability(capability):
            results[entry.node_id] = await self.send(
                entry.node_id,
                payload,
                payload_type,
            )
        return results
    
    async def send_bytes(
        self,
        destination: str,
        data: bytes,
    ) -> bool:
        """
        Send raw bytes directly to a connected peer.
        
        Note: Multi-hop is NOT supported for raw bytes - only direct
        connections work. Use `send()` with payload for multi-hop.
        """
        if not self._connection_manager.is_connected_to(destination):
            if self._logger:
                self._logger.log(
                    f"Cannot send bytes to '{destination}': not connected",
                    level="WARNING",
                    tag="network"
                )
            return False
        
        entry = self._registry.get(destination)
        if not entry:
            return False
        
        try:
            adapter = self._connection_manager.get_adapter(entry.transport)
            return await adapter.send_bytes(destination, data)
        except Exception as e:
            if self._logger:
                self._logger.log(
                    f"Failed to send bytes to '{destination}': {e}",
                    level="ERROR",
                    tag="network"
                )
            return False
    
    # =========================================================================
    # Events
    # =========================================================================
    
    def on_message(self, callback: MessageEventCallback) -> None:
        """
        Register handler for incoming messages.
        
        Callback signature:
            async def handler(envelope: MessageEnvelope, from_peer: str, connection)
        """
        self._on_message = callback
    
    def on_peer_connected(self, callback: PeerEventCallback) -> None:
        """
        Register handler for peer connection events.
        
        Callback signature:
            async def handler(peer_id: str, node_entry: NodeEntry)
        """
        self._on_peer_connected = callback
    
    def on_peer_disconnected(self, callback: PeerEventCallback) -> None:
        """
        Register handler for peer disconnection events.
        
        Callback signature:
            async def handler(peer_id: str, node_entry: NodeEntry)
        """
        self._on_peer_disconnected = callback
    
    # =========================================================================
    # Monitoring
    # =========================================================================
    
    def get_network_status(self) -> NetworkStatus:
        """Get comprehensive network status."""
        all_nodes = self._registry.get_all()
        required = self._topology.get_required_connections(
            [n.node_id for n in all_nodes]
        )
        required = [n for n in required if n != self._self_node_id]
        connected = self._connection_manager.get_connected_peers()
        
        return NetworkStatus(
            self_node_id=self._self_node_id,
            topology=self._topology.topology_type.value,
            total_nodes=len(all_nodes),
            required_peers=len(required),
            connected_peers=len([p for p in connected if p in required]),
            online_nodes=sum(
                1 for n in all_nodes
                if n.status == PeerStatus.CONNECTED
            ),
            missing_connections=[
                p for p in required if p not in connected
            ],
        )
    
    def get_info(self) -> dict:
        """Get comprehensive network information."""
        return {
            "module": "system_network",
            "version": "1.0.0",
            "self_node_id": self._self_node_id,
            "network_status": self.get_network_status().to_dict(),
            "registry": self._registry.get_stats(),
            "routing": self._router.get_stats(),
            "connections": self._connection_manager.get_status(),
            "topology": self._topology.get_info(),
        }