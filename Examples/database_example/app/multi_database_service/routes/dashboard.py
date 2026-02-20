"""
Dashboard page routes for Multi-Database Service.

This module provides routes for:
- Database statistics and overview
- Connection information display
- Quick actions navigation
"""


def register_dashboard_routes(http_api, template, db_manager, logger):
    """Register dashboard routes."""
    
    @http_api.get("/multi-db/dashboard")
    async def dashboard_page(request: http_api.Request):
        """Database dashboard page."""
        if not db_manager.is_connected():
            content = """
            <div class="card">
                <h1>Dashboard</h1>
                <p class="text-muted">No database connection. Please <a href="/multi-db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Dashboard", active_menu="multi_db_dashboard")
            return http_api.HTMLResponse(content=html)
        
        info = await db_manager.get_database_info()
        conn = info.get("connection", {})
        tables = info.get("tables", [])
        
        # Build stats cards
        stats_html = f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{info.get('total_tables', 0)}</div>
                <div class="stat-label">Tables</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{info.get('total_rows', 0)}</div>
                <div class="stat-label">Total Rows</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{conn.get('driver', '-').upper()}</div>
                <div class="stat-label">Database Type</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{conn.get('connection_time', '-')[:16] if conn.get('connection_time') else '-'}</div>
                <div class="stat-label">Connected At</div>
            </div>
        </div>
        """
        
        # Build tables overview
        if tables:
            table_cards = ""
            for table in tables[:6]:
                table_cards += f"""
                <div class="stat-card">
                    <div class="stat-value">{table['rows']}</div>
                    <div class="stat-label">{table['name']}</div>
                    <a href="/multi-db/data?table={table['name']}" class="btn btn-sm">View</a>
                </div>
                """
            
            tables_html = f'<div class="stats-grid">{table_cards}</div>'
        else:
            tables_html = '<p class="text-muted">No tables found. <a href="/multi-db/tables/create-sample">Create sample tables</a></p>'
        
        content = f"""
        <div class="card">
            <h1>Database Dashboard</h1>
            <p class="text-muted">Connection: <strong>{conn.get('name', '-')}</strong></p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Statistics</h2>
            {stats_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Tables Overview</h2>
            {tables_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Connection Info</h2>
            <div class="info-grid">
                <div class="info-item">
                    <span class="info-label">Driver:</span>
                    <span class="info-value">{conn.get('driver', '-').upper()}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Host:</span>
                    <span class="info-value">{conn.get('host') or conn.get('path') or '-'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Database:</span>
                    <span class="info-value">{conn.get('database') or '-'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Status:</span>
                    <span class="info-value status-connected">Connected</span>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Quick Actions</h2>
            <div class="card-actions">
                <a href="/multi-db/connection" class="btn">Manage Connections</a>
                <a href="/multi-db/tables" class="btn">Manage Tables</a>
                <a href="/multi-db/data" class="btn">Edit Data</a>
            </div>
        </div>
        """
        
        html = template.render(content, title="Dashboard", active_menu="multi_db_dashboard")
        return http_api.HTMLResponse(content=html)
    
    if logger:
        logger.log("Dashboard routes registered", tag="multi_db")
    
    return