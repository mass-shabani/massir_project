import json
import os
from pathlib import Path
from core.apis.system_apis import CoreConfigAPI

class SettingsManager(CoreConfigAPI):
    def __init__(self, settings_path: str = "app_settings.json"): # تغییر نام فایل
        self._settings = self._load_settings(settings_path)

    def _load_settings(self, path: str) -> dict:
        full_path = Path(path)
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {} 

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        self._settings[key] = value

    def is_debug(self) -> bool:
        return self._settings.get("debug_mode", False)
    
    def get_project_name(self) -> str:
        return self._settings.get("project_name", "Unknown Project")
    
    def get_banner_template(self) -> str:
        # قالب کامل بنر شامل خط چین و نوی‌لاین
        return self._settings.get("project_banner_template", "{project_name}\n")
    
    def get_system_log_template(self) -> str:
        return self._settings.get("system_log_template", "[{project_name}] [{level}] {message}")
    
    def get_banner_color_code(self) -> str:
        return self._settings.get("banner_color_code", "33") # پیش‌فرض زرد
    
    def get_system_log_color_code(self) -> str:
        return self._settings.get("system_log_color_code", "96") # پیش‌فرض آبی روشن