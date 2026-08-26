"""
System hook types for framework lifecycle events.

This module defines the SystemHook enum which covers core framework
lifecycle events only. Module-specific hooks should be created as
Hook instances (see hooks.py) by the relevant modules.

Design principle:
- SystemHook: Core framework lifecycle events (defined here)
- Hook: Module-defined custom hooks (defined in hooks.py)
"""

from enum import Enum


class SystemHook(Enum):
    """
    System hook types for core framework lifecycle events.
    
    These hooks are triggered by the framework core during specific
    lifecycle phases. Modules can register callbacks for these events
    to react to framework state changes.
    
    Note: Module-specific events should be defined as Hook instances
    by the relevant modules, not added to this enum.
    """
    
    # Application lifecycle events
    ON_SETTINGS_LOADED = "on_settings_loaded"
    """Triggered when settings are loaded and available."""
    
    ON_APP_BOOTSTRAP_START = "on_app_bootstrap_start"
    """Triggered when application bootstrap process starts."""
    
    ON_APP_BOOTSTRAP_END = "on_app_bootstrap_end"
    """Triggered when application bootstrap process completes."""
    
    ON_ALL_MODULES_STARTED = "on_all_modules_started"
    """Triggered when all modules from all run order groups have started."""
    
    ON_SHUTDOWN_REQUEST = "on_shutdown_request"
    """Triggered when a shutdown is requested via request_shutdown()."""
    
    ON_RESTART_REQUEST = "on_restart_request"
    """Triggered when a restart is requested via request_restart()."""
    
    # Run order group lifecycle events
    ON_GROUP_START = "on_group_start"
    """Triggered when a run order group starts executing. Receives group name."""
    
    ON_GROUP_COMPLETE = "on_group_complete"
    """Triggered when a run order group completes execution. Receives group name."""
    
    ON_GROUP_STOP = "on_group_stop"
    """Triggered when a run order group is stopping. Receives group name."""
    
    # Module lifecycle events
    ON_MODULE_STARTED = "on_module_started"
    """Triggered when a module's start() method completes. Receives module instance."""
    
    ON_MODULE_STOPPED = "on_module_stopped"
    """Triggered when a module's stop() method completes. Receives module instance."""
    
    # Service lifecycle events
    ON_SERVICE_REGISTERED = "on_service_registered"
    """Triggered when a service is registered. Receives service name and instance."""
    
    ON_SERVICE_REMOVED = "on_service_removed"
    """Triggered when a service is removed. Receives service name."""
    
    # Error handling
    ON_ERROR = "on_error"
    """Triggered when an error occurs. Receives error and context info."""