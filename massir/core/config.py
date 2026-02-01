import json
import os
from pathlib import Path
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI

class SettingsManager(CoreConfigAPI):
    """مدیریت تنظیمات پروژه از فایل JSON"""
    def __init__(self, settings_path: str = "app_settings.json"):
        self._settings = self._load_settings(settings_path)

    def _load_settings(self, path: str) -> dict:
        full_path = Path(path)
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {} 

    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value):
        self._settings[key] = value

    # تنظیمات هسته
    def is_debug(self) -> bool: return self.get("core.debug_mode", False)
    def get_project_name(self) -> str: return self.get("core.project_name", "Unknown Project")
    def get_banner_template(self) -> str: return self.get("core.project_banner_template", "{project_name}\n")
    def get_system_log_template(self) -> str: return self.get("core.system_log_template", "[{level}] {message}")
    def get_banner_color_code(self) -> str: return self.get("core.banner_color_code", "33")
    def get_system_log_color_code(self) -> str: return self.get("core.system_log_color_code", "96")

    # تنظیمات وب
    def get_web_host(self) -> str: return self.get("fastapi_provider.web.host", "127.0.0.1")
    def get_web_port(self) -> int: return self.get("fastapi_provider.web.port", 8000)
    def get_web_reload(self) -> bool: return self.get("fastapi_provider.web.reload", False)

class DefaultConfig(CoreConfigAPI):
    """کانفیگ پیش‌فرض ساده"""
    def get(self, key: str): return None

class DefaultLogger(CoreLoggerAPI):
    """لاگر پیش‌فرض که از تنظیمات استفاده می‌کند"""
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api

    def log(self, message: str, level: str = "INFO"):
        if not self.config.is_debug():
            return
        if os.name == 'nt': os.system('')
        
        template = self.config.get_system_log_template()
        color_code = self.config.get_system_log_color_code()
        formatted_msg = template.format(
            project_name=self.config.get_project_name(),
            level=level,
            message=message
        )
        color_code_start = f'\033[{color_code}m'
        reset_code = '\033[0m'
        print(f"{color_code_start}{formatted_msg}{reset_code}")