"""
Web UI routes aggregator for Multi-Database Service.

This module aggregates all route modules and provides a single
registration function for use in the main module.
"""
from .connection import register_connection_routes
from .tables import register_tables_routes
from .data import register_data_routes
from .dashboard import register_dashboard_routes
from .transactions import register_transaction_routes
from .schema import register_schema_routes


def register_page_routes(http_api, template, db_manager, logger):
    """
    Register all web page routes for multi-database management UI.
    
    This function aggregates route registration from all route modules:
    - Connection routes (connection.py)
    - Tables routes (tables.py)
    - Data editor routes (data.py)
    - Dashboard routes (dashboard.py)
    - Transaction routes (transactions.py)
    - Schema routes (schema.py)
    """
    # Register routes from each module
    register_connection_routes(http_api, template, db_manager, logger)
    register_tables_routes(http_api, template, db_manager, logger)
    register_data_routes(http_api, template, db_manager, logger)
    register_dashboard_routes(http_api, template, db_manager, logger)
    register_transaction_routes(http_api, template, db_manager, logger)
    register_schema_routes(http_api, template, db_manager, logger)
    
    if logger:
        logger.log("All Multi-Database web UI routes registered", tag="multi_db")
