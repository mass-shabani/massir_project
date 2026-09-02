# Changelog

All notable changes to the Massir framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0 Alpha] - 2026-09-02

### Core Architecture

#### Run Order Groups System
- **Added**: `RunOrderGroupManager` as the primary module execution orchestrator
- **Added**: `RunAtRegistry` for dynamic validation and registration of `run_at` values
- **Added**: `RunOrderGroup` dataclass representing module execution groups
- **Added**: `ModuleInfo` dataclass for discovered module metadata
- **Changed**: Module loading system completely redesigned from type-based (system/application) to group-based execution
- **Changed**: `app_settings.json` group entries now support `name`, `run_at`, `path`, and `names` parameters
- **Changed**: Modules execute in sequential group order; shutdown executes in reverse
- **Changed**: Groups can target specific system hook trigger points via `run_at` parameter
- **Changed**: Default `run_at` value is `"on_start"` (executed during bootstrap)

#### Module Interface Simplification
- **Removed**: `IModule.load()` method — logic merged into `start()`
- **Removed**: `IModule.ready()` method — replaced by hook system
- **Changed**: `IModule` now provides only `start()` and `stop()` lifecycle methods (both optional)
- **Changed**: Module metadata (`name`, `id`, `provides`, `requires`) populated from `manifest.json` at instantiation

#### ModuleLoader Refactoring
- **Changed**: `ModuleLoader` reduced to lightweight utility class
- **Changed**: Module discovery logic moved to `RunOrderGroupManager.discover_modules_for_group()`
- **Changed**: Dependency sorting moved to `RunOrderGroupManager._sort_by_dependencies()`
- **Changed**: Module starting/stopping moved to `RunOrderGroupManager.execute_group()` and `shutdown_all_groups()`
- **Changed**: `instantiate()` now accepts dictionary-based module info instead of positional arguments
- **Removed**: System/application module type distinction from loader

### Hook System

#### Extended Hook Architecture
- **Added**: `Hook` class for module-defined custom hook types
- **Added**: `HooksManager` now supports both `SystemHook` (enum) and `Hook` (custom) instances
- **Added**: `App.register_hook()` accepts both `SystemHook` and `Hook` types
- **Added**: `App.trigger_hook()` for dispatching custom hooks
- **Added**: `HooksManager.set_logger()` for error logging during dispatch
- **Added**: `hooks.get_registered_hooks()` for introspection
- **Added**: `hooks.is_coroutine_function()` compatibility helper (replaces deprecated `asyncio.iscoroutinefunction`)
- **Changed**: `SystemHook.ON_MODULE_LOADED` renamed to `SystemHook.ON_MODULE_STARTED`
- **Changed**: Auto-callback registration for `run_at` groups matching non-default system hooks

#### New SystemHook Events
- **Added**: `ON_SETTINGS_LOADED` - triggered when settings are loaded
- **Added**: `ON_APP_BOOTSTRAP_START` - triggered at bootstrap start
- **Added**: `ON_APP_BOOTSTRAP_END` - triggered at bootstrap completion
- **Added**: `ON_ALL_MODULES_STARTED` - triggered after all groups complete
- **Added**: `ON_GROUP_START` / `ON_GROUP_COMPLETE` / `ON_GROUP_STOP` - group lifecycle
- **Added**: `ON_MODULE_STARTED` / `ON_MODULE_STOPPED` - module lifecycle
- **Added**: `ON_SERVICE_REGISTERED` / `ON_SERVICE_REMOVED` - service registry events
- **Added**: `ON_ERROR` - global error handler
- **Added**: `ON_SHUTDOWN_REQUEST` / `ON_RESTART_REQUEST` - lifecycle requests

### Configuration System

#### Four-Tier Priority System
- **Added**: Module defaults layer as lowest priority (below core defaults)
- **Added**: `SettingsManager.register_module_defaults()` class method for module default registration
- **Added**: `SettingsManager.apply_module_defaults()` instance method for runtime injection
- **Changed**: Priority order: Module Defaults → Core Defaults → JSON File → User Code
- **Changed**: `app_settings.json` no longer uses `"type"` field in module groups
- **Changed**: New required fields in module groups: `"name"` (optional, auto-generated), `"run_at"` (optional, defaults to `"on_start"`)

#### Default Settings Changes
- **Changed**: `debug_mode` default changed from `True` to `False` (production-ready)
- **Added**: `show_critical_levels` parameter (default: `3`) for fine-grained critical level visibility
- **Changed**: CORE log level auto-hidden when `debug_mode` is `False`
- **Changed**: Default log template updated to `"{timestamp}|{level}:\t\b[{tag}] {message}"`
- **Removed**: Color code settings (`banner_color_code`, `system_log_color_code`) from core defaults
- **Removed**: `"type"` field from module group configuration schema
- **Changed**: Project version updated to `"0.2.0 Alpha"`

### Logging System

#### Core Logger Updates
- **Changed**: `DefaultLogger.log()` now includes timestamp and tag in formatted output
- **Added**: `_SafeFormatDict` for safe template formatting with missing keys
- **Changed**: `log_internal()` utility removed — replaced with direct `CoreLoggerAPI` calls
- **Changed**: `CoreConfigAPI` now includes `get_system_log_template()` and `get_banner_template()`
- **Removed**: Color-specific methods (`get_banner_color`, `get_log_color`, `get_print_color`) from `CoreConfigAPI`
- **Changed**: Human-readable color names (e.g., `"bright_cyan"`) replace numeric ANSI codes in configuration

#### System Logger Module Restructure (brief)
- **Added**: New `core/` subdirectory with `colors.py`, `defaults.py`, `logger.py` modules
- **Added**: `SystemLoggerDefaults` dataclass for centralized defaults injection
- **Added**: Extended `Colors` class with 256-color palette and true color support
- **Added**: Background color support for all log elements
- **Changed**: `manifest.json` version updated to `0.3`, removed `type` field
- **Changed**: HTTP request formatting logic extracted to separate location

### Core API Changes

- **Changed**: `CoreConfigAPI` abstract methods reduced to essential interface (`get`, `get_system_log_template`, `get_banner_template`)
- **Changed**: `CoreLoggerAPI` interface maintained with `log()` and `print()` methods
- **Added**: `App._bootstrap_phases()` restructured for hook-based execution flow
- **Changed**: `App._shutdown_all()` dispatches `ON_SHUTDOWN_REQUEST` before stopping groups
- **Changed**: Background task management integrated with hook system

### Bug Fixes

- **Fixed**: Module metadata no longer duplicated between class attributes and manifest
- **Fixed**: Logger reference updates in `App` now use mutable list pattern correctly
- **Fixed**: Template formatting with missing keys no longer raises exceptions
- **Fixed**: Windows ANSI color support initialization

### Migration Guide

#### From 0.1.x to 0.2.0

**1. Update `app_settings.json`:**
```json
// Before
{
    "modules": [
        {"path": "...", "type": "systems", "names": [...]}
    ]
}

// After
{
    "modules": [
        {"name": "my_group", "path": "...", "names": [...], "run_at": "on_start"}
    ]
}
```

**2. Update module implementations:**
```python
# Before
class MyModule(IModule):
    async def load(self, context): ...
    async def start(self, context): ...
    async def ready(self, context): ...
    async def stop(self, context): ...

# After
class MyModule(IModule):
    async def start(self, context): ...  # load() logic merged here
    async def stop(self, context): ...
```

**3. Update manifest.json:**
```json
// Before
{"name": "...", "type": "system", "entrypoint": "...", ...}

// After
{"name": "...", "entrypoint": "...", "provides": [...], "requires": [...], ...}
```

**4. Replace `ready()` functionality with hooks:**
```python
# Before
async def ready(self, context):
    # Post-start logic
    ...

# After
async def start(self, context):
    app = context.get_app()
    app.register_hook(SystemHook.ON_ALL_MODULES_STARTED, self._on_ready)

async def _on_ready(self):
    # Post-start logic
    ...
```

**5. Update log configuration:**
```json
// Before
{
    "logs": {"debug_mode": true},
    "template": {"system_log_color_code": "96"}
}

// After
{
    "logs": {"debug_mode": false, "show_critical_levels": 3}
}
```

## [0.1.0] - 2026-02-24

### Initial Release
- Initial alpha release of the Massir framework
- Basic module loading with system/application distinction
- Core services (config, logger, path) initialization
- Basic hook system with limited lifecycle events
- Default logger with template support
- Module discovery from configured paths
- Dependency resolution and topological sorting