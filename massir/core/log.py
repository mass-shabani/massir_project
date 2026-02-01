import os
from massir.core.core_apis import CoreLoggerAPI, CoreConfigAPI

def print_banner(config_api: CoreConfigAPI):
    """چاپ بنر پروژه بر اساس تنظیمات"""
    template = config_api.get_banner_template()
    project_name = config_api.get_project_name()
    banner_content = template.format(project_name=project_name)
    color_code = config_api.get_banner_color_code()
    
    if os.name == 'nt': os.system('')
    
    color_start = f'\033[{color_code}m'
    reset_code = '\033[0m'
    print(f"{color_start}{banner_content}{reset_code}")

def log_internal(config_api: CoreConfigAPI, logger_api: CoreLoggerAPI, message: str):
    """چاپ پیام‌های داخلی هسته با چک کردن دیباگ"""
    if not config_api.is_debug():
        return
    logger_api.log(message, level="INFO")