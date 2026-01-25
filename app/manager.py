from pathlib import Path

from .config import Config
from .registry import ServiceRegistry
from .event_system import EventSystem, Event
from .interfaces import BaseModule
from .loader import ModuleLoader
from .exceptions import ModuleLoadError

class LoadedModule:
    def __init__(self, name: str, instance: BaseModule):
        self.name = name
        self.instance = instance

class CoreManager:
    """
    مدیر مرکزی پروژه: بارگذاری ماژول‌ها،
    Service Registry و Event System را کنترل می‌کند
    """

    def __init__(self):
        self.registry = ServiceRegistry()
        self.event_system = EventSystem()
        self.loader = ModuleLoader()
        self.loaded_modules: dict[str, LoadedModule] = {}

    def load_modules(self):
        """
        بارگذاری همه ماژول‌ها
        """
        for module_path in self.loader.list_modules():
            try:
                setting = self.loader.load_setting(module_path)
                if not setting.get("enabled", False):
                    continue  # اگر ماژول غیرفعال باشد، رد می‌شود
                name = setting.get("name", module_path.name)
                entrypoint = setting.get("entrypoint")
                if not entrypoint:
                    raise ModuleLoadError("entrypoint تعریف نشده")
                module_cls = self.loader.import_entrypoint(module_path, entrypoint)
                instance: BaseModule = module_cls()
                # setup module
                instance.setup(self)
                # register module
                self.loaded_modules[name] = LoadedModule(name, instance)
            except ModuleLoadError as e:
                print("[CoreManager] Error loading module:", e)

    def unload_module(self, name: str):
        """
        غیرفعال کردن ماژول
        """
        module = self.loaded_modules.get(name)
        if module:
            try:
                module.instance.shutdown()
            except Exception as e:
                print(f"[CoreManager] Error shutting down {name}: {e}")
            # حذف سرویس‌ها اگر ثبت شده اند
            # می‌توان اینجا unregister سرویس‌ها نیز انجام داد
            del self.loaded_modules[name]

    def get_service(self, name: str):
        """
        گرفتن سرویس ثبت شده
        """
        return self.registry.get(name)

    def register_service(self, name: str, service: object):
        """
        ثبت سرویس جدید
        """
        self.registry.register(name, service)

    def dispatch_event(self, event: Event):
        """
        انتشار event به EventSystem
        """
        self.event_system.dispatch(event)
