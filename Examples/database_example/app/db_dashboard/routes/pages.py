"""
Dashboard page routes for Database Dashboard Module.

This module provides routes for:
- Database statistics
- Connection information
- Cache and pool statistics
"""


def register_routes(http_api, template, dashboard_service, connection_service, logger):
    """Register dashboard routes."""
    
    @http_api.get("/db/dashboard")
    async def dashboard_page(request: http_api.Request):
        """Dashboard page."""
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>📊 Dashboard</h1>
                <p class="text-muted">No database connection. Please <a href="/db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Dashboard", active_menu="db_dashboard")
            return http_api.HTMLResponse(content=html)
        
        data = await dashboard_service.get_dashboard_data()
        
        # Build database info HTML
        db_info = data.get("database", {})
        if db_info.get("connected"):
            db_html = f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{db_info.get('tables_count', 0)}</div>
                    <div class="stat-label">Tables</div>
                </div>
            </div>
            """
        else:
            db_html = '<p class="text-muted">Database information unavailable.</p>'
        
        # Build table stats HTML
        table_stats = data.get("tables", [])
        if table_stats:
            table_rows = ""
            for stat in table_stats[:10]:  # Show first 10 tables
                table_rows += f"""
                <tr>
                    <td>{stat.get('name', '-')}</td>
                    <td>{stat.get('rows', 0)}</td>
                </tr>
                """
            tables_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead><tr><th>Table</th><th>Rows</th></tr></thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
            """
        else:
            tables_html = '<p class="text-muted">No tables found.</p>'
        
        # Build connections HTML
        conn_info = data.get("connections", {})
        connections = conn_info.get("connections", [])
        if connections:
            conn_rows = ""
            for conn in connections:
                status = "✅ Connected" if conn.get("connected") else "❌ Disconnected"
                active_badge = ' <span class="badge badge-primary">Active</span>' if conn.get("name") == conn_info.get("active") else ""
                conn_rows += f"""
                <tr>
                    <td>{conn.get('name')}{active_badge}</td>
                    <td>{conn.get('driver', '-').upper()}</td>
                    <td>{status}</td>
                </tr>
                """
            conn_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead><tr><th>Name</th><th>Driver</th><th>Status</th></tr></thead>
                    <tbody>{conn_rows}</tbody>
                </table>
            </div>
            """
        else:
            conn_html = '<p class="text-muted">No connections.</p>'
        
        # Build cache stats HTML
        cache_stats = data.get("cache", {})
        if cache_stats:
            cache_html = f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{cache_stats.get('size', 0)}</div>
                    <div class="stat-label">Cache Size</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{cache_stats.get('hits', 0)}</div>
                    <div class="stat-label">Cache Hits</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{cache_stats.get('misses', 0)}</div>
                    <div class="stat-label">Cache Misses</div>
                </div>
            </div>
            """
        else:
            cache_html = '<p class="text-muted">Cache statistics unavailable.</p>'
        
        # Build pool info HTML
        pool_info = data.get("pool", {})
        if pool_info:
            pool_html = f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{pool_info.get('size', '-')}</div>
                    <div class="stat-label">Pool Size</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{pool_info.get('idle', '-')}</div>
                    <div class="stat-label">Idle Connections</div>
                </div>
            </div>
            """
        else:
            pool_html = '<p class="text-muted">Pool information unavailable.</p>'
        
        content = f"""
        <div class="card">
            <h1>📊 Dashboard</h1>
            <p class="text-muted">Database overview and statistics. Active: <strong>{connection_service.get_active_connection_name()}</strong></p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Database Overview</h2>
            {db_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Tables</h2>
            {tables_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Connections</h2>
            {conn_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Cache Statistics</h2>
            {cache_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">Connection Pool</h2>
            {pool_html}
        </div>
        
        <style>
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary-color);
        }}
        .stat-label {{
            color: var(--text-muted);
            margin-top: 0.5rem;
        }}
        </style>
        """
        
        html = template.render(content, title="Dashboard", active_menu="db_dashboard")
        return http_api.HTMLResponse(content=html)
