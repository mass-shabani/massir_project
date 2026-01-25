import asyncio
import signal
import sys
from core import Kernel

async def main():
    kernel = Kernel()
    
    # هندل کردن خاموشی ناگهانی
    def signal_handler(sig, frame):
        print("\n⚠️ Interrupt received. Shutting down...")
        asyncio.create_task(kernel.shutdown())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # بوت‌استرپ فریم‌ورک
    await kernel.bootstrap(modules_dir="modules")
    
    # برنامه در اینجا اجرا می‌شود. 
    # برای تست، یک لوپ ساده نگه می‌داریم.
    print("✨ Application is running. Press Ctrl+C to stop.")
    
    # چون این یک فریم‌ورک است، منطق برنامه باید در ماژول‌ها باشد
    # اینجا فقط یک تاخیر برای نشان دادن حیات برنامه است
    await asyncio.sleep(5) 
    
    await kernel.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass