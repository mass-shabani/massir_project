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
            logger.log("AppModule started successfully and using System Logger!", 
                       level="INFO", 
                       tag="app_consumer", 
                       level_color=colors.BRIGHT_BLUE , 
                       text_color=colors.GREEN,
                       bracket_color=colors.BRIGHT_BLUE)
            logger.log("Performing some business logic...", 
                       level="INFO", 
                       tag="app_consumer",
                       level_color=colors.BRIGHT_BLUE, 
                       text_color=colors.GREEN, 
                       bracket_color=colors.BRIGHT_BLUE)
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
