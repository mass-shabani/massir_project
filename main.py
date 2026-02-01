import asyncio
# ⭐ طبق درخواست شما: دسترسی به هسته از طریق نیم‌اسپیس massir.core
from massir import Kernel

async def main():
    kernel = Kernel()
    await kernel.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass