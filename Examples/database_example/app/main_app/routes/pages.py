"""
Main App Routes - Home and About pages.
"""


def register_routes(http_api, template, logger):
    """Register main app routes."""
    
    @http_api.get("/")
    async def home(request: http_api.Request):
        """Home page."""
        content = f"""
        <div class="card">
            <h1>Welcome to Database Example</h1>
            <p class="text-muted">A demonstration of the Massir Framework database module capabilities.</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">🗄️</div>
                <div class="stat-label">SQLite Database</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">📊</div>
                <div class="stat-label">Table Management</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">🔍</div>
                <div class="stat-label">Query Builder</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">⚡</div>
                <div class="stat-label">Fast Operations</div>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Features</h2>
            <ul style="list-style: disc; padding-left: 20px;">
                <li>Create and manage database tables</li>
                <li>Insert, update, and delete records</li>
                <li>Query data with flexible filters</li>
                <li>Execute raw SQL queries</li>
                <li>Transaction support</li>
                <li>Connection pooling</li>
                <li>Query caching</li>
            </ul>
        </div>
        
        <div class="card">
            <h2 class="card-title">Quick Links</h2>
            <div class="card-actions">
                <a href="/db" class="btn btn-primary">Database Dashboard</a>
                <a href="/db/tables" class="btn">View Tables</a>
                <a href="/db/query" class="btn">Execute Query</a>
            </div>
        </div>
        """
        html = template.render(content, title="Home", active_menu="main_app_home")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/about")
    async def about(request: http_api.Request):
        """About page."""
        content = f"""
        <div class="card">
            <h1>About Database Example</h1>
            <p class="text-muted">Learn more about this application and the Massir Framework.</p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Massir Framework</h2>
            <p>Massir is a modular Python framework designed for building scalable and maintainable applications. 
            It provides a plugin-based architecture where each module can be independently developed, tested, and deployed.</p>
            <br>
            <p><strong>Key Features:</strong></p>
            <ul style="list-style: disc; padding-left: 20px; margin-top: 10px;">
                <li>Modular architecture with dependency injection</li>
                <li>Hot-pluggable modules</li>
                <li>Built-in database abstraction layer</li>
                <li>FastAPI integration for web services</li>
                <li>Hook system for event-driven programming</li>
                <li>Configuration management</li>
            </ul>
        </div>
        
        <div class="card">
            <h2 class="card-title">System Database Module</h2>
            <p>The system_database module provides a comprehensive database abstraction layer supporting:</p>
            <br>
            <div class="grid grid-3">
                <div class="stat-card">
                    <div class="stat-value">SQLite</div>
                    <div class="stat-label">Lightweight, file-based</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">PostgreSQL</div>
                    <div class="stat-label">Enterprise-grade</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">MySQL</div>
                    <div class="stat-label">Popular choice</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Version</h2>
            <p><strong>Framework:</strong> Massir 0.0.5 alpha</p>
            <p><strong>Database Module:</strong> 1.0.0</p>
            <p><strong>Python:</strong> 3.10+</p>
        </div>
        """
        html = template.render(content, title="About", active_menu="main_app_about")
        return http_api.HTMLResponse(content=html)
    
    if logger:
        logger.log("Main app routes registered", tag="main_app")
