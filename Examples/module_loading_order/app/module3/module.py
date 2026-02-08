from massir.core.interfaces import IModule

class Module3(IModule):
    async def load(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("...<m3>... Module3 Loading...", level_color='\033[93m', text_color='\033[96m')

    async def start(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("...<m3>... Module3 started successfully!", level_color='\033[93m', text_color='\033[96m')
            logger.log("...<m3>... Performing Module3 business logic...", level="CUST", level_color='\033[93m', text_color='\033[96m')
        else:
            print("   [Module3] Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("...<m3>... Module3 stopped.", level_color='\033[93m', text_color='\033[96m')
