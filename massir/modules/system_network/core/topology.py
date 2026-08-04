"""
Topology management for network structure.

Defines the logical arrangement of nodes and determines which
connections each node must maintain.
"""

from enum import Enum
from typing import Optional

from .exceptions import TopologyError


class TopologyType(str, Enum):
    """Supported network topology types."""
    
    FULL_MESH = "mesh"       # Every node connects to every other node
    STAR = "star"            # All nodes connect to a central hub
    RING = "ring"            # Nodes form a circular chain
    TREE = "tree"            # Hierarchical parent-child structure
    LINE = "line"            # Linear chain of nodes
    CUSTOM = "custom"        # User-defined edge list


class TopologyManager:
    """
    Manages network topology and determines required connections.
    
    Given a set of nodes and a topology type, computes which peers
    each node should maintain direct connections to.
    """
    
    def __init__(self, self_node_id: str):
        self._self_node_id = self_node_id
        self._topology_type = TopologyType.FULL_MESH
        self._hub_node: Optional[str] = None
        self._parent_node: Optional[str] = None
        self._custom_edges: list[tuple[str, str]] = []
    
    @property
    def topology_type(self) -> TopologyType:
        """Get the current topology type."""
        return self._topology_type
    
    @property
    def self_node_id(self) -> str:
        """Get this node's ID."""
        return self._self_node_id
    
    def set_topology(
        self,
        topology: str | TopologyType,
        hub_node: Optional[str] = None,
        parent_node: Optional[str] = None,
        custom_edges: Optional[list[tuple[str, str]]] = None,
    ) -> None:
        """
        Set the network topology.
        
        Args:
            topology: Topology type (string or enum)
            hub_node: Required for STAR topology
            parent_node: Required for TREE topology (this node's parent)
            custom_edges: Required for CUSTOM topology (list of (src, dst))
        
        Raises:
            TopologyError: If configuration is invalid
        """
        if isinstance(topology, str):
            try:
                topology = TopologyType(topology.lower())
            except ValueError:
                valid = [t.value for t in TopologyType]
                raise TopologyError(
                    f"Invalid topology '{topology}'. Valid: {valid}"
                )
        
        self._topology_type = topology
        self._hub_node = hub_node
        self._parent_node = parent_node
        self._custom_edges = custom_edges or []
        
        # Validate configuration
        if topology == TopologyType.STAR and not hub_node:
            raise TopologyError("STAR topology requires hub_node")
        
        if topology == TopologyType.TREE and not parent_node:
            # Root node has no parent - allowed
            pass
        
        if topology == TopologyType.CUSTOM and not custom_edges:
            raise TopologyError("CUSTOM topology requires custom_edges")
    
    def get_required_connections(self, all_nodes: list[str]) -> list[str]:
        """
        Compute which nodes this node must connect to based on topology.
        
        Args:
            all_nodes: List of all node IDs in the network
        
        Returns:
            List of node IDs this node must connect to
        
        Raises:
            TopologyError: If topology is invalid for the node set
        """
        if not all_nodes:
            return []
        
        if self._self_node_id not in all_nodes:
            raise TopologyError(
                f"Self node '{self._self_node_id}' not in all_nodes"
            )
        
        others = [n for n in all_nodes if n != self._self_node_id]
        
        if self._topology_type == TopologyType.FULL_MESH:
            return self._compute_mesh(others)
        elif self._topology_type == TopologyType.STAR:
            return self._compute_star(others)
        elif self._topology_type == TopologyType.RING:
            return self._compute_ring(all_nodes)
        elif self._topology_type == TopologyType.LINE:
            return self._compute_line(all_nodes)
        elif self._topology_type == TopologyType.TREE:
            return self._compute_tree()
        elif self._topology_type == TopologyType.CUSTOM:
            return self._compute_custom()
        
        return []
    
    def _compute_mesh(self, others: list[str]) -> list[str]:
        """Mesh: connect to all other nodes."""
        return others
    
    def _compute_star(self, others: list[str]) -> list[str]:
        """Star: hub connects to all, others connect only to hub."""
        if self._self_node_id == self._hub_node:
            return others
        return [self._hub_node] if self._hub_node else []
    
    def _compute_ring(self, all_nodes: list[str]) -> list[str]:
        """Ring: connect to previous and next nodes in sorted order."""
        if len(all_nodes) < 2:
            return []
        
        sorted_nodes = sorted(all_nodes)
        idx = sorted_nodes.index(self._self_node_id)
        n = len(sorted_nodes)
        
        prev_node = sorted_nodes[(idx - 1) % n]
        next_node = sorted_nodes[(idx + 1) % n]
        
        if len(all_nodes) == 2:
            return [prev_node]  # Only one neighbor
        
        return [prev_node, next_node]
    
    def _compute_line(self, all_nodes: list[str]) -> list[str]:
        """Line: connect only to immediate neighbors in sorted order."""
        if len(all_nodes) < 2:
            return []
        
        sorted_nodes = sorted(all_nodes)
        idx = sorted_nodes.index(self._self_node_id)
        
        connections = []
        if idx > 0:
            connections.append(sorted_nodes[idx - 1])
        if idx < len(sorted_nodes) - 1:
            connections.append(sorted_nodes[idx + 1])
        
        return connections
    
    def _compute_tree(self) -> list[str]:
        """Tree: connect only to parent (children connect to us)."""
        if self._parent_node:
            return [self._parent_node]
        return []  # Root node - waits for children to connect
    
    def _compute_custom(self) -> list[str]:
        """Custom: use provided edge list."""
        targets = []
        for src, dst in self._custom_edges:
            if src == self._self_node_id and dst not in targets:
                targets.append(dst)
        return targets
    
    def get_all_edges(self, all_nodes: list[str]) -> list[tuple[str, str]]:
        """
        Get all edges in the network for visualization/analysis.
        
        Returns:
            List of (source, destination) tuples
        """
        edges = []
        for node in all_nodes:
            # Temporarily pretend to be this node to compute its edges
            original_self = self._self_node_id
            try:
                self._self_node_id = node
                connections = self.get_required_connections(all_nodes)
                for target in connections:
                    edges.append((node, target))
            finally:
                self._self_node_id = original_self
        return edges
    
    def get_info(self) -> dict:
        """Get topology information."""
        return {
            "type": self._topology_type.value,
            "self_node_id": self._self_node_id,
            "hub_node": self._hub_node,
            "parent_node": self._parent_node,
            "custom_edges_count": len(self._custom_edges),
        }