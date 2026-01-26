from abc import ABC, abstractmethod
from core.registry import ModuleRegistry

# تعریف ModuleContext در اینجا برای جلوگیری از Circular Import
class ModuleContext:
    def __init__(self):
        self.services = ModuleRegistry()
        self.metadata = {} 

class IModule(ABC):
    """
    همه ماژول‌ها باید از این کلاس ارث‌بری کنند.
    هسته فقط این اینترفیس را می‌شناسد.
    """
    name: str = ""

    @abstractmethod
    async def load(self, context: ModuleContext):
        """
        فاز اول: لود اولیه و ثبت سرویس‌ها در Registry.
        """
        pass

    @abstractmethod
    async def start(self, context: ModuleContext):
        """
        فاز دوم: شروع کار و ارتباط با سایر ماژول‌ها.
        """
        pass

    @abstractmethod
    async def stop(self, context: ModuleContext):
        """
        فاز سوم: پاکسازی منابع.
        """
        pass