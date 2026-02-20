"""
Multi-Database Service - Routes package.

This package provides routes for:
- Connection management
- Tables management
- Data editing
- Dashboard
"""
from .connection import register_connection_routes
from .tables import register_tables_routes
from .data import register_data_routes
from .dashboard import register_dashboard_routes

__all__ = [
    "register_connection_routes",
    "register_tables_routes", 
    "register_data_routes",
    "register_dashboard_routes"
]
