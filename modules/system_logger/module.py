import datetime
import os
from core.interfaces import IModule
from core.apis.system_apis import CoreLoggerAPI
from core.hooks.definitions import SystemHook

class AdvancedLogger(CoreLoggerAPI):
    # تعریف کدهای رنگ ANSI
    GREEN = '\033[92m'
    RESET = '\033[0m'

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # فعال‌سازی رنگ در ترمینال‌های ویندوز (اگر در CMD استاندارد اجرا شود)
        # در VS Code یا PowerShell/Windows Terminal نیازی نیست اما برای اطمینان:
        if os.name == 'nt':
            os.system('')

        # فرمت جدید: [زمان (سبز)] [سطح] تب پیام
        print(f"{self.GREEN}[{timestamp}]{self.RESET} [{level}]\t{message}")

class SystemLoggerModule(IModule):
    async def load(self, context):
        self.context = context 

        my_logger = AdvancedLogger()
        context.services.set("core_logger", my_logger)
        
        kernel = context.get_kernel()
        kernel.register_hook(SystemHook.ON_MODULE_LOADED, self._on_module_loaded)

    async def start(self, context):
        logger = context.services.get("core_logger")
        logger.log("System Logger Module Active. Output formatting updated.")

    async def stop(self, context):
        pass

    def _on_module_loaded(self, module_instance):
        logger = self.context.services.get("core_logger")
        logger.log(f"Detected loaded module: {module_instance.name}", level="DEBUG")