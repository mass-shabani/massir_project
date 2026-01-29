import asyncio
from core import Kernel

async def main():
    kernel = Kernel()
    await kernel.bootstrap(modules_dir="modules")
    
    # # نگه داشتن برنامه برای تست
    # print("✨ App running. Press Ctrl+C to exit.")
    # await asyncio.sleep(5)
    
    await kernel.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass