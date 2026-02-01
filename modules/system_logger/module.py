import datetime
import os
from typing import Optional
from massir.core.interfaces import IModule
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.hook_types import SystemHook

class AdvancedLogger(CoreLoggerAPI):
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api
        if self.config is None:
            self.config = self._get_fallback()

    def _get_fallback(self):
        class F:
            def get_project_name(self): return "Unknown"
            def get_system_log_template(self): return "[{level}]\t{message}"
            def get_system_log_color_code(self): return "92"
            def is_debug(self): return True
            def show_logs(self): return True
            def get_hide_log_levels(self): return []
            def get_hide_log_tags(self): return []
        return F()

    def _should_log(self, level: str, tag: Optional[str] = None) -> bool:
        """
        منطق فیلترینگ پیشرفته (مشابه هسته)
        1. show_logs
        2. hide_log_tags
        3. hide_log_levels
        4. debug_mode (برای خطاها)
        """
        config = self.config

        # 1. کلید اصلی
        if not config.show_logs():
            return False

        # 2. فیلتر تگ‌ها (اختیاری)
        if tag:
            hidden_tags = config.get_hide_log_tags()
            for hidden_tag in hidden_tags:
                if tag == hidden_tag: # تطبیق دقیق تگ
                    return False

        # 3. فیلتر سطوح پیشرفته (hide_log_levels)
        # اگر سطح پیام در لیست سیاه باشد، مخفی کن
        hidden_levels = config.get_hide_log_levels()
        if level in hidden_levels:
            return False

        # 4. کنترل debug_mode بر اساس درخواست شما
        # فقط سطوح ERROR, WARNING, EXCEPTION تحت تأثیر debug_mode قرار می‌گیرند
        critical_levels = ["ERROR", "WARNING", "EXCEPTION", "CRITICAL"]
        if level in critical_levels:
            if not config.is_debug():
                return False
        
        return True

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None,
            level_color: Optional[str] = None, text_color: Optional[str] = None, bracket_color: Optional[str] = None):
        """
        پیشرفته‌ترین متد لاگ.
        آرگومان‌های رنگ اختیاری هستند و در صورت عدم ورود از رنگ‌های پیش‌فرض استفاده می‌شود.
        """
        # 1. بررسی فیلترینگ (مشابه هسته)
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        # 2. تعریف رنگ‌ها (Defaults)
        # رنگ پیش‌فرض براکت‌ها: سبز
        _bracket_color = bracket_color if bracket_color else '\033[92m'
        # رنگ پیش‌فرض متن (اگر خطا نباشد): سفید
        _text_color = text_color if text_color else '\033[97m'
        # رنگ پیش‌فرض سطح (اگر خطا نباشد): سبز
        _level_color = level_color if level_color else '\033[92m'
        
        RESET = '\033[0m'
        COLOR_RED = '\033[91m'

        # 3. اعمال رنگ قرمز برای سطح ERROR (اگر آرگومن خاصی داده نشده)
        if level == "ERROR" and level_color is None:
            _level_color = COLOR_RED
            _text_color = COLOR_RED # متن خطا هم قرمز باشد

        # 4. ساخت کامپوننت‌ها
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # براکت زمان: [timestamp]
        str_time = f"{_bracket_color}[{timestamp}]{RESET} "
        
        # براکت سطح: [INFO]
        str_header = f"{_level_color}[{level}]{RESET} "

        # بخش پیام
        if level == "ERROR":
            str_message = f"{_text_color}{message}{RESET}"
        else:
            str_message = f"{_text_color}{message}{RESET}"

        # 5. چاپ نهایی
        # طبق کد قبلی تب بین هدر و پیام وجود دارد
        print(f"{str_time}{str_header}\t{str_message}")

class SystemLoggerModule(IModule):
    async def load(self, context):
        self.context = context 
        config = context.services.get("core_config")
        
        my_logger = AdvancedLogger(config)
        context.services.set("core_logger", my_logger)
        
        kernel = context.get_kernel()
        kernel.register_hook(SystemHook.ON_MODULE_LOADED, self._on_module_loaded)
        kernel.register_hook(SystemHook.ON_SETTINGS_LOADED, self._on_settings_loaded)

    async def start(self, context):
        logger = context.services.get("core_logger")
        # استفاده از تگ System برای فیلتر کردن لاگ‌های سیستمی در تنظیمات
        logger.log("System Logger Module Active.", tag="System")

    async def stop(self, context):
        pass

    def _on_settings_loaded(self):
        pass

    def _on_module_loaded(self, module_instance):
        logger = self.context.services.get("core_logger")
        # استفاده از تگ Detailed
        logger.log(f"Detected loaded module: {module_instance.name}", level="DEBUG", tag="Detailed")