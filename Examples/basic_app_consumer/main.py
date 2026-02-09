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
    Main entry point for the basic app consumer example.

    This function initializes and runs the Massir application with a single
    application module that demonstrates basic module functionality.
    """
    # Initial settings with higher priority than JSON configuration
    # If defined in JSON, this value will override it
    initial_settings = {
        # "logs": {
        #     "show_banner": True,
        #     "hide_log_tags": ["core_init", "core_hooks"],
        # },
        "template": {
            # "banner_color_code": "33"
        },
    }
    # Use local settings from the SubApp folder

    app = App(
        initial_settings=initial_settings,
        settings_path="app_settings.json",
        app_dir=CURRENT_ROOT
    )

    await app.run()

    # Display active paths within the project
    # print(f"MASSIR_ROOT = {str(app.path.massir.resolve())}")
    # print(f"CURRENT_ROOT = {str(app.path.app.resolve())}")

    # Change active paths
    # app.path.set("massir_dir", MASSIR_ROOT)
    # app.path.set("app_dir", CURRENT_ROOT.parent)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
