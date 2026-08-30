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

### Key Advantages
- **Separation of Concerns**: Each module handles specific application aspects
- **Flexible Composition**: Applications assembled from interchangeable modules
- **Easy Maintenance**: Changes to one module don't affect others
- **Independent Testing**: Modules can be tested in isolation

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
├── massir/                      # Core framework package
│   ├── __init__.py
│   ├── core/                    # Core system components
│   │   ├── __init__.py
│   │   ├── api.py              # API initialization
│   │   ├── app.py              # Main App class
│   │   ├── config.py           # Configuration handling
│   │   ├── core_apis.py        # Core API interfaces
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── hook_types.py       # Hook type definitions
│   │   ├── hooks.py            # Hook management
│   │   ├── inject.py           # Dependency injection
│   │   ├── interfaces.py       # Module interfaces (IModule, ModuleContext)
│   │   ├── log.py              # Logging utilities
│   │   ├── module_loader.py    # Module discovery and loading
│   │   ├── path.py             # Path management
│   │   ├── registry.py         # Service registry
│   │   ├── settings_default.py # Default configuration values
│   │   ├── settings_manager.py # Settings management with priority
│   │   └── stop.py             # Graceful shutdown handling
│   └── modules/                # Built-in system modules
├── pyproject.toml
└── tests/                      # Unit and integration tests
```

### Core Components

#### Main Application Class (`app.py`)
- **`App`**: The central orchestrator managing the entire application lifecycle
- Handles module discovery, loading, starting, and stopping
- Manages background tasks and signal handlers
- Supports graceful shutdown and hot-reload restart capabilities
- Implements event hooks for extensibility

#### Module Loader (`module_loader.py`)
- Discovers modules from configured paths
- Validates dependencies using `requires` and `provides` fields
- Supports automatic dependency resolution and sorting
- Handles system and application modules separately
- Implements forced execution for critical modules

---

## 3. Technical Information about Modules and Their Structure

### Built-in System Modules

The framework includes the following system modules in `massir/modules/`:

| Module | Type | Purpose |
|--------|------|---------|
| `network_fastapi` | Network | FastAPI-based web server |
| `network_socket` | Network | Raw TCP/UDP socket communication |
| `network_ssl` | Network | SSL/TLS encryption layer |
| `network_websocket` | Network | WebSocket protocol support |
| `system_database` | System | Async database middleware (PostgreSQL, MySQL, SQLite) |
| `system_encryption` | System | Encryption and cryptographic services |
| `system_logger` | System | Advanced logging with color support and filtering |
| `system_network` | System | High-level network management (unified API) |

### Module Directory Structure

Each module follows a standardized structure:

```
module_name/
├── __init__.py              # Module initialization
├── manifest.json           # Module metadata and configuration
├── module.py               # Main module class implementation
├── requirements.txt        # Module-specific dependencies (optional)
└── core/ or drivers/       # Internal components (optional)
```

### Manifest Configuration (`manifest.json`)

Each module must include a `manifest.json` file defining its metadata:

```json
{
  "name": "system_logger",
  "version": "1.0",
  "enabled": true,
  "type": "system",
  "entrypoint": "SystemLoggerModule",
  "provides": ["core_logger"],
  "requires": [],
  "forced_execute": false
}
```

**Key Fields:**
- **`name`**: Unique identifier for the module
- **`type`**: Either `"system"` or `"application"`
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
    
    async def load(self, context: ModuleContext):
        """Load module and initialize resources"""
        pass
    
    async def start(self, context: ModuleContext):
        """Start module and execute business logic"""
        pass
    
    async def ready(self, context: ModuleContext):
        """Called after all modules have started"""
        pass
    
    async def stop(self, context: ModuleContext):
        """Stop module and cleanup resources"""
        pass
```

### Module Context (`ModuleContext`)

Provides modules with access to shared services:
- **`context.services`**: Service registry for dependency injection
- **`context.get_app()`**: Access to the main application instance
- **`context.metadata`**: Shared metadata storage

---

## 4. Usage Method with Example Projects

### Basic Application Setup

Based on the example projects, here's the standard usage pattern:

#### 1. Main Entry Point (`main.py`)

```python
import asyncio
import sys
from pathlib import Path

# Setup path
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
      "path": "{massir_dir}/modules",
      "type": "systems",
      "names": ["system_logger", "network_fastapi"]
    },
    {
      "path": "{app_dir}/app",
      "type": "all",
      "names": "all"
    }
  ],
  "system": {
    "auto_shutdown": false,
    "auto_shutdown_delay": 0.0
  },
  "logs": {
    "show_logs": true,
    "show_banner": true,
    "debug_mode": true
  }
}
```

#### 3. Module Organization

Create your custom modules in an `app/` directory:

```
my_project/
├── main.py
├── app_settings.json
└── app/                    # Application modules directory
    ├── auth_module/
    │   ├── manifest.json
    │   └── module.py
    └── user_module/
        ├── manifest.json
        └── module.py
```

### Loading Strategies

**Explicit Module Loading:**
```json
{
  "path": "{app_dir}/app",
  "type": "applications",
  "names": ["auth_module", "user_module"]
}
```

**Automatic Discovery:**
```json
{
  "path": "{app_dir}/app",
  "type": "all",
  "names": "all"
}
```

When using `"names": "all"`, the framework automatically discovers all modules in the specified path and sorts them based on their dependency graph.

---

## 5. Customization, Configuration, and Configuration Freedom

### Configuration Priority Order

The `SettingsManager` implements a **three-tier priority system**:

```
Priority 1 (Highest): User Code (initial_settings)
    ↓
Priority 2: JSON Settings File (app_settings.json)
    ↓
Priority 3 (Lowest): Default Values (settings_default.py)
```

This allows developers to:
1. Set sensible defaults in the framework
2. Override via JSON for deployment-specific settings
3. Override via code for runtime/programmatic control

### Configuration Categories

#### System Configuration
```json
{
  "system": {
    "auto_shutdown": true,
    "auto_shutdown_delay": 10.0
  }
}
```

#### Logging Configuration
```json
{
  "logs": {
    "show_logs": true,
    "show_banner": true,
    "hide_log_levels": ["DEBUG"],
    "hide_log_tags": ["http"],
    "debug_mode": true
  }
}
```

#### Project Information
```json
{
  "information": {
    "project_name": "My Application",
    "project_version": "1.0.0",
    "project_info": "Custom description"
  }
}
```

#### Template Customization
```json
{
  "template": {
    "project_banner_template": "\n\t{project_name}\n\t{project_version}\n",
    "system_log_template": "[{level}]\t{message}",
    "banner_color": "yellow",
    "log_color": "bright_cyan"
  }
}
```

### Module-Specific Configuration

Modules can define their own configuration namespaces:

```json
{
  "fastapi_provider": {
    "title": "API Server",
    "version": "1.0.0",
    "web": {
      "host": "0.0.0.0",
      "port": 8080,
      "reload": false,
      "workers": 4
    },
    "cors": {
      "origins": ["*"],
      "credentials": true
    }
  }
}
```

### Dynamic Module Control

**Enable/Disable Modules:**
- Set `"enabled": false` in `manifest.json`
- Exclude from `names` list in settings

**Dependency Management:**
- Modules declare `requires` and `provides` in manifest
- Framework automatically resolves dependency order
- Circular dependencies are detected and reported
- Missing dependencies can be bypassed with `forced_execute: true`

**Path Placeholders:**
- `{massir_dir}`: Resolves to the Massir framework directory
- `{app_dir}`: Resolves to the user application directory

### Advanced Configuration Features

1. **Nested Key Access:**
   ```python
   config.get("logs.debug_mode", True)
   config.get("fastapi_provider.web.port", 8080)
   ```

2. **Module Type Filtering:**
   ```json
   {
     "type": "systems"    // Only load system modules
   },
   {
     "type": "applications"  // Only load application modules
   },
   {
     "type": "all"        // Load both types
   }
   ```

3. **Hot Reload Support:**
   The `App` class supports programmatic restart via `app.request_restart()`, which:
   - Stops all modules gracefully
   - Clears all loaded state
   - Re-bootstraps the entire application
   - Reloads configuration from files

4. **Hook System:**
   Register callbacks for lifecycle events:
   ```python
   from massir.core.hook_types import SystemHook
   
   app.register_hook(SystemHook.ON_SETTINGS_LOADED, callback)
   app.register_hook(SystemHook.ON_MODULE_LOADED, callback)
   app.register_hook(SystemHook.ON_ALL_MODULES_READY, callback)
   app.register_hook(SystemHook.ON_SHUTDOWN_REQUEST, callback)
   ```

### Configuration Flexibility Examples

**Example 1: Development vs Production**
```json
// Development (app_settings.dev.json)
{
  "logs": { "debug_mode": true },
  "fastapi_provider": { "web": { "reload": true } }
}

// Production (app_settings.prod.json)
{
  "logs": { "debug_mode": false },
  "fastapi_provider": { "web": { "reload": false, "workers": 4 } }
}
```

**Example 2: Feature Flags**
```json
{
  "modules": [
    {
      "path": "{app_dir}/app",
      "type": "applications",
      "names": ["core_module", "optional_module"]
    }
  ]
}
```

Simply remove `"optional_module"` from the list to disable it without code changes.

---

## Summary

Massir provides a robust, flexible foundation for building modular Python applications with:
- Clear separation of concerns through plugin architecture
- Comprehensive lifecycle management (load → start → ready → stop)
- Advanced dependency resolution and automatic sorting
- Multi-tier configuration system with clear priority rules
- Extensible hook system for custom behaviors
- Built-in support for common patterns (web APIs, databases, logging, networking)

The framework excels at enabling teams to build complex applications from interchangeable, independently-developed components while maintaining configuration flexibility across different deployment environments.