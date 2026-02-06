from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from massir.core.registry import ModuleRegistry

if TYPE_CHECKING:
    from massir.core.app import App

class ModuleContext:
    """
    کانتکست که در اختیار تمام ماژول‌ها قرار می‌گیرد.
    شامل رجیستری سرویس‌ها و رفرنس به هسته برای ثبت کال‌بک‌ها.
    """
    def __init__(self):
        self._app = None
        self.services = ModuleRegistry()
        self.metadata = {}

    def set_app(self, app: 'App'):
        self._app = app

    def get_app(self) -> 'App':
        return self._app

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