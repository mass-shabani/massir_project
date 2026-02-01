# massir/core/core_apis.py

from abc import ABC, abstractmethod

class CoreLoggerAPI(ABC):
    """
    اینترفیس استاندارد لاگینگ هسته.
    ماژول‌های سیستمی می‌توانند این را پیاده‌سازی کنند.
    """
    @abstractmethod
    def log(self, message: str, level: str = "INFO"):
        pass

class CoreConfigAPI(ABC):
    """
    اینترفیس استاندارد دسترسی به تنظیمات.
    """
    @abstractmethod
    def get(self, key: str):
        pass