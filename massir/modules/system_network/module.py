"""
System Network Module for Massir Framework

Provides high-level network management with transport-agnostic messaging,
topology management, routing, and node registry.

This module unifies network_socket and network_websocket transports under
a single network_api interface, allowing application modules to work with
distributed networks without knowing the underlying transport.
"""

import json
from pathlib import Path
from typing import Optional, Any

from massir.core.interfaces import IModule

from .core.network_api import NetworkAPI
from .core.registry import NodeRegistry
from .core.topology import TopologyManager, TopologyType
from .core.router import Router
from .core.connection_manager import ConnectionManager
from .core.adapters import SocketAdapter, WebSocketAdapter
from .core.exceptions import NetworkConfigError


class SystemNetworkModule(IModule):
    """
    System Network Module.
    
    Provides network_api service for:
    - Transport-agnostic messaging (socket or websocket)
    - Topology management (mesh, star, ring, tree, line, custom)
    - Node registry (static, dynamic-ready)
    - Multi-hop routing with TTL protection
    - Connection lifecycle management
    
    Optional dependencies:
    - socket_api: Enables "socket" transport
    - websocket_api: Enables "websocket" transport
    
    At least one transport must be available.
    """
    
    name = "system_network"
    provides = ["network_api"]
    
    def __init__(self):
        self._api: Optional[NetworkAPI] = None
        self._logger: Any = None
        self._config: dict = {}
        self._module_dir: Path = Path(__file__).parent
        
        # Core components
        self._registry: Optional[NodeRegistry] = None
        self._topology: Optional[TopologyManager] = None
        self._router: Optional[Router] = None
        self._connection_manager: Optional[ConnectionManager] = None
    
    async def load(self, context):
        """Load the network module and initialize components."""
        self._logger = context.services.get("core_logger")
        core_config = context.services.get("core_config")
        
        # Load configuration
        self._config = self._load_default_config()
        if core_config:
            user_config = core_config.get("system_network", {})
            if isinstance(user_config, dict):
                self._config = self._merge_config(self._config, user_config)
        
        if hasattr(context, 'app_dir'):
            self._resolve_path_placeholders(context.app_dir)
        
        # Validate configuration
        self._validate_config()
        
        # Initialize core components
        self_node_conf = self._config.get("self_node", {})
        self_node_id = self_node_conf.get("node_id", "node1")
        
        # 1. Registry
        self._registry = NodeRegistry(mode="static")
        self._registry.set_self_node(
            node_id=self_node_id,
            metadata=self_node_conf.get("metadata", {}),
            capabilities=self_node_conf.get("capabilities", []),
        )
        
        # Load nodes from config
        nodes_conf = self._config.get("nodes", [])
        loaded = self._registry.load_from_config(nodes_conf)
        if self._logger:
            self._logger.log(
                f"NodeRegistry loaded {loaded} remote node(s), self='{self_node_id}'",
                tag="network"
            )
        
        # 2. Topology
        self._topology = TopologyManager(self_node_id)
        topology_conf = self._config.get("topology", {})
        self._topology.set_topology(
            topology=topology_conf.get("type", "mesh"),
            hub_node=topology_conf.get("hub_node"),
            parent_node=topology_conf.get("parent_node"),
            custom_edges=topology_conf.get("custom_edges"),
        )
        if self._logger:
            self._logger.log(
                f"Topology set to: {self._topology.topology_type.value}",
                tag="network"
            )
        
        # 3. Router
        self._router = Router(
            self_node_id=self_node_id,
            topology=self._topology,
            registry=self._registry,
        )
        
        # 4. Connection Manager
        self._connection_manager = ConnectionManager(
            self_node_id=self_node_id,
            registry=self._registry,
            topology=self._topology,
            logger=self._logger,
        )
        
        # Register available transport adapters
        transports_available = []
        
        socket_api = context.services.get("socket_api")
        if socket_api:
            socket_adapter = SocketAdapter(socket_api, self._logger)
            self._connection_manager.register_adapter("socket", socket_adapter)
            transports_available.append("socket")
        
        websocket_api = context.services.get("websocket_api")
        if websocket_api:
            ws_adapter = WebSocketAdapter(websocket_api, self._logger)
            self._connection_manager.register_adapter("websocket", ws_adapter)
            transports_available.append("websocket")
        
        if not transports_available:
            if self._logger:
                self._logger.log(
                    "Warning: No transport adapters available. "
                    "Enable network_socket or network_websocket module.",
                    level="WARNING",
                    tag="network"
                )
        
        # 5. Network API
        self._api = NetworkAPI(
            self_node_id=self_node_id,
            registry=self._registry,
            topology=self._topology,
            router=self._router,
            connection_manager=self._connection_manager,
            config=self._config,
            logger=self._logger,
        )
        
        # Register service
        context.services.set("network_api", self._api)
        
        if self._logger:
            self._logger.log(
                f"SystemNetworkModule loaded - "
                f"node='{self_node_id}', "
                f"transports={transports_available}, "
                f"topology={self._topology.topology_type.value}",
                tag="network"
            )
    
    async def start(self, context):
        """Start the network module."""
        # Start all adapters
        for transport in self._connection_manager.get_available_transports():
            try:
                adapter = self._connection_manager.get_adapter(transport)
                await adapter.start()
            except Exception as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to start adapter '{transport}': {e}",
                        level="ERROR",
                        tag="network"
                    )
        
        # Auto-connect if configured
        conn_conf = self._config.get("connection", {})
        if conn_conf.get("auto_connect_on_start", True):
            results = await self._connection_manager.connect_to_required_peers()
            success_count = sum(1 for v in results.values() if v)
            if self._logger:
                self._logger.log(
                    f"Auto-connect: {success_count}/{len(results)} peers connected",
                    tag="network"
                )
        
        if self._logger:
            self._logger.log("SystemNetworkModule started", tag="network")
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self._logger and self._api:
            status = self._api.get_network_status()
            self._logger.log(
                f"SystemNetworkModule ready - "
                f"{status.connected_peers}/{status.required_peers} peers connected, "
                f"health={status.health_percentage:.1f}%",
                tag="network"
            )
    
    async def stop(self, context):
        """Stop the network module and disconnect all peers."""
        if self._connection_manager:
            await self._connection_manager.disconnect_all()
            
            for transport in self._connection_manager.get_available_transports():
                try:
                    adapter = self._connection_manager.get_adapter(transport)
                    await adapter.stop()
                except Exception:
                    pass
        
        if self._logger:
            self._logger.log("SystemNetworkModule stopped", tag="network")
        
        self._api = None
    
    # =========================================================================
    # Configuration Helpers
    # =========================================================================
    
    def _load_default_config(self) -> dict:
        """Load default configuration from config.json."""
        config_path = self._module_dir / "config.json"
        
        default_config = {
            "self_node": {
                "node_id": "node1",
                "metadata": {},
                "capabilities": [],
            },
            "topology": {
                "type": "mesh",
                "hub_node": None,
                "parent_node": None,
                "custom_edges": [],
            },
            "nodes": [],
            "routing": {
                "default_ttl": 10,
                "enable_multi_hop": True,
                "route_cache_ttl_seconds": 60.0,
            },
            "connection": {
                "auto_connect_on_start": True,
                "auto_reconnect": True,
                "reconnect_delay_seconds": 5.0,
                "health_check_interval_seconds": 30.0,
            },
            "message": {
                "include_trace_id": True,
                "include_timestamp": True,
                "max_payload_size_bytes": 16 * 1024 * 1024,
            },
            "logging": {
                "tag": "network",
                "log_routing": False,
                "log_envelopes": False,
                "log_topology_changes": True,
            },
        }
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    file_config = json.load(f)
                    if isinstance(file_config, dict):
                        default_config = self._merge_config(
                            default_config, file_config
                        )
            except (json.JSONDecodeError, IOError) as e:
                if self._logger:
                    self._logger.log(
                        f"Failed to load config.json: {e}",
                        level="WARNING",
                        tag="network"
                    )
        
        return default_config
    
    def _merge_config(self, base: dict, override: dict) -> dict:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def _resolve_path_placeholders(self, app_dir) -> None:
        """Resolve {app_dir} placeholders in configuration."""
        app_dir_str = str(app_dir)
        
        def resolve(obj):
            if isinstance(obj, str):
                return obj.replace("{app_dir}", app_dir_str)
            elif isinstance(obj, dict):
                return {k: resolve(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [resolve(item) for item in obj]
            return obj
        
        self._config = resolve(self._config)
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        self_node = self._config.get("self_node", {})
        if not self_node.get("node_id"):
            raise NetworkConfigError("self_node.node_id is required")
        
        topology = self._config.get("topology", {})
        valid_topologies = [t.value for t in TopologyType]
        if topology.get("type") not in valid_topologies:
            raise NetworkConfigError(
                f"topology.type must be one of {valid_topologies}"
            )
        
        routing = self._config.get("routing", {})
        ttl = routing.get("default_ttl", 10)
        if not isinstance(ttl, int) or ttl < 1:
            raise NetworkConfigError(
                f"routing.default_ttl must be positive integer, got {ttl}"
            )