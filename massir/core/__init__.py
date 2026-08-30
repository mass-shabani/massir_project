"""
Core module for the Massir framework.

This module exports all core classes and functions needed by the
application and module developers.
"""

from .app import App
from .interfaces import IModule, ModuleContext
from .registry import ModuleRegistry
from .core_apis import CoreLoggerAPI, CoreConfigAPI
from .hook_types import SystemHook
from .hooks import Hook, HooksManager
from .module_loader import ModuleLoader
from .api import initialize_core_services
from .log import print_banner, DefaultLogger
from .path import Path
from .run_order_group import (
    RunOrderGroupManager,
    RunOrderGroup,
    ModuleInfo,
    RunAtRegistry,
)
from .exceptions import (
    FrameworkError,
    ModuleLoadError,
    DependencyResolutionError
)

__all__ = [
    # Core application
    'App',
    
    # Module interfaces
    'IModule',
    'ModuleContext',
    
    # Services
    'ModuleRegistry',
    'CoreLoggerAPI',
    'CoreConfigAPI',
    
    # Hooks
    'SystemHook',
    'Hook',
    'HooksManager',
    
    # Module loading
    'ModuleLoader',
    'ModuleInfo',
    'RunOrderGroup',
    'RunOrderGroupManager',
    'RunAtRegistry',
    
    # Utilities
    'initialize_core_services',
    'print_banner',
    'DefaultLogger',
    'Path',
    
    # Exceptions
    'FrameworkError',
    'ModuleLoadError',
    'DependencyResolutionError',
]