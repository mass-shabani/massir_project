"""
Basic Website Example - A simple website using Massir framework.

This example demonstrates how to build a simple website with:
- Jinja2 templating
- Multiple pages (index, about, contact)
- Login and user panel
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
    Main entry point for the basic website example.
    """
    # Initial settings
    initial_settings = {
        "fastapi_provider": {
            "title": "Basic Website",
            "version": "1.0.0",
            "description": "A simple website built with Massir framework",
            "web": {
                "host": "127.0.0.1",
                "port": 8080,
                "reload": False
            },
            "cors": {
                "origins": ["*"],
                "credentials": True,
                "methods": ["*"],
                "headers": ["*"]
            },
            "gzip": {
                "enabled": True,
                "minimum_size": 1000
            }
        }
    }

    app = App(
        initial_settings=initial_settings,
        settings_path="app_settings.json",
        app_dir=CURRENT_ROOT
    )

    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
