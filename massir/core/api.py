# massir/core/api.py
"""
رابط‌های اصلی و سرویس‌های هسته
"""
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.registry import ModuleRegistry
from massir.core.config import SettingsManager, DefaultLogger
from massir.core.path import Path
import os
from typing import Optional

def initialize_core_services(
    registry: ModuleRegistry,
    initial_settings: Optional[dict] = None,
    settings_path: str = "__dir__",
    app_dir: Optional[str] = None
):
    """
    ساخت و رجیستر کردن سرویس‌های هسته
    
    Args:
        registry: رجیستری ماژول
        initial_settings: تنظیمات کد (بالاترین اولویت)
        settings_path: مسیر فایل تنظیمات JSON
        app_dir: مسیر پوشه برنامه کاربر
    """
    # ساخت شیء Path
    path_manager = Path(app_dir)
    
    # حل مسیر فایل تنظیمات
    if settings_path == "__cwd__":
        full_settings_path = path_manager.resolve("app")
    elif settings_path == "__dir__":
        full_settings_path = path_manager.resolve("app")
    elif not os.path.isabs(settings_path):
        full_settings_path = path_manager.resolve("app") / settings_path
    else:
        full_settings_path = settings_path
    
    # ابتدا DefaultLogger را با کانفیگ پیش‌فرض بساز
    # این لاگر برای لاگ کردن خطاها در حین لود تنظیمات استفاده می‌شود
    logger_api = DefaultLogger(None)  # None = از fallback استفاده کن
    
    # ثبت logger در SettingsManager برای استفاده در کلاس
    SettingsManager.set_logger(logger_api)
    
    # حالا SettingsManager را بساز (اگر خطای JSON باشد، با logger لاگ می‌شود)
    config_api = SettingsManager(str(full_settings_path), initial_settings=initial_settings)
    
    # به‌روزرسانی logger با کانفیگ صحیح (چون حالا کانفیگ لود شده)
    logger_api.config = config_api
    
    # رجیستر سرویس‌ها
    registry.set("core_config", config_api)
    registry.set("core_logger", logger_api)
    registry.set("core_path", path_manager)
    
    return logger_api, config_api, path_manager
