"""
Node Registry for tracking network nodes.

Maintains metadata about all known nodes including their transport
type, endpoint configuration, and current status.
"""

from datetime import datetime
from typing import Any, Optional

from .types import NodeEntry, PeerStatus
from .exceptions import NodeNotFoundError


class NodeRegistry:
    """
    Registry of all known nodes in the network.
    
    Phase 1: Static configuration (loaded from config file).
    Future: Dynamic discovery via gossip protocol.
    """
    
    def __init__(self, mode: str = "static"):
        """
        Initialize the registry.
        
        Args:
            mode: "static" for config-based, "dynamic" for gossip (future)
        """
        self._mode = mode
        self._nodes: dict[str, NodeEntry] = {}
        self._self_node_id: Optional[str] = None
    
    @property
    def mode(self) -> str:
        """Get registry mode."""
        return self._mode
    
    @property
    def self_node_id(self) -> Optional[str]:
        """Get this node's ID."""
        return self._self_node_id
    
    def set_self_node(
        self,
        node_id: str,
        metadata: Optional[dict] = None,
        capabilities: Optional[list[str]] = None,
    ) -> None:
        """
        Set this node's identity.
        
        Args:
            node_id: This node's unique identifier
            metadata: Optional metadata about this node
            capabilities: Optional list of capabilities this node has
        """
        self._self_node_id = node_id
        
        # Register self in registry as a special entry
        self._nodes[node_id] = NodeEntry(
            node_id=node_id,
            transport="self",
            endpoint={},
            metadata=metadata or {},
            capabilities=capabilities or [],
            status=PeerStatus.CONNECTED,
            last_seen=datetime.now(),
        )
    
    def register(
        self,
        node_id: str,
        transport: str,
        endpoint: dict[str, Any],
        metadata: Optional[dict] = None,
        capabilities: Optional[list[str]] = None,
    ) -> NodeEntry:
        """
        Register a node in the registry.
        
        Args:
            node_id: Unique node identifier
            transport: Transport type ("socket" or "websocket")
            endpoint: Transport-specific endpoint configuration
            metadata: Optional metadata dict
            capabilities: Optional list of capabilities
        
        Returns:
            The created NodeEntry
        """
        entry = NodeEntry(
            node_id=node_id,
            transport=transport,
            endpoint=endpoint,
            metadata=metadata or {},
            capabilities=capabilities or [],
        )
        self._nodes[node_id] = entry
        return entry
    
    def unregister(self, node_id: str) -> bool:
        """
        Remove a node from the registry.
        
        Returns True if the node was removed, False if not found.
        """
        if node_id in self._nodes and node_id != self._self_node_id:
            del self._nodes[node_id]
            return True
        return False
    
    def get(self, node_id: str) -> Optional[NodeEntry]:
        """Get a node entry by ID, or None if not found."""
        return self._nodes.get(node_id)
    
    def get_or_raise(self, node_id: str) -> NodeEntry:
        """Get a node entry or raise NodeNotFoundError."""
        entry = self._nodes.get(node_id)
        if entry is None:
            raise NodeNotFoundError(node_id)
        return entry
    
    def get_all(self) -> list[NodeEntry]:
        """Get all registered nodes."""
        return list(self._nodes.values())
    
    def get_all_ids(self) -> list[str]:
        """Get all registered node IDs."""
        return list(self._nodes.keys())
    
    def get_remote_nodes(self) -> list[NodeEntry]:
        """Get all nodes except self."""
        return [
            n for n in self._nodes.values()
            if n.node_id != self._self_node_id
        ]
    
    def get_by_capability(self, capability: str) -> list[NodeEntry]:
        """Get all nodes that have a specific capability."""
        return [
            n for n in self._nodes.values()
            if capability in n.capabilities
            and n.node_id != self._self_node_id
        ]
    
    def get_by_transport(self, transport: str) -> list[NodeEntry]:
        """Get all nodes using a specific transport."""
        return [
            n for n in self._nodes.values()
            if n.transport == transport
        ]
    
    def update_status(
        self,
        node_id: str,
        status: PeerStatus,
        latency_ms: Optional[float] = None,
    ) -> None:
        """Update the status of a node."""
        entry = self._nodes.get(node_id)
        if entry:
            entry.status = status
            entry.last_seen = datetime.now()
            if latency_ms is not None:
                entry.latency_ms = latency_ms
    
    def increment_reconnect(self, node_id: str) -> None:
        """Increment the reconnect counter for a node."""
        entry = self._nodes.get(node_id)
        if entry:
            entry.reconnect_count += 1
    
    def load_from_config(self, nodes_config: list[dict]) -> int:
        """
        Load nodes from configuration list.
        
        Args:
            nodes_config: List of node configuration dicts
        
        Returns:
            Number of nodes loaded
        """
        count = 0
        for node_conf in nodes_config:
            if not isinstance(node_conf, dict):
                continue
            
            node_id = node_conf.get("node_id")
            if not node_id or node_id == self._self_node_id:
                continue
            
            self.register(
                node_id=node_id,
                transport=node_conf.get("transport", "socket"),
                endpoint=node_conf.get("endpoint", {}),
                metadata=node_conf.get("metadata", {}),
                capabilities=node_conf.get("capabilities", []),
            )
            count += 1
        
        return count
    
    def get_stats(self) -> dict:
        """Get registry statistics."""
        all_nodes = self.get_all()
        return {
            "mode": self._mode,
            "self_node_id": self._self_node_id,
            "total_nodes": len(all_nodes),
            "remote_nodes": len(self.get_remote_nodes()),
            "by_status": {
                status.value: sum(
                    1 for n in all_nodes if n.status == status
                )
                for status in PeerStatus
            },
            "by_transport": {
                transport: len(self.get_by_transport(transport))
                for transport in ["socket", "websocket", "self"]
            },
        }