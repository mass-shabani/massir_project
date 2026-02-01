import os
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
    ⭐ تگ پیش‌فرض "core" است و به لاگر ارسال می‌شود تا فیلتر شود.
    """
    logger_api.log(message, level="INFO", tag=tag)