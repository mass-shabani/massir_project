"""
Message Demo Module

Demonstrates Message Mode operations:
- Periodic broadcast to all peers
- Message handling and routing
- Request/reply patterns

NOTE: Uses logger.print for demo output (similar to ssl_example).
      No direct imports from network_socket - uses factory methods.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from massir.core.interfaces import IModule


class MessageDemoModule(IModule):
    """
    Demonstrates Message Mode features in the distributed network.
    """
    
    name = "message_demo"
    
    def __init__(self):
        self.node_service = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
        self._broadcast_task = None
        self._message_counter = 0
    
    async def load(self, context):
        """Load the module."""
        self.node_service = context.services.get("node_service")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("message_demo", {})
        
        if self.logger:
            if self.node_service:
                self.logger.log(
                    "MessageDemoModule loaded",
                    tag="msg_demo",
                    text_color=self.colors.BRIGHT_MAGENTA if self.colors else None
                )
            else:
                self.logger.log(
                    "MessageDemoModule loaded (node_service not yet available, will retry)",
                    tag="msg_demo",
                    level="WARNING"
                )
    
    async def start(self, context):
        """Start periodic broadcast if configured."""
        # Retry getting node_service if not available at load time
        if not self.node_service:
            self.node_service = context.services.get("node_service")
        
        if not self.node_service:
            if self.logger:
                self.logger.log(
                    "Cannot start MessageDemo: node_service not available",
                    tag="msg_demo",
                    level="ERROR"
                )
            return
        
        if self._config.get("enabled", True) and self._config.get("auto_broadcast_on_start", True):
            await self._initial_broadcast()
            self._broadcast_task = asyncio.create_task(self._broadcast_loop())
    
    async def ready(self, context):
        """Called when all modules are ready."""
        # Retry getting node_service if not available
        if not self.node_service:
            self.node_service = context.services.get("node_service")
        
        if self.logger and self.node_service:
            node_id = self.node_service.get_node_id()
            peers = self.node_service.get_connected_peers()
            self.logger.log(
                f"MessageDemo ready on '{node_id}' - {len(peers)} peers",
                tag="msg_demo"
            )
    
    async def stop(self, context):
        """Stop broadcast task."""
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        if self.logger:
            self.logger.log(
                f"MessageDemo stopped - {self._message_counter} messages sent",
                tag="msg_demo"
            )
    
    # =========================================================================
    # Broadcast Logic
    # =========================================================================
    
    async def _initial_broadcast(self):
        """Send initial broadcast message."""
        if not self.node_service:
            return
            
        node_id = self.node_service.get_node_id()
        peers = self.node_service.get_connected_peers()
        
        if not peers:
            if self.logger:
                self.logger.log(
                    "No connected peers yet - waiting before first broadcast",
                    tag="msg_demo",
                    level="INFO"
                )
            return
        
        # Use node_service.create_message() - NO direct imports
        msg = self.node_service.create_message(
            msg_type="data",
            payload={
                "event": "node_online",
                "node_id": node_id,
                "timestamp": datetime.now().isoformat(),
                "message": f"Hello network from {node_id}!",
            },
            message_id=str(uuid.uuid4()),
        )
        
        results = await self.node_service.broadcast(msg)
        
        if self.logger:
            success = sum(1 for v in results.values() if v)
            # Use logger.print for demo output
            self.logger.print("", tag="msg_demo")
            self.logger.print("=" * 60, tag="msg_demo")
            self.logger.print(f"📢 Initial broadcast: {success}/{len(results)} peers received", tag="msg_demo")
            self.logger.print("=" * 60, tag="msg_demo")
    
    async def _broadcast_loop(self):
        """Periodically broadcast status messages."""
        interval = self._config.get("broadcast_interval_seconds", 5.0)
        template = self._config.get("broadcast_message", "Hello from {node_id}!")
        
        # Wait for node_service to be available
        wait_count = 0
        while not self.node_service and wait_count < 30:
            await asyncio.sleep(1)
            wait_count += 1
        
        if not self.node_service:
            if self.logger:
                self.logger.log(
                    "MessageDemo: node_service never became available",
                    tag="msg_demo",
                    level="ERROR"
                )
            return
        
        node_id = self.node_service.get_node_id()
        
        try:
            while True:
                await asyncio.sleep(interval)
                
                peers = self.node_service.get_connected_peers()
                if not peers:
                    continue
                
                self._message_counter += 1
                
                # Use node_service.create_message() - NO direct imports
                msg = self.node_service.create_message(
                    msg_type="data",
                    payload={
                        "event": "periodic_hello",
                        "node_id": node_id,
                        "message": template.format(node_id=node_id),
                        "counter": self._message_counter,
                        "timestamp": datetime.now().isoformat(),
                    },
                    message_id=str(uuid.uuid4()),
                )
                
                results = await self.node_service.broadcast(msg)
                
                if self.logger:
                    success = sum(1 for v in results.values() if v)
                    # Use logger.print for demo output
                    self.logger.print(
                        f"📢 Broadcast #{self._message_counter}: "
                        f"{success}/{len(results)} peers",
                        tag="msg_demo"
                    )
        
        except asyncio.CancelledError:
            pass