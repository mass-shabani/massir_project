import asyncio
from core import Kernel

async def main():
    kernel = Kernel()
    # ⭐ استفاده از متد run() به جای bootstrap()
    await kernel.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass