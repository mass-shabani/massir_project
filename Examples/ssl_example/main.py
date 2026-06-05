"""
SSL Example - Main Entry Point

This example demonstrates all features of the network_ssl module:
- TLS 1.3 server and client contexts
- mTLS (mutual TLS) authentication
- Certificate lifecycle management
- Hot-reload of certificates
- Expiry monitoring and warnings
"""

import asyncio
import sys
from pathlib import Path

# Add the main project path to sys.path
MASSIR_ROOT = Path(__file__).parent.parent.parent.resolve()
CURRENT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from massir import App


async def main():
    """
    Main entry point for the SSL example.
    
    This example demonstrates using the network_ssl module
    for secure TLS communications.
    """
    app = App(
        settings_path="app_settings.json",
        app_dir=CURRENT_ROOT
    )
    
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass