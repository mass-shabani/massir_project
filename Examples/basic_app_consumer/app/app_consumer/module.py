from massir.core.interfaces import IModule


class AppModule(IModule):
    """
    Basic application module demonstrating module functionality.

    This module demonstrates how to use the system logger service
    injected by the core framework to log messages during module lifecycle.

    Lifecycle methods:
    - start(): Called when the module is started (during bootstrap)
    - stop(): Called when the application shuts down
    """

    async def start(self, context):
        """
        Start the module and execute business logic.

        This is the main entry point for module initialization.
        In the new Massir architecture, start() is called directly
        by RunOrderGroupManager during bootstrap.

        Args:
            context: The module context containing services and configuration.
        """
        logger = context.services.get("core_logger")
        colors = context.services.get("log_colors")
        

        if logger and colors:
            logger.print("\nThis is custom logs: ", tag="app_consumer")
            logger.log("AppModule started successfully and using System Logger!", 
                       level="INFO", 
                       tag="app_consumer", 
                       timestamp_color=colors.CYAN,
                       level_color=colors.BRIGHT_BLUE,
                       tag_color=colors.BRIGHT_MAGENTA,
                       text_color=colors.BRIGHT_MAGENTA,
                       bold=True,
                       italic=True)
            logger.log("Performing some business logic...", 
                       level="INFO", 
                       tag="app_consumer",
                       timestamp_color=colors.CYAN,
                       level_color=colors.BRIGHT_BLUE,
                       tag_color=colors.BRIGHT_MAGENTA,
                       text_color=colors.BRIGHT_MAGENTA,
                       bold=True,
                       italic=True)
            logger.log("error test", level="ERROR", tag="app_consumer")
            logger.log("warning test", level="WARNING", tag="app_consumer")
            logger.log("critical test", level="CRITICAL", tag="app_consumer")
            logger.print("End of custom logs.\n", color="green", bold=True, tag="app_consumer")
        else:
            print("   [AppModule] Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        """
        Stop the module and cleanup resources.

        Called during application shutdown in reverse execution order.

        Args:
            context: The module context containing services and configuration.
        """
        logger = context.services.get("core_logger")
        if logger:
            logger.log("AppModule stopped.", tag="app_consumer")
