import importlib
import json
from pathlib import Path

from .config import Config
from .exceptions import ModuleLoadError

class ModuleLoader:
    """
    بارگذاری ماژول‌ها
    """

    def __init__(self):
        self.modules_dir = Config.get_modules_path()

    def list_modules(self) -> list[Path]:
        """
        لیست دایرکتوری ماژول‌ها
        """
        return [p for p in self.modules_dir.iterdir() if p.is_dir()]

    def load_setting(self, module_path: Path) -> dict:
        """
        خواندن setting.json ماژول
        """
        config_file = module_path / "setting.json"
        if not config_file.exists():
            raise ModuleLoadError(f"setting.json not found in {module_path}")
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def import_entrypoint(self, module_path: Path, entrypoint: str) -> object:
        """
        import کردن کلاس اصلی ماژول
        """
        # entrypoint example: "calendar_module.py::CalendarUIModule"
        file, cls = entrypoint.split("::")
        file = file.replace(".py", "")
        module_name = f"app.modules.{module_path.name}.{file}"
        try:
            mod = importlib.import_module(module_name)
            return getattr(mod, cls)
        except Exception as e:
            raise ModuleLoadError(f"Cannot import entrypoint {entrypoint}: {e}")
