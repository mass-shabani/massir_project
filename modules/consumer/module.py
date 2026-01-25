import asyncio
from core import IModule

# ما اینترفیس ICalculator را اینجا تعریف نمی‌کنیم چون نمی‌دانیم چیه.
# ما فقط روی قرارداد ظاهری (نام متد) توافق می‌کنیم.

class AppModule(IModule):
    async def load(self, context):
        print("   [AppModule] Loaded (Dependency requested: calculator_service)")

    async def start(self, context):
        # دریافت سرویس مورد نیاز
        calc = context.services.get("calculator_service")
        
        if calc and hasattr(calc, 'add'):
            print("   [AppModule] Successfully connected to calculator service.")
            # استفاده از سرویس بدون دانستن کلاس واقعی آن
            result = calc.add(10, 20)
            print(f"   [AppModule] Result received: {result}")
        else:
            print("   [AppModule] ERROR: Calculator service missing or invalid!")

    async def stop(self, context):
        print("   [AppModule] Stopped.")