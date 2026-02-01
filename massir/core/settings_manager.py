import json
from pathlib import Path
from massir.core.core_apis import CoreConfigAPI

class SettingsManager(CoreConfigAPI):
    def __init__(self, settings_path: str = "app_settings.json"):
        self._settings = self._load_settings(settings_path)

    def _load_settings(self, path: str) -> dict:
        full_path = Path(path)
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {} 

    def get(self, key: str, default=None):
        """دریافت مقدار با قابلیت پشتیبانی از کلیدهای تو در تو"""
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

    # --- تنظیمات هسته (Core) ---
    def is_debug(self) -> bool:
        return self.get("core.debug_mode", False)
    
    def get_project_name(self) -> str:
        return self.get("core.project_name", "Unknown Project")
    
    def get_banner_template(self) -> str:
        return self.get("core.project_banner_template", "{project_name}\n")
    
    def get_system_log_template(self) -> str:
        return self.get("core.system_log_template", "[{level}] {message}")
    
    def get_banner_color_code(self) -> str:
        return self.get("core.banner_color_code", "33")
    
    def get_system_log_color_code(self) -> str:
        return self.get("core.system_log_color_code", "96")

    # --- تنظیمات وب (برای استفاده در fastapi_provider) ---
    def get_web_host(self) -> str:
        return self.get("fastapi_provider.web.host", "127.0.0.1")
    
    def get_web_port(self) -> int:
        return self.get("fastapi_provider.web.port", 8000)
    
    def get_web_reload(self) -> bool:
        return self.get("fastapi_provider.web.reload", False)