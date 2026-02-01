import datetime
import os
from core.interfaces import IModule
from core.system_apis import CoreLoggerAPI, CoreConfigAPI
from core.hook_types import SystemHook

class AdvancedLogger(CoreLoggerAPI):
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api
        if self.config is None:
            self.config = self._get_fallback()

    def _get_fallback(self):
        class F:
            def get_project_name(self): return "Unknown"
            def get_system_log_template(self): return "[{level}] {message}"
            def get_system_log_color_code(self): return "92"
            def is_debug(self): return True
        return F()

    def log(self, message: str, level: str = "INFO"):
        # ⭐ منطق جدید برای دیباگ:
        # پیام‌های DEBUG فقط اگر debug_mode True باشند چاپ می‌شوند.
        # پیام‌های INFO, WARNING, ERROR همیشه چاپ می‌شوند.
        if level == "DEBUG" and not self.config.is_debug():
            return

        if os.name == 'nt':
            os.system('')

        # --- تعریف کدهای رنگ ---
        COLOR_GREEN = '\033[92m'  # برای براکت‌ها
        COLOR_WHITE = '\033[97m'  # برای متن پیام
        COLOR_RED = '\033[91m'    # برای متن خطا
        RESET = '\033[0m'

        # 2. ساخت کامپوننت‌ها
        
        # تغییر فرمت تاریخ و ساعت (تاریخ + ساعت)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # براکت زمان: [2023-10-27 12:30:45]
        str_time = f"{COLOR_GREEN}[{timestamp}]{RESET} "
        
        # براکت سطح پیام: [INFO] (بدون نام پروژه)
        str_header = f"{COLOR_GREEN}[{level}]{RESET} "

        # بخش پیام
        if level == "ERROR":
            str_message = f"{COLOR_RED}{message}{RESET}"
        else:
            str_message = f"{COLOR_WHITE}{message}{RESET}"

        # چاپ نهایی
        print(f"{str_time}{str_header}\t{str_message}")

class SystemLoggerModule(IModule):
    async def load(self, context):
        self.context = context 
        
        # ⭐ اصلاح شده: دریافت کانفیگ از رجیستری سرویس‌ها
        # (چون در run.py سرویس‌ها قبل از لود ماژول‌ها ست می‌شوند)
        config = context.services.get("core_config")
        
        my_logger = AdvancedLogger(config)
        context.services.set("core_logger", my_logger)
        
        kernel = context.get_kernel()
        kernel.register_hook(SystemHook.ON_MODULE_LOADED, self._on_module_loaded)
        kernel.register_hook(SystemHook.ON_SETTINGS_LOADED, self._on_settings_loaded)

    async def start(self, context):
        logger = context.services.get("core_logger")
        logger.log("System Logger Module Active.")

    async def stop(self, context):
        pass

    def _on_settings_loaded(self):
        pass

    def _on_module_loaded(self, module_instance):
        logger = self.context.services.get("core_logger")
        # این پیام سطح DEBUG دارد، بنابراین در حالت پروداکشن مخفی می‌شود
        logger.log(f"Detected loaded module: {module_instance.name}", level="DEBUG")