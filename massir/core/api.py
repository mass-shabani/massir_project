# ایمپورت از نیم‌اسپیس massir
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.registry import ModuleRegistry
from massir.core.config import SettingsManager, DefaultLogger
from typing import Optional

def initialize_core_services(registry: ModuleRegistry, initial_settings: Optional[dict] = None):
    """ساخت و رجیستر کردن سرویس‌های هسته با اولویت صحیح تنظیمات"""
    # ابتدا SettingsManager را با تمام تنظیمات (JSON + Code) می‌سازیم
    config_api = SettingsManager("app_settings.json", initial_settings=initial_settings)
    
    # لاگر را با کانفیگ صحیح می‌سازیم
    logger_api = DefaultLogger(config_api)
    
    registry.set("core_config", config_api)
    registry.set("core_logger", logger_api)
    
    return logger_api, config_api
