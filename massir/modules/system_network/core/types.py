"""
Type definitions for system_network module.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class PeerStatus(str, Enum):
    """Status of a peer in the network."""
    
    UNKNOWN = "unknown"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


@dataclass
class NodeEntry:
    """
    Registry entry for a node in the network.
    
    Contains all metadata needed to connect to and communicate with a node.
    """
    
    node_id: str
    transport: str                    # "socket" or "websocket"
    endpoint: dict[str, Any]          # Transport-specific endpoint config
    metadata: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    status: PeerStatus = PeerStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    latency_ms: Optional[float] = None
    reconnect_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "node_id": self.node_id,
            "transport": self.transport,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "last_seen": (
                self.last_seen.isoformat() if self.last_seen else None
            ),
            "latency_ms": self.latency_ms,
            "reconnect_count": self.reconnect_count,
        }


@dataclass
class NetworkStatus:
    """Overall status of the network from this node's perspective."""
    
    self_node_id: str
    topology: str
    total_nodes: int
    required_peers: int
    connected_peers: int
    online_nodes: int
    missing_connections: list[str] = field(default_factory=list)
    
    @property
    def is_fully_connected(self) -> bool:
        """Check if all required peers are connected."""
        return self.connected_peers >= self.required_peers
    
    @property
    def health_percentage(self) -> float:
        """Network health as percentage (0-100)."""
        if self.required_peers == 0:
            return 100.0
        return (self.connected_peers / self.required_peers) * 100.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "self_node_id": self.self_node_id,
            "topology": self.topology,
            "total_nodes": self.total_nodes,
            "required_peers": self.required_peers,
            "connected_peers": self.connected_peers,
            "online_nodes": self.online_nodes,
            "missing_connections": self.missing_connections,
            "is_fully_connected": self.is_fully_connected,
            "health_percentage": round(self.health_percentage, 2),
        }