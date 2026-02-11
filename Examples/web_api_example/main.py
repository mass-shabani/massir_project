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
    Main entry point for the web API example.
    
    This example demonstrates using the network_fastapi module
    to create a simple web API with multiple endpoints.
    """
    # Initial settings
    initial_settings = {
        "fastapi_provider": {
            "title": "Massir Web API Example",
            "version": "1.0.0",
            "description": "Example web API using network_fastapi module",
            "web": {
                "host": "127.0.0.1",
                "port": 8000,
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
