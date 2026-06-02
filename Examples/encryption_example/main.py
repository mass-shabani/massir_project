"""
Encryption Example - Main Entry Point

This example demonstrates all features of the system_encryption module:
- AES-256-GCM symmetric encryption
- RSA-4096 asymmetric encryption and signing
- HMAC message authentication
- Key management and serialization
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
    Main entry point for the encryption example.
    
    This example demonstrates using the system_encryption module
    for various cryptographic operations.
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