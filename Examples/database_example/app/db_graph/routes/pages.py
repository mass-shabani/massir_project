"""
Routes for the db_graph module.

GET  /db/graph              → HTML page (graph canvas)
GET  /db/graph/data         → JSON schema payload (used by graph.js)
GET  /db/graph/css          → graph.css  (served inline, no static-file mount needed)
GET  /db/graph/js           → graph.js   (served inline)
"""
from pathlib import Path

_STATIC = Path(__file__).parent.parent / "static"


def register_routes(http_api, template, graph_service, connection_service, logger):

    # ── static assets served as plain-text responses ─────────────────────────
    # (mirrors how template_service serves its CSS – no StaticFiles mount needed)

    @http_api.get("/db/graph/css")
    async def graph_css(request: http_api.Request):
        css = (_STATIC / "css" / "graph.css").read_text(encoding="utf-8")
        return http_api.PlainTextResponse(content=css, media_type="text/css")

    @http_api.get("/db/graph/js")
    async def graph_js(request: http_api.Request):
        js = (_STATIC / "js" / "graph.js").read_text(encoding="utf-8")
        return http_api.PlainTextResponse(content=js, media_type="application/javascript")

    # ── JSON API ──────────────────────────────────────────────────────────────

    @http_api.get("/db/graph/data")
    async def graph_data(request: http_api.Request):
        """Return live schema data as JSON."""
        data = await graph_service.get_graph_data()
        return http_api.JSONResponse(content=data)

    # ── HTML page ─────────────────────────────────────────────────────────────

    @http_api.get("/db/graph")
    async def graph_page(request: http_api.Request):
        """Interactive schema graph page."""
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>🕸️ Schema Graph</h1>
                <p class="text-muted">
                    No active database connection.
                    Please <a href="/db/connection">connect to a database</a> first.
                </p>
            </div>
            """
            html = template.render(content, title="Schema Graph",
                                   active_menu="db_graph")
            return http_api.HTMLResponse(content=html)

        additional_css = '<link rel="stylesheet" href="/db/graph/css">'
        additional_js  = '<script src="/db/graph/js"></script>'
        content        = _build_html()

        html = template.render(
            content,
            title          = "Schema Graph",
            active_menu    = "db_graph",
            additional_css = additional_css,
            additional_js  = additional_js,
        )
        return http_api.HTMLResponse(content=html)


# ── page HTML helper ──────────────────────────────────────────────────────────

def _build_html() -> str:
    return """
<!-- ═══ Graph page ═══════════════════════════════════════════════════════════ -->

<div class="gr-page-header">
    <div class="gr-header-top">
        <div>
            <h1 class="gr-title">🕸️ Schema Graph</h1>
            <p class="gr-subtitle" id="grConnName">Loading schema…</p>
        </div>
        <div class="gr-header-btns">
            <button class="gr-btn" id="btnRefresh"  title="Reload schema from database">↺ Refresh</button>
            <button class="gr-btn" id="btnFit"      title="Fit all nodes in view">⊞ Fit View</button>
            <button class="gr-btn gr-btn--toggle active" id="btnEdges" title="Show / hide FK lines">≋ Edges</button>
            <button class="gr-btn gr-btn--toggle"   id="btnMini"  title="Show / hide minimap">⊟ Map</button>
        </div>
    </div>

    <!-- stat strip -->
    <div class="gr-stats">
        <span class="gr-stat"><span class="gr-stat-val" id="sTables">–</span>&nbsp;tables</span>
        <span class="gr-stat"><span class="gr-stat-val" id="sEdges">–</span>&nbsp;relations</span>
        <span class="gr-stat"><span class="gr-stat-val" id="sCols">–</span>&nbsp;columns</span>
        <span class="gr-stat"><span class="gr-stat-val" id="sIdx">–</span>&nbsp;indexes</span>
    </div>
</div>

<!-- legend -->
<div class="gr-legend">
    <div class="gr-legend-item"><span class="gr-badge gr-pk">PK</span> Primary Key</div>
    <div class="gr-legend-item"><span class="gr-badge gr-fk">FK</span> Foreign Key</div>
    <div class="gr-legend-item"><span class="gr-badge gr-uk">UK</span> Unique</div>
    <div class="gr-legend-item">
        <svg width="36" height="10">
            <line x1="0" y1="5" x2="30" y2="5" stroke="#63b3ed" stroke-width="1.5" stroke-dasharray="4,3"/>
            <polygon points="26,2 34,5 26,8" fill="#63b3ed"/>
        </svg>
        CASCADE
    </div>
    <div class="gr-legend-item">
        <svg width="36" height="10">
            <line x1="0" y1="5" x2="30" y2="5" stroke="#f6ad55" stroke-width="1.5"/>
            <polygon points="26,2 34,5 26,8" fill="#f6ad55"/>
        </svg>
        SET NULL
    </div>
    <div class="gr-legend-item">
        <svg width="36" height="10">
            <line x1="0" y1="5" x2="30" y2="5" stroke="#fc8181" stroke-width="1.5" stroke-dasharray="2,2"/>
            <polygon points="26,2 34,5 26,8" fill="#fc8181"/>
        </svg>
        RESTRICT
    </div>
</div>

<!-- canvas -->
<div class="gr-canvas-wrap" id="grWrap">
    <svg id="grSvg" class="gr-svg"></svg>
    <div id="grNodes" class="gr-nodes"></div>
    <div id="grLoading" class="gr-overlay">
        <div class="gr-spinner"></div>
        <p>Loading schema…</p>
    </div>
    <div id="grEmpty" class="gr-overlay" style="display:none">
        <p style="font-size:1.1rem">🗄️</p>
        <p>No tables found in this database.</p>
        <a href="/db/tables" style="color:#63b3ed">Create some tables →</a>
    </div>
    <!-- minimap -->
    <canvas id="grMinimap" class="gr-minimap"></canvas>
</div>

<!-- tooltip -->
<div id="grTooltip" class="gr-tooltip" style="display:none"></div>
"""
