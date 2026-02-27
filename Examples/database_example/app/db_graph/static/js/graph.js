/**
 * db_graph v3 — Schema Graph Engine
 * ═══════════════════════════════════════════════════════════════════
 *
 * ARCHITECTURE FIX (v3):
 *   All table cards are rendered as <foreignObject> elements *inside*
 *   the SVG, under a single <g id="grViewport"> transform group.
 *   Edges are also inside the same group.
 *
 *   Pan, zoom, and scroll apply ONE transform to grViewport.
 *   This means edges and nodes ALWAYS move together — perfectly.
 *
 *   Previous approach (nodes in HTML div, edges in SVG overlay) caused
 *   misalignment on scroll/zoom because the two layers had independent
 *   transforms.
 *
 * Controls:
 *   • Scroll wheel      → zoom in/out (around cursor)
 *   • Drag canvas       → pan
 *   • Drag node header  → reposition table
 *   • Fit button        → zoom to fit all tables
 *   + / - buttons       → zoom steps
 */
;(function () {
'use strict';

/* ── Constants ───────────────────────────────────────────────────────── */
const NODE_W   = 220;   // foreignObject width  (px, in SVG user units)
const NODE_H_HEAD = 36; // header height
const NODE_H_COL  = 22; // per column row
const NODE_H_FOOT = 24;
const NODE_H_MAX  = 320;
const MAX_COLS = 12;

const ZOOM_MIN = 0.15;
const ZOOM_MAX = 2.5;
const ZOOM_STEP = 0.15;

const PALETTE = [
  '#3b82f6','#8b5cf6','#10b981','#f59e0b',
  '#ef4444','#06b6d4','#f97316','#ec4899',
  '#14b8a6','#6366f1',
];

/* ── DOM refs ─────────────────────────────────────────────────────────── */
const wrap     = document.getElementById('grWrap');
const svgEl    = document.getElementById('grSvg');
const defs     = document.getElementById('grDefs');
const viewport = document.getElementById('grViewport');
const edgesG   = document.getElementById('grEdgesGroup');
const nodesG   = document.getElementById('grNodesGroup');
const loading  = document.getElementById('grLoading');
const emptyEl  = document.getElementById('grEmpty');
const tooltip  = document.getElementById('grTooltip');
const minimap  = document.getElementById('grMinimap');

const btnRefresh = document.getElementById('btnRefresh');
const btnFit     = document.getElementById('btnFit');
const btnEdges   = document.getElementById('btnEdges');
const btnMini    = document.getElementById('btnMini');
const btnZoomIn  = document.getElementById('btnZoomIn');
const btnZoomOut = document.getElementById('btnZoomOut');
const elZoomVal  = document.getElementById('grZoomVal');

const elTables = document.getElementById('sTables');
const elEdges  = document.getElementById('sEdges');
const elCols   = document.getElementById('sCols');
const elIdx    = document.getElementById('sIdx');
const elConn   = document.getElementById('grConnName');

/* ── State ────────────────────────────────────────────────────────────── */
let gData     = null;
let positions = {};        // { tableName: {x, y} } — in SVG user space
let showEdges = true;
let showMini  = false;

// viewport transform: tx, ty = pan offsets; scale = zoom
let tx = 0, ty = 0, scale = 1;

let isPanning = false;
let panSX = 0, panSY = 0;   // start of pan (screen coords)
let panTX = 0, panTY = 0;   // tx/ty at pan start

let dragging = null;   // { name, startMX, startMY, startX, startY }

let palIdx = 0;
const tblColor = {};
function colorFor(n) {
  if (!tblColor[n]) tblColor[n] = PALETTE[palIdx++ % PALETTE.length];
  return tblColor[n];
}

/* ── Bootstrap ────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  buildDefs();
  loadGraph();

  btnRefresh?.addEventListener('click', () => { resetState(); loadGraph(); });
  btnFit?.addEventListener('click', fitView);
  btnEdges?.addEventListener('click', () => {
    showEdges = !showEdges;
    btnEdges.classList.toggle('active', showEdges);
    redrawEdges();
  });
  btnMini?.addEventListener('click', () => {
    showMini = !showMini;
    btnMini.classList.toggle('active', showMini);
    minimap.style.display = showMini ? 'block' : 'none';
    if (showMini) drawMinimap();
  });
  btnZoomIn?.addEventListener('click',  () => applyZoom(scale + ZOOM_STEP, wrapCx(), wrapCy()));
  btnZoomOut?.addEventListener('click', () => applyZoom(scale - ZOOM_STEP, wrapCx(), wrapCy()));

  initPan();
  initWheel();
  initDrag();
});

/* ── Load schema ──────────────────────────────────────────────────────── */
async function loadGraph() {
  showLoading(true);
  try {
    const res = await fetch('/db/graph/data');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    gData = await res.json();

    if (!gData.connected || !gData.tables?.length) {
      showLoading(false);
      emptyEl.style.display = 'flex';
      return;
    }

    if (elConn) elConn.textContent =
      `connection: ${gData.connection_name || '–'} · ${gData.tables.length} tables`;

    updateStats(gData.stats);
    computeLayout(gData.tables, gData.edges);
    renderNodes(gData.tables);
    redrawEdges();
    fitView();

  } catch (err) {
    console.error('[db_graph]', err);
    emptyEl.style.display = 'flex';
    emptyEl.querySelectorAll('p')[1].textContent = `⚠ ${err.message}`;
  } finally {
    showLoading(false);
  }
}

/* ── Reset ────────────────────────────────────────────────────────────── */
function resetState() {
  positions = {};
  palIdx = 0;
  Object.keys(tblColor).forEach(k => delete tblColor[k]);
  edgesG.innerHTML = '';
  nodesG.innerHTML = '';
  emptyEl.style.display = 'none';
  tx = ty = 0; scale = 1;
  applyTransform();
  if (elConn) elConn.textContent = 'Loading schema…';
}

/* ── Stats ─────────────────────────────────────────────────────────────── */
function updateStats(s) {
  if (elTables) elTables.textContent = s?.tables  ?? '–';
  if (elEdges)  elEdges.textContent  = s?.edges   ?? '–';
  if (elCols)   elCols.textContent   = s?.columns ?? '–';
  if (elIdx)    elIdx.textContent    = s?.indexes ?? '–';
}

/* ── Layout ───────────────────────────────────────────────────────────── */
function computeLayout(tables, edges) {
  const W = wrap.clientWidth  / scale || 900;
  const H = wrap.clientHeight / scale || 660;
  const PAD = 44, n = tables.length;
  if (!n) return;

  const deg = {};
  tables.forEach(t => { deg[t.name] = 0; });
  (edges || []).forEach(e => {
    if (e.from_table) deg[e.from_table] = (deg[e.from_table] || 0) + 1;
    if (e.to_table)   deg[e.to_table]   = (deg[e.to_table]   || 0) + 1;
  });
  const sorted = [...tables].sort((a, b) => deg[b.name] - deg[a.name]);

  const cols  = Math.max(1, Math.ceil(Math.sqrt(n * 1.4)));
  const cellW = Math.max(NODE_W + PAD, (W - PAD * 2) / cols);
  const cellH = Math.max(NODE_H_MAX + PAD, (H - PAD * 2) / Math.ceil(n / cols));

  sorted.forEach((t, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    positions[t.name] = {
      x: PAD + col * cellW + (row % 2 ? cellW * 0.2 : 0),
      y: PAD + row * cellH,
    };
  });
}

/* ── Node height ─────────────────────────────────────────────────────── */
function nodeHeight(tbl) {
  const colCount = Math.min(tbl.columns?.length || 0, MAX_COLS);
  const hasMore  = (tbl.columns?.length || 0) > MAX_COLS;
  return NODE_H_HEAD
       + colCount * NODE_H_COL
       + (hasMore ? NODE_H_COL : 0)
       + NODE_H_FOOT;
}

/* ── Render nodes ────────────────────────────────────────────────────── */
function renderNodes(tables) {
  tables.forEach(tbl => {
    const pos   = positions[tbl.name] || { x: 40, y: 40 };
    const color = colorFor(tbl.name);
    const h     = nodeHeight(tbl);

    // <foreignObject> wraps the HTML card inside SVG space
    const fo = mkSvg('foreignObject');
    fo.setAttribute('id',     `grfo-${cssEsc(tbl.name)}`);
    fo.setAttribute('x',      pos.x);
    fo.setAttribute('y',      pos.y);
    fo.setAttribute('width',  NODE_W);
    fo.setAttribute('height', h);
    fo.dataset.table = tbl.name;

    // xmlns required for proper foreignObject rendering
    fo.innerHTML =
      `<div xmlns="http://www.w3.org/1999/xhtml" class="gr-node" id="grn-${cssEsc(tbl.name)}"
            style="border-top: 2.5px solid ${color}; height:${h}px;">
        <div class="gr-node-head" style="background:${hexA(color,.07)}"
             data-drag="${esc(tbl.name)}">
          <span class="gr-node-icon">🗄️</span>
          <span class="gr-node-name" style="color:${color}">${esc(tbl.name)}</span>
          <span class="gr-node-count">${tbl.columns?.length ?? 0}</span>
        </div>
        <div class="gr-node-body">
          ${buildColRows(tbl.columns || [])}
        </div>
        <div class="gr-node-foot">
          <span>${(tbl.indexes||[]).length} idx</span>
          <span>${fmtRows(tbl.row_count)}</span>
        </div>
      </div>`;

    // tooltip on head hover
    const head = fo.querySelector('.gr-node-head');
    head?.addEventListener('mouseenter', ev => showTip(ev, buildTipHtml(tbl, color)));
    head?.addEventListener('mouseleave', hideTip);

    nodesG.appendChild(fo);
  });

  markFkBadges();
}

function buildColRows(cols) {
  const visible = cols.slice(0, MAX_COLS);
  let html = '';
  visible.forEach(col => {
    const b = badgeFor(col);
    html += `<div class="gr-col" data-col="${escAttr(col.name)}">
      <span class="gr-col-badge ${b.cls}">${b.lbl}</span>
      <span class="gr-col-name">${esc(col.name)}</span>
      <span class="gr-col-type">${esc(shortType(col.type))}</span>
    </div>`;
  });
  if (cols.length > MAX_COLS)
    html += `<div class="gr-col-more">+ ${cols.length - MAX_COLS} more columns…</div>`;
  return html;
}

function badgeFor(col) {
  if (col.primary_key) return { cls: 'cbadge-pk', lbl: 'PK' };
  if (col.unique)      return { cls: 'cbadge-uk', lbl: 'UK' };
  return { cls: 'cbadge-empty', lbl: '' };
}

function markFkBadges() {
  if (!gData?.edges) return;
  const fkMap = {};
  gData.edges.forEach(e => {
    (e.from_columns || []).forEach(c => {
      (fkMap[e.from_table] = fkMap[e.from_table] || new Set()).add(c);
    });
  });
  Object.entries(fkMap).forEach(([tbl, cols]) => {
    const nodeEl = document.getElementById(`grn-${cssEsc(tbl)}`);
    if (!nodeEl) return;
    cols.forEach(colName => {
      const row = nodeEl.querySelector(`[data-col="${cssEsc(colName)}"]`);
      if (!row) return;
      const badge = row.querySelector('.gr-col-badge');
      if (badge?.classList.contains('cbadge-empty')) {
        badge.className = 'gr-col-badge cbadge-fk';
        badge.textContent = 'FK';
      }
    });
  });
}

/* ── SVG defs (arrowhead markers) ────────────────────────────────────── */
function buildDefs() {
  const markers = {
    'CASCADE':  '#3b82f6',
    'SET_NULL': '#f59e0b',
    'RESTRICT': '#ef4444',
  };
  let html = '';
  Object.entries(markers).forEach(([k, c]) => {
    html += `<marker id="arr-${k}" markerWidth="8" markerHeight="8"
               refX="7" refY="4" orient="auto">
               <path d="M0,0.5 L7,4 L0,7.5 Z" fill="${c}" opacity=".9"/>
             </marker>
             <marker id="arrS-${k}" markerWidth="5" markerHeight="5"
               refX="4" refY="2.5" orient="auto">
               <circle cx="2.5" cy="2.5" r="2" fill="${c}" opacity=".8"/>
             </marker>`;
  });
  defs.innerHTML = html;
}

/* ── Draw edges ───────────────────────────────────────────────────────── */
function redrawEdges() {
  edgesG.innerHTML = '';
  if (!showEdges || !gData?.edges?.length) return;
  gData.edges.forEach(drawEdge);
  if (showMini) drawMinimap();
}

function drawEdge(edge) {
  const fp = positions[edge.from_table];
  const tp = positions[edge.to_table];
  if (!fp || !tp || edge.from_table === edge.to_table) return;

  const fh = nodeHeight(gData.tables.find(t => t.name === edge.from_table) || {});
  const th = nodeHeight(gData.tables.find(t => t.name === edge.to_table)   || {});

  // Compute port centres in SVG user space (no DOM rect needed!)
  const fCx = fp.x + NODE_W / 2, fCy = fp.y + fh / 2;
  const tCx = tp.x + NODE_W / 2, tCy = tp.y + th / 2;

  let sx, sy, ex, ey;
  if (Math.abs(fCx - tCx) >= Math.abs(fCy - tCy)) {
    sx = fCx > tCx ? fp.x : fp.x + NODE_W;     sy = fCy;
    ex = tCx < fCx ? tp.x + NODE_W : tp.x;     ey = tCy;
  } else {
    sx = fCx; sy = fCy > tCy ? fp.y : fp.y + fh;
    ex = tCx; ey = tCy < fCy ? tp.y + th : tp.y;
  }

  const act   = (edge.on_delete || 'RESTRICT').toUpperCase().replace(/ /g, '_');
  const color = edgeColor(act);
  const dash  = act === 'CASCADE' ? '6,3' : act === 'SET_NULL' ? '' : '2.5,2.5';
  const key   = ['CASCADE','SET_NULL','RESTRICT'].includes(act) ? act : 'RESTRICT';

  // bezier path
  const path = mkSvg('path');
  path.setAttribute('d', bezier(sx, sy, ex, ey));
  path.setAttribute('stroke', color);
  path.setAttribute('stroke-width', '1.6');
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke-opacity', '.7');
  if (dash) path.setAttribute('stroke-dasharray', dash);
  path.setAttribute('marker-end', `url(#arr-${key})`);
  path.setAttribute('marker-start', `url(#arrS-${key})`);
  edgesG.appendChild(path);

  // mid-label
  const mx = (sx + ex) / 2, my = (sy + ey) / 2;
  const pill = mkSvg('g');
  const lbl  = mkSvg('text');
  lbl.setAttribute('class', 'gr-edge-lbl');
  lbl.setAttribute('x', mx);
  lbl.setAttribute('y', my - 5);
  lbl.setAttribute('text-anchor', 'middle');
  lbl.setAttribute('fill', color);
  lbl.setAttribute('opacity', '.75');
  lbl.textContent = act.substring(0, 3);
  pill.appendChild(lbl);
  edgesG.appendChild(pill);
}

function edgeColor(act) {
  if (act === 'CASCADE')  return '#3b82f6';
  if (act === 'SET_NULL') return '#f59e0b';
  return '#ef4444';
}

function bezier(sx, sy, ex, ey) {
  const dx = Math.abs(ex - sx) * .5;
  const cx1 = sx + (ex >= sx ?  dx : -dx);
  const cx2 = ex - (ex >= sx ?  dx : -dx);
  return `M ${sx} ${sy} C ${cx1} ${sy}, ${cx2} ${ey}, ${ex} ${ey}`;
}

/* ── Viewport transform ───────────────────────────────────────────────── */
function applyTransform() {
  viewport.setAttribute('transform', `translate(${tx},${ty}) scale(${scale})`);
  if (elZoomVal) elZoomVal.textContent = Math.round(scale * 100) + '%';
  if (showMini) drawMinimap();
}

function applyZoom(newScale, cx, cy) {
  newScale = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, newScale));
  // Zoom around screen point (cx, cy)
  const ratio = newScale / scale;
  tx = cx - ratio * (cx - tx);
  ty = cy - ratio * (cy - ty);
  scale = newScale;
  applyTransform();
}

function wrapCx() { return wrap.clientWidth  / 2; }
function wrapCy() { return wrap.clientHeight / 2; }

/* ── Pan ──────────────────────────────────────────────────────────────── */
function initPan() {
  wrap.addEventListener('mousedown', ev => {
    // Only start panning if clicking canvas background (not a node)
    const target = ev.target;
    if (target.closest('.gr-node-head[data-drag]')) return; // handled by drag
    if (target.closest('.gr-node')) return;
    if (ev.button !== 0) return;
    isPanning = true;
    panSX = ev.clientX; panSY = ev.clientY;
    panTX = tx;         panTY = ty;
    wrap.style.cursor = 'grabbing';
    ev.preventDefault();
  });

  document.addEventListener('mousemove', ev => {
    if (!isPanning) return;
    tx = panTX + (ev.clientX - panSX);
    ty = panTY + (ev.clientY - panSY);
    applyTransform();
  });

  document.addEventListener('mouseup', () => {
    if (isPanning) { isPanning = false; wrap.style.cursor = 'grab'; }
  });
}

/* ── Scroll-wheel zoom ───────────────────────────────────────────────── */
function initWheel() {
  wrap.addEventListener('wheel', ev => {
    ev.preventDefault();
    const delta = ev.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
    const rect  = wrap.getBoundingClientRect();
    const cx    = ev.clientX - rect.left;
    const cy    = ev.clientY - rect.top;
    applyZoom(scale + delta, cx, cy);
  }, { passive: false });
}

/* ── Node drag ────────────────────────────────────────────────────────── */
function initDrag() {
  // Delegate to document-level listeners for smooth dragging
  document.addEventListener('mousedown', ev => {
    const head = ev.target.closest('[data-drag]');
    if (!head) return;
    const name = head.dataset.drag;
    if (!name || !positions[name]) return;
    const pos = positions[name];
    dragging = {
      name,
      startMX: ev.clientX,
      startMY: ev.clientY,
      startX:  pos.x,
      startY:  pos.y,
    };
    ev.stopPropagation();
    ev.preventDefault();
  });

  document.addEventListener('mousemove', ev => {
    if (!dragging) return;
    // Convert mouse delta from screen to SVG user space
    const dx = (ev.clientX - dragging.startMX) / scale;
    const dy = (ev.clientY - dragging.startMY) / scale;
    const nx = dragging.startX + dx;
    const ny = dragging.startY + dy;

    // Update foreignObject position
    const fo = document.getElementById(`grfo-${cssEsc(dragging.name)}`);
    if (fo) {
      fo.setAttribute('x', nx);
      fo.setAttribute('y', ny);
    }
    positions[dragging.name] = { x: nx, y: ny };
    redrawEdges();
  });

  document.addEventListener('mouseup', () => {
    dragging = null;
  });
}

/* ── Fit view ────────────────────────────────────────────────────────── */
function fitView() {
  if (!gData?.tables?.length) return;
  const W = wrap.clientWidth, H = wrap.clientHeight;
  const PAD = 36;

  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  gData.tables.forEach(t => {
    const p = positions[t.name];
    if (!p) return;
    const h = nodeHeight(t);
    x0 = Math.min(x0, p.x);           y0 = Math.min(y0, p.y);
    x1 = Math.max(x1, p.x + NODE_W);  y1 = Math.max(y1, p.y + h);
  });

  const bW = x1 - x0 || 1, bH = y1 - y0 || 1;
  const newScale = Math.min(
    (W - PAD * 2) / bW,
    (H - PAD * 2) / bH,
    1.0   // never zoom in beyond 100% on fit
  );
  scale = Math.max(ZOOM_MIN, newScale);
  tx = (W - bW * scale) / 2 - x0 * scale;
  ty = (H - bH * scale) / 2 - y0 * scale;
  applyTransform();
}

/* ── Minimap ─────────────────────────────────────────────────────────── */
function drawMinimap() {
  if (!showMini || !gData?.tables?.length) return;
  const ctx = minimap.getContext('2d');
  const mW = minimap.width  = 170;
  const mH = minimap.height = 110;
  ctx.clearRect(0, 0, mW, mH);

  // bounding box of all nodes (user space)
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  gData.tables.forEach(t => {
    const p = positions[t.name];
    if (!p) return;
    const h = nodeHeight(t);
    x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y);
    x1 = Math.max(x1, p.x + NODE_W); y1 = Math.max(y1, p.y + h);
  });
  const bW = (x1 - x0) || 1, bH = (y1 - y0) || 1;
  const PAD = 8;
  const sc = Math.min((mW - PAD*2) / bW, (mH - PAD*2) / bH);

  function toM(x, y) {
    return [PAD + (x - x0) * sc, PAD + (y - y0) * sc];
  }

  // edges
  (gData.edges || []).forEach(e => {
    const fp = positions[e.from_table], tp = positions[e.to_table];
    if (!fp || !tp) return;
    const fh = nodeHeight(gData.tables.find(t => t.name === e.from_table) || {});
    const th = nodeHeight(gData.tables.find(t => t.name === e.to_table)   || {});
    const [fx, fy] = toM(fp.x + NODE_W/2, fp.y + fh/2);
    const [tx2,ty2] = toM(tp.x + NODE_W/2, tp.y + th/2);
    ctx.beginPath();
    ctx.strokeStyle = edgeColor((e.on_delete || '').toUpperCase().replace(/ /g,'_'));
    ctx.globalAlpha = .45; ctx.lineWidth = .8;
    ctx.moveTo(fx, fy); ctx.lineTo(tx2, ty2); ctx.stroke();
  });
  ctx.globalAlpha = 1;

  // nodes
  gData.tables.forEach(t => {
    const p = positions[t.name];
    if (!p) return;
    const h = nodeHeight(t);
    const [mx, my] = toM(p.x, p.y);
    ctx.fillStyle   = hexA(colorFor(t.name), .25);
    ctx.strokeStyle = colorFor(t.name);
    ctx.lineWidth   = .8;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(mx, my, NODE_W*sc, h*sc, 2);
    else ctx.rect(mx, my, NODE_W*sc, h*sc);
    ctx.fill(); ctx.stroke();
  });

  // viewport rect (convert from screen to user space then to minimap)
  const vx0 = (-tx) / scale, vy0 = (-ty) / scale;
  const vW  = wrap.clientWidth / scale, vH = wrap.clientHeight / scale;
  const [vmx, vmy] = toM(vx0, vy0);
  ctx.strokeStyle = 'rgba(59,130,246,.55)';
  ctx.lineWidth   = 1;
  ctx.strokeRect(vmx, vmy, vW * sc, vH * sc);
}

/* ── Tooltip ─────────────────────────────────────────────────────────── */
function showTip(ev, html) {
  tooltip.innerHTML = html;
  tooltip.style.display = 'block';
  moveTip(ev);
}
function hideTip() { tooltip.style.display = 'none'; }
function moveTip(ev) {
  const tw = tooltip.offsetWidth || 240;
  const th = tooltip.offsetHeight || 90;
  let lx = ev.clientX + 14, ly = ev.clientY + 14;
  if (lx + tw > window.innerWidth  - 8) lx = ev.clientX - tw - 14;
  if (ly + th > window.innerHeight - 8) ly = ev.clientY - th - 14;
  tooltip.style.left = lx + 'px';
  tooltip.style.top  = ly + 'px';
}
document.addEventListener('mousemove', ev => {
  if (tooltip.style.display === 'block') moveTip(ev);
});

function buildTipHtml(tbl, color) {
  const relCount = (gData?.edges || [])
    .filter(e => e.from_table === tbl.name || e.to_table === tbl.name).length;
  const rows = tbl.row_count != null ? tbl.row_count.toLocaleString() : '–';
  return `<strong style="color:${color}">${esc(tbl.name)}</strong><br>
    <span class="gr-tip-label">columns</span> ${tbl.columns?.length ?? 0}&emsp;
    <span class="gr-tip-label">indexes</span> ${(tbl.indexes||[]).length}&emsp;
    <span class="gr-tip-label">relations</span> ${relCount}<br>
    <span class="gr-tip-label">rows</span> ${rows}`;
}

/* ── Helpers ─────────────────────────────────────────────────────────── */
function showLoading(v) { loading.style.display = v ? 'flex' : 'none'; }

function mkSvg(tag) { return document.createElementNS('http://www.w3.org/2000/svg', tag); }

function esc(s)     { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function escAttr(s) { return String(s ?? '').replace(/"/g,'&quot;'); }
function cssEsc(s)  {
  if (window.CSS?.escape) return CSS.escape(s);
  return String(s).replace(/([!"#$%&'()*+,.\/:;<=>?@[\\\]^`{|}~\s])/g,'\\$1');
}

function hexA(hex, a) {
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function shortType(t) {
  const lower = String(t ?? '').toLowerCase();
  return ({
    'character varying':              'varchar',
    'integer':                        'int',
    'bigint':                         'int8',
    'smallint':                       'int2',
    'boolean':                        'bool',
    'timestamp without time zone':    'timestamp',
    'timestamp with time zone':       'timestamptz',
    'double precision':               'float8',
  })[lower] || lower.split('(')[0];
}

function fmtRows(n) {
  if (n == null) return '';
  return n === 0 ? '0 rows' : n.toLocaleString() + ' rows';
}

// polyfill roundRect
if (!CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function (x,y,w,h,r) {
    this.beginPath();
    this.moveTo(x+r,y);
    this.lineTo(x+w-r,y); this.quadraticCurveTo(x+w,y,x+w,y+r);
    this.lineTo(x+w,y+h-r); this.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    this.lineTo(x+r,y+h); this.quadraticCurveTo(x,y+h,x,y+h-r);
    this.lineTo(x,y+r); this.quadraticCurveTo(x,y,x+r,y);
    this.closePath();
  };
}

})();
