"""
Exception hierarchy for system_network module.
"""


class NetworkError(Exception):
    """Base exception for all network-related errors."""
    pass


class NetworkConfigError(NetworkError):
    """Raised when network configuration is invalid."""
    pass


class RoutingError(NetworkError):
    """Raised when routing operations fail."""
    pass


class NodeNotFoundError(RoutingError):
    """Raised when a target node is not found in the registry."""
    
    def __init__(self, node_id: str):
        super().__init__(f"Node '{node_id}' not found in registry")
        self.node_id = node_id


class NoRouteError(RoutingError):
    """Raised when no route exists to the destination."""
    
    def __init__(self, source: str, destination: str):
        super().__init__(
            f"No route from '{source}' to '{destination}'"
        )
        self.source = source
        self.destination = destination


class TransportNotAvailableError(NetworkError):
    """Raised when a required transport adapter is not available."""
    
    def __init__(self, transport: str):
        super().__init__(f"Transport '{transport}' is not available")
        self.transport = transport


class EnvelopeExpiredError(NetworkError):
    """Raised when a message envelope's TTL has expired."""
    
    def __init__(self, envelope_id: str, ttl: int):
        super().__init__(
            f"Envelope '{envelope_id}' expired after {ttl} hops"
        )
        self.envelope_id = envelope_id
        self.ttl = ttl


class TopologyError(NetworkError):
    """Raised when topology configuration is invalid."""
    pass