# Massir Project Analysis Report

> For a quick overview and getting started, see the main [README.md](../README.md).

## 1. Project Description and Mission

**Massir** is a modular application framework for Python designed to enable developers to build scalable and maintainable applications through a plugin-based architecture. The framework's core mission is to provide a structured approach to application development by separating functionality into independent, self-contained modules.

### Core Philosophy

The framework is built on the principle of **modularity**, where complex applications are decomposed into smaller components that can be:
- **Loaded, started, and stopped independently** - Each module operates autonomously
- **Developed in parallel** - Teams can work on different modules simultaneously
- **Dynamically configured** - Modules can be enabled/disabled without modifying core code
- **Reused across projects** - Reducing development time through component sharing
- **Executed in controlled groups** - Run order groups provide precise execution timing

### Key Advantages
- **Separation of Concerns**: Each module handles specific application aspects
- **Flexible Composition**: Applications assembled from interchangeable modules
- **Easy Maintenance**: Changes to one module don't affect others
- **Independent Testing**: Modules can be tested in isolation
- **Trigger-Based Execution**: Modules can execute at specific lifecycle points

### Target Use Cases
- Web Applications and API Gateways
- Microservices Architecture
- Data Processing Pipelines
- IoT Applications
- Desktop Applications with plugin support
- Monitoring Systems

---

## 2. Technical Source Code Information and File Structure

### Repository Structure

```
massir_project/
├── .gitignore
├── Examples/                    # Example applications demonstrating usage
│   ├── basic_app_consumer/
│   ├── basic_website_example/
│   ├── database_example/
│   ├── encryption_example/
│   ├── module_loading_order/
│   ├── network_nodes_test_example/
│   ├── socket_example/
│   ├── ssl_example/
│   └── web_api_example/
├── README.md
├── Docs/
│   └── PROJECT_ANALYSIS.md     # This document
│   └── Changelog.md     
├── massir/                      # Core framework package
│   ├── __init__.py             # Main entry point (exports App)
│   ├── core/                    # Core system components
│   │   ├── __init__.py         # Core exports
│   │   ├── api.py              # Core services initialization
│   │   ├── app.py              # Main App class
│   │   ├── core_apis.py        # CoreConfigAPI, CoreLoggerAPI interfaces
│   │   ├── exceptions.py       # FrameworkError, ModuleLoadError, DependencyResolutionError
│   │   ├── hook_types.py       # SystemHook enum
│   │   ├── hooks.py            # Hook class, HooksManager
│   │   ├── interfaces.py       # IModule, ModuleContext
│   │   ├── log.py              # DefaultLogger, print_banner
│   │   ├── module_loader.py    # ModuleLoader (instantiate, check_requirements)
│   │   ├── path.py             # Path manager
│   │   ├── registry.py         # ModuleRegistry (service registry)
│   │   ├── run_order_group.py  # RunOrderGroupManager, RunOrderGroup, RunAtRegistry
│   │   ├── settings_default.py # Default settings values
│   │   └── settings_manager.py # SettingsManager (4-tier priority)
│   └── modules/                # Built-in system modules
├── pyproject.toml
└── tests/                      # Unit and integration tests
```

### Core Components

#### Main Application Class (`app.py`)
- **`App`**: The central orchestrator managing the entire application lifecycle
- Handles core service initialization (config, logger, path)
- Manages run order group execution via `RunOrderGroupManager`
- Supports both `SystemHook` and custom `Hook` registration/triggering
- Manages background tasks and signal handlers
- Supports graceful shutdown and hot-reload restart capabilities
- Implements phase-based bootstrap (parse → register callbacks → dispatch hooks → execute groups)

#### Run Order Group Manager (`run_order_group.py`)
- **`RunOrderGroupManager`**: Primary module execution orchestrator
- **`RunAtRegistry`**: Dynamic registry for valid `run_at` values
- **`RunOrderGroup`**: Dataclass for group configuration
- **`ModuleInfo`**: Dataclass for discovered module metadata
- Handles module discovery, dependency sorting, and group execution
- Auto-registers callbacks for non-default `run_at` values
- Tracks execution order for reverse shutdown
- Supports group execution at any system hook trigger point

#### Module Loader (`module_loader.py`)
- **`ModuleLoader`**: Lightweight utility for module instantiation
- **`instantiate()`**: Creates module instance from manifest data
- **`check_requirements()`**: Verifies module dependencies are available
- Does NOT handle discovery, grouping, sorting, or starting (handled by RunOrderGroupManager)

#### Hooks System (`hooks.py`, `hook_types.py`)
- **`SystemHook`**: Enum for core framework lifecycle events
- **`Hook`**: Class for module-defined custom hook types
- **`HooksManager`**: Manages registration and dispatching of both hook types
- Supports both synchronous and asynchronous callbacks

---

## 3. Technical Information about Modules and Their Structure

### Built-in System Modules

The framework includes the following system modules in `massir/modules/`:

| Module | Provides | Purpose |
|--------|----------|---------|
| `network_fastapi` | `http_api`, `router_api`, `net_api`, `server_api` | FastAPI-based web server |
| `network_socket` | `socket_api` | Raw TCP/UDP socket communication |
| `network_ssl` | `ssl_api` | SSL/TLS encryption layer |
| `network_websocket` | `websocket_api` | WebSocket protocol support |
| `system_database` | `database_service`, `database_types` | Async database middleware (PostgreSQL, MySQL, SQLite) |
| `system_encryption` | `encryption_api` | Encryption and cryptographic services |
| `system_logger` | `core_logger`, `log_colors` | Advanced logging with color support and filtering |
| `system_network` | `network_api` | High-level network management (unified API) |

### Module Directory Structure

Each module follows a standardized structure:

```
module_name/
├── __init__.py              # Module initialization and exports
├── manifest.json           # Module metadata and configuration
├── module.py               # Main module class implementation
├── requirements.txt        # Module-specific dependencies (optional)
└── core/                   # Internal implementation (optional)
    ├── __init__.py
    └── ...                 # Internal components
```

### Manifest Configuration (`manifest.json`)

Each module must include a `manifest.json` file defining its metadata:

```json
{
    "name": "system_logger",
    "version": "0.3",
    "enabled": true,
    "entrypoint": "SystemLoggerModule",
    "provides": ["core_logger"],
    "requires": [],
    "forced_execute": false
}
```

**Key Fields:**
- **`name`**: Unique identifier for the module
- **`version`**: Module version string
- **`entrypoint`**: Class name to instantiate from `module.py`
- **`provides`**: List of capabilities/services this module offers
- **`requires`**: List of dependencies this module needs
- **`enabled`**: Toggle to enable/disable the module
- **`forced_execute`**: Execute even if dependencies are missing

### Module Interface (`IModule`)

All modules must implement the `IModule` interface from `massir.core.interfaces`:

```python
class IModule(ABC):
    name: str = ""
    id: str = ""
    provides: list = []
    requires: list = []
    _context: 'ModuleContext' = None
    
    async def start(self, context: 'ModuleContext') -> None:
        """Start the module. Called when run order group executes."""
        pass
    
    async def stop(self, context: 'ModuleContext') -> None:
        """Stop the module. Called during shutdown in reverse order."""
        pass
```

**Lifecycle:**
- `start()`: Called when the module's run order group is executed. Initialize resources, register services, start servers.
- `stop()`: Called during shutdown in reverse order of group execution. Cleanup resources, close connections.

For post-start logic (replacing old `ready()`), use hooks:
```python
async def start(self, context):
    app = context.get_app()
    app.register_hook(SystemHook.ON_ALL_MODULES_STARTED, self._on_ready)

async def _on_ready(self):
    # Post-start logic
    ...
```

### Module Context (`ModuleContext`)

Provides modules with access to shared services:
- **`context.services`**: Service registry for dependency injection
- **`context.get_app()`**: Access to the main application instance
- **`context.metadata`**: Shared metadata storage
- **`context.app_dir`**: Application directory path
- **`context.massir_dir`**: Massir framework directory path

---

## 4. Configuration System

### Four-Tier Priority System

The `SettingsManager` implements a **four-tier priority system**:

```
Priority 1 (Highest): User Code (initial_settings)
        ↓
Priority 2: JSON Settings File (app_settings.json)
        ↓
Priority 3: Core Defaults (settings_default.py)
        ↓
Priority 4 (Lowest): Module Defaults (registered by modules)
```

This allows modules to:
1. Register their own defaults (lowest priority)
2. Framework provides core defaults
3. Users override via JSON for deployment-specific settings
4. Users override via code for runtime/programmatic control

### Module Defaults Injection

Modules can register their own configuration defaults:

```python
from massir.modules.system_logger.core.defaults import SystemLoggerDefaults

# In module start():
config = context.services.get("core_config")
if config:
    defaults = SystemLoggerDefaults()
    config.apply_module_defaults(defaults.to_dict())
```

### Configuration Schema

#### Module Groups (in `app_settings.json`)

```json
{
    "modules": [
        {
            "name": "my_group",
            "path": "{app_dir}/modules",
            "names": ["module1", "module2"],
            "run_at": "on_start"
        }
    ]
}
```

**Fields:**
- **`name`**: Optional group identifier (auto-generated if missing)
- **`path`**: Path to module directory (supports `{massir_dir}` and `{app_dir}` placeholders)
- **`names`**: List of module names, or `"all"` for auto-discovery
- **`run_at`**: Execution trigger point (default: `"on_start"`)

#### Run-At Values

Valid `run_at` values are dynamically registered from:
1. Default `"on_start"` (bootstrap execution)
2. All `SystemHook` enum values (triggered when hook fires)

When `SystemHook` changes, valid `run_at` values automatically update.

#### System Configuration

```json
{
    "system": {
        "auto_shutdown": false,
        "auto_shutdown_delay": 0.0
    }
}
```

#### Logging Configuration

```json
{
    "logs": {
        "show_logs": true,
        "show_banner": true,
        "hide_log_levels": [],
        "hide_log_tags": [],
        "debug_mode": false,
        "show_critical_levels": 3
    }
}
```

**`show_critical_levels`** values:
- `0`: Hide all critical levels (ERROR, WARNING, CRITICAL)
- `1`: Show only ERROR
- `2`: Show ERROR and WARNING
- `3`: Show all critical levels (default)

**`debug_mode`**: When `False` (default), CORE-level logs are automatically hidden.

---

## 5. Usage Method with Example Projects

### Basic Application Setup

#### 1. Main Entry Point (`main.py`)

```python
import asyncio
import sys
from pathlib import Path

MASSIR_ROOT = Path(__file__).parent.parent.parent.resolve()
CURRENT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(MASSIR_ROOT))

from massir import App

async def main():
    # Optional: Override settings via code
    initial_settings = {
        "fastapi_provider": {
            "title": "My Application",
            "web": {
                "host": "127.0.0.1",
                "port": 8080
            }
        }
    }
    
    app = App(
        initial_settings=initial_settings,
        settings_path="app_settings.json",
        app_dir=CURRENT_ROOT
    )
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

#### 2. Application Settings (`app_settings.json`)

```json
{
    "modules": [
        {
            "name": "core_services",
            "path": "{massir_dir}/modules",
            "names": ["system_logger", "network_fastapi"],
            "run_at": "on_start"
        },
        {
            "name": "app_modules",
            "path": "{app_dir}/app",
            "names": "all",
            "run_at": "on_start"
        }
    ],
    "system": {
        "auto_shutdown": false,
        "auto_shutdown_delay": 0.0
    },
    "logs": {
        "show_logs": true,
        "show_banner": true,
        "debug_mode": false,
        "show_critical_levels": 3
    }
}
```

### Loading Strategies

**Explicit Module Loading:**
```json
{
    "path": "{app_dir}/app",
    "names": ["auth_module", "user_module"],
    "run_at": "on_start"
}
```

**Automatic Discovery:**
```json
{
    "path": "{app_dir}/app",
    "names": "all",
    "run_at": "on_start"
}
```

**Deferred Execution:**
```json
{
    "path": "{app_dir}/app",
    "names": ["cleanup_module"],
    "run_at": "on_shutdown_request"
}
```

---

## 6. Hook System

### System Hooks (`SystemHook` enum)

Core framework lifecycle events:

| Hook | Description |
|------|-------------|
| `ON_SETTINGS_LOADED` | Settings are loaded |
| `ON_APP_BOOTSTRAP_START` | Bootstrap starts |
| `ON_APP_BOOTSTRAP_END` | Bootstrap completes |
| `ON_ALL_MODULES_STARTED` | All groups completed |
| `ON_SHUTDOWN_REQUEST` | Shutdown requested |
| `ON_RESTART_REQUEST` | Restart requested |
| `ON_GROUP_START` | Group starts executing |
| `ON_GROUP_COMPLETE` | Group completes |
| `ON_GROUP_STOP` | Group stopping |
| `ON_MODULE_STARTED` | Module's `start()` completes |
| `ON_MODULE_STOPPED` | Module's `stop()` completes |
| `ON_SERVICE_REGISTERED` | Service registered |
| `ON_SERVICE_REMOVED` | Service removed |
| `ON_ERROR` | Error occurred |

### Custom Hooks (`Hook` class)

Modules can define their own hooks:

```python
from massir import Hook

ON_NETWORK_READY = Hook("on_network_ready")

# In another module:
app.register_hook(ON_NETWORK_READY, my_callback)

# In the module that owns the hook:
await app.trigger_hook(ON_NETWORK_READY, *args)
```

---

## 7. Summary

Massir provides a robust, flexible foundation for building modular Python applications with:
- Clear separation of concerns through plugin architecture
- Run order groups for precise execution control
- Four-tier configuration system with module defaults injection
- Extensible hook system (system + custom hooks)
- Simple module interface (`start()`/`stop()` only)
- Built-in support for common patterns (web APIs, databases, logging, networking)
- Dynamic `run_at` system that automatically adapts to hook changes

The framework excels at enabling teams to build complex applications from interchangeable, independently-developed components while maintaining configuration flexibility across different deployment environments.