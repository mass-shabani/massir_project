import asyncio
from core import IModule

# ⭐ این اینترفیس فقط در همین فایل تعریف شده است. هسته اصلا خبری ندارد.
class ICalculator:
    def add(self, a, b): pass

class RealCalculator(ICalculator):
    def add(self, a, b):
        print(f"   [Calculator] Calculating {a} + {b} = {a+b}")
        return a + b

class MathModule(IModule):
    async def load(self, context):
        # ثبت نمونه سرویس با کلیدی که در manifest نوشتیم
        calc = RealCalculator()
        context.services.set("calculator_service", calc)
        print("   [MathModule] Service 'calculator_service' registered.")

    async def start(self, context):
        print("   [MathModule] Started.")

    async def stop(self, context):
        print("   [MathModule] Stopped.")