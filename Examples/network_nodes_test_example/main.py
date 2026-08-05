"""
Network Nodes Test Example - Multi-Node Entry Point

Comprehensive test of system_network capabilities:
- Transport-agnostic messaging (socket + websocket)
- Topology management
- Multi-hop routing
- Capability-based messaging
- Broadcast and direct messaging
- Network monitoring
- Graceful shutdown with report

Usage:
    NODE_ID=node1 python main.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the main project path to sys.path
MASSIR_ROOT = Path(__file__).parent.parent.parent.resolve()
CURRENT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from massir import App


async def main():
    """Main entry point for a network test node."""
    node_id = os.environ.get("NODE_ID", "node1")
    
    # Try to load node-specific settings
    node_config_path = CURRENT_ROOT / "configs" / f"{node_id}.json"
    settings_path = "app_settings.json"
    
    if node_config_path.exists():
        settings_path = str(node_config_path)
        print(f"📋 Using node config: {settings_path}")
    else:
        print(f"📋 Using default app_settings.json (NODE_ID={node_id})")
    
    app = App(
        settings_path=settings_path,
        app_dir=CURRENT_ROOT
    )
    
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
