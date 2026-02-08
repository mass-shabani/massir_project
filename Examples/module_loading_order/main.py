import asyncio
import sys
from pathlib import Path

# اضافه کردن مسیر پروژه اصلی به sys.path
MASSIR_ROOT = Path(__file__).parent.parent.parent.resolve()
CURRENT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from massir import App

async def main():
    # تنظیمات کد با اولویت بالاتر از JSON
    initial_settings = {
        "template": {
            "banner_color_code": "33"
        },
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
