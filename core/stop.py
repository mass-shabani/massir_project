import asyncio
from typing import List, Dict
from core.interfaces import IModule
from core.system_apis import CoreLoggerAPI, CoreConfigAPI
from core.log import log_internal

async def shutdown(modules: Dict[str, IModule], background_tasks: List[asyncio.Task], 
                  config_api: CoreConfigAPI, logger_api: CoreLoggerAPI):
    """اجرای مراحل توقف برنامه"""
    log_internal(config_api, logger_api, "🛑 Shutting down framework...")
    
    # کنسل کردن تسک‌های پس‌زمینه
    for task in background_tasks:
        if not task.done():
            task.cancel()
            
    # استاپ ماژول‌ها به ترتیب معکوس
    for instance in reversed(list(modules.values())):
        try:
            await instance.stop(instance._context)
        except Exception as e:
            logger_api.log(f"Error stopping module {instance.name}: {e}", level="ERROR")