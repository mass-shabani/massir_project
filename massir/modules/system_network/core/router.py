"""
Router for computing paths between nodes.

Uses BFS on the topology graph to find shortest paths, supporting
multi-hop routing for topologies like star, ring, tree, and line.
"""

from collections import deque
from dataclasses import dataclass
from typing import Optional

from .topology import TopologyManager
from .registry import NodeRegistry
from .exceptions import NoRouteError


@dataclass
class Route:
    """
    A computed route from source to destination.
    
    Attributes:
        source: Originating node
        destination: Final target node
        hops: Ordered list of nodes in the path (includes source & destination)
        next_hop: The immediate next node to forward to
        hop_count: Number of intermediate hops (excluding source)
    """
    
    source: str
    destination: str
    hops: list[str]
    next_hop: str
    hop_count: int = 0
    
    @property
    def is_direct(self) -> bool:
        """Check if this is a direct (single-hop) route."""
        return len(self.hops) == 2
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "destination": self.destination,
            "hops": self.hops,
            "next_hop": self.next_hop,
            "hop_count": self.hop_count,
            "is_direct": self.is_direct,
        }


class Router:
    """
    Computes routes between nodes based on network topology.
    
    Uses BFS (Breadth-First Search) to find shortest paths on the
    topology graph. Supports both direct and multi-hop routing.
    """
    
    def __init__(
        self,
        self_node_id: str,
        topology: TopologyManager,
        registry: NodeRegistry,
    ):
        self._self_node_id = self_node_id
        self._topology = topology
        self._registry = registry
    
    def _build_adjacency(self) -> dict[str, set[str]]:
        """
        Build adjacency graph from topology.
        
        The graph is bidirectional: if A->B is an edge, B->A is also added
        (since WebSocket/Socket connections are bidirectional).
        """
        all_nodes = self._registry.get_all_ids()
        adjacency: dict[str, set[str]] = {node: set() for node in all_nodes}
        
        # For each node, compute its required connections
        for node in all_nodes:
            # Save and restore self_node_id to simulate being each node
            original_self = self._topology.self_node_id
            try:
                # Temporarily change topology's view
                self._topology._self_node_id = node
                connections = self._topology.get_required_connections(all_nodes)
                for target in connections:
                    adjacency[node].add(target)
                    adjacency[target].add(node)  # Bidirectional
            finally:
                self._topology._self_node_id = original_self
        
        return adjacency
    
    def find_route(self, destination: str) -> Optional[Route]:
        """
        Find the shortest route to a destination using BFS.
        
        Args:
            destination: Target node ID
        
        Returns:
            Route object, or None if no route exists
        """
        if destination == self._self_node_id:
            return Route(
                source=self._self_node_id,
                destination=destination,
                hops=[self._self_node_id],
                next_hop=self._self_node_id,
                hop_count=0,
            )
        
        # Check destination exists
        if not self._registry.get(destination):
            return None
        
        # Build adjacency graph
        adjacency = self._build_adjacency()
        
        # BFS
        queue: deque[tuple[str, list[str]]] = deque([
            (self._self_node_id, [self._self_node_id])
        ])
        visited = {self._self_node_id}
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in adjacency.get(current, set()):
                if neighbor in visited:
                    continue
                
                new_path = path + [neighbor]
                
                if neighbor == destination:
                    return Route(
                        source=self._self_node_id,
                        destination=destination,
                        hops=new_path,
                        next_hop=new_path[1] if len(new_path) > 1 else destination,
                        hop_count=len(new_path) - 1,
                    )
                
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        
        return None
    
    def find_route_or_raise(self, destination: str) -> Route:
        """Find route or raise NoRouteError if not found."""
        route = self.find_route(destination)
        if route is None:
            raise NoRouteError(self._self_node_id, destination)
        return route
    
    def get_routing_table(self) -> dict[str, Route]:
        """
        Compute the full routing table (routes to all nodes).
        
        Returns:
            Dictionary mapping node_id to Route
        """
        routes = {}
        for node_id in self._registry.get_all_ids():
            if node_id == self._self_node_id:
                continue
            route = self.find_route(node_id)
            if route:
                routes[node_id] = route
        return routes
    
    def get_stats(self) -> dict:
        """Get router statistics."""
        table = self.get_routing_table()
        direct = sum(1 for r in table.values() if r.is_direct)
        multi_hop = len(table) - direct
        
        return {
            "total_routes": len(table),
            "direct_routes": direct,
            "multi_hop_routes": multi_hop,
            "topology": self._topology.topology_type.value,
        }