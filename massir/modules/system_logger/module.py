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
        config = self.config

        if not config.show_logs():
            return False

        if tag:
            hidden_tags = config.get_hide_log_tags()
            if isinstance(hidden_tags, list) and tag in hidden_tags:
                return False

        hidden_levels = config.get_hide_log_levels()
        if isinstance(hidden_levels, list):
            if level in hidden_levels:
                return False

        critical_levels = ["ERROR", "WARNING", "EXCEPTION", "CRITICAL"]
        if level in critical_levels and not config.is_debug():
            return False
        
        return True

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None,
            level_color: Optional[str] = None, text_color: Optional[str] = None, bracket_color: Optional[str] = None):
        # ⭐ بررسی فیلترینگ
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

        # رنگ‌های پیش‌فرض
        _bracket_color = bracket_color if bracket_color else '\033[92m'
        _text_color = text_color if text_color else '\033[97m'
        _level_color = level_color if level_color else '\033[92m'
        
        RESET = '\033[0m'
        COLOR_RED = '\033[91m'

        if level == "ERROR" and level_color is None:
            _level_color = COLOR_RED
            _text_color = COLOR_RED

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        str_time = f"{_bracket_color}[{timestamp}]{RESET} "
        str_header = f"{_level_color}[{level}]{RESET} "

        if level == "ERROR":
            str_message = f"{_text_color}{message}{RESET}"
        else:
            str_message = f"{_text_color}{message}{RESET}"

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
        # ⭐ اصلاح مهم: به‌روزرسانی رفرنس کانفیگ ماژول
        # چون ممکن است تنظیمات کد (initial_settings) بعد از load اعمال شده باشد
        # یا کانفیگ در رجیستری جایگزین شده باشد.
        logger = context.services.get("core_logger")
        if logger and hasattr(logger, 'config'):
            logger.config = context.services.get("core_config")

        logger.log("System Logger Module Active.", tag="System")

    async def stop(self, context):
        pass

    def _on_settings_loaded(self):
        pass

    def _on_module_loaded(self, module_instance):
        logger = self.context.services.get("core_logger")
        logger.log(f"Detected loaded module: {module_instance.name}", level="DEBUG", tag="Detailed")