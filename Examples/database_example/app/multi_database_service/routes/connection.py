"""
Connection page routes for Multi-Database Service.

This module provides routes for:
- Connection management page
- Testing and establishing connections
- Creating new SQLite databases
- Disconnecting from databases
"""


def register_connection_routes(http_api, template, db_manager, logger):
    """Register connection management routes."""
    
    @http_api.get("/multi-db/connection")
    async def connection_page(request: http_api.Request):
        """Connection management page."""
        connections = db_manager.get_connections()
        active_name = db_manager.get_active_connection_name()
        logs = db_manager.get_logs(20)
        
        # Get message from query params
        message = request.query_params.get("message", "")
        msg_type = request.query_params.get("type", "info")
        
        # Build connections list HTML
        if connections:
            conn_rows = ""
            for conn in connections:
                status_class = "status-connected" if conn["connected"] else "status-disconnected"
                status_text = "✅ Connected" if conn["connected"] else "❌ Disconnected"
                active_badge = ' <span class="badge badge-primary">Active</span>' if conn["name"] == active_name else ""
                
                # Show resolved path for SQLite
                display_path = conn.get('resolved_path') or conn['path'] or conn['host'] or '-'
                
                conn_rows += f"""
                <tr>
                    <td>{conn['name']}{active_badge}</td>
                    <td><span class="badge">{conn['driver'].upper()}</span></td>
                    <td class="path-cell" title="{display_path}">{display_path}</td>
                    <td>{conn['database'] or '-'}</td>
                    <td><span class="{status_class}">{status_text}</span></td>
                    <td class="actions">
                        {f'<a href="/multi-db/connection/{conn["name"]}/activate" class="btn btn-sm">Activate</a>' if conn["name"] != active_name else ''}
                        <a href="/multi-db/connection/{conn['name']}/disconnect" class="btn btn-sm btn-danger">Disconnect</a>
                    </td>
                </tr>
                """
            
            connections_html = f"""
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Driver</th>
                            <th>Path/Host</th>
                            <th>Database</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>{conn_rows}</tbody>
                </table>
            </div>
            """
        else:
            connections_html = '<p class="text-muted">No active connections. Create a new connection below.</p>'
        
        # Build logs HTML
        logs_html = ""
        for log in logs:
            level_class = f"log-{log['level'].lower()}"
            logs_html += f"""
            <div class="log-entry {level_class}">
                <span class="log-time">{log['timestamp']}</span>
                <span class="log-level">[{log['level']}]</span>
                <span class="log-message">{log['message']}</span>
            </div>
            """
        
        # Message alert
        message_html = ""
        if message:
            alert_class = "alert-success" if msg_type == "success" else "alert-error" if msg_type == "error" else "alert-warning" if msg_type == "warning" else "alert-info"
            message_html = f'<div class="alert {alert_class}">{message}</div>'
        
        content = f"""
        <div class="card">
            <h1>🔗 Database Connection</h1>
            <p class="text-muted">Connect to SQLite, PostgreSQL, or MySQL databases.</p>
        </div>
        
        {message_html}
        
        <div class="card">
            <h2 class="card-title">Active Connections</h2>
            {connections_html}
        </div>
        
        <div class="card">
            <h2 class="card-title">New Connection</h2>
            <form action="/multi-db/connection/connect" method="POST" class="form">
                <div class="form-row">
                    <div class="form-group">
                        <label for="name">Connection Name</label>
                        <input type="text" id="name" name="name" value="my_connection" required>
                    </div>
                    <div class="form-group">
                        <label for="driver">Database Type</label>
                        <select id="driver" name="driver" onchange="toggleConnectionFields()">
                            <option value="sqlite">SQLite</option>
                            <option value="postgresql">PostgreSQL</option>
                            <option value="mysql">MySQL</option>
                        </select>
                    </div>
                </div>
                
                <div id="sqlite-fields" class="form-section">
                    <div class="form-group">
                        <label for="path">Database Path</label>
                        <input type="text" id="path" name="path" value="data/multi_db.db" placeholder="data/mydb.db or {{app_dir}}/data/mydb.db">
                        <small class="text-muted">
                            Supports: relative paths, <code>{{app_dir}}</code>, <code>{{massir_dir}}</code>, and absolute paths
                        </small>
                    </div>
                </div>
                
                <div id="remote-fields" class="form-section" style="display: none;">
                    <div class="form-row">
                        <div class="form-group">
                            <label for="host">Host</label>
                            <input type="text" id="host" name="host" value="localhost">
                        </div>
                        <div class="form-group">
                            <label for="port">Port</label>
                            <input type="number" id="port" name="port" placeholder="Auto">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="database">Database Name</label>
                            <input type="text" id="database" name="database">
                        </div>
                        <div class="form-group">
                            <label for="user">Username</label>
                            <input type="text" id="user" name="user">
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password">
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="submit" name="action" value="test" class="btn btn-listless">Test Connection</button>
                    <button type="submit" name="action" value="connect" class="btn btn-primary">Connect</button>
                    <button type="submit" name="action" value="create" class="btn btn-success" id="create-btn">Create New Database</button>
                </div>
            </form>
        </div>
        
        <div class="card">
            <h2 class="card-title">Connection Logs</h2>
            <div class="log-container">
                {logs_html if logs_html else '<p class="text-muted">No logs yet.</p>'}
            </div>
            <div class="card-actions">
                <a href="/multi-db/connection/clear-logs" class="btn btn-sm">Clear Logs</a>
            </div>
        </div>
        
        <script>
        function toggleConnectionFields() {{
            const driver = document.getElementById('driver').value;
            const sqliteFields = document.getElementById('sqlite-fields');
            const remoteFields = document.getElementById('remote-fields');
            const createBtn = document.getElementById('create-btn');
            
            if (driver === 'sqlite') {{
                sqliteFields.style.display = 'block';
                remoteFields.style.display = 'none';
                createBtn.style.display = 'inline-block';
            }} else {{
                sqliteFields.style.display = 'none';
                remoteFields.style.display = 'block';
                createBtn.style.display = 'none';
                
                // Set default ports
                const portInput = document.getElementById('port');
                if (!portInput.value) {{
                    portInput.value = driver === 'postgresql' ? 5432 : 3306;
                }}
            }}
        }}
        // Initialize on page load
        toggleConnectionFields();
        </script>
        """
        
        html = template.render(content, title="Database Connection", active_menu="multi_db_connection")
        return http_api.HTMLResponse(content=html)
    
    @http_api.post("/multi-db/connection/connect")
    async def connection_connect(request: http_api.Request):
        """Handle connection form submission."""
        form = await request.form()
        action = form.get("action", "connect")
        
        config = {
            "name": form.get("name", "default"),
            "driver": form.get("driver", "sqlite"),
            "host": form.get("host"),
            "port": int(form.get("port")) if form.get("port") else None,
            "database": form.get("database"),
            "user": form.get("user"),
            "password": form.get("password"),
            "path": form.get("path")
        }
        
        if action == "test":
            result = await db_manager.test_connection(config)
            if result["success"]:
                return http_api.RedirectResponse(
                    url=f"/multi-db/connection?message={result['message']}&type=success",
                    status_code=303
                )
            else:
                return http_api.RedirectResponse(
                    url=f"/multi-db/connection?message={result['message']}&type=error",
                    status_code=303
                )
        elif action == "create":
            # Create new SQLite database
            if config["driver"] != "sqlite":
                return http_api.RedirectResponse(
                    url="/multi-db/connection?message=Create database is only available for SQLite&type=error",
                    status_code=303
                )
            result = await db_manager.connections.create_database(config)
            if result["success"]:
                return http_api.RedirectResponse(
                    url=f"/multi-db/connection?message={result['message']}&type=success",
                    status_code=303
                )
            else:
                return http_api.RedirectResponse(
                    url=f"/multi-db/connection?message={result['message']}&type=error",
                    status_code=303
                )
        else:
            # Connect
            result = await db_manager.connect(config)
            if result["success"]:
                return http_api.RedirectResponse(url="/multi-db/connection", status_code=303)
            else:
                return http_api.RedirectResponse(
                    url=f"/multi-db/connection?message={result['message']}&type=error",
                    status_code=303
                )
    
    @http_api.get("/multi-db/connection/{name}/disconnect")
    async def connection_disconnect(request: http_api.Request):
        """Disconnect a database connection."""
        name = request.path_params["name"]
        await db_manager.disconnect(name)
        return http_api.RedirectResponse(url="/multi-db/connection", status_code=303)
    
    @http_api.get("/multi-db/connection/{name}/activate")
    async def connection_activate(request: http_api.Request):
        """Set a connection as active."""
        name = request.path_params["name"]
        db_manager.set_active_connection(name)
        return http_api.RedirectResponse(url="/multi-db/connection", status_code=303)
    
    @http_api.get("/multi-db/connection/clear-logs")
    async def connection_clear_logs(request: http_api.Request):
        """Clear connection logs."""
        db_manager.clear_logs()
        return http_api.RedirectResponse(url="/multi-db/connection", status_code=303)
    
    if logger:
        logger.log("Connection routes registered", tag="multi_db")
