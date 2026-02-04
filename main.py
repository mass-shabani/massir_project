import asyncio
from massir import App

async def main():
    # تنظیمات کد با اولویت بالاتر از JSON
    # مثلا: پوشه ماژول‌ها را از اینجا تغییر می‌دهیم
    # اگر در JSON تعریف شده باشد، این مقدار جایگزین می‌شود
    initial_settings = {
        "system": {
            # "modules_dir": ["./massir/modulesss", "./app"] # اگر این پوشه وجود نداشته، طبق کد قبلی خطا می‌دهد و سرچ می‌کند
        },

    }

    app = App(initial_settings=initial_settings)
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass