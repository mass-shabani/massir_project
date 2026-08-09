# Massir

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-alpha-success.svg)]()

Massir is a modular application framework for Python designed to enable developers to build scalable and maintainable applications through a plugin-based architecture.

The Massir project was born from the idea that project structures and code can be split into multiple parts without worrying about breaking code or affecting other parts of the project. In essence, with a dynamic modular structure within a project, it can be developed without concern and by an unlimited number of different development teams without development concurrency issues. Even if the development team is reduced to one person, developing a project using Massir's modular standard can greatly reduce code complexity and entanglement. Massir takes responsibility for managing this modular structure. And with a lightweight core and simple capabilities, it can make development faster.

## Features

| Feature | Description |
|---------|-------------|
| **Modular Architecture** | Load, start, and stop modules independently |
| **Dependency Resolution** | Automatic module dependency sorting and validation |
| **Multi-Transport Networking** | Socket, WebSocket, SSL, and FastAPI support |
| **Configuration Management** | Multi-tier priority system (code → JSON → defaults) |
| **Lifecycle Hooks** | Extensible event system for custom behaviors |
| **Hot Reload** | Runtime application restart capability |
| **Async Core** | Built on asyncio for high-performance I/O |

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

### Example Projects

See [`Examples/`](../Examples/) for complete working examples. More examples will be added during the development process.

## Documentation

For detailed architecture, module structure, configuration options, and advanced usage, see [Docs/PROJECT_ANALYSIS.md](Docs/PROJECT_ANALYSIS.md).

## License

![License](https://img.shields.io/badge/license-MIT-yellow.svg)

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
