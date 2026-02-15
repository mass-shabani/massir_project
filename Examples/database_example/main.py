"""
Database Example - Demonstrates the system_database module.

This example shows how to:
- Use the database service
- Create tables
- Insert, update, delete records
- Query data
- Use transactions
"""
import sys
import asyncio
from pathlib import Path

MASSIR_ROOT = Path(__file__).parent.parent.parent.resolve()
CURRENT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from massir.core.app import App


async def main():
    """Main entry point."""
    # Get the directory where this script is located
    
    # Create the application
    app = App(
        settings_path="./app_settings.json",
        app_dir=CURRENT_ROOT
    )
    
    # Run the application
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())