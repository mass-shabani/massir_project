from massir.core.interfaces import IModule


class Module3(IModule):
    """
    Third application module demonstrating module loading order.

    This module logs all messages with the ...<m3>... prefix to identify
    its output in the console. It uses bright yellow color for level tags
    and bright cyan for text.
    """

    async def load(self, context):
        """
        Load the module and initialize resources.

        Args:
            context: The module context containing services and configuration.
        """
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")
        
        if self.logger and self.colors:
            self.logger.log("...<m3>... Module3 Loading...", level_color=self.colors.BRIGHT_YELLOW, text_color=self.colors.BRIGHT_CYAN)

    async def start(self, context):
        """
        Start the module and execute business logic.

        Args:
            context: The module context containing services and configuration.
        """
        if self.logger and self.colors:
            self.logger.log("...<m3>... Module3 started successfully!", level_color=self.colors.BRIGHT_YELLOW, text_color=self.colors.BRIGHT_CYAN)
            self.logger.log("...<m3>... Performing Module3 business logic...", level="CUST", level_color=self.colors.BRIGHT_YELLOW, text_color=self.colors.BRIGHT_CYAN)
        else:
            print("   [Module3] Fallback to standard print because system logger is missing.")

    async def ready(self, context):
        """
        Called when all modules have started and are ready.

        Args:
            context: The module context containing services and configuration.
        """
        if self.logger and self.colors:
            self.logger.log("...<m3>... Module3 is ready! All modules have started.", level_color=self.colors.BRIGHT_YELLOW, text_color=self.colors.BRIGHT_CYAN)
        else:
            print("   [Module3] Ready - Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        """
        Stop the module and cleanup resources.

        Args:
            context: The module context containing services and configuration.
        """
        if self.logger and self.colors:
            self.logger.log("...<m3>... Module3 stopped.", level_color=self.colors.BRIGHT_YELLOW, text_color=self.colors.BRIGHT_CYAN)
