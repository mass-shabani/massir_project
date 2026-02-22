"""
Dashboard page routes for Multi-Database Service.

This module provides routes for:
- Database statistics and overview
- Connection information display
- Cache statistics
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
        
        # Get cache statistics
        cache_stats = db_manager.get_cache_stats()
        
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
        
        # Build cache statistics section
        if cache_stats:
            cache_cards = ""
            for db_name, stats in cache_stats.items():
                hit_rate = stats.get('hit_rate', 0)
                hit_rate_class = "cache-good" if hit_rate > 50 else "cache-low"
                cache_cards += f"""
                <div class="cache-stat-card">
                    <h4>{db_name}</h4>
                    <div class="cache-stats-grid">
                        <div class="cache-stat">
                            <span class="cache-value {hit_rate_class}">{hit_rate}%</span>
                            <span class="cache-label">Hit Rate</span>
                        </div>
                        <div class="cache-stat">
                            <span class="cache-value">{stats.get('hits', 0)}</span>
                            <span class="cache-label">Hits</span>
                        </div>
                        <div class="cache-stat">
                            <span class="cache-value">{stats.get('misses', 0)}</span>
                            <span class="cache-label">Misses</span>
                        </div>
                        <div class="cache-stat">
                            <span class="cache-value">{stats.get('size', 0)}/{stats.get('max_size', 0)}</span>
                            <span class="cache-label">Size</span>
                        </div>
                    </div>
                    <div class="cache-details">
                        <small>Evictions: {stats.get('evictions', 0)} | Expirations: {stats.get('expirations', 0)} | TTL: {stats.get('default_ttl', 0)}s</small>
                    </div>
                </div>
                """
            
            cache_html = f'<div class="cache-stats-container">{cache_cards}</div>'
        else:
            cache_html = '<p class="text-muted">Cache statistics not available.</p>'
        
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
        
        # Get pool info
        pool_info = db_manager.get_pool_info()
        pool_html = ""
        if pool_info:
            pool_html = f"""
            <div class="info-item">
                <span class="info-label">Pool Size:</span>
                <span class="info-value">{pool_info.get('size', '-')}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Idle Connections:</span>
                <span class="info-value">{pool_info.get('idle', '-')}</span>
            </div>
            """
        
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
            <h2 class="card-title">Cache Statistics</h2>
            {cache_html}
            <div class="card-actions">
                <button onclick="clearCache()" class="btn btn-sm btn-warning">Clear Cache</button>
                <button onclick="refreshCacheStats()" class="btn btn-sm">Refresh</button>
            </div>
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
                {pool_html}
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Quick Actions</h2>
            <div class="card-actions">
                <a href="/multi-db/connection" class="btn">Manage Connections</a>
                <a href="/multi-db/tables" class="btn">Manage Tables</a>
                <a href="/multi-db/data" class="btn">Edit Data</a>
                <a href="/multi-db/transactions" class="btn">Transactions</a>
            </div>
        </div>
        
        <script>
        async function clearCache() {{
            if (!confirm('Are you sure you want to clear all cache?')) return;
            
            try {{
                const response = await fetch('/multi-db/api/cache/clear', {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    alert('Cache cleared successfully');
                    refreshCacheStats();
                }} else {{
                    alert('Failed to clear cache: ' + result.message);
                }}
            }} catch (error) {{
                alert('Error: ' + error.message);
            }}
        }}
        
        async function refreshCacheStats() {{
            location.reload();
        }}
        </script>
        
        <style>
        .cache-stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
        }}
        .cache-stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
        }}
        .cache-stat-card h4 {{
            margin: 0 0 0.75rem 0;
            color: var(--text-color);
        }}
        .cache-stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.5rem;
        }}
        .cache-stat {{
            text-align: center;
        }}
        .cache-value {{
            display: block;
            font-size: 1.25rem;
            font-weight: 600;
        }}
        .cache-label {{
            display: block;
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .cache-good {{
            color: var(--success-color);
        }}
        .cache-low {{
            color: var(--warning-color);
        }}
        .cache-details {{
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
        }}
        </style>
        """
        
        html = template.render(content, title="Dashboard", active_menu="multi_db_dashboard")
        return http_api.HTMLResponse(content=html)
    
    # ==================== API Routes ====================
    
    @http_api.post("/multi-db/api/cache/clear")
    async def api_cache_clear(request: http_api.Request):
        """Clear all cache."""
        try:
            await db_manager.clear_cache()
            return {"success": True, "message": "Cache cleared"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    @http_api.get("/multi-db/api/cache/stats")
    async def api_cache_stats(request: http_api.Request):
        """Get cache statistics."""
        stats = db_manager.get_cache_stats()
        return {"stats": stats}
    
    if logger:
        logger.log("Dashboard routes registered", tag="multi_db")
    
    return