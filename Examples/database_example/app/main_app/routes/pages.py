"""
Main App Routes - Home and About pages.
"""


def register_routes(http_api, template, logger):
    """Register main app routes."""
    
    @http_api.get("/")
    async def home(request: http_api.Request):
        """Home page."""
        content = """
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
            <ul class="feature-list">
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
            <div class="quick-links">
                <a href="/db" class="quick-link-item">
                    <span class="quick-link-icon">📊</span>
                    <span class="quick-link-label">Database Dashboard</span>
                </a>
                <a href="/db/users" class="quick-link-item">
                    <span class="quick-link-icon">👥</span>
                    <span class="quick-link-label">Manage Users</span>
                </a>
                <a href="/db/products" class="quick-link-item">
                    <span class="quick-link-icon">📦</span>
                    <span class="quick-link-label">Manage Products</span>
                </a>
                <a href="/db/query" class="quick-link-item">
                    <span class="quick-link-icon">🔍</span>
                    <span class="quick-link-label">Execute Query</span>
                </a>
            </div>
        </div>
        """
        html = template.render(content, title="Home", active_menu="main_app_home")
        return http_api.HTMLResponse(content=html)
    
    @http_api.get("/about")
    async def about(request: http_api.Request):
        """About page."""
        content = """
        <div class="card">
            <h1>About Database Example</h1>
            <p class="text-muted">Learn more about this application and the Massir Framework.</p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Massir Framework</h2>
            <p>Massir is a modular Python framework designed for building scalable and maintainable applications. 
            It provides a plugin-based architecture where each module can be independently developed, tested, and deployed.</p>
            <div class="mt-20">
                <p><strong>Key Features:</strong></p>
                <ul class="feature-list">
                    <li>Modular architecture with dependency injection</li>
                    <li>Hot-pluggable modules</li>
                    <li>Built-in database abstraction layer</li>
                    <li>FastAPI integration for web services</li>
                    <li>Hook system for event-driven programming</li>
                    <li>Configuration management</li>
                </ul>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">System Database Module</h2>
            <p>The system_database module provides a comprehensive database abstraction layer supporting:</p>
            <div class="mt-20">
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
        </div>
        
        <div class="card">
            <h2 class="card-title">Version</h2>
            <div class="version-info">
                <div class="version-row">
                    <span class="version-label">Framework:</span>
                    <span class="version-value">Massir 0.0.5 alpha</span>
                </div>
                <div class="version-row">
                    <span class="version-label">Database Module:</span>
                    <span class="version-value">1.0.0</span>
                </div>
                <div class="version-row">
                    <span class="version-label">Python:</span>
                    <span class="version-value">3.10+</span>
                </div>
            </div>
        </div>
        """
        html = template.render(content, title="About", active_menu="main_app_about")
        return http_api.HTMLResponse(content=html)
    
    if logger:
        logger.log("Main app routes registered", tag="main_app")
