import os
from pathlib import Path

class Config:
    """
    تنظیمات پایهٔ پروژه
    """

    BASE_DIR = Path(__file__).parent.parent
    MODULES_DIR = BASE_DIR / "modules"

    @classmethod
    def get_modules_path(cls) -> Path:
        return cls.MODULES_DIR

    @classmethod
    def is_dev(cls) -> bool:
        return os.getenv("ENV", "dev") == "dev"
