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
        self._restart_event = asyncio.Event()

        # Module name management variables
        self._system_module_names: List[str] = []
        self._app_module_names: List[str] = []
        
        # Store initial settings for restart
        self._initial_settings = initial_settings
        self._settings_path = settings_path

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
    
    # --- Shutdown and Restart ---
    def request_shutdown(self):
        """
        Request a graceful shutdown of the application.
        
        This method can be called from any module to initiate
        a clean shutdown sequence. The application will stop
        all modules and background tasks in the correct order.
        """
        log_internal(
            self._config_api_ref[0], 
            self._logger_api_ref[0], 
            "Shutdown requested programmatically [🛑]...", 
            level="CORE"
        )
        # Dispatch shutdown hook (synchronously since we're not in async context)
        asyncio.create_task(self.hooks.dispatch(SystemHook.ON_SHUTDOWN_REQUEST))
        self._stop_event.set()
    
    def request_restart(self):
        """
        Request a restart of the application.
        
        This method initiates a full restart cycle:
        1. Stop all modules and background tasks
        2. Clear all loaded modules
        3. Re-bootstrap the application from scratch
        
        Useful for hot-reloading configuration or modules.
        """
        log_internal(
            self._config_api_ref[0], 
            self._logger_api_ref[0], 
            "Restart requested programmatically [🔄]...", 
            level="CORE"
        )
        # Dispatch restart hook (synchronously since we're not in async context)
        asyncio.create_task(self.hooks.dispatch(SystemHook.ON_RESTART_REQUEST))
        self._restart_event.set()
        self._stop_event.set()
    
    def is_restart_requested(self) -> bool:
        """
        Check if a restart has been requested.
        
        Returns:
            True if restart was requested, False otherwise
        """
        return self._restart_event.is_set()

    # --- Signal handling ---
    def _setup_signal_handlers(self, loop: asyncio.AbstractEventLoop):
        """
        Setup signal handlers for graceful shutdown.

        Args:
            loop: The asyncio event loop
        """
        def _shutdown_handler():
            log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Shutdown signal received.[🛑] Initiating graceful shutdown...", level="CORE")
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
        
        Supports restart functionality - if request_restart() was called,
        the application will shutdown and then re-bootstrap from scratch.
        """
        loop = asyncio.get_running_loop()
        self._setup_signal_handlers(loop)

        while True:
            try:
                await self._bootstrap_phases()
                
                # Ready phase - called after bootstrap is complete
                # This ensures all modules are started and background tasks are running
                await self._ready_all_modules()
                await self.hooks.dispatch(SystemHook.ON_ALL_MODULES_READY)
                
                # Check for auto_shutdown setting
                auto_shutdown = self._config_api_ref[0].get("system.auto_shutdown", False)
                if auto_shutdown:
                    # Get configurable delay (default 0.5 seconds)
                    shutdown_delay = self._config_api_ref[0].get("system.auto_shutdown_delay", 0.0)
                    
                    if shutdown_delay > 0:
                        await asyncio.sleep(shutdown_delay)

                    log_internal(
                        self._config_api_ref[0], 
                        self._logger_api_ref[0], 
                        "Auto-shutdown is enabled. Initiating shutdown...", 
                        level="CORE"
                    )
                    self._stop_event.set()
                else:
                    log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Application is running. Press Ctrl+C to stop.", level="CORE")
                
                # Wait for stop event, but also handle KeyboardInterrupt on Windows
                while not self._stop_event.is_set():
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=0.5)
                    except asyncio.TimeoutError:
                        # Continue waiting
                        pass

            except asyncio.CancelledError:
                log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Core run loop cancelled.", level="CORE")
            except KeyboardInterrupt:
                log_internal(self._config_api_ref[0], self._logger_api_ref[0], "\n\nKeyboard interrupt received. Initiating graceful shutdown...", level="CORE")
            except Exception as e:
                log_internal(self._config_api_ref[0], self._logger_api_ref[0], f"Fatal Error in core execution: {e}", level="ERROR")
            finally:
                await shutdown(self.modules, self._background_tasks,
                              self._config_api_ref[0], self._logger_api_ref[0],
                              self._system_module_names, self._app_module_names)
            
            # Check if restart was requested
            if self._restart_event.is_set():
                log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Restarting application...", level="CORE")
                await self._reset_for_restart()
                # Continue the while loop to re-bootstrap
            else:
                # Normal shutdown, exit the loop
                break
    
    async def _reset_for_restart(self):
        """
        Reset application state for restart.
        
        Clears all modules, tasks, and events to prepare for a fresh start.
        """
        # Clear modules
        self.modules.clear()
        
        # Clear module name lists
        self._system_module_names.clear()
        self._app_module_names.clear()
        
        # Clear background tasks
        self._background_tasks.clear()
        
        # Reset events
        self._stop_event.clear()
        self._restart_event.clear()
        
        # Re-initialize context and hooks
        self.context = ModuleContext()
        self.hooks = HooksManager()
        
        # Re-bootstrap system services
        self._bootstrap_system(self._initial_settings, self._settings_path)
        
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Application state reset complete.", level="CORE")

    async def _bootstrap_phases(self):
        """
        Manage module bootstrap phases.
        
        This method handles:
        - Loading settings
        - Discovering and loading modules
        - Starting modules
        
        The ready phase is called separately after this completes.
        """
        # Phase 0 - Settings loaded
        await self.hooks.dispatch(SystemHook.ON_SETTINGS_LOADED)
        print_banner(self._config_api_ref[0])

        # Phase 1 - Bootstrap start
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_START)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Starting Massir Framework...", level="CORE", tag="core_init")

        # Phase 2 - Discover and load system modules
        system_modules_config = self._config_api_ref[0].get_modules_config_for_type("systems")
        system_data, disabled_system, _ = await self._discover_modules(system_modules_config, is_system=True)
        await self._load_system_modules(system_data, disabled_system)

        # Phase 3 - Discover and load application modules
        app_modules_config = self._config_api_ref[0].get_modules_config_for_type("applications")
        app_data, disabled_app, should_sort = await self._discover_modules(app_modules_config, is_system=False)
        await self._load_application_modules(app_data, disabled_system, disabled_app, should_sort)

        # Phase 4 - Start all modules
        await self._start_all_modules()

        # Phase 5 - Bootstrap end
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_END)
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "Framework bootstrap complete.", level="CORE")

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
        Call ready on all modules after bootstrap is complete.
        
        This method is called after _bootstrap_phases() finishes,
        ensuring all modules are loaded, started, and background tasks
        (like servers) are running.
        """
        await self.loader.ready_all_modules(
            self.modules,
            self._system_module_names,
            self._app_module_names,
            self._logger_api_ref,
            self._config_api_ref,
            self.hooks
        )
        
        log_internal(self._config_api_ref[0], self._logger_api_ref[0], "All modules ready. Application initialization complete.", level="CORE")
