# ⭐ ایمپورت از نیم‌اسپیس massir
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.registry import ModuleRegistry
from massir.core.config import SettingsManager, DefaultLogger

def initialize_core_services(registry: ModuleRegistry):
    """ساخت و رجیستر کردن سرویس‌های پیش‌فرض هسته"""
    config_api = SettingsManager()
    logger_api = DefaultLogger(config_api)
    
    registry.set("core_config", config_api)
    registry.set("core_logger", logger_api)
    
    return logger_api, config_api