"""
Socket Example - Multi-Node Entry Point

Each node runs this same main.py but with different configuration
loaded from configs/<NODE_ID>.json based on environment variable.

Usage:
    # with local variable
    NODE_ID=node1 python main.py
    
    # without local variable(using app_settings.json)
    python main.py
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
    """
    Main entry point for a socket node.
    
    Configuration priority:
    1. configs/<NODE_ID>.json (if NODE_ID env var is set)
    2. app_settings.json (default)
    """
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
        pass