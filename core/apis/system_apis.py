# core/apis/system_apis.py

from abc import ABC, abstractmethod

class CoreLoggerAPI(ABC):
    """
    API استاندارد لاگینگ هسته.
    ماژول‌های سیستمی می‌توانند این را پیاده‌سازی و ریسایت کنند.
    """
    @abstractmethod
    def log(self, message: str, level: str = "INFO"):
        pass

class CoreConfigAPI(ABC):
    """
    API استاندارد دسترسی به تنظیمات.
    """
    @abstractmethod
    def get(self, key: str):
        pass