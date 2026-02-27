"""
Routes for the db_graph module — v3
Single-viewport architecture: nodes are rendered as SVG foreignObject
elements inside a <g> transform group, so edges and nodes always move together.
"""
from pathlib import Path

_STATIC = Path(__file__).parent.parent / "static"


def register_routes(http_api, template, graph_service, connection_service, logger):

    @http_api.get("/db/graph/css")
    async def graph_css(request: http_api.Request):
        css = (_STATIC / "css" / "graph.css").read_text(encoding="utf-8")
        return http_api.PlainTextResponse(content=css, media_type="text/css")

    @http_api.get("/db/graph/js")
    async def graph_js(request: http_api.Request):
        js = (_STATIC / "js" / "graph.js").read_text(encoding="utf-8")
        return http_api.PlainTextResponse(content=js, media_type="application/javascript")

    @http_api.get("/db/graph/data")
    async def graph_data(request: http_api.Request):
        data = await graph_service.get_graph_data()
        return http_api.JSONResponse(content=data)

    @http_api.get("/db/graph")
    async def graph_page(request: http_api.Request):
        if not connection_service.is_connected():
            content = """
            <div class="card">
                <h1>🕸️ Schema Graph</h1>
                <p class="text-muted">
                    No active database connection.
                    Please <a href="/db/connection">connect to a database</a> first.
                </p>
            </div>"""
            html = template.render(content, title="Schema Graph", active_menu="db_graph")
            return http_api.HTMLResponse(content=html)

        additional_css = '<link rel="stylesheet" href="/db/graph/css">'
        additional_js  = '<script src="/db/graph/js" defer></script>'

        html = template.render(
            _build_html(),
            title          = "Schema Graph",
            active_menu    = "db_graph",
            additional_css = additional_css,
            additional_js  = additional_js,
        )
        return http_api.HTMLResponse(content=html)


def _build_html() -> str:
    return """
<!-- ═══ Schema Graph ══════════════════════════════════════════════════ -->

<!-- Header card -->
<div class="gr-header">
  <div class="gr-header-row">
    <div class="gr-header-left">
      <div class="gr-title-row">
        <span class="gr-title-icon">🕸️</span>
        <h1 class="gr-title">Schema Graph</h1>
      </div>
      <p class="gr-subtitle" id="grConnName">Loading schema…</p>
    </div>
    <div class="gr-toolbar">
      <button class="gr-btn"               id="btnRefresh" title="Reload schema">↺ Refresh</button>
      <button class="gr-btn"               id="btnFit"     title="Fit all tables">⊞ Fit</button>
      <button class="gr-btn gr-btn-toggle active" id="btnEdges"   title="Toggle FK lines">⌁ Edges</button>
      <button class="gr-btn gr-btn-toggle" id="btnMini"    title="Toggle minimap">⊟ Map</button>
      <div class="gr-zoom-group">
        <button class="gr-btn gr-btn-icon" id="btnZoomOut" title="Zoom out">−</button>
        <span class="gr-zoom-val"          id="grZoomVal">100%</span>
        <button class="gr-btn gr-btn-icon" id="btnZoomIn"  title="Zoom in">+</button>
      </div>
    </div>
  </div>

  <div class="gr-stats-row">
    <div class="gr-stat"><span class="gr-stat-n" id="sTables">–</span> tables</div>
    <div class="gr-stat"><span class="gr-stat-n" id="sEdges">–</span> relations</div>
    <div class="gr-stat"><span class="gr-stat-n" id="sCols">–</span> columns</div>
    <div class="gr-stat"><span class="gr-stat-n" id="sIdx">–</span> indexes</div>
  </div>
</div>

<!-- Legend -->
<div class="gr-legend">
  <span class="gr-leg-item"><span class="gr-badge gr-pk">PK</span> Primary Key</span>
  <span class="gr-leg-item"><span class="gr-badge gr-fk">FK</span> Foreign Key</span>
  <span class="gr-leg-item"><span class="gr-badge gr-uk">UK</span> Unique</span>
  <span class="gr-leg-item">
    <svg width="34" height="10" style="vertical-align:middle">
      <line x1="2" y1="5" x2="26" y2="5" stroke="#3b82f6" stroke-width="1.5" stroke-dasharray="4,3"/>
      <polygon points="22,2 30,5 22,8" fill="#3b82f6"/>
    </svg> CASCADE
  </span>
  <span class="gr-leg-item">
    <svg width="34" height="10" style="vertical-align:middle">
      <line x1="2" y1="5" x2="26" y2="5" stroke="#f59e0b" stroke-width="1.5"/>
      <polygon points="22,2 30,5 22,8" fill="#f59e0b"/>
    </svg> SET NULL
  </span>
  <span class="gr-leg-item">
    <svg width="34" height="10" style="vertical-align:middle">
      <line x1="2" y1="5" x2="26" y2="5" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="2,2"/>
      <polygon points="22,2 30,5 22,8" fill="#ef4444"/>
    </svg> RESTRICT
  </span>
</div>

<!-- Canvas: single SVG owns EVERYTHING (nodes + edges) -->
<div class="gr-canvas-wrap" id="grWrap">
  <!--
    KEY ARCHITECTURE:
    - One <svg> fills the canvas
    - <defs> holds markers
    - <g id="grViewport"> is the single transform target for pan+zoom
    - <g id="grEdgesGroup"> holds all path/text edge elements
    - <g id="grNodesGroup"> holds foreignObject wrappers (the table cards)
    Edges are drawn BELOW nodes (z-order = DOM order).
  -->
  <svg id="grSvg" class="gr-svg" xmlns="http://www.w3.org/2000/svg">
    <defs id="grDefs"></defs>
    <g id="grViewport">
      <g id="grEdgesGroup"></g>
      <g id="grNodesGroup"></g>
    </g>
  </svg>

  <!-- overlays stay outside SVG so they're always on top -->
  <div id="grLoading" class="gr-overlay">
    <div class="gr-spinner"></div>
    <p>Loading schema…</p>
  </div>
  <div id="grEmpty" class="gr-overlay" style="display:none">
    <div style="font-size:2.5rem">🗄️</div>
    <p>No tables found in this database.</p>
    <a href="/db/tables">Create some tables →</a>
  </div>

  <!-- minimap canvas -->
  <canvas id="grMinimap" class="gr-minimap"></canvas>

  <!-- zoom hint -->
  <div class="gr-hint">Scroll to zoom · Drag canvas to pan · Drag tables to rearrange</div>
</div>

<!-- Tooltip (outside canvas, fixed position) -->
<div id="grTooltip" class="gr-tooltip" style="display:none"></div>
"""
