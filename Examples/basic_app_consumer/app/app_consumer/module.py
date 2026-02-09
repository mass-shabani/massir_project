from massir.core.interfaces import IModule


class AppModule(IModule):
    """
    Basic application module demonstrating module functionality.

    This module demonstrates how to use the system logger service injected
    by the core framework to log messages during module lifecycle.
    """

    async def load(self, context):
        """
        Load the module and initialize resources.

        Args:
            context: The module context containing services and configuration.
        """
        logger = context.services.get("core_logger")
        if logger:
            logger.log("AppConsumer Loading...", level_color='\033[94m')

    async def start(self, context):
        """
        Start the module and execute business logic.

        Retrieves the system logger service injected by the core framework
        and uses it to log messages.

        Args:
            context: The module context containing services and configuration.
        """
        logger = context.services.get("core_logger")

        if logger:
            logger.log("App Module started successfully and using System Logger!", level_color='\033[94m')
            logger.log("Performing some business logic...", level="CUST", level_color='\033[94m')
        else:
            print("   [AppModule] Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        """
        Stop the module and cleanup resources.

        Args:
            context: The module context containing services and configuration.
        """
        pass