import asyncio
import signal
from pathlib import Path
from typing import List, Dict, Optional, TYPE_CHECKING

# Imports with flat structure
from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook
from massir.core.module_loader import ModuleLoader
from massir.core.api import initialize_core_services
from massir.core.log import print_banner, log_internal
from massir.core.hooks import HooksManager
from massir.core.stop import shutdown
from massir.core.path import Path as PathManager

if TYPE_CHECKING:
    from massir.core.app import App


class App:
    """
    Main application class.

    Responsible for managing lifecycle, modules, and settings.
    """

    def __init__(
        self,
        initial_settings: Optional[dict] = None,
        settings_path: Optional[str] = None,
        app_dir: Optional[str] = None
    ):
        """
        Initialize the application.

        Args:
            initial_settings: Code settings (highest priority)
            settings_path: Path to JSON settings file
                - "./config/settings.json" : Relative path
                - "/absolute/path.json" : Absolute path
                - "__cwd__" : Current directory
            app_dir: Path to user application directory (where main.py is located)
        """
        # Path management
        self.path = PathManager(app_dir)

        # Module loader with access to path
        self.loader = ModuleLoader(path=self.path)

        self.modules: Dict[str, IModule] = {}
        self.context = ModuleContext()
        self.hooks = HooksManager()

        # References to allow modification by other modules
        self._logger_api_ref = [None]
        self._config_api_ref = [None]
        self._background_tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

        # Module name management variables
        self._system_module_names: List[str] = []
        self._app_module_names: List[str] = []

        # Initialize services
        self._bootstrap_system(initial_settings, settings_path)

    def _bootstrap_system(self, initial_settings: Optional[dict], settings_path: str):
        """
        Bootstrap system services.

        Args:
            initial_settings: Initial settings dictionary
            settings_path: Path to settings file
        """
        # First register services with complete settings
        _, _, self.path = initialize_core_services(
            self.context.services,
            initial_settings,
            settings_path,
            str(self.path.app)
        )

        # Get references to registered services
        self._config_api_ref[0] = self.context.services.get("core_config")
        self._logger_api_ref[0] = self.context.services.get("core_logger")

        self.context.set_app(self)

    # --- Hooks ---
    def register_hook(self, hook: SystemHook, callback):
        """
        Register a hook callback.

        Args:
            hook: The hook type
            callback: The callback function
        """
        self.hooks.register(hook, callback, self._logger_api_ref[0])

    # --- Task management ---
    def register_background_task(self, coroutine):
        """
        Register a background task (e.g., Uvicorn).

        Args:
            coroutine: The coroutine or function to run as background task
        """
        if asyncio.iscoroutinefunction(coroutine):
            task = asyncio.create_task(coroutine())
            self._background_tasks.append(task)
        else:
            task = asyncio.create_task(asyncio.to_thread(coroutine))
            self._background_tasks.append(task)

    # --- Signal handling ---
    def _setup_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        """
        Setup signal handlers for graceful shutdown.

        Args:
            loop: The asyncio event loop
        """
        def _shutdown_handler():
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Shutdown signal received. Initiating graceful shutdown...", level="CORE")
            self._stop_event.set()

        # Try Unix-style signal handlers first
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            # Windows fallback: use signal.signal() with wakeup fd
            import sys
            if sys.platform == 'win32':
                # Use signal.signal for Windows
                def _win_shutdown_handler(signum, frame):
                    _shutdown_handler()
                signal.signal(signal.SIGINT, _win_shutdown_handler)
                signal.signal(signal.SIGTERM, _win_shutdown_handler)

    # --- Lifecycle ---
    async def run(self):
        """
        Main entry point for the application.
        """
        loop = asyncio.get_running_loop()
        self._setup_signal_handlers(loop)

        try:
            await self._bootstrap_phases()
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Application is running. Press Ctrl+C to stop.", level="CORE")
            
            # Wait for stop event, but also handle KeyboardInterrupt on Windows
            while not self._stop_event.is_set():
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    # Continue waiting
                    pass

        except asyncio.CancelledError:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Core run loop cancelled.", level="CORE", tag="core")
        except KeyboardInterrupt:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "\n\nKeyboard interrupt received. Initiating graceful shutdown...", level="CORE")
        except Exception as e:
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], f"Fatal Error in core execution: {e}", level="ERROR", tag="core")
        finally:
            await shutdown(self.modules, self._background_tasks,
                          self._config_api_ref[0], self._logger_api_ref[0],
                          self._system_module_names, self._app_module_names)

    async def _bootstrap_phases(self):
        """
        Manage module bootstrap phases.
        """
        # Phase 0
        await self.hooks.dispatch(SystemHook.ON_SETTINGS_LOADED)
        print_banner(self._config_api_ref[0])

        # Phase 1
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_START)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Starting Massir Framework...", level="CORE", tag="core_init")

        # Get module settings based on folder type
        # System phase: folders with type='systems' or type='all'
        system_modules_config = self._config_api_ref[0].get_modules_config_for_type("systems")
        system_data, disabled_system, _ = await self._discover_modules(system_modules_config, is_system=True)
        await self._load_system_modules(system_data, disabled_system)

        # Application phase: folders with type='applications' or type='all'
        app_modules_config = self._config_api_ref[0].get_modules_config_for_type("applications")
        app_data, disabled_app, should_sort = await self._discover_modules(app_modules_config, is_system=False)
        await self._load_application_modules(app_data, disabled_system, disabled_app, should_sort)

        # Phase 3 - Start modules in order
        await self._start_all_modules()

        # Phase 4 - Call ready on all modules
        await self._ready_all_modules()

        # Final phase
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_END)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Framework initialization complete.", level="CORE", tag="core")

    async def _discover_modules(self, modules_config: List[Dict], is_system: bool) -> tuple[List[Dict], Dict[str, List[str]], bool]:
        """
        Discover modules from settings.

        Args:
            modules_config: List of module settings
            is_system: Are these system modules?

        Returns:
            Tuple of (List of discovered modules, disabled modules dict, should_sort flag)
        """
        return await self.loader.discover_modules(
            modules_config,
            is_system,
            self._config_api_ref[0],
            self._logger_api_ref[0]
        )

    async def _load_system_modules(self, system_data: List[Dict], disabled_modules: Dict[str, List[str]] = None):
        """
        Load system modules.

        Args:
            system_data: List of system module information
            disabled_modules: Dictionary of disabled modules and their capabilities
        """
        await self.loader.load_system_modules(
            system_data,
            self.modules,
            self.context,
            self._logger_api_ref,
            self._config_api_ref,
            disabled_modules or {}
        )

        # Collect system module names
        for mod_info in system_data:
            mod_name = mod_info["manifest"]["name"]
            if mod_name in self.modules:
                self._system_module_names.append(mod_name)

    async def _load_application_modules(self, app_data: List[Dict], disabled_system: Dict[str, List[str]] = None, disabled_app: Dict[str, List[str]] = None, should_sort: bool = False):
        """
        Load application modules.

        Args:
            app_data: List of application module information
            disabled_system: Dictionary of disabled system modules
            disabled_app: Dictionary of disabled application modules
            should_sort: Whether to sort modules by dependencies (True when names="all")
        """
        # Combine disabled modules
        all_disabled = {**(disabled_system or {}), **(disabled_app or {})}
        
        await self.loader.load_application_modules(
            app_data,
            self.modules,
            self.context,
            self._logger_api_ref,
            self._config_api_ref,
            all_disabled,
            should_sort
        )

        # Collect application module names
        for mod_info in app_data:
            mod_name = mod_info["manifest"]["name"]
            if mod_name in self.modules:
                self._app_module_names.append(mod_name)

    async def _start_all_modules(self):
        """
        Start all modules.
        """
        await self.loader.start_all_modules(
            self.modules,
            self._system_module_names,
            self._app_module_names,
            self._logger_api_ref,
            self._config_api_ref,
            self.hooks
        )

    async def _ready_all_modules(self):
        """
        Call ready on all modules after they have started.
        """
        await self.loader.ready_all_modules(
            self.modules,
            self._system_module_names,
            self._app_module_names,
            self._logger_api_ref,
            self._config_api_ref,
            self.hooks
        )
