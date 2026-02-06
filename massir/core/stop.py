import asyncio
from typing import List, Dict, Optional
# ⭐ ایمپورت از نیم‌اسپیس massir
from massir.core.interfaces import IModule
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI
from massir.core.log import log_internal

async def shutdown(modules: Dict[str, IModule], background_tasks: List[asyncio.Task], 
                  config_api: CoreConfigAPI, logger_api: CoreLoggerAPI,
                  system_module_names: Optional[List[str]] = None,
                  app_module_names: Optional[List[str]] = None):
    """
    اجرای مراحل توقف برنامه
    
    Args:
        modules: دیکشنری تمام ماژول‌ها
        background_tasks: لیست تسک‌های پس‌زمینه
        config_api: API تنظیمات
        logger_api: API لاگر
        system_module_names: لیست نام ماژول‌های سیستمی (اختیاری)
        app_module_names: لیست نام ماژول‌های کاربردی (اختیاری)
    """
    log_internal(config_api, logger_api, "🛑 Shutting down framework...")
    
    # کنسل کردن تسک‌های پس‌زمینه
    for task in background_tasks:
        if not task.done():
            task.cancel()
    
    # اگر لیست‌های نام ماژول‌ها ارائه شده، از ترتیب صحیح استفاده کن
    if system_module_names is not None and app_module_names is not None:
        # استاپ ماژول‌های کاربردی به ترتیب معکوس
        log_internal(config_api, logger_api, "Stopping Application Modules...", tag="core")
        for mod_name in reversed(app_module_names):
            if mod_name in modules:
                try:
                    await modules[mod_name].stop(modules[mod_name]._context)
                    logger_api.log(f"Application module '{mod_name}' stopped", level="INFO", tag="core")
                except Exception as e:
                    logger_api.log(f"Error stopping application module '{mod_name}': {e}", level="ERROR", tag="core")
        
        # استاپ ماژول‌های سیستمی به ترتیب معکوس
        log_internal(config_api, logger_api, "Stopping System Modules...", tag="core")
        for mod_name in reversed(system_module_names):
            if mod_name in modules:
                try:
                    await modules[mod_name].stop(modules[mod_name]._context)
                    logger_api.log(f"System module '{mod_name}' stopped", level="INFO", tag="core")
                except Exception as e:
                    logger_api.log(f"Error stopping system module '{mod_name}': {e}", level="ERROR", tag="core")
    else:
        # حالت سازگار با نسخه‌های قبلی: استاپ همه ماژول‌ها به ترتیب معکوس
        log_internal(config_api, logger_api, "Stopping Modules (legacy mode)...", tag="core")
        for instance in reversed(list(modules.values())):
            try:
                await instance.stop(instance._context)
            except Exception as e:
                logger_api.log(f"Error stopping module {instance.name}: {e}", level="ERROR", tag="core")