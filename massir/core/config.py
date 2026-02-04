import json
import os
from pathlib import Path
from typing import Optional

from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI

class SettingsManager(CoreConfigAPI):
    def __init__(self, settings_path: str = "app_settings.json", initial_settings: Optional[dict] = None):
        """
        ترتیب اولویت:
        1. Defaults (کد سخت‌کد شده)
        2. Settings from JSON (فایل)
        3. User Code (initial_settings) - بالاترین اولویت
        """
        # 1.
        self._settings = self._get_defaults()
        
        # 2.
        self._load_settings(settings_path)
        
        # 3. (Code overrides JSON)
        if initial_settings:
            self.update_settings(initial_settings)

    def _get_defaults(self) -> dict:
        return {
            "system": {
                "modules_dir": ["./massir/modules"]
            },
            "logs": {
                "show_logs": True,
                "show_banner": True,
                "hide_log_levels": [],
                "hide_log_tags": [],
                "debug_mode": True
            },
            "information": {
                "project_name": "Massir Framework",
                "project_version": "0.0.3 alpha",
                "project_info": "Modular Application Architecture"
            },
            "template": {
                "project_banner_template": "\n\t{project_name}\n\t{project_version}\n\t{project_info}\n",
                "system_log_template": "[{level}]\t{message}",
                "banner_color_code": "33",
                "system_log_color_code": "96"
            },
        }

    def _load_settings(self, path: str) -> dict:
        full_path = Path(path)
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                self.update_settings(json_data)
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
        keys = key.split('.')
        current = self._settings
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def update_settings(self, new_settings: dict):
        """ادغام یک دیکشنری جدید با تنظیمات فعلی"""
        for key, value in new_settings.items():
            if isinstance(value, dict) and isinstance(self._settings.get(key), dict):
                self._settings[key].update(value)
            else:
                self._settings[key] = value

    # --- تنظیمات سیستم ---
    def get_modules_dir(self) -> list:
        val = self.get("system.modules_dir")
        if isinstance(val, str): return [val]
        return val if isinstance(val, list) else ["./massir/modules"]

    # --- تنظیمات لاگ (Logs) ---
    def show_logs(self) -> bool:
        return self.get("logs.show_logs", True)
    
    def show_banner(self) -> bool:
        return self.get("logs.show_banner", True)

    def get_hide_log_levels(self) -> list:
        val = self.get("logs.hide_log_levels")
        if isinstance(val, list): return val
        return []

    def get_hide_log_tags(self) -> list:
        val = self.get("logs.hide_log_tags")
        if isinstance(val, list): return val
        return []

    def is_debug(self) -> bool:
        return self.get("logs.debug_mode", True)

    # --- اطلاعات پروژه ---
    def get_project_name(self) -> str:
        return self.get("information.project_name", "Unknown Project")
    
    def get_project_version(self) -> str:
        return self.get("information.project_version", "1.0.0")
    
    def get_project_info(self) -> str:
        return self.get("information.project_info", "")

    # --- تمپلیت‌ها ---
    def get_banner_template(self) -> str:
        template = self.get("template.project_banner_template", "{project_name}\n")
        return template

    def get_system_log_template(self) -> str:
        return self.get("template.system_log_template", "[{level}] {message}")
    
    def get_banner_color_code(self) -> str:
        return self.get("template.banner_color_code", "33")
    
    def get_system_log_color_code(self) -> str:
        return self.get("template.system_log_color_code", "96")

# --- مقادیر پیش‌فرض ---
class DefaultConfig(CoreConfigAPI):
    def get(self, key: str): return None

class DefaultLogger(CoreLoggerAPI):
    """
    لاگر پیش‌فرض ساده.
    ⭐ آپدیت شده تا آرگومان‌های اضافی (مثل level_color) را نادیده بگیرد و کرش نکند.
    """
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api

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

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None, **kwargs):
        """
        متد لاگ با پشتیبانی از **kwargs** برای جلوگیری از کرش.
        اگر آرگومان‌های رنگ (level_color و ...) دریافت شوند، این کلاس آن‌ها را نادیده می‌گیرد.
        """
        if not self._should_log(level, tag):
            return

        if os.name == 'nt':
            os.system('')

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