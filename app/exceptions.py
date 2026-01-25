class ModuleLoadError(Exception):
    """خطا هنگام بارگذاری ماژول"""
    pass

class ServiceNotFoundError(Exception):
    """وقتی سرویسی ثبت نشده باشد"""
    pass

class EventHandleError(Exception):
    """خطا هنگام اجرای Event Handler"""
    pass
