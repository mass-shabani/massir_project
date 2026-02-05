# massir/core/settings_default.py
"""
مقادیر پیش‌فرض تنظیمات
"""
from typing import Optional
from massir.core.core_apis import CoreConfigAPI

# مقادیر پیش‌فرض تنظیمات
DEFAULT_SETTINGS = {
    "system": {
        "modules": [
            {"path": "{massir_dir}", "names": []}
        ]
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

class DefaultConfig(CoreConfigAPI):
    """
    کلاس کانفیگ پیش‌فرض ساده.
    از این کلاس زمانی استفاده می‌شود که کانفیگ اصلی وجود ندارد.
    """
    def get(self, key: str) -> None:
        """همیشه None برمی‌گرداند"""
        return None

def get_default_settings() -> dict:
    """
    دریافت مقادیر پیش‌فرض تنظیمات
    
    Returns:
        دیکشنری مقادیر پیش‌فرض
    """
    return DEFAULT_SETTINGS.copy()

def create_default_config() -> CoreConfigAPI:
    """
    ساخت یک نمونه از DefaultConfig
    
    Returns:
        نمونه DefaultConfig
    """
    return DefaultConfig()
