from typing import Type

class Event:
    """
    کلاس پایه برای Eventها
    """
    pass

class EventSystem:
    """
    Event System مرکزی که handlerها را نگه می‌دارد
    """

    def __init__(self):
        self._handlers: dict[Type[Event], list] = {}

    def register_handler(self, event_type: Type[Event], handler: object):
        """
        handler برای event_type مشخص ثبت می‌شود
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def dispatch(self, event: Event):
        """
        انتشار event به handlerهای ثبت شده
        """
        handlers = self._handlers.get(type(event), [])
        for handler in handlers:
            try:
                handler.handle(event)
            except Exception as e:
                # در صورت نیاز می‌توان لاگ خطا را اضافه کرد
                print(f"[EventSystem] Error dispatching {event}: {e}")
