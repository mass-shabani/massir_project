from typing import Any

class ServiceRegistry:
    """
    رجیستری سرویس‌ها:
    ماژول‌ها سرویس‌هایشان را اینجا ثبت می‌کنند
    """

    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any):
        """
        سرویس را ثبت می‌کند
        """
        self._services[name] = service

    def unregister(self, name: str):
        """
        حذف سرویس
        """
        if name in self._services:
            del self._services[name]

    def get(self, name: str) -> Any | None:
        """
        دریافت سرویس
        """
        return self._services.get(name)
