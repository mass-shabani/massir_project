"""
Transactions page routes for Database Transactions Module.

This module provides routes for:
- Transaction management (begin, commit, rollback)
- SQL query execution
"""


def register_routes(http_api, template, transaction_service, connection_service, logger):
    """Register transaction management routes."""
    
    @http_api.get("/db/transactions")
    async def transactions_page(request: http_api.Request):
        """Transactions management page."""
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>🔄 Transactions</h1>
                <p class="text-muted">No database connection. Please <a href="/db/connection">connect to a database</a> first.</p>
            </div>
            """
            html = template.render(content, title="Transactions", active_menu="db_transactions")
            return http_api.HTMLResponse(content=html)
        
        status = transaction_service.get_transaction_status()
        logs = connection_service.get_logs(20)
        
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
        
        status_badge = '<span class="badge badge-success">Active</span>' if status["has_active"] else '<span class="badge">Inactive</span>'
        
        content = f"""
        <div class="card">
            <h1>🔄 Transactions</h1>
            <p class="text-muted">Manage database transactions. Active: <strong>{connection_service.get_active_connection_name()}</strong></p>
        </div>
        
        <div class="card">
            <h2 class="card-title">Transaction Status</h2>
            <p>Current Status: {status_badge}</p>
            <div class="card-actions">
                <button onclick="beginTransaction()" class="btn btn-primary">Begin Transaction</button>
                <button onclick="commitTransaction()" class="btn btn-success">Commit</button>
                <button onclick="rollbackTransaction()" class="btn btn-danger">Rollback</button>
            </div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Execute SQL</h2>
            <form id="sql-form" class="form">
                <div class="form-group">
                    <label for="sql">SQL Query</label>
                    <textarea id="sql" name="sql" rows="5" placeholder="SELECT * FROM users;"></textarea>
                </div>
                <div class="form-actions">
                    <button type="button" onclick="executeSQL()" class="btn btn-primary">Execute</button>
                </div>
            </form>
            <div id="sql-result"></div>
        </div>
        
        <div class="card">
            <h2 class="card-title">Operation Logs</h2>
            <div class="log-container">
                {logs_html if logs_html else '<p class="text-muted">No logs yet.</p>'}
            </div>
        </div>
        
        <script>
        async function beginTransaction() {{
            try {{
                const response = await fetch('/db/api/transactions/begin', {{ method: 'POST' }});
                const result = await response.json();
                showMessage(result.message, result.success ? 'success' : 'error');
                if (result.success) location.reload();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function commitTransaction() {{
            try {{
                const response = await fetch('/db/api/transactions/commit', {{ method: 'POST' }});
                const result = await response.json();
                showMessage(result.message, result.success ? 'success' : 'error');
                if (result.success) location.reload();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function rollbackTransaction() {{
            try {{
                const response = await fetch('/db/api/transactions/rollback', {{ method: 'POST' }});
                const result = await response.json();
                showMessage(result.message, result.success ? 'success' : 'error');
                if (result.success) location.reload();
            }} catch (error) {{
                showMessage('Error: ' + error.message, 'error');
            }}
        }}
        
        async function executeSQL() {{
            const sql = document.getElementById('sql').value;
            if (!sql.trim()) {{
                showMessage('Please enter a SQL query', 'warning');
                return;
            }}
            
            try {{
                const response = await fetch('/db/api/transactions/execute', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ sql: sql }})
                }});
                
                const result = await response.json();
                
                if (result.success) {{
                    let html = '<div class="alert alert-success">Query executed successfully';
                    if (result.rowcount !== undefined) {{
                        html += ` - ${{result.rowcount}} rows affected`;
                    }}
                    html += '</div>';
                    
                    if (result.rows && result.rows.length > 0) {{
                        html += '<div class="table-wrapper"><table><thead><tr>';
                        const headers = Object.keys(result.rows[0]);
                        headers.forEach(h => html += `<th>${{h}}</th>`);
                        html += '</tr></thead><tbody>';
                        result.rows.forEach(row => {{
                            html += '<tr>';
                            headers.forEach(h => html += `<td>${{row[h]}}</td>`);
                            html += '</tr>';
                        }});
                        html += '</tbody></table></div>';
                    }}
                    
                    document.getElementById('sql-result').innerHTML = html;
                }} else {{
                    document.getElementById('sql-result').innerHTML = `<div class="alert alert-error">${{result.error}}</div>`;
                }}
            }} catch (error) {{
                document.getElementById('sql-result').innerHTML = `<div class="alert alert-error">Error: ${{error.message}}</div>`;
            }}
        }}
        
        function showMessage(message, type) {{
            const container = document.getElementById('sql-result');
            const alertClass = type === 'success' ? 'alert-success' : type === 'error' ? 'alert-error' : 'alert-info';
            container.innerHTML = `<div class="alert ${{alertClass}}">${{message}}</div>`;
        }}
        </script>
        """
        
        html = template.render(content, title="Transactions", active_menu="db_transactions")
        return http_api.HTMLResponse(content=html)
    
    # API Routes
    @http_api.post("/db/api/transactions/begin")
    async def api_begin_transaction(request: http_api.Request):
        """Begin a new transaction."""
        result = await transaction_service.begin_transaction()
        return result
    
    @http_api.post("/db/api/transactions/commit")
    async def api_commit_transaction(request: http_api.Request):
        """Commit the current transaction."""
        result = await transaction_service.commit_transaction()
        return result
    
    @http_api.post("/db/api/transactions/rollback")
    async def api_rollback_transaction(request: http_api.Request):
        """Rollback the current transaction."""
        result = await transaction_service.rollback_transaction()
        return result
    
    @http_api.post("/db/api/transactions/execute")
    async def api_execute_sql(request: http_api.Request):
        """Execute SQL query."""
        data = await request.json()
        sql = data.get("sql", "")
        params = data.get("params", [])
        result = await transaction_service.execute_sql(sql, params)
        return result
