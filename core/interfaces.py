from abc import ABC, abstractmethod
from core.kernel import ModuleContext

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
        در این مرحله نباید به سرویس‌های دیگران دسترسی زد چون هنوز لود نشده‌اند.
        """
        pass

    @abstractmethod
    async def start(self, context: ModuleContext):
        """
        فاز دوم: شروع کار و ارتباط با سایر ماژول‌ها.
        در این مرحله می‌توان از context.services.get استفاده کرد.
        """
        pass

    @abstractmethod
    async def stop(self, context: ModuleContext):
        """
        فاز سوم: پاکسازی منابع قبل از بسته شدن.
        """
        pass