"""
Main application class for the Massir framework.

This module provides the App class that serves as the central orchestrator
for the entire framework. It manages:
- Core service initialization
- Run order group execution based on system triggers
- Hook dispatching (both SystemHook and Hook)
- Background task management
- Graceful shutdown and restart

The run_at system is fully dynamic:
- "on_start" groups execute during bootstrap
- Groups with SystemHook-based run_at values execute when their
  corresponding hook is dispatched (via auto-registered callbacks)
"""

import asyncio
import signal
from typing import List, Dict, Optional, Union

from massir.core.interfaces import IModule, ModuleContext
from massir.core.hook_types import SystemHook
from massir.core.hooks import Hook, HooksManager
from massir.core.module_loader import ModuleLoader
from massir.core.api import initialize_core_services
from massir.core.log import print_banner, log_internal
from massir.core.path import Path as PathManager
from massir.core.run_order_group import RunOrderGroupManager


class App:
    """
    Main application class.
    
    This class manages the complete application lifecycle:
    1. Initialization of core services (config, logger, path)
    2. Parsing run order groups from configuration
    3. Auto-registration of callbacks for non-default run_at values
    4. Execution of on_start groups during bootstrap
    5. Event dispatching via hooks system
    6. Graceful shutdown in reverse execution order
    7. Restart capability for hot-reloading
    
    The class supports both system hooks (SystemHook enum) and
    custom hooks (Hook instances created by modules).
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
            initial_settings: Code settings (highest priority override)
            settings_path: Path to JSON settings file
            app_dir: Path to user application directory
        """
        # Path management
        self.path = PathManager(app_dir)
        
        # Module loader
        self.loader = ModuleLoader(path=self.path)
        
        # Module registry (global)
        self.modules: Dict[str, IModule] = {}
        
        # Module context
        self.context = ModuleContext()
        
        # Hooks manager
        self.hooks = HooksManager()
        
        # Run order groups manager
        self.run_groups = RunOrderGroupManager(
            self.hooks, self.loader, self.path
        )
        
        # References to core services (mutable lists for updating)
        self._logger_api_ref = [None]
        self._config_api_ref = [None]
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        
        # Lifecycle events
        self._stop_event = asyncio.Event()
        self._restart_event = asyncio.Event()
        
        # Store settings for restart
        self._initial_settings = initial_settings
        self._settings_path = settings_path
        
        # Bootstrap core services
        self._bootstrap_system(initial_settings, settings_path)
    
    def _bootstrap_system(
        self,
        initial_settings: Optional[dict],
        settings_path: Optional[str]
    ) -> None:
        """
        Bootstrap core services.
        
        This method initializes the core services (config, logger, path)
        and registers them in the service registry.
        
        Args:
            initial_settings: Initial settings dictionary
            settings_path: Path to settings file
        """
        # Initialize core services
        _, _, self.path = initialize_core_services(
            self.context.services,
            initial_settings,
            settings_path,
            str(self.path.app)
        )
        
        # Get references to registered services
        self._config_api_ref[0] = self.context.services.get("core_config")
        self._logger_api_ref[0] = self.context.services.get("core_logger")
        
        # Set logger in hooks manager
        self.hooks.set_logger(self._logger_api_ref[0])
        
        # Set app reference in context
        self.context.set_app(self)
    
    # =========================================================================
    # Public API - Hooks
    # =========================================================================
    
    def register_hook(
        self,
        hook: Union[SystemHook, Hook],
        callback
    ) -> None:
        """
        Register a hook callback.
        
        This method accepts both SystemHook enum values and Hook
        instances created by modules.
        
        Args:
            hook: The hook type (SystemHook or Hook)
            callback: The callback function
        """
        self.hooks.register(
            hook, callback, self._logger_api_ref[0]
        )
    
    async def trigger_hook(
        self,
        hook: Union[SystemHook, Hook],
        *args,
        **kwargs
    ) -> None:
        """
        Trigger a hook to all registered callbacks.
        
        This method allows modules to dispatch their custom hooks
        (Hook instances) or system hooks to all registered callbacks.
        
        Args:
            hook: The hook to trigger (SystemHook or Hook)
            *args: Positional arguments for callbacks
            **kwargs: Keyword arguments for callbacks
        """
        await self.hooks.dispatch(hook, *args, **kwargs)
    
    # =========================================================================
    # Public API - Tasks
    # =========================================================================
    
    def register_background_task(self, coroutine) -> None:
        """
        Register a background task.
        
        Background tasks are automatically cancelled during shutdown.
        
        Args:
            coroutine: Coroutine or function to run as background task
        """
        if asyncio.iscoroutinefunction(coroutine):
            task = asyncio.create_task(coroutine())
        else:
            task = asyncio.create_task(asyncio.to_thread(coroutine))
        self._background_tasks.append(task)
    
    # =========================================================================
    # Public API - Lifecycle Control
    # =========================================================================
    
    def request_shutdown(self) -> None:
        """
        Request a graceful shutdown of the application.
        
        This method sets the stop event. The actual shutdown sequence
        (including dispatching ON_SHUTDOWN_REQUEST hook) is handled
        in the run loop's finally block.
        """
        log_internal(
            self._config_api_ref[0],
            self._logger_api_ref[0],
            "Shutdown requested programmatically...",
            level="CORE"
        )
        self._stop_event.set()
    
    def request_restart(self) -> None:
        """
        Request a restart of the application.
        
        This method initiates a full restart cycle:
        1. Stop all modules and background tasks
        2. Clear all loaded modules
        3. Re-bootstrap the application from scratch
        """
        log_internal(
            self._config_api_ref[0],
            self._logger_api_ref[0],
            "Restart requested programmatically...",
            level="CORE"
        )
        self._restart_event.set()
        self._stop_event.set()
    
    def is_restart_requested(self) -> bool:
        """
        Check if a restart has been requested.
        
        Returns:
            True if restart was requested, False otherwise
        """
        return self._restart_event.is_set()
    
    # =========================================================================
    # Lifecycle - Main Run Loop
    # =========================================================================
    
    async def run(self) -> None:
        """
        Main entry point for the application.
        
        This method runs the application lifecycle:
        1. Setup signal handlers
        2. Bootstrap (parse groups, register callbacks, execute on_start)
        3. Wait for stop signal
        4. Dispatch ON_RESTART_REQUEST if restart requested
        5. Dispatch ON_SHUTDOWN_REQUEST (triggers matching run_at groups)
        6. Stop all groups in reverse execution order
        7. Check for restart (loop back if restart requested)
        """
        loop = asyncio.get_running_loop()
        self._setup_signal_handlers(loop)
        
        while True:
            try:
                await self._bootstrap_phases()
                
                # Check for auto_shutdown setting
                auto_shutdown = self._config_api_ref[0].get(
                    "system.auto_shutdown", False
                )
                
                if auto_shutdown:
                    delay = self._config_api_ref[0].get(
                        "system.auto_shutdown_delay", 0.0
                    )
                    if delay > 0:
                        await asyncio.sleep(delay)
                    
                    log_internal(
                        self._config_api_ref[0],
                        self._logger_api_ref[0],
                        "Auto-shutdown is enabled. Initiating shutdown...",
                        level="CORE"
                    )
                    self._stop_event.set()
                else:
                    log_internal(
                        self._config_api_ref[0],
                        self._logger_api_ref[0],
                        "Application is running. Press Ctrl+C to stop.",
                        level="CORE"
                    )
                
                # Wait for stop event
                while not self._stop_event.is_set():
                    try:
                        await asyncio.wait_for(
                            self._stop_event.wait(), timeout=0.5
                        )
                    except asyncio.TimeoutError:
                        continue
                
            except KeyboardInterrupt:
                log_internal(
                    self._config_api_ref[0],
                    self._logger_api_ref[0],
                    "\nKeyboard interrupt received. "
                    "Initiating graceful shutdown...",
                    level="CORE"
                )
            except Exception as e:
                log_internal(
                    self._config_api_ref[0],
                    self._logger_api_ref[0],
                    f"Fatal error in core execution: {e}",
                    level="ERROR"
                )
            finally:
                await self._shutdown_all()
                
                # Check if restart was requested
                if self._restart_event.is_set():
                    log_internal(
                        self._config_api_ref[0],
                        self._logger_api_ref[0],
                        "Restarting application...",
                        level="CORE"
                    )
                    await self._reset_for_restart()
                else:
                    break
    
    async def _bootstrap_phases(self) -> None:
        """
        Execute bootstrap phases using run order groups.
        
        Phase order:
        1. Parse groups from configuration (validates run_at values)
        2. Register callbacks for non-default run_at values
        3. Dispatch ON_SETTINGS_LOADED (may trigger matching groups)
        4. Print banner
        5. Dispatch ON_APP_BOOTSTRAP_START (may trigger matching groups)
        6. Execute on_start groups (the default run_at)
        7. Dispatch ON_APP_BOOTSTRAP_END (may trigger matching groups)
        """
        # Phase 1: Parse groups and validate run_at values
        modules_config = self._config_api_ref[0].get_modules_config()
        self.run_groups.parse_groups_from_config(
            modules_config,
            self._config_api_ref,
            self._logger_api_ref
        )
        
        # Phase 2: Register callbacks for non-default run_at values
        # This must happen BEFORE any hooks are dispatched so that
        # groups with run_at matching early hooks (like on_settings_loaded)
        # are executed when those hooks fire
        self.run_groups.register_run_at_callbacks(
            self.modules,
            self.context,
            self._config_api_ref,
            self._logger_api_ref
        )
        
        # Phase 3: Dispatch ON_SETTINGS_LOADED
        # Groups with run_at="on_settings_loaded" execute via callback
        await self.hooks.dispatch(SystemHook.ON_SETTINGS_LOADED)
        print_banner(self._config_api_ref[0])
        
        # Phase 4: Dispatch ON_APP_BOOTSTRAP_START
        # Groups with run_at="on_app_bootstrap_start" execute via callback
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_START)
        
        log_internal(
            self._config_api_ref[0],
            self._logger_api_ref[0],
            "Starting Massir Framework...",
            level="CORE", tag="core_init"
        )
        
        # Phase 5: Execute on_start groups (the default run_at)
        await self.run_groups.execute_on_start_groups(
            self.modules,
            self.context,
            self._config_api_ref,
            self._logger_api_ref
        )
        
        # Phase 6: Dispatch ON_APP_BOOTSTRAP_END
        # Groups with run_at="on_app_bootstrap_end" execute via callback
        await self.hooks.dispatch(SystemHook.ON_APP_BOOTSTRAP_END)
        
        log_internal(
            self._config_api_ref[0],
            self._logger_api_ref[0],
            "Framework bootstrap complete.",
            level="CORE"
        )
    
    async def _shutdown_all(self) -> None:
        """
        Execute the complete shutdown sequence.
        
        This method:
        1. Cancels all background tasks
        2. Dispatches ON_RESTART_REQUEST if restart was requested
           (triggers groups with run_at="on_restart_request")
        3. Dispatches ON_SHUTDOWN_REQUEST
           (triggers groups with run_at="on_shutdown_request")
        4. Stops all groups in reverse execution order
        """
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Dispatch ON_RESTART_REQUEST if restart was requested
        # Groups with run_at="on_restart_request" execute via callback
        if self._restart_event.is_set():
            await self.hooks.dispatch(SystemHook.ON_RESTART_REQUEST)
        
        # Dispatch ON_SHUTDOWN_REQUEST
        # Groups with run_at="on_shutdown_request" execute via callback
        await self.hooks.dispatch(SystemHook.ON_SHUTDOWN_REQUEST)
        
        # Stop all groups in reverse execution order
        await self.run_groups.shutdown_all_groups(
            self.modules,
            self.context,
            self._config_api_ref,
            self._logger_api_ref
        )
    
    async def _reset_for_restart(self) -> None:
        """
        Reset application state for restart.
        
        This method clears all state to prepare for a fresh bootstrap:
        - Module registry
        - Run order groups
        - Background tasks
        - Lifecycle events
        - Re-initializes context and hooks
        """
        # Clear modules
        self.modules.clear()
        
        # Clear background tasks
        self._background_tasks.clear()
        
        # Reset events
        self._stop_event.clear()
        self._restart_event.clear()
        
        # Re-initialize context and hooks
        self.context = ModuleContext()
        self.hooks = HooksManager()
        self.run_groups = RunOrderGroupManager(
            self.hooks, self.loader, self.path
        )
        
        # Re-bootstrap core services
        self._bootstrap_system(
            self._initial_settings, self._settings_path
        )
        
        log_internal(
            self._config_api_ref[0],
            self._logger_api_ref[0],
            "Application state reset complete.",
            level="CORE"
        )
    
    def _setup_signal_handlers(
        self,
        loop: asyncio.AbstractEventLoop
    ) -> None:
        """
        Setup signal handlers for graceful shutdown.
        
        This method handles both Unix and Windows signal handling:
        - Unix: Uses loop.add_signal_handler (preferred)
        - Windows: Falls back to signal.signal()
        
        Args:
            loop: The asyncio event loop
        """
        def _shutdown_handler() -> None:
            """Signal handler callback for shutdown."""
            log_internal(
                self._config_api_ref[0],
                self._logger_api_ref[0],
                "Shutdown signal received. "
                "Initiating graceful shutdown...",
                level="CORE"
            )
            self._stop_event.set()
        
        # Try Unix-style signal handlers first
        try:
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, _shutdown_handler)
        except NotImplementedError:
            # Windows fallback
            import sys
            if sys.platform == 'win32':
                def _win_shutdown_handler(signum, frame):
                    _shutdown_handler()
                
                signal.signal(signal.SIGINT, _win_shutdown_handler)
                signal.signal(signal.SIGTERM, _win_shutdown_handler)