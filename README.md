# Massir

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-alpha-success.svg)]()
[![Version](https://img.shields.io/badge/version-0.2.0--alpha-orange)]()

Massir is a modular application framework for Python designed to enable developers to build scalable and maintainable applications through a plugin-based architecture.

The Massir project was born from the idea that project structures and code can be split into multiple parts without worrying about breaking code or affecting other parts of the project. In essence, with a dynamic modular structure within a project, it can be developed without concern and by an unlimited number of different development teams without development concurrency issues. Even if the development team is reduced to one person, developing a project using Massir's modular standard can greatly reduce code complexity and entanglement. Massir takes responsibility for managing this modular structure. And with a lightweight core and simple capabilities, it can make development faster.

## Features

| Feature | Description |
|---------|-------------|
| **Run Order Groups** | Organize modules into execution groups with trigger-based scheduling |
| **Dynamic Run-At System** | Execute module groups at specific system hook trigger points |
| **Module Lifecycle Hooks** | Extensible event system with system and custom hook support |
| **Dependency Resolution** | Automatic module dependency sorting and validation |
| **Multi-Transport Networking** | Socket, WebSocket, SSL, and FastAPI support |
| **Configuration Management** | Four-tier priority system (module → code → JSON → defaults) |
| **Module Defaults Injection** | Modules can register their own configuration defaults |
| **Hot Reload** | Runtime application restart capability |
| **Async Core** | Built on asyncio for high-performance I/O |
| **Simple Module Interface** | Only `start()` and `stop()` methods required |

## Quick Start

### Basic Usage

```python
import asyncio
from massir import App

async def main():
    app = App(
        settings_path="app_settings.json",
        app_dir="."
    )
    await app.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

### Configuration Example

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

### Module Example

```python
from massir import IModule, ModuleContext

class MyModule(IModule):
    async def start(self, context: ModuleContext):
        # Initialize resources, register services
        logger = context.services.get("core_logger")
        if logger:
            logger.log("MyModule started", tag="my_module")
    
    async def stop(self, context: ModuleContext):
        # Cleanup resources
        pass
```

### Custom Hooks

```python
from massir import Hook

# Define a custom hook
ON_DATA_READY = Hook("on_data_ready")

# Register callback
app.register_hook(ON_DATA_READY, my_callback)

# Trigger
await app.trigger_hook(ON_DATA_READY, data)
```

## Run Order Groups

The `run_at` parameter in module groups determines when they execute:

| `run_at` Value | Description |
|----------------|-------------|
| `"on_start"` | Default. Executes during application bootstrap |
| `"on_settings_loaded"` | Executes when settings are loaded |
| `"on_app_bootstrap_start"` | Executes at bootstrap start |
| `"on_app_bootstrap_end"` | Executes at bootstrap completion |
| `"on_all_modules_started"` | Executes after all groups complete |
| `"on_shutdown_request"` | Executes when shutdown is requested |
| `"on_restart_request"` | Executes when restart is requested |
| Any `SystemHook` value | Executes when that hook fires |

## Example Projects

See [`Examples/`](Examples/) for complete working examples. More examples will be added during the development process.

## Documentation

- [Project Analysis](Docs/PROJECT_ANALYSIS.md) - Detailed architecture and module structure
- [Changelog](Docs/CHANGELOG.md) - Version history and migration guides

## License

![License](https://img.shields.io/badge/license-MIT-yellow.svg)
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.