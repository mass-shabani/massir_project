# massir/core/settings_manager.py
"""
مدیریت تنظیمات پروژه
"""
import json
import os
from pathlib import Path
from typing import Optional

from massir.core.core_apis import CoreConfigAPI, CoreLoggerAPI
from massir.core.settings_default import (
    get_default_settings,
    DEFAULT_SETTINGS,
    DefaultConfig,
)
from massir.core.log import DefaultLogger, _FallbackConfig

class SettingsManager(CoreConfigAPI):
    """
    مدیریت تنظیمات پروژه
    
    ترتیب اولویت:
    1. Defaults (مقادیر پیش‌فرض)
    2. Settings from JSON (فایل)
    3. User Code (initial_settings) - بالاترین اولویت
    """
    
    # لاگر کلاسی - برای لاگ کردن قبل از ثبت logger اصلی
    _class_logger: Optional[CoreLoggerAPI] = None
    
    @classmethod
    def set_logger(cls, logger_api: CoreLoggerAPI):
        """تنظیم logger برای استفاده در کلاس"""
        cls._class_logger = logger_api
    
    def _log(self, message: str, level: str = "ERROR"):
        """لاگ کردن با logger کلاسی یا لاگر موقت"""
        if SettingsManager._class_logger:
            SettingsManager._class_logger.log(message, level=level, tag="config")
        else:
            print(f"[{level}] [config] {message}")
    
    def __init__(self, settings_path: str = "app_settings.json", initial_settings: Optional[dict] = None):
        """
        Args:
            settings_path: مسیر فایل JSON
            initial_settings: تنظیمات کد (بالاترین اولویت)
        """
        # 1. مقادیر پیش‌فرض
        self._settings = get_default_settings()
        
        # 2. خواندن از JSON
        self._load_settings(settings_path)
        
        # 3. تنظیمات کد (بالاترین اولویت)
        if initial_settings:
            self.update_settings(initial_settings)
    
    def _load_settings(self, path: str):
        """خواندن تنظیمات از فایل JSON با مدیریت خطا"""
        full_path = Path(path)
        if full_path.exists():
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    self.update_settings(json_data)
            except json.JSONDecodeError as e:
                self._log(f"Invalid JSON in {full_path}: {e}")
                self._log("Skipping settings file. Using default settings.")
            except Exception as e:
                self._log(f"Failed to load settings from {full_path}: {e}")
                self._log("Skipping settings file. Using default settings.")
    
    def get(self, key: str, default=None):
        """دریافت مقدار با پشتیبانی از کلیدهای تو در تو"""
        keys = key.split('.')
        value = self._settings
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value):
        """تنظیم مقدار"""
        keys = key.split('.')
        current = self._settings
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    def update_settings(self, new_settings: dict):
        """ادغام تنظیمات جدید با تنظیمات فعلی"""
        for key, value in new_settings.items():
            if isinstance(value, dict) and isinstance(self._settings.get(key), dict):
                self._settings[key].update(value)
            else:
                self._settings[key] = value
    
    # --- تنظیمات سیستم ---
    def get_modules_dir(self) -> list:
        """دریافت مسیرهای ماژول‌ها (فرمت قدیمی - برای سازگاری)"""
        val = self.get("system.modules_dir")
        if isinstance(val, str):
            return [val]
        return val if isinstance(val, list) else ["./massir/modules"]
    
    def get_modules_config(self) -> list:
        """دریافت تنظیمات ماژول‌ها (فرمت جدید با path و names)"""
        val = self.get("system.modules", [])
        if not isinstance(val, list):
            return []
        return val
    
    # --- تنظیمات لاگ ---
    def show_logs(self) -> bool:
        return self.get("logs.show_logs", True)
    
    def show_banner(self) -> bool:
        return self.get("logs.show_banner", True)
    
    def get_hide_log_levels(self) -> list:
        val = self.get("logs.hide_log_levels")
        if isinstance(val, list):
            return val
        return []
    
    def get_hide_log_tags(self) -> list:
        val = self.get("logs.hide_log_tags")
        if isinstance(val, list):
            return val
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
        return self.get("template.project_banner_template", "{project_name}\n")
    
    def get_system_log_template(self) -> str:
        return self.get("template.system_log_template", "[{level}] {message}")
    
    def get_banner_color_code(self) -> str:
        return self.get("template.banner_color_code", "33")
    
    def get_system_log_color_code(self) -> str:
        return self.get("template.system_log_color_code", "96")

