from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

# ⭐ اصلاح ایمپورت: استفاده از نیم‌اسپیس massir
from massir.core.registry import ModuleRegistry

if TYPE_CHECKING:
    # برای تایپ چیک از massir.core.run استفاده می‌کنیم
    from massir.core.run import Kernel

class ModuleContext:
    """
    کانتکست که در اختیار تمام ماژول‌ها قرار می‌گیرد.
    شامل رجیستری سرویس‌ها و رفرنس به هسته برای ثبت کال‌بک‌ها.
    """
    def __init__(self):
        self._kernel = None
        self.services = ModuleRegistry()
        self.metadata = {}

    def set_kernel(self, kernel: 'Kernel'):
        self._kernel = kernel

    def get_kernel(self) -> 'Kernel':
        return self._kernel

class IModule(ABC):
    """
    اینترفیس پایه برای تمام ماژول‌ها
    """
    name: str = ""

    @abstractmethod
    async def load(self, context: ModuleContext):
        pass

    @abstractmethod
    async def start(self, context: ModuleContext):
        pass

    @abstractmethod
    async def stop(self, context: ModuleContext):
        pass