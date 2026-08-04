"""
System Network Core Module

High-level network management providing:
- Transport-agnostic messaging (works with socket and websocket)
- Topology management (mesh, star, ring, tree, line, custom)
- Node registry (static configuration, dynamic discovery ready)
- Multi-hop routing with TTL protection
- Message envelope with routing metadata
- Connection lifecycle management
"""

from .network_api import NetworkAPI
from .topology import TopologyManager, TopologyType
from .registry import NodeRegistry, NodeEntry
from .router import Router, Route
from .connection_manager import ConnectionManager
from .envelope import MessageEnvelope
from .types import NetworkStatus, PeerStatus
from .exceptions import (
    NetworkError,
    NetworkConfigError,
    RoutingError,
    NodeNotFoundError,
    NoRouteError,
    TransportNotAvailableError,
    EnvelopeExpiredError,
    TopologyError,
)

__all__ = [
    "NetworkAPI",
    "TopologyManager",
    "TopologyType",
    "NodeRegistry",
    "NodeEntry",
    "Router",
    "Route",
    "ConnectionManager",
    "MessageEnvelope",
    "NetworkStatus",
    "PeerStatus",
    "NetworkError",
    "NetworkConfigError",
    "RoutingError",
    "NodeNotFoundError",
    "NoRouteError",
    "TransportNotAvailableError",
    "EnvelopeExpiredError",
    "TopologyError",
]