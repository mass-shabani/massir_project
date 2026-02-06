# massir/core/path.py
"""
مدیریت مسیرهای پروژه
"""
from typing import Optional, Dict
from pathlib import Path as PathLib

class Path:
    """
    کلاس مدیریت مسیرهای پروژه
    
    این کلاس مسیرهای مختلف پروژه را نگهداری می‌کند و امکان
    تغییر و دسترسی به آنها را فراهم می‌کند.
    
    مسیرهای پیش‌فرض:
        - massir_dir: پوشه اصلی فریم‌ورک Massir
        - app_dir: پوشه برنامه کاربر (جایی که main.py قرار دارد)
    """
    
    def __init__(self, app_dir: Optional[str] = None):
        """
        Args:
            app_dir: مسیر پوشه برنامه کاربر
        """
        # تشخیص خودکار massir_dir
        # path.py در massir/core/path.py است
        # massir/__init__.py در massir/__init__.py است
        # پس باید 2 سطح بالا برویم
        self._massir_dir = PathLib(__file__).parent.parent.resolve()
        # تنظیم app_dir
        if app_dir:
            self._app_dir = PathLib(app_dir).resolve()
        else:
            self._app_dir = PathLib.cwd().resolve()
        
        # دیکشنری مسیرهای اضافی
        self._custom_paths: Dict[str, PathLib] = {}
    
    @property
    def massir(self) -> PathLib:
        """مسیر فریم‌ورک Massir (فقط خواندنی)"""
        return self._massir_dir
    
    @property
    def app(self) -> PathLib:
        """مسیر برنامه کاربر"""
        return self._app_dir
    
    def get(self, key: str) -> str:
        """
        دریافت مسیر به صورت رشته
        
        Args:
            key: نام مسیر (massir، app، یا نام سفارشی)
            
        Returns:
            رشته مسیر
        """
        if key in ("massir_dir", "massir"):
            return str(self._massir_dir)
        elif key in ("app_dir", "app"):
            return str(self._app_dir)
        elif key in self._custom_paths:
            return str(self._custom_paths[key])
        else:
            raise KeyError(f"Path '{key}' not found")
    
    def set(self, key: str, value: str):
        """
        تنظیم یا اضافه کردن مسیر
        
        Args:
            key: نام مسیر
            value: مقدار مسیر (رشته)
        """
        if key in ("massir_dir", "massir"):
            self._massir_dir = PathLib(value).resolve()
        elif key in ("app_dir", "app"):
            self._app_dir = PathLib(value).resolve()
        else:
            self._custom_paths[key] = PathLib(value).resolve()
    
    def resolve(self, key: str) -> PathLib:
        """
        دریافت مسیر به صورت PathLib
        
        Args:
            key: نام مسیر (massir، massir_dir، app، app_dir، یا نام سفارشی)
            
        Returns:
            شیء PathLib
        """
        if key in ("massir_dir", "massir"):
            return self._massir_dir
        elif key in ("app_dir", "app"):
            return self._app_dir
        elif key in self._custom_paths:
            return self._custom_paths[key]
        else:
            raise KeyError(f"Path '{key}' not found")
    
    def get_all_folders(self, base_key: str) -> list[str]:
        """
        دریافت لیست تمام پوشه‌های موجود در مسیر پایه
        
        Args:
            base_key: کلید مسیر پایه (مثل 'massir_dir' یا 'app_dir')
            
        Returns:
            لیست نام پوشه‌ها
        """
        base_path = self.resolve(base_key)
        if base_path.exists() and base_path.is_dir():
            return [f.name for f in base_path.iterdir() if f.is_dir()]
        return []
    
    def __str__(self) -> str:
        return f"Path(massir={self._massir_dir}, app={self._app_dir})"
    
    def __repr__(self) -> str:
        return self.__str__()
