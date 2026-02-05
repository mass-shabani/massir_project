from massir.core.interfaces import IModule

class AppModule(IModule):
    async def load(self, context):
        logger = context.services.get("core_logger")
        if logger:
            logger.log("AppConsumer Loading...", level_color='\033[94m')

    async def start(self, context):
        # دریافت لاگر سیستمی که توسط هسته تزریق شده است
        logger = context.services.get("core_logger")
        
        if logger:
            logger.log("App Module started successfully and using System Logger!")
            logger.log("Performing some business logic...", level="MASS")
        else:
            print("   [AppModule] Fallback to standard print because system logger is missing.")

    async def stop(self, context):
        pass