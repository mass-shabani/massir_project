import json
import os
from pathlib import Path
from typing import Optional

from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI

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

    # --- تنظیمات سیستم ---
    def get_modules_dir(self) -> list:
        val = self.get("system.modules_dir", ["./modules"])
        # اگر کاربر یه رشته مسیر داده، داخل لیست می‌گذاریم تا حلقه روی آن کار کند
        if isinstance(val, str):
            return [val]
        return val

    # --- تنظیمات لاگ (Logs) ---
    def show_logs(self) -> bool:
        return self.get("logs.show_logs", True)
    
    def show_banner(self) -> bool:
        return self.get("logs.show_banner", True)

    def get_hide_log_levels(self) -> list:
        """سطوحی که نباید نمایش داده شوند (مثلا ['DEBUG'])"""
        val = self.get("logs.hide_log_levels")
        # ⭐ بررسی نوع: اگر لیست نیست، لیست خالی برگردان
        if isinstance(val, list):
            return val
        return []

    def get_hide_log_tags(self) -> list:
        """تگ‌هایی که نباید نمایش داده شوند"""
        val = self.get("logs.hide_log_tags")
        # ⭐ بررسی نوع: اگر لیست نیست، لیست خالی برگردان
        if isinstance(val, list):
            return val
        return []

    def is_debug(self) -> bool:
        """
        حالت دیباگ:
        طبق درخواست: فقط اجازه خروجی خطاها، هشدارها و اکسپشن‌ها را می‌دهد.
        """
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
    """لاگر پیش‌فرض با منطق فیلترینگ جدید و کنترل خطا"""
    def __init__(self, config_api: CoreConfigAPI):
        self.config = config_api

    def _should_log(self, level: str, tag: Optional[str] = None) -> bool:
        """
        بررسی اینکه آیا پیام باید چاپ شود.
        """
        config = self.config

        if not config.show_logs():
            return False

        if tag:
            hidden_tags = config.get_hide_log_tags()
            # از all() استفاده می‌کنیم تا مطمئن شویم hidden_tags لیست است
            if isinstance(hidden_tags, list) and tag in hidden_tags:
                return False

        hidden_levels = config.get_hide_log_levels()
        # ⭐ بررسی نوع قبل از استفاده در دستور in
        if isinstance(hidden_levels, list):
            if level in hidden_levels:
                return False

        critical_levels = ["ERROR", "WARNING", "EXCEPTION", "CRITICAL"]
        if level in critical_levels:
            if not config.is_debug():
                return False

        return True

    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None):
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