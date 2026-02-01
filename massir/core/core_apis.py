from abc import ABC, abstractmethod
from typing import Optional # اضافه شد

class CoreLoggerAPI(ABC):
    """
    اینترفیس استاندارد لاگینگ هسته.
    """
    @abstractmethod
    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None):
        pass

class CoreConfigAPI(ABC):
    """
    اینترفیس استاندارد دسترسی به تنظیمات.
    """
    @abstractmethod
    def get(self, key: str):
        pass