"""
Message Demo Module

Demonstrates Message Mode operations in the distributed network:
- Periodic broadcast to all connected peers
- Message handling and routing
- Request/reply patterns (future extension)

NOTE: This module does NOT import types directly from network_socket.
All message creation goes through node_service.create_message() which
delegates to socket_api factory methods.

OUTPUT STRATEGY:
- logger.print: For broadcast events and message exchanges
  → Uses 'color' parameter (magenta for outgoing broadcasts)
  → Compact format for periodic broadcasts
  → Full format with bg_color for important events (initial broadcast)
- logger.log: For errors, warnings, and general info
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List

from massir.core.interfaces import IModule


class MessageDemoModule(IModule):
    """
    Demonstrates Message Mode features in the distributed network.
    
    This module periodically broadcasts messages to all connected peers,
    showing the message framing, codec (JSON), and multi-peer delivery
    capabilities of the network_socket module.
    """
    
    def __init__(self):
        self.node_service = None
        self.logger = None
        self.colors = None
        self._config: Dict = {}
        self._broadcast_task = None
        self._message_counter = 0
    
    async def start(self, context):
        """
        Start the message demo:
        1. Retrieve required services from the context
        2. Load configuration from app_settings.json
        3. Start periodic broadcast if configured
        """
        self.node_service = context.services.get("node_service")
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        # Load configuration from app_settings.json
        core_config = context.services.get("core_config")
        if core_config:
            self._config = core_config.get("message_demo", {})
        
        if self.logger:
            if self.node_service:
                self.logger.log("MessageDemoModule started", tag="msg_demo")
            else:
                # node_service may not be available yet due to module load ordering
                # Will retry in start() and ready() phases
                self.logger.log(
                    "MessageDemoModule started (node_service not yet available, will retry)",
                    tag="msg_demo",
                    level="WARNING"
                )
        
        # Retry getting node_service if not available at load time
        # This handles module ordering issues gracefully
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
    
    async def stop(self, context):
        """Stop broadcast task and cleanup."""
        if self._broadcast_task and not self._broadcast_task.done():
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
        
        if self.logger:
            self._print_box(
                title="🛑 MESSAGE DEMO STOPPED",
                lines=[f"Total messages sent: {self._message_counter}"],
                color=self.colors.BRIGHT_YELLOW if self.colors else None
            )
    
    # =========================================================================
    # Broadcast Logic
    # =========================================================================
    
    async def _initial_broadcast(self):
        """
        Send an initial broadcast announcing this node's presence.
        
        This is sent once when the module starts, before the periodic
        broadcast loop begins.
        """
        if not self.node_service:
            return
        
        node_id = self.node_service.get_node_id()
        peers = self.node_service.get_connected_peers()
        
        if not peers:
            if self.logger:
                self.logger.log(
                    "No connected peers yet - waiting before first broadcast",
                    tag="msg_demo"
                )
            return
        
        # Create message using factory method (no direct imports needed)
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
            self._print_box(
                title="📢 INITIAL BROADCAST",
                lines=[
                    f"Event:       node_online",
                    f"From:        {node_id}",
                    f"Delivered:   {success}/{len(results)} peers",
                    f"Peers:       {', '.join(results.keys())}",
                ],
                color=self.colors.BRIGHT_MAGENTA if self.colors else None,
                bg_color=self.colors.BG_BLUE if self.colors else None
            )
    
    async def _broadcast_loop(self):
        """
        Periodically broadcast status messages to all connected peers.
        
        The broadcast interval and message template are configurable
        via app_settings.json.
        """
        interval = self._config.get("broadcast_interval_seconds", 5.0)
        template = self._config.get("broadcast_message", "Hello from {node_id}!")
        
        # Wait for node_service to become available (up to 30 seconds)
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
                
                # Create periodic hello message
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
                    self._print_box(
                        title=f"📢 BROADCAST #{self._message_counter}",
                        lines=[
                            f"From:      {node_id}",
                            f"Delivered: {success}/{len(results)} peers",
                        ],
                        color=self.colors.BRIGHT_MAGENTA if self.colors else None,
                        compact=True
                    )
        
        except asyncio.CancelledError:
            pass
    
    # =========================================================================
    # Visual Output Helpers
    # =========================================================================
    
    def _print_box(
        self,
        title: str,
        lines: List[str],
        color=None,
        bg_color=None,
        compact: bool = False
    ):
        """
        Print a visually distinct box for broadcast events.
        
        Uses the same formatting convention as socket_node for consistency.
        """
        if not self.logger:
            return
        
        width = 62
        
        if compact:
            separator = "─" * width
            self.logger.print(f"┌{separator}┐", tag="msg_demo", color=color)
            self.logger.print(
                f"│ {title:<{width-2}} │",
                tag="msg_demo",
                color=color,
                bg_color=bg_color,
                bold=True
            )
            for line in lines:
                if len(line) > width - 4:
                    line = line[:width-7] + "..."
                self.logger.print(
                    f"│   {line:<{width-4}} │",
                    tag="msg_demo",
                    color=color
                )
            self.logger.print(f"└{separator}┘", tag="msg_demo", color=color)
        else:
            separator = "═" * width
            self.logger.print(f"╔{separator}╗", tag="msg_demo", color=color, bold=True)
            self.logger.print(
                f"║  {title:<{width-3}}║",
                tag="msg_demo",
                color=color,
                bg_color=bg_color,
                bold=True
            )
            self.logger.print(f"╠{separator}╣", tag="msg_demo", color=color, bold=True)
            for line in lines:
                if len(line) > width - 3:
                    line = line[:width-6] + "..."
                self.logger.print(
                    f"║  {line:<{width-3}} ║",
                    tag="msg_demo",
                    color=color
                )
            self.logger.print(f"╚{separator}╝", tag="msg_demo", color=color, bold=True)
        
        self.logger.print("", tag="msg_demo")
