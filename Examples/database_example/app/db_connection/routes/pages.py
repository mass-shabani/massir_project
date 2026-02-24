"""
Connection page routes for Database Connection Module.

This module provides routes for:
- Connection management page
- Testing and establishing connections (AJAX)
- Creating new SQLite databases
- Disconnecting from databases
- Session-based connection storage
"""


def register_routes(http_api, template, connection_service, logger):
    """Register connection management routes."""
    
    @http_api.get("/db/connection")
    async def connection_page(request: http_api.Request):
        """Connection management page."""
        connections = connection_service.get_connections()
        active_name = connection_service.get_active_connection_name()
        logs = connection_service.get_logs(20)
        
        # Get saved connections from session
        saved_connections = []
        if hasattr(request, 'session'):
            saved_connections = request.session.get('saved_connections', [])
        
        # Build saved connections dropdown HTML
        saved_connections_options = '<option value="">-- Select Saved Connection --</option>'
        for conn in saved_connections:
            saved_connections_options += f'<option value="{conn["name"]}">{conn["name"]} ({conn["driver"].upper()})</option>'
        
        saved_connections_json = str(saved_connections).replace("'", '"').replace('True', 'true').replace('False', 'false').replace('None', 'null')
        
        # Build connections list HTML
        if connections:
            conn_rows = ""
            for conn in connections:
                status_class = "status-connected" if conn["connected"] else "status-disconnected"
                status_text = "✅ Connected" if conn["connected"] else "❌ Disconnected"
                active_badge = ' <span class="badge badge-primary">Active</span>' if conn["name"] == active_name else ""
                
                # Show appropriate path/host based on driver
                if conn['driver'] == 'sqlite':
                    display_path = conn.get('resolved_path') or conn.get('path') or '-'
                else:
                    # For PostgreSQL/MySQL, show host:port
                    host = conn.get('host', 'localhost')
                    port = conn.get('port')
                    display_path = f"{host}:{port}" if port else host
                
                conn_rows += f"""
                <tr>
                    <td>{conn['name']}{active_badge}</td>
                    <td><span class="badge">{conn['driver'].upper()}</span></td>
                    <td class="path-cell" title="{display_path}">{display_path}</td>
                    <td>{conn['database'] or '-'}</td>
                    <td><span class="{status_class}">{status_text}</span></td>
                    <td class="actions">
                        {f'<button onclick="activateConnection(\'{conn["name"]}\')" class="btn btn-sm">Activate</button>' if conn["name"] != active_name else ''}
                        <button onclick="disconnectConnection('{conn['name']}')" class="btn btn-sm btn-danger">Disconnect</button>
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
        
        content = f"""
        <div class="card">
            <h1>🔗 Database Connection</h1>
            <p class="text-muted">Connect to SQLite, PostgreSQL, or MySQL databases.</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="card">
            <h2 class="card-title">Active Connections</h2>
            <div id="connections-list">{connections_html}</div>
        </div>
        
        <div class="card">
            <h2 class="card-title">New Connection</h2>
            
            <!-- Saved Connections Section - Always Visible -->
            <div class="form-group" id="saved-connections-section">
                <label for="saved-connection">Saved Connections</label>
                <div class="form-row-inline">
                    <select id="saved-connection" name="saved_connection" onchange="loadSavedConnection()">
                        {saved_connections_options}
                    </select>
                    <button type="button" onclick="saveConnection()" class="btn btn-sm btn-icon" title="Save Connection">💾</button>
                    <button type="button" onclick="deleteSavedConnection()" class="btn btn-sm btn-icon btn-danger" title="Delete Saved Connection">🗑️</button>
                </div>
            </div>
            
            <form id="connection-form" class="form">
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
                        <div class="form-row-inline">
                            <input type="text" id="path" name="path" placeholder="e.g., data/mydb.db">
                            <button type="button" onclick="createDatabase()" class="btn btn-success btn-icon" title="Create New Database">➕</button>
                        </div>
                        <small class="text-muted">
                            Supports: relative paths, <code>{{app_dir}}</code>, <code>{{massir_dir}}</code>, and absolute paths
                        </small>
                    </div>
                </div>
                
                <div id="remote-fields" class="form-section" style="display: none;">
                    <!-- URI Input for MySQL/PostgreSQL -->
                    <div class="form-group">
                        <label for="uri">Connection URI <small class="text-muted">(optional - auto-fill fields)</small></label>
                        <div class="form-row-inline">
                            <input type="text" id="uri" name="uri" placeholder="mysql://user:password@host:port/database">
                            <button type="button" onclick="parseUri()" class="btn btn-sm" title="Parse URI">Parse</button>
                        </div>
                        <small class="text-muted">Format: <code>mysql://user:password@host:port/database</code> or <code>postgresql://user:password@host:port/database</code></small>
                    </div>
                    
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
                
                <!-- Advanced Settings (Pool Configuration) -->
                <details class="advanced-settings">
                    <summary>Advanced Settings</summary>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="pool_min_size">Pool Min</label>
                            <input type="number" id="pool_min_size" name="pool_min_size" value="5" min="1" max="100">
                        </div>
                        <div class="form-group">
                            <label for="pool_max_size">Pool Max</label>
                            <input type="number" id="pool_max_size" name="pool_max_size" value="20" min="1" max="100">
                        </div>
                        <div class="form-group">
                            <label for="pool_timeout">Timeout</label>
                            <input type="number" id="pool_timeout" name="pool_timeout" value="30" min="1" max="300">
                        </div>
                        <div class="form-group">
                            <label for="connect_timeout">Connect Timeout</label>
                            <input type="number" id="connect_timeout" name="connect_timeout" value="10" min="1" max="60">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="cache_ttl">Cache TTL (sec)</label>
                            <input type="number" id="cache_ttl" name="cache_ttl" value="300" min="0" max="3600">
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="cache_enabled" name="cache_enabled" checked>
                                Enable Cache
                            </label>
                        </div>
                    </div>
                </details>
                
                <div class="form-actions">
                    <button type="button" onclick="testConnection()" class="btn">Test</button>
                    <button type="button" onclick="connectDatabase()" class="btn btn-primary">Connect</button>
                </div>
            </form>
        </div>
        
        <div class="card">
            <h2 class="card-title">Connection Logs</h2>
            <div class="log-container" id="logs-container">
                {logs_html if logs_html else '<p class="text-muted">No logs yet.</p>'}
            </div>
            <div class="card-actions">
                <button onclick="clearLogs()" class="btn btn-sm">Clear Logs</button>
            </div>
        </div>
        
        <script>
        // Saved connections data
        let savedConnections = {saved_connections_json};
        
        // Initialize page
        document.addEventListener('DOMContentLoaded', function() {{
            toggleConnectionFields();
            updateSavedConnectionsSection();
        }});
        
        function updateSavedConnectionsSection() {{
            const section = document.getElementById('saved-connections-section');
            section.style.display = 'block'; // Always visible
            updateSavedConnectionsDropdown();
        }}
        
        function updateSavedConnectionsDropdown() {{
            const select = document.getElementById('saved-connection');
            select.innerHTML = '<option value="">-- Select Saved Connection --</option>';
            savedConnections.forEach(conn => {{
                select.innerHTML += `<option value="${{conn.name}}">${{conn.name}} (${{conn.driver.toUpperCase()}})</option>`;
            }});
        }}
        
        function loadSavedConnection() {{
            const name = document.getElementById('saved-connection').value;
            if (!name) return;
            
            const conn = savedConnections.find(c => c.name === name);
            if (conn) {{
                document.getElementById('name').value = conn.name;
                document.getElementById('driver').value = conn.driver;
                
                if (conn.driver === 'sqlite') {{
                    document.getElementById('path').value = conn.path || '';
                }} else {{
                    document.getElementById('host').value = conn.host || 'localhost';
                    document.getElementById('port').value = conn.port || '';
                    document.getElementById('database').value = conn.database || '';
                    document.getElementById('user').value = conn.user || '';
                    document.getElementById('password').value = conn.password || '';
                }}
                
                toggleConnectionFields();
            }}
        }}
        
        function deleteSavedConnection() {{
            const name = document.getElementById('saved-connection').value;
            if (!name) return;
            
            if (confirm(`Delete saved connection "${{name}}"?`)) {{
                savedConnections = savedConnections.filter(c => c.name !== name);
                saveConnectionsToSession();
                updateSavedConnectionsSection();
                showMessage('Connection deleted from saved list', 'info');
            }}
        }}
        
        function toggleConnectionFields() {{
            const driver = document.getElementById('driver').value;
            const sqliteFields = document.getElementById('sqlite-fields');
            const remoteFields = document.getElementById('remote-fields');
            
            if (driver === 'sqlite') {{
                sqliteFields.style.display = 'block';
                remoteFields.style.display = 'none';
            }} else {{
                sqliteFields.style.display = 'none';
                remoteFields.style.display = 'block';
                
                // Set default ports
                const portInput = document.getElementById('port');
                if (!portInput.value) {{
                    portInput.value = driver === 'postgresql' ? 5432 : 3306;
                }}
            }}
        }}
        
        function parseUri() {{
            const uri = document.getElementById('uri').value.trim();
            if (!uri) {{
                showMessage('Please enter a URI', 'warning');
                return;
            }}
            
            try {{
                // Parse URI: mysql://user:password@host:port/database
                // or postgresql://user:password@host:port/database
                const regex = /^(mysql|postgresql):\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)$/;
                const match = uri.match(regex);
                
                if (match) {{
                    const driver = match[1];
                    const user = match[2];
                    const password = match[3];
                    const host = match[4];
                    const port = match[5];
                    const database = match[6];
                    
                    document.getElementById('driver').value = driver;
                    document.getElementById('user').value = user;
                    document.getElementById('password').value = password;
                    document.getElementById('host').value = host;
                    document.getElementById('port').value = port;
                    document.getElementById('database').value = database;
                    
                    toggleConnectionFields();
                    showMessage('URI parsed successfully', 'success');
                }} else {{
                    showMessage('Invalid URI format. Use: mysql://user:password@host:port/database', 'error');
                }}
            }} catch (error) {{
                showMessage('Error parsing URI: ' + error.message, 'error');
            }}
        }}
        
        function getFormData() {{
            return {{
                name: document.getElementById('name').value,
                driver: document.getElementById('driver').value,
                path: document.getElementById('path').value,
                host: document.getElementById('host').value,
                port: document.getElementById('port').value ? parseInt(document.getElementById('port').value) : null,
                database: document.getElementById('database').value,
                user: document.getElementById('user').value,
                password: document.getElementById('password').value,
                // Pool settings
                pool_min_size: parseInt(document.getElementById('pool_min_size').value) || 5,
                pool_max_size: parseInt(document.getElementById('pool_max_size').value) || 20,
                pool_timeout: parseFloat(document.getElementById('pool_timeout').value) || 30,
                connect_timeout: parseFloat(document.getElementById('connect_timeout').value) || 10,
                cache_ttl: parseInt(document.getElementById('cache_ttl').value) || 300,
                cache_enabled: document.getElementById('cache_enabled').checked
            }};
        }}
        
        async function testConnection() {{
            const formData = getFormData();
            
            try {{
                const response = await fetch('/db/api/connection/test', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(formData)
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                }} else {{
                    showMessage(result.message, 'error');
                }}
                
                refreshLogs();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function connectDatabase() {{
            const formData = getFormData();
            
            try {{
                const response = await fetch('/db/api/connection/connect', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(formData)
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                    refreshConnections();
                }} else {{
                    showMessage(result.message, 'error');
                }}
                
                refreshLogs();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function createDatabase() {{
            const formData = getFormData();
            
            if (formData.driver !== 'sqlite') {{
                showMessage('Create database is only available for SQLite', 'error');
                return;
            }}
            
            try {{
                const response = await fetch('/db/api/connection/create', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(formData)
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(result.message, 'success');
                }} else {{
                    showMessage(result.message, 'error');
                }}
                
                refreshLogs();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function saveConnection() {{
            const formData = getFormData();
            
            // Check if name already exists
            const existingIndex = savedConnections.findIndex(c => c.name === formData.name);
            if (existingIndex >= 0) {{
                if (!confirm(`Connection "${{formData.name}}" already exists. Overwrite?`)) {{
                    return;
                }}
                savedConnections[existingIndex] = formData;
            }} else {{
                savedConnections.push(formData);
            }}
            
            await saveConnectionsToSession();
            updateSavedConnectionsSection();
            showMessage(`Connection "${{formData.name}}" saved`, 'success');
        }}
        
        async function saveConnectionsToSession() {{
            try {{
                await fetch('/db/api/connection/save-session', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ connections: savedConnections }})
                }});
            }} catch (error) {{
                console.error('Failed to save connections to session:', error);
            }}
        }}
        
        async function disconnectConnection(name) {{
            try {{
                const response = await fetch(`/db/api/connection/${{name}}/disconnect`, {{
                    method: 'POST'
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(`Disconnected from ${{name}}`, 'success');
                    refreshConnections();
                }} else {{
                    showMessage(result.message, 'error');
                }}
                
                refreshLogs();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function activateConnection(name) {{
            try {{
                const response = await fetch(`/db/api/connection/${{name}}/activate`, {{
                    method: 'POST'
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    showMessage(`Connection ${{name}} activated`, 'success');
                    refreshConnections();
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function clearLogs() {{
            try {{
                const response = await fetch('/db/api/connection/clear-logs', {{
                    method: 'POST'
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    document.getElementById('logs-container').innerHTML = '<p class="text-muted">No logs yet.</p>';
                }}
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function refreshConnections() {{
            try {{
                const response = await fetch('/db/api/connection/list');
                const data = await response.json();
                
                if (data.connections.length > 0) {{
                    let html = `<div class="table-wrapper"><table><thead><tr>
                        <th>Name</th><th>Driver</th><th>Path/Host</th><th>Database</th><th>Status</th><th>Actions</th>
                    </tr></thead><tbody>`;
                    
                    data.connections.forEach(conn => {{
                        const statusClass = conn.connected ? 'status-connected' : 'status-disconnected';
                        const statusText = conn.connected ? '✅ Connected' : '❌ Disconnected';
                        const activeBadge = conn.active ? ' <span class="badge badge-primary">Active</span>' : '';
                        
                        // Show appropriate path/host based on driver
                        let displayPath;
                        if (conn.driver === 'sqlite') {{
                            displayPath = conn.resolved_path || conn.path || '-';
                        }} else {{
                            // For PostgreSQL/MySQL, show host:port
                            const host = conn.host || 'localhost';
                            const port = conn.port;
                            displayPath = port ? `${{host}}:${{port}}` : host;
                        }}
                        
                        html += `<tr>
                            <td>${{conn.name}}${{activeBadge}}</td>
                            <td><span class="badge">${{conn.driver.toUpperCase()}}</span></td>
                            <td class="path-cell" title="${{displayPath}}">${{displayPath}}</td>
                            <td>${{conn.database || '-'}}</td>
                            <td><span class="${{statusClass}}">${{statusText}}</span></td>
                            <td class="actions">
                                ${{conn.active ? '' : `<button onclick="activateConnection('${{conn.name}}')" class="btn btn-sm">Activate</button>`}}
                                <button onclick="disconnectConnection('${{conn.name}}')" class="btn btn-sm btn-danger">Disconnect</button>
                            </td>
                        </tr>`;
                    }});
                    
                    html += '</tbody></table></div>';
                    document.getElementById('connections-list').innerHTML = html;
                }} else {{
                    document.getElementById('connections-list').innerHTML = '<p class="text-muted">No active connections. Create a new connection below.</p>';
                }}
            }} catch (error) {{
                console.error('Failed to refresh connections:', error);
            }}
        }}
        
        async function refreshLogs() {{
            try {{
                const response = await fetch('/db/api/connection/logs');
                const data = await response.json();
                
                if (data.logs.length > 0) {{
                    let html = '';
                    data.logs.forEach(log => {{
                        const levelClass = `log-${{log.level.toLowerCase()}}`;
                        html += `<div class="log-entry ${{levelClass}}">
                            <span class="log-time">${{log.timestamp}}</span>
                            <span class="log-level">[${{log.level}}]</span>
                            <span class="log-message">${{log.message}}</span>
                        </div>`;
                    }});
                    document.getElementById('logs-container').innerHTML = html;
                }} else {{
                    document.getElementById('logs-container').innerHTML = '<p class="text-muted">No logs yet.</p>';
                }}
            }} catch (error) {{
                console.error('Failed to refresh logs:', error);
            }}
        }}
        
        function showMessage(message, type) {{
            const container = document.getElementById('message-container');
            const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-error' : type === 'warning' ? 'alert-warning' : 'alert-info';
            container.innerHTML = `<div class="alert ${{alertClass}}">${{message}}</div>`;
            
            // Auto-hide after 5 seconds
            setTimeout(() => {{
                container.innerHTML = '';
            }}, 5000);
        }}
        </script>
        
        <style>
        .form-row-inline {{
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }}
        .form-row-inline input,
        .form-row-inline select {{
            flex: 1;
        }}
        .btn-icon {{
            min-width: 36px;
            padding: 0.4rem 0.6rem;
            font-size: 1rem;
        }}
        .btn-success {{
            background-color: #28a745;
            color: white;
        }}
        .btn-success:hover {{
            background-color: #218838;
        }}
        .advanced-settings {{
            margin-top: 0.75rem;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 0.4rem 0.75rem;
        }}
        .advanced-settings summary {{
            cursor: pointer;
            font-weight: 500;
            color: var(--text-muted);
            padding: 0.4rem 0;
            font-size: 0.9rem;
        }}
        .advanced-settings summary:hover {{
            color: var(--text-color);
        }}
        .advanced-settings[open] summary {{
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 0.75rem;
        }}
        .form-section {{
            margin-bottom: 0.75rem;
        }}
        .form-group {{
            margin-bottom: 0.5rem;
        }}
        .form-group label {{
            margin-bottom: 0.2rem;
        }}
        .card {{
            padding: 1rem;
        }}
        .card-title {{
            margin-bottom: 0.5rem;
        }}
        .form-actions {{
            margin-top: 0.75rem;
        }}
        #saved-connections-section {{
            margin-bottom: 0.75rem;
        }}
        </style>
        """
        
        html = template.render(content, title="Database Connection", active_menu="db_connection")
        return http_api.HTMLResponse(content=html)
    
    # ==================== API Routes ====================
    
    @http_api.get("/db/api/connection/list")
    async def api_connection_list(request: http_api.Request):
        """Get list of active connections."""
        connections = connection_service.get_connections()
        active_name = connection_service.get_active_connection_name()
        
        for conn in connections:
            conn["active"] = (conn["name"] == active_name)
        
        return {"connections": connections}
    
    @http_api.post("/db/api/connection/test")
    async def api_connection_test(request: http_api.Request):
        """Test a database connection."""
        data = await request.json()
        result = await connection_service.test_connection(data)
        return result
    
    @http_api.post("/db/api/connection/connect")
    async def api_connection_connect(request: http_api.Request):
        """Connect to a database."""
        data = await request.json()
        result = await connection_service.connect(data)
        return result
    
    @http_api.post("/db/api/connection/create")
    async def api_connection_create(request: http_api.Request):
        """Create a new SQLite database."""
        data = await request.json()
        result = await connection_service.create_database(data)
        return result
    
    @http_api.post("/db/api/connection/save-session")
    async def api_connection_save_session(request: http_api.Request):
        """Save connections to session."""
        data = await request.json()
        connections = data.get("connections", [])
        
        # Store in session
        if hasattr(request, 'session'):
            request.session['saved_connections'] = connections
        
        return {"success": True}
    
    @http_api.get("/db/api/connection/logs")
    async def api_connection_logs(request: http_api.Request):
        """Get connection logs."""
        logs = connection_service.get_logs(20)
        return {"logs": logs}
    
    @http_api.post("/db/api/connection/clear-logs")
    async def api_connection_clear_logs(request: http_api.Request):
        """Clear connection logs."""
        connection_service.clear_logs()
        return {"success": True}
    
    @http_api.post("/db/api/connection/{name}/disconnect")
    async def api_connection_disconnect(request: http_api.Request):
        """Disconnect a database connection."""
        name = request.path_params["name"]
        await connection_service.disconnect(name)
        return {"success": True, "message": f"Disconnected from {name}"}
    
    @http_api.post("/db/api/connection/{name}/activate")
    async def api_connection_activate(request: http_api.Request):
        """Set a connection as active."""
        name = request.path_params["name"]
        connection_service.set_active_connection(name)
        return {"success": True, "message": f"Connection {name} activated"}
