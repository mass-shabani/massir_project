"""
Message Envelope for routing metadata.

Wraps application payloads with routing information needed for
multi-hop delivery across the network.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .exceptions import EnvelopeExpiredError


@dataclass
class MessageEnvelope:
    """
    Message envelope with routing metadata.
    
    Wraps application-level payloads with routing information needed
    for multi-hop delivery. Each hop decrements TTL to prevent infinite
    forwarding loops.
    
    Structure:
        - source: Originating node
        - destination: Final target node
        - route: Ordered list of hops from source to destination
        - current_hop: Index of current position in route
        - ttl: Remaining hops allowed (decrements on forward)
        - payload: Actual application data
    """
    
    # Routing metadata
    source: str
    destination: str
    route: list[str]
    current_hop: int = 0
    ttl: int = 10
    
    # Message identification
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Application payload
    payload_type: str = "data"
    payload: Any = None
    
    def should_forward(self) -> bool:
        """
        Check if this envelope needs to be forwarded to the next hop.
        
        Returns True if current hop is not the final destination.
        """
        return self.current_hop < len(self.route) - 1
    
    def next_hop(self) -> Optional[str]:
        """
        Get the next node to forward this envelope to.
        
        Returns None if already at destination.
        """
        next_idx = self.current_hop + 1
        if next_idx < len(self.route):
            return self.route[next_idx]
        return None
    
    def advance_hop(self) -> None:
        """
        Advance to the next hop in the route.
        
        Raises:
            EnvelopeExpiredError: If TTL has expired
        """
        if self.ttl <= 0:
            raise EnvelopeExpiredError(self.message_id, self.ttl)
        
        self.current_hop += 1
        self.ttl -= 1
    
    def is_expired(self) -> bool:
        """Check if TTL has expired."""
        return self.ttl <= 0
    
    def is_for_me(self, my_node_id: str) -> bool:
        """Check if this envelope is addressed to the given node."""
        return self.destination == my_node_id
    
    def is_at_destination(self) -> bool:
        """Check if envelope has reached its destination."""
        if not self.route:
            return False
        return self.current_hop >= len(self.route) - 1
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert envelope to dictionary for transport.
        
        This format is sent over the wire and must be compatible with
        both network_socket and network_websocket.
        """
        return {
            "__envelope__": True,
            "source": self.source,
            "destination": self.destination,
            "route": self.route,
            "current_hop": self.current_hop,
            "ttl": self.ttl,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "payload_type": self.payload_type,
            "payload": self.payload,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageEnvelope":
        """Reconstruct envelope from dictionary."""
        if not isinstance(data, dict) or not data.get("__envelope__"):
            raise ValueError("Invalid envelope format")
        
        return cls(
            source=data["source"],
            destination=data["destination"],
            route=data["route"],
            current_hop=data.get("current_hop", 0),
            ttl=data.get("ttl", 10),
            message_id=data.get("message_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            trace_id=data.get("trace_id", str(uuid.uuid4())),
            payload_type=data.get("payload_type", "data"),
            payload=data.get("payload"),
        )
    
    @classmethod
    def is_envelope(cls, data: Any) -> bool:
        """Check if data is an envelope dictionary."""
        return (
            isinstance(data, dict)
            and data.get("__envelope__") is True
        )
    
    def __repr__(self) -> str:
        return (
            f"MessageEnvelope(id={self.message_id[:8]}..., "
            f"{self.source}->{self.destination}, "
            f"hop={self.current_hop}/{len(self.route)-1}, "
            f"ttl={self.ttl})"
        )