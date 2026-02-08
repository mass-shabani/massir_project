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
    # اگر در JSON تعریف شده باشد، این مقدار جایگزین می‌شود
    initial_settings = {
        # "logs": {
        #     "show_banner": True,
        #     "hide_log_tags": ["core_init", "core_hooks"],
        # },
        "template": {
        # "banner_color_code": "33"
  },
    }
    # استفاده از تنظیمات محلی پوشه SubApp

    app = App(
        initial_settings = initial_settings,
        settings_path = "app_settings.json",
        app_dir = CURRENT_ROOT
    )

    
    await app.run()



    # نمایش مسیرهای فعال درون پروژه
    # print (f"MASSIR_ROOT = {str(app.path.massir.resolve())}")
    # print (f"CURRENT_ROOT = {str(app.path.app.resolve())}")

    # تغییر مسیرهای فعال
    # app.path.set("massir_dir", MASSIR_ROOT)
    # app.path.set("app_dir", CURRENT_ROOT.parent)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
