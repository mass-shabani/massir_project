from massir.core.interfaces import IModule


class Module1(IModule):
    """
    First application module demonstrating module loading order.

    This module logs all messages with the ...<m1>... prefix to identify
    its output in the console. It uses bright yellow color for level tags
    and bright cyan for text.
    """

    async def start(self, context):
        """
        Start the module and execute business logic.

        Args:
            context: The module context containing services and configuration.
        """
        self.logger = context.services.get("core_logger")
        self.colors = context.services.get("log_colors")

        if self.logger and self.colors:
            self.logger.log("...<m1>... Module1 started successfully!", 
                            tag="CUST", 
                            tag_color=self.colors.LIME, 
                            text_color=self.colors.LIME)
            self.logger.log("...<m1>... Performing Module1 business logic...", 
                            tag="CUST", 
                            tag_color=self.colors.LIME, 
                            text_color=self.colors.LIME)
        else:
            print("   [Module1] Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        """
        Stop the module and cleanup resources.

        Args:
            context: The module context containing services and configuration.
        """
        if self.logger and self.colors:
            self.logger.log("...<m1>... Module1 stopped.", 
                            tag="CUST", 
                            tag_color=self.colors.LIME, 
                            text_color=self.colors.LIME)
