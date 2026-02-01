from core.config import SettingsManager, DefaultLogger, DefaultConfig
from core.registry import ModuleRegistry
from core.system_apis import CoreLoggerAPI, CoreConfigAPI

def initialize_core_services(registry: ModuleRegistry):
    """ساخت و رجیستر کردن سرویس‌های پیش‌فرض هسته"""
    config_api = SettingsManager()
    logger_api = DefaultLogger(config_api)
    
    registry.set("core_config", config_api)
    registry.set("core_logger", logger_api)
    
    return logger_api, config_api