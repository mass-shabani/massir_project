# massir/core/log.py
"""
توابع و کلاس‌های مربوط به لاگینگ
"""
import os
from typing import Optional
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI

def print_banner(config_api: CoreConfigAPI):
    if not config_api.show_banner():
        return
    template = config_api.get_banner_template()
    project_name = config_api.get_project_name()
    project_version = config_api.get_project_version()
    project_info = config_api.get_project_info()
    
    banner_content = template.format(
        project_name=project_name,
        project_version=project_version,
        project_info=project_info
    )
    color_code = config_api.get_banner_color_code()
    if os.name == 'nt': os.system('')
    color_start = f'\033[{color_code}m'
    reset_code = '\033[0m'
    print(f"{color_start}{banner_content}{reset_code}")

def log_internal(config_api: CoreConfigAPI, logger_api: CoreLoggerAPI, message: str, tag: str = "core"):
    """
    چاپ پیام‌های داخلی هسته.
    """
    logger_api.log(message, level="INFO", tag=tag)

# --- کلاس‌های کمکی برای لاگ ---

class _FallbackLogger:
    """
    لاگر موقت برای زمانی که logger اصلی وجود ندارد.
    از این کلاس زمانی استفاده می‌شود که DefaultLogger با config_api=None ساخته شود.
    """
    def log(self, message: str, level: str = "INFO", tag: Optional[str] = None, **kwargs):
        level_prefix = f"[{level}]" if level else ""
        tag_prefix = f" [{tag}]" if tag else ""
        print(f"{level_prefix}{tag_prefix} {message}")

class _FallbackConfig:
    """
    کانفیگ fallback برای زمانی که کانفیگ اصلی وجود ندارد.
    """
    def get_project_name(self) -> str:
        return "Massir"
    
    def get_system_log_template(self) -> str:
        return "[{level}]\t{message}"
    
    def get_system_log_color_code(self) -> str:
        return "96"
    
    def is_debug(self) -> bool:
        return True
    
    def show_logs(self) -> bool:
        return True
    
    def get_hide_log_levels(self) -> list:
        return []
    
    def get_hide_log_tags(self) -> list:
        return []
    
    def show_banner(self) -> bool:
        return True
    
    def get_banner_template(self) -> str:
        return "{project_name}\n"
    
    def get_banner_color_code(self) -> str:
        return "33"
