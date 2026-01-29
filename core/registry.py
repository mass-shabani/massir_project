from typing import Any, Optional

class ModuleRegistry:
    def __init__(self):
        self._services = {}

    def set(self, key: str, instance: Any):
        """ثبت یک سرویس با کلید رشته‌ای"""
        # if key in self._services:
        #     # هشدار می‌دهیم که در حال بازنویسی یک سرویس هستیم
        #     print(f"⚠️ Warning: Overwriting service '{key}'")
        self._services[key] = instance

    def get(self, key: str) -> Optional[Any]:
        """دریافت سرویس با کلید رشته‌ای"""
        return self._services.get(key)

    def has(self, key: str) -> bool:
        return key in self._services

    def remove(self, key: str):
        if key in self._services:
            del self._services[key]