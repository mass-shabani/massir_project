from typing import Any, Dict

class BaseModule:
    """
    قرارداد (Interface) پایه برای ماژول‌ها
    """

    def setup(self, manager: "CoreManager"):
        """
        زمان load شدن ماژول، setup ماژول اجرا می‌شود.
        :param manager: رفرنس به CoreManager
        """
        raise NotImplementedError

    def shutdown(self):
        """
        زمان unload شدن ماژول
        """
        raise NotImplementedError

    def services(self) -> Dict[str, Any]:
        """
        سرویس‌هایی که این ماژول ارائه می‌دهد
        """
        return {}
