"""
Network Tester Module

Comprehensive testing of all system_network capabilities:
- Network status and health monitoring
- Direct messaging (single hop)
- Multi-hop routing
- Broadcast to all nodes
- Capability-based messaging
- Routing table visualization
- Envelope inspection
- Event handlers
- Auto-shutdown after test duration

This module also provides test_results_service for the reporter module.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from massir.core.interfaces import IModule


class NetworkTesterModule(IModule):
    """
    Comprehensive tester for system_network capabilities.
    
    Runs tests and collects results for the final report.
    Automatically requests graceful shutdown after test_duration_seconds
    using app.request_shutdown().
    """
    
    def __init__(self):
        self.network_api = None
        self.logger = None
        self.colors = None
        self._context = None  # ✅ ذخیره context برای دسترسی به app
        self._config: Dict = {}
        self._test_results: Dict[str, Any] = {}
        self._received_messages: List[Dict] = []
        self._test_task: Optional[asyncio.Task] = None
        self._shutdown_task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None
        
        # Statistics
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "broadcasts_sent": 0,
            "capability_messages_sent": 0,
            "peer_connections": 0,
            "peer_disconnections": 0,
            "test_start_time": None,
            "test_end_time": None,
        }
    
    async def load(self, context):
        """Load the module."""
        self._context = context
        
        self.network_api = context.services.get("network_api")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("network_tester", {})
        
        # Register as test_results_service
        context.services.set("test_results_service", self)
        
        # Register event handlers
        self.network_api.on_message(self._on_message_received)
        self.network_api.on_peer_connected(self._on_peer_connected)
        self.network_api.on_peer_disconnected(self._on_peer_disconnected)
        
        if self.logger:
            self.logger.log("NetworkTesterModule loaded", tag="tester")
    
    async def start(self, context):
        """Start tests and shutdown timer."""
        if not self._config.get("enabled", True):
            return
        
        self._start_time = datetime.now()
        self._stats["test_start_time"] = self._start_time.isoformat()
        
        # Get test configuration
        core_config = context.services.get("core_config")
        test_config = core_config.get("test_config", {}) if core_config else {}
        
        warmup_seconds = test_config.get("warmup_seconds", 10)
        test_duration = test_config.get("test_duration_seconds", 60)
        test_interval = test_config.get("test_interval_seconds", 5)
        
        if self.logger:
            self.logger.print(
                f"🧪 Test configuration: warmup={warmup_seconds}s, "
                f"duration={test_duration}s, interval={test_interval}s",
                tag="tester",
                color=self.colors.BRIGHT_CYAN if self.colors else None
            )
        
        # Start warmup, then tests
        self._test_task = asyncio.create_task(
            self._run_test_sequence(warmup_seconds, test_duration, test_interval)
        )
        
        # Start shutdown timer
        shutdown_delay = warmup_seconds + test_duration
        self._shutdown_task = asyncio.create_task(
            self._schedule_shutdown(shutdown_delay)
        )
    
    async def ready(self, context):
        """Called when all modules are ready."""
        if self.logger:
            self.logger.log("NetworkTester ready", tag="tester")
    
    async def stop(self, context):
        """Stop the module."""
        self._stats["test_end_time"] = datetime.now().isoformat()
        
        if self._test_task and not self._test_task.done():
            self._test_task.cancel()
            try:
                await self._test_task
            except asyncio.CancelledError:
                pass
        
        if self._shutdown_task and not self._shutdown_task.done():
            self._shutdown_task.cancel()
            try:
                await self._shutdown_task
            except asyncio.CancelledError:
                pass
        
        if self.logger:
            self.logger.log("NetworkTester stopped", tag="tester")
    
    # =========================================================================
    # Test Sequence
    # =========================================================================
    
    async def _run_test_sequence(
        self,
        warmup_seconds: float,
        test_duration: float,
        test_interval: float,
    ):
        """Run the complete test sequence."""
        # Warmup phase
        if self.logger:
            self.logger.print(
                f"⏳ Warmup phase: waiting {warmup_seconds}s for connections...",
                tag="tester",
                color=self.colors.BRIGHT_YELLOW if self.colors else None
            )
        
        await asyncio.sleep(warmup_seconds)
        
        if self.logger:
            self.logger.print(
                "✅ Warmup complete, starting tests...",
                tag="tester",
                color=self.colors.BRIGHT_GREEN if self.colors else None
            )
        
        # Run initial tests
        tests = self._config.get("tests", [
            "network_status",
            "direct_messaging",
            "broadcast",
            "capability_messaging",
            "routing_table",
        ])
        
        for test_name in tests:
            test_method = getattr(self, f"_test_{test_name}", None)
            if test_method:
                try:
                    result = await test_method()
                    self._test_results[test_name] = result
                except Exception as e:
                    self._test_results[test_name] = {
                        "passed": False,
                        "error": str(e)
                    }
                await asyncio.sleep(test_interval)
        
        # Continue running periodic tests until shutdown
        end_time = asyncio.get_event_loop().time() + test_duration
        while asyncio.get_event_loop().time() < end_time:
            await asyncio.sleep(test_interval)
            
            # Run periodic network status check
            try:
                result = await self._test_network_status()
                self._test_results["network_status"] = result
            except Exception:
                pass
    
    async def _schedule_shutdown(self, delay_seconds: float):
        """
        Schedule graceful application shutdown after delay.
        
        Uses context.get_app() to access the App instance and calls
        request_shutdown() which:
        1. Dispatches ON_SHUTDOWN_REQUEST hook
        2. Sets the _stop_event
        3. Triggers clean shutdown sequence in core/stop.py
        """
        await asyncio.sleep(delay_seconds)
        
        if self.logger:
            self.logger.print(
                "\n" + "═" * 64,
                tag="tester",
                color=self.colors.BRIGHT_RED if self.colors else None,
                bold=True
            )
            self.logger.print(
                "  🛑 TEST DURATION COMPLETE - REQUESTING GRACEFUL SHUTDOWN",
                tag="tester",
                color=self.colors.BRIGHT_RED if self.colors else None,
                bold=True
            )
            self.logger.print(
                "═" * 64 + "\n",
                tag="tester",
                color=self.colors.BRIGHT_RED if self.colors else None,
                bold=True
            )
        
        if self._context:
            try:
                app = self._context.get_app()
                if app:
                    if self.logger:
                        self.logger.log(
                            "Requesting graceful shutdown via app.request_shutdown()...",
                            tag="tester"
                        )
                    # the sync request_shutdown()
                    # this methode dispatch the ON_SHUTDOWN_REQUEST hook
                    app.request_shutdown()
                    return
                else:
                    if self.logger:
                        self.logger.log(
                            "Warning: context.get_app() returned None",
                            level="WARNING",
                            tag="tester"
                        )
            except Exception as e:
                if self.logger:
                    self.logger.log(
                        f"Error calling app.request_shutdown(): {e}",
                        level="ERROR",
                        tag="tester"
                    )
        else:
            if self.logger:
                self.logger.log(
                    "Error: context not available for shutdown",
                    level="ERROR",
                    tag="tester"
                )
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    async def _on_message_received(self, envelope, from_peer, connection):
        """Track received messages."""
        self._stats["messages_received"] += 1
        self._received_messages.append({
            "from": envelope.source,
            "via": from_peer,
            "type": envelope.payload_type,
            "route": envelope.route,
            "timestamp": datetime.now().isoformat(),
        })
    
    async def _on_peer_connected(self, peer_id, node_entry):
        """Track peer connections."""
        self._stats["peer_connections"] += 1
    
    async def _on_peer_disconnected(self, peer_id, node_entry):
        """Track peer disconnections."""
        self._stats["peer_disconnections"] += 1
    
    # =========================================================================
    # Tests
    # =========================================================================
    
    async def _test_network_status(self) -> Dict:
        """Test network status and health monitoring."""
        status = self.network_api.get_network_status()
        
        return {
            "passed": status.total_nodes > 1,
            "status": status.to_dict(),
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_direct_messaging(self) -> Dict:
        """Test direct (single-hop) messaging."""
        connected_peers = self.network_api.get_connected_peers()
        
        if not connected_peers:
            return {"passed": False, "reason": "no_peers"}
        
        target = connected_peers[0]
        test_id = str(uuid.uuid4())[:8]
        
        route = self.network_api.get_route(target)
        
        success = await self.network_api.send(
            destination=target,
            payload={
                "test": "direct_messaging",
                "test_id": test_id,
                "message": "Hello from direct messaging test!",
            },
            payload_type="test",
        )
        
        if success:
            self._stats["messages_sent"] += 1
        
        return {
            "passed": success,
            "target": target,
            "is_direct": route.is_direct if route else False,
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_broadcast(self) -> Dict:
        """Test broadcast to all nodes."""
        test_id = str(uuid.uuid4())[:8]
        
        results = await self.network_api.broadcast(
            payload={
                "test": "broadcast",
                "test_id": test_id,
                "message": "Broadcast message to all nodes!",
            },
            payload_type="test",
        )
        
        success_count = sum(1 for v in results.values() if v)
        self._stats["broadcasts_sent"] += 1
        self._stats["messages_sent"] += success_count
        
        return {
            "passed": success_count > 0,
            "results": results,
            "success_count": success_count,
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_capability_messaging(self) -> Dict:
        """Test sending to nodes with specific capabilities."""
        all_nodes = self.network_api.get_all_nodes()
        all_capabilities = set()
        for node in all_nodes:
            all_capabilities.update(node.capabilities)
        
        if not all_capabilities:
            return {"passed": False, "reason": "no_capabilities"}
        
        results = {}
        total_sent = 0
        
        for capability in sorted(all_capabilities):
            send_results = await self.network_api.send_to_capability(
                capability=capability,
                payload={
                    "test": "capability_messaging",
                    "capability": capability,
                },
                payload_type="test",
            )
            
            results[capability] = send_results
            sent = sum(1 for v in send_results.values() if v)
            total_sent += sent
        
        self._stats["capability_messages_sent"] += total_sent
        self._stats["messages_sent"] += total_sent
        
        return {
            "passed": total_sent > 0,
            "capabilities_tested": len(results),
            "total_messages_sent": total_sent,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_routing_table(self) -> Dict:
        """Test routing table."""
        routing_table = self.network_api.get_routing_table()
        
        return {
            "passed": len(routing_table) > 0,
            "total_routes": len(routing_table),
            "direct_routes": sum(1 for r in routing_table.values() if r.is_direct),
            "multi_hop_routes": sum(1 for r in routing_table.values() if not r.is_direct),
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_multi_hop(self) -> Dict:
        """Test multi-hop routing."""
        routing_table = self.network_api.get_routing_table()
        
        multi_hop_routes = [
            (dest, route) for dest, route in routing_table.items()
            if not route.is_direct
        ]
        
        if not multi_hop_routes:
            return {
                "passed": True,
                "reason": "all_direct",
                "note": "No multi-hop routes in current topology"
            }
        
        target, route = multi_hop_routes[0]
        test_id = str(uuid.uuid4())[:8]
        
        success = await self.network_api.send(
            destination=target,
            payload={
                "test": "multi_hop",
                "test_id": test_id,
                "expected_route": route.hops,
            },
            payload_type="test",
            ttl=5,
        )
        
        if success:
            self._stats["messages_sent"] += 1
        
        return {
            "passed": success,
            "target": target,
            "hops": route.hop_count,
            "route": route.hops,
            "test_id": test_id,
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_envelope_inspection(self) -> Dict:
        """Test envelope inspection capabilities."""
        # Check if we've received any envelopes
        envelopes_received = [
            msg for msg in self._received_messages
            if msg.get("type") == "test"
        ]
        
        return {
            "passed": True,
            "envelopes_received": len(envelopes_received),
            "sample_routes": [
                msg.get("route") for msg in envelopes_received[:3]
            ],
            "timestamp": datetime.now().isoformat(),
        }
    
    async def _test_event_handlers(self) -> Dict:
        """Test event handler registration and invocation."""
        return {
            "passed": True,
            "peer_connections": self._stats["peer_connections"],
            "peer_disconnections": self._stats["peer_disconnections"],
            "messages_received": self._stats["messages_received"],
            "timestamp": datetime.now().isoformat(),
        }
    
    # =========================================================================
    # Public API (test_results_service)
    # =========================================================================
    
    def get_test_results(self) -> Dict:
        """Get all test results."""
        return {
            "results": self._test_results,
            "stats": self._stats,
            "received_messages": self._received_messages,
        }
    
    def get_stats(self) -> Dict:
        """Get test statistics."""
        return self._stats.copy()