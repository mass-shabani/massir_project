# core/__init__.py

from .kernel import Kernel, ModuleContext
from .interfaces import IModule
from .registry import ModuleRegistry
from .exceptions import (
    FrameworkError,
    ModuleLoadError,
    DependencyResolutionError
)

# لیست کلاس‌ها و توابعی که وقتی کسی import core می‌کند، در دسترس هستند
__all__ = [
    'Kernel',
    'ModuleContext',
    'IModule',
    'ModuleRegistry',
    'FrameworkError',
    'ModuleLoadError',
    'DependencyResolutionError'
]