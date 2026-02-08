from massir.core.interfaces import IModule

class Module1(IModule):
    async def load(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("...<m1>... Module1 Loading...", level_color='\033[93m', text_color='\033[96m')

    async def start(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("...<m1>... Module1 started successfully!", level_color='\033[93m', text_color='\033[96m')
            logger.log("...<m1>... Performing Module1 business logic...", level="CUST", level_color='\033[93m', text_color='\033[96m')
        else:
            print("   [Module1] Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("...<m1>... Module1 stopped.", level_color='\033[93m', text_color='\033[96m')
