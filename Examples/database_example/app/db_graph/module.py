"""
Database Graph Module - Visual schema explorer.

Provides an interactive graph visualization of database tables
and their relationships, using the same dark aesthetic as the
Xamaan schema diagram.

Integrates with database_example project via:
  - db_connection_service  (schema data)
  - template_service       (page rendering & menu)
  - menu_manager           (nav registration)
"""
from massir.core.interfaces import IModule, ModuleContext

from .services import GraphService
from .routes  import register_routes


class DbGraphModule(IModule):

    name     = "db_graph"
    provides = []
    requires = ["db_connection_service"]

    def __init__(self):
        self.http_api           = None
        self.logger             = None
        self.template           = None
        self.menu_manager       = None
        self.graph_service      = None
        self.connection_service = None

    # ── lifecycle ──────────────────────────────────────────────────

    async def load(self, context: ModuleContext):
        self.http_api           = context.services.get("http_api")
        self.logger             = context.services.get("core_logger")
        self.template           = context.services.get("template_service")
        self.menu_manager       = context.services.get("menu_manager")
        self.connection_service = context.services.get("db_connection_service")

        self.graph_service = GraphService(self.connection_service)

        if self.logger:
            self.logger.log("DbGraph loaded", tag="db_graph")

    async def start(self, context: ModuleContext):
        register_routes(
            self.http_api,
            self.template,
            self.graph_service,
            self.connection_service,
            self.logger,
        )

        if self.menu_manager:
            self.menu_manager.register_menu(
                id    = "db_graph",
                label = "Graph",
                url   = "/db/graph",
                icon  = "🕸️",
                order = 65,
            )

        if self.logger:
            self.logger.log("DbGraph routes registered at /db/graph", tag="db_graph")

    async def stop(self, context: ModuleContext):
        if self.menu_manager:
            self.menu_manager.unregister_menu("db_graph")
