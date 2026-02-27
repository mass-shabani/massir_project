/**
 * db_graph — Schema Graph Engine  v2.0
 * ──────────────────────────────────────────────────────────────
 * Fetches live schema JSON from /db/graph/data, then:
 *  • renders draggable table nodes
 *  • draws bezier FK edges on an SVG overlay
 *  • supports pan, fit-view, minimap, edge toggle, refresh
 */

;(function () {
'use strict';

/* ── DOM refs ────────────────────────────────────────────────── */
const wrap      = document.getElementById('grWrap');
const svgEl     = document.getElementById('grSvg');
const nodesEl   = document.getElementById('grNodes');
const loading   = document.getElementById('grLoading');
const emptyMsg  = document.getElementById('grEmpty');
const tooltip   = document.getElementById('grTooltip');
const minimap   = document.getElementById('grMinimap');

const btnRefresh = document.getElementById('btnRefresh');
const btnFit     = document.getElementById('btnFit');
const btnEdges   = document.getElementById('btnEdges');
const btnMini    = document.getElementById('btnMini');

const elTables = document.getElementById('sTables');
const elEdges  = document.getElementById('sEdges');
const elCols   = document.getElementById('sCols');
const elIdx    = document.getElementById('sIdx');
const elConn   = document.getElementById('grConnName');

/* ── State ───────────────────────────────────────────────────── */
let gData       = null;        // full graph payload
let positions   = {};          // { tableName: {x, y} }
let showEdges   = true;
let showMini    = false;
let panX = 0, panY = 0;
let isPanning   = false;
let panStart    = {x: 0, y: 0};
let zTop        = 10;

/* ── Colour palette (10 colours cycled) ─────────────────────── */
const PALETTE = [
  '#63b3ed','#b794f4','#68d391','#f6ad55',
  '#fc8181','#76e4f7','#fbd38d','#f687b3',
  '#9ae6b4','#bee3f8',
];
let palIdx = 0;
const tblColor = {};
function colorFor(name) {
  if (!tblColor[name]) tblColor[name] = PALETTE[palIdx++ % PALETTE.length];
  return tblColor[name];
}

/* ── Bootstrap ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadGraph();

  btnRefresh?.addEventListener('click', () => { reset(); loadGraph(); });
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

  initPan();
  initWheelZoom();
});

/* ── Load ────────────────────────────────────────────────────── */
async function loadGraph() {
  showLoading(true);
  try {
    const res = await fetch('/db/graph/data');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    gData = await res.json();

    if (!gData.connected || !gData.tables?.length) {
      showLoading(false);
      emptyMsg.style.display = 'flex';
      return;
    }

    if (elConn) elConn.textContent =
      `connection: ${gData.connection_name || '–'}`
      + ` · ${gData.tables.length} tables`;

    updateStats(gData.stats);
    computeLayout(gData.tables, gData.edges);
    renderNodes(gData.tables);
    redrawEdges();

  } catch (err) {
    console.error('[db_graph] load error:', err);
    emptyMsg.style.display = 'flex';
    emptyMsg.querySelector('p:last-of-type')
      .textContent = `⚠ Failed to load schema: ${err.message}`;
  } finally {
    showLoading(false);
  }
}

/* ── Reset ───────────────────────────────────────────────────── */
function reset() {
  positions = {};
  palIdx    = 0;
  Object.keys(tblColor).forEach(k => delete tblColor[k]);
  nodesEl.innerHTML = '';
  svgEl.innerHTML   = '';
  emptyMsg.style.display = 'none';
  panX = panY = 0;
  nodesEl.style.transform = '';
  if (elConn) elConn.textContent = 'Loading schema…';
}

/* ── Stats ───────────────────────────────────────────────────── */
function updateStats(s) {
  if (elTables) elTables.textContent = s?.tables  ?? '–';
  if (elEdges)  elEdges.textContent  = s?.edges   ?? '–';
  if (elCols)   elCols.textContent   = s?.columns ?? '–';
  if (elIdx)    elIdx.textContent    = s?.indexes ?? '–';
}

/* ── Auto-layout ─────────────────────────────────────────────── */
function computeLayout(tables, edges) {
  const W   = wrap.clientWidth  || 920;
  const H   = wrap.clientHeight || 640;
  const PAD = 42;
  const NW  = 230, NH = 270;
  const n   = tables.length;
  if (!n) return;

  // degree map → high-degree nodes get centre-priority
  const deg = {};
  tables.forEach(t => { deg[t.name] = 0; });
  (edges || []).forEach(e => {
    if (e.from_table) deg[e.from_table] = (deg[e.from_table] || 0) + 1;
    if (e.to_table)   deg[e.to_table]   = (deg[e.to_table]   || 0) + 1;
  });
  const sorted = [...tables].sort((a, b) => deg[b.name] - deg[a.name]);

  const cols  = Math.max(1, Math.ceil(Math.sqrt(n * 1.5)));
  const cellW = Math.max(NW + PAD, (W - PAD * 2) / cols);
  const cellH = Math.max(NH + PAD, (H - PAD * 2) / Math.ceil(n / cols));

  sorted.forEach((t, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const jog = (row % 2) ? cellW * 0.22 : 0;   // stagger alternating rows
    positions[t.name] = {
      x: PAD + col * cellW + jog,
      y: PAD + row * cellH,
    };
  });
}

/* ── Render nodes ────────────────────────────────────────────── */
function renderNodes(tables) {
  tables.forEach((tbl, i) => {
    const pos   = positions[tbl.name] || {x: 60 + i * 240, y: 60};
    const color = colorFor(tbl.name);
    const el    = buildNode(tbl, color, pos, i);
    nodesEl.appendChild(el);
    makeDraggable(el, tbl.name);
  });
  // mark FK columns based on edges
  markFkBadges();
}

function buildNode(tbl, color, pos, z) {
  const el      = document.createElement('div');
  el.className  = 'gr-node';
  el.id         = `grn-${cssEsc(tbl.name)}`;
  el.dataset.table = tbl.name;
  el.style.cssText = `left:${pos.x}px; top:${pos.y}px; z-index:${z + 3};`
                   + ` border-top:2px solid ${color};`;

  el.innerHTML = [
    `<div class="gr-node-head" style="background:${hexA(color,.09)}">`,
      `<span class="gr-node-icon">🗄️</span>`,
      `<span class="gr-node-name" style="color:${color}">${esc(tbl.name)}</span>`,
      `<span class="gr-node-count">${tbl.columns?.length ?? 0} cols</span>`,
    `</div>`,
    `<div class="gr-node-body" id="grb-${cssEsc(tbl.name)}">`,
      buildColRows(tbl.columns || []),
    `</div>`,
    `<div class="gr-node-foot">`,
      `<span>${(tbl.indexes||[]).length} idx</span>`,
      `<span>${fmtRows(tbl.row_count)}</span>`,
    `</div>`,
  ].join('');

  // head hover → tooltip
  el.querySelector('.gr-node-head').addEventListener('mouseenter', ev => {
    showTip(ev, buildTipHtml(tbl, color));
  });
  el.querySelector('.gr-node-head').addEventListener('mouseleave', hideTip);

  return el;
}

function buildColRows(columns) {
  const MAX = 12;
  let html = '';
  columns.slice(0, MAX).forEach(col => {
    const b = badgeFor(col);
    html += `<div class="gr-col" data-col="${escAttr(col.name)}">` +
      `<span class="gr-col-badge ${b.cls}">${b.lbl}</span>` +
      `<span class="gr-col-name">${esc(col.name)}</span>` +
      `<span class="gr-col-type">${esc(shortType(col.type))}</span>` +
    `</div>`;
  });
  if (columns.length > MAX)
    html += `<div class="gr-col-more">+ ${columns.length - MAX} more…</div>`;
  return html;
}

function badgeFor(col) {
  if (col.primary_key)  return {cls: 'cbadge-pk', lbl: 'PK'};
  if (col.unique)       return {cls: 'cbadge-uk', lbl: 'UK'};
  return {cls: 'cbadge-empty', lbl: ''};
}

function markFkBadges() {
  if (!gData?.edges) return;
  const fkMap = {};   // { tableName: Set<colName> }
  gData.edges.forEach(e => {
    (e.from_columns || []).forEach(c => {
      (fkMap[e.from_table] = fkMap[e.from_table] || new Set()).add(c);
    });
  });
  Object.entries(fkMap).forEach(([tbl, cols]) => {
    const bodyEl = document.getElementById(`grb-${cssEsc(tbl)}`);
    if (!bodyEl) return;
    cols.forEach(colName => {
      const row = bodyEl.querySelector(`[data-col="${cssEsc(colName)}"]`);
      if (!row) return;
      const badge = row.querySelector('.gr-col-badge');
      if (badge?.classList.contains('cbadge-empty')) {
        badge.className  = 'gr-col-badge cbadge-fk';
        badge.textContent = 'FK';
      }
    });
  });
}

/* ── SVG edges ───────────────────────────────────────────────── */
function redrawEdges() {
  svgEl.innerHTML = buildDefs();
  if (!showEdges || !gData?.edges?.length) return;
  gData.edges.forEach(e => drawEdge(e));
  if (showMini) drawMinimap();
}

function buildDefs() {
  const markers = {
    'CASCADE':  '#63b3ed',
    'SET_NULL': '#f6ad55',
    'RESTRICT': '#fc8181',
    'DEFAULT':  '#fc8181',
  };
  let d = '<defs>';
  Object.entries(markers).forEach(([k, c]) => {
    d += `<marker id="arr-${k}" markerWidth="7" markerHeight="7"
            refX="6" refY="3.5" orient="auto">
            <path d="M0,1 L6,3.5 L0,6 Z" fill="${c}" opacity=".85"/>
          </marker>`;
  });
  d += '</defs>';
  return d;
}

function drawEdge(edge) {
  const fEl = document.getElementById(`grn-${cssEsc(edge.from_table)}`);
  const tEl = document.getElementById(`grn-${cssEsc(edge.to_table)}`);
  if (!fEl || !tEl || edge.from_table === edge.to_table) return;

  const fR = nodeRect(fEl);
  const tR = nodeRect(tEl);
  const {sx, sy, ex, ey} = calcPorts(fR, tR);

  const act   = (edge.on_delete || 'RESTRICT').toUpperCase().replace(' ', '_');
  const color = edgeColor(act);
  const dash  = act === 'CASCADE' ? '5,3' : act === 'SET_NULL' ? '0' : '2,2';
  const mid   = `url(#arr-${['CASCADE','SET_NULL','RESTRICT'].includes(act) ? act : 'DEFAULT'})`;

  // path
  const path = mkSvg('path');
  path.setAttribute('class', 'gr-edge');
  path.setAttribute('d', bezier(sx, sy, ex, ey));
  path.setAttribute('stroke', color);
  path.setAttribute('stroke-width', '1.5');
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke-opacity', '.62');
  if (dash !== '0') path.setAttribute('stroke-dasharray', dash);
  path.setAttribute('marker-end', mid);
  svgEl.appendChild(path);

  // label
  const mx = (sx + ex) / 2;
  const my = (sy + ey) / 2;
  const lbl = mkSvg('text');
  lbl.setAttribute('class', 'gr-edge-lbl');
  lbl.setAttribute('x', mx);
  lbl.setAttribute('y', my - 5);
  lbl.setAttribute('text-anchor', 'middle');
  lbl.setAttribute('fill', color);
  lbl.setAttribute('opacity', '.65');
  lbl.textContent = act.substring(0, 3);
  svgEl.appendChild(lbl);

  // origin dot
  const dot = mkSvg('circle');
  dot.setAttribute('cx', sx); dot.setAttribute('cy', sy); dot.setAttribute('r', '3.5');
  dot.setAttribute('fill', color); dot.setAttribute('opacity', '.8');
  svgEl.appendChild(dot);
}

function edgeColor(act) {
  if (act === 'CASCADE')  return '#63b3ed';
  if (act === 'SET_NULL') return '#f6ad55';
  return '#fc8181';
}

function nodeRect(el) {
  const wR = wrap.getBoundingClientRect();
  const eR = el.getBoundingClientRect();
  return {
    x: eR.left - wR.left - panX,
    y: eR.top  - wR.top  - panY,
    w: eR.width, h: eR.height,
  };
}

function calcPorts(f, t) {
  const fCx = f.x + f.w/2, fCy = f.y + f.h/2;
  const tCx = t.x + t.w/2, tCy = t.y + t.h/2;
  let sx, sy, ex, ey;
  if (Math.abs(fCx - tCx) >= Math.abs(fCy - tCy)) {
    sx = fCx > tCx ? f.x : f.x + f.w;   sy = fCy;
    ex = tCx < fCx ? t.x + t.w : t.x;   ey = tCy;
  } else {
    sx = fCx; sy = fCy > tCy ? f.y : f.y + f.h;
    ex = tCx; ey = tCy < fCy ? t.y + t.h : t.y;
  }
  return {sx, sy, ex, ey};
}

function bezier(sx, sy, ex, ey) {
  const dx = Math.abs(ex - sx) * .55;
  const dy = Math.abs(ey - sy) * .55;
  const cx1 = sx + (ex > sx ?  dx : -dx);
  const cx2 = ex - (ex > sx ?  dx : -dx);
  const cy1 = sy;
  const cy2 = ey;
  return `M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${ex} ${ey}`;
}

/* ── Drag nodes ──────────────────────────────────────────────── */
function makeDraggable(el, name) {
  let dragging = false;
  let sm = {x:0, y:0}, sp = {x:0, y:0};

  el.addEventListener('mousedown', ev => {
    if (ev.button !== 0) return;
    dragging = true;
    sm = {x: ev.clientX, y: ev.clientY};
    sp = {x: parseInt(el.style.left), y: parseInt(el.style.top)};
    el.style.zIndex = ++zTop;
    el.classList.add('gr-node--dragging');
    ev.stopPropagation();
  });

  document.addEventListener('mousemove', ev => {
    if (!dragging) return;
    const nx = sp.x + ev.clientX - sm.x;
    const ny = sp.y + ev.clientY - sm.y;
    el.style.left = nx + 'px';
    el.style.top  = ny + 'px';
    positions[name] = {x: nx, y: ny};
    redrawEdges();
  });

  document.addEventListener('mouseup', () => {
    if (dragging) { dragging = false; el.classList.remove('gr-node--dragging'); }
  });
}

/* ── Pan canvas ──────────────────────────────────────────────── */
function initPan() {
  wrap.addEventListener('mousedown', ev => {
    if (ev.target !== wrap && ev.target !== svgEl
        && !ev.target.classList.contains('gr-nodes')) return;
    isPanning = true;
    panStart  = {x: ev.clientX - panX, y: ev.clientY - panY};
    wrap.style.cursor = 'grabbing';
  });
  document.addEventListener('mousemove', ev => {
    if (!isPanning) return;
    panX = ev.clientX - panStart.x;
    panY = ev.clientY - panStart.y;
    nodesEl.style.transform = `translate(${panX}px,${panY}px)`;
    redrawEdges();
  });
  document.addEventListener('mouseup', () => {
    if (isPanning) { isPanning = false; wrap.style.cursor = 'grab'; }
  });
}

/* ── Wheel zoom (pan only on shift) ─────────────────────────── */
function initWheelZoom() {
  wrap.addEventListener('wheel', ev => {
    ev.preventDefault();
    const STEP = 40;
    if (ev.shiftKey) {
      panX -= ev.deltaX || 0;
      panY -= ev.deltaY || 0;
    } else {
      panY -= ev.deltaY > 0 ? STEP : -STEP;
    }
    nodesEl.style.transform = `translate(${panX}px,${panY}px)`;
    redrawEdges();
  }, {passive: false});
}

/* ── Fit view ────────────────────────────────────────────────── */
function fitView() {
  if (!gData?.tables?.length) return;
  const W = wrap.clientWidth, H = wrap.clientHeight;
  const PAD = 40;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  gData.tables.forEach(t => {
    const p = positions[t.name];
    if (!p) return;
    x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y);
    x1 = Math.max(x1, p.x + 220); y1 = Math.max(y1, p.y + 280);
  });
  panX = (W - (x1 - x0)) / 2 - x0 + PAD;
  panY = (H - (y1 - y0)) / 2 - y0 + PAD;
  nodesEl.style.transform = `translate(${panX}px,${panY}px)`;
  redrawEdges();
}

/* ── Minimap ─────────────────────────────────────────────────── */
function drawMinimap() {
  if (!showMini || !gData?.tables?.length) return;
  const ctx = minimap.getContext('2d');
  const mW  = minimap.width  = 160;
  const mH  = minimap.height = 100;
  ctx.clearRect(0, 0, mW, mH);

  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  gData.tables.forEach(t => {
    const p = positions[t.name];
    if (!p) return;
    x0 = Math.min(x0, p.x); y0 = Math.min(y0, p.y);
    x1 = Math.max(x1, p.x + 220); y1 = Math.max(y1, p.y + 280);
  });
  const bW = x1 - x0 || 1, bH = y1 - y0 || 1;
  const scX = (mW - 10) / bW, scY = (mH - 10) / bH;
  const sc  = Math.min(scX, scY);

  // draw edges
  if (gData.edges) {
    gData.edges.forEach(e => {
      const fp = positions[e.from_table], tp = positions[e.to_table];
      if (!fp || !tp) return;
      ctx.beginPath();
      ctx.strokeStyle = edgeColor((e.on_delete || '').toUpperCase().replace(' ','_'));
      ctx.globalAlpha = .5;
      ctx.lineWidth   = .8;
      ctx.moveTo(5 + (fp.x + 110 - x0) * sc, 5 + (fp.y + 30 - y0) * sc);
      ctx.lineTo(5 + (tp.x + 110 - x0) * sc, 5 + (tp.y + 30 - y0) * sc);
      ctx.stroke();
    });
  }
  ctx.globalAlpha = 1;

  // draw nodes
  gData.tables.forEach(t => {
    const p = positions[t.name];
    if (!p) return;
    ctx.fillStyle   = hexA(colorFor(t.name), .7);
    ctx.strokeStyle = colorFor(t.name);
    ctx.lineWidth   = .6;
    ctx.beginPath();
    ctx.roundRect(
      5 + (p.x - x0) * sc,
      5 + (p.y - y0) * sc,
      220 * sc, 30 * sc, 2
    );
    ctx.fill(); ctx.stroke();
  });

  // viewport indicator
  const vx = 5 + (-panX - x0) * sc;
  const vy = 5 + (-panY - y0) * sc;
  const vw = wrap.clientWidth  * sc;
  const vh = wrap.clientHeight * sc;
  ctx.strokeStyle = 'rgba(255,255,255,.35)';
  ctx.lineWidth   = .8;
  ctx.strokeRect(vx, vy, vw, vh);
}

/* ── Tooltip ─────────────────────────────────────────────────── */
function showTip(ev, html) {
  tooltip.innerHTML      = html;
  tooltip.style.display  = 'block';
  moveTip(ev);
}
function hideTip()  { tooltip.style.display = 'none'; }
function moveTip(ev) {
  const tw = tooltip.offsetWidth  || 220;
  const th = tooltip.offsetHeight || 80;
  let tx = ev.clientX + 14, ty = ev.clientY + 14;
  if (tx + tw > window.innerWidth  - 8) tx = ev.clientX - tw - 14;
  if (ty + th > window.innerHeight - 8) ty = ev.clientY - th - 14;
  tooltip.style.left = tx + 'px';
  tooltip.style.top  = ty + 'px';
}
document.addEventListener('mousemove', ev => {
  if (tooltip.style.display === 'block') moveTip(ev);
});

function buildTipHtml(tbl, color) {
  const relCount = (gData?.edges || [])
    .filter(e => e.from_table === tbl.name || e.to_table === tbl.name).length;
  const rows = tbl.row_count != null ? tbl.row_count.toLocaleString() : '–';
  return `<strong style="color:${color}">${esc(tbl.name)}</strong><br>`
       + `<span style="color:#4a5568">columns:</span> ${tbl.columns?.length ?? 0}&emsp;`
       + `<span style="color:#4a5568">indexes:</span> ${(tbl.indexes||[]).length}&emsp;`
       + `<span style="color:#4a5568">relations:</span> ${relCount}<br>`
       + `<span style="color:#4a5568">rows:</span> ${rows}`;
}

/* ── Helpers ─────────────────────────────────────────────────── */
function showLoading(v) { loading.style.display = v ? 'flex' : 'none'; }

function esc(s)     { return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function escAttr(s) { return String(s ?? '').replace(/"/g,'&quot;'); }
function cssEsc(s)  {
  if (window.CSS?.escape) return CSS.escape(s);
  return String(s).replace(/([!"#$%&'()*+,./:;<=>?@[\\\]^`{|}~\s])/g,'\\$1');
}
function mkSvg(tag) { return document.createElementNS('http://www.w3.org/2000/svg', tag); }

function hexA(hex, a) {
  const r = parseInt(hex.slice(1,3),16);
  const g = parseInt(hex.slice(3,5),16);
  const b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}

function shortType(t) {
  const lower = String(t ?? '').toLowerCase();
  return ({
    'character varying': 'varchar',
    'integer':           'int',
    'bigint':            'int8',
    'smallint':          'int2',
    'boolean':           'bool',
    'timestamp without time zone': 'timestamp',
    'timestamp with time zone':    'timestamptz',
    'double precision':  'float8',
  })[lower] || lower.split('(')[0];
}

function fmtRows(n) {
  if (n == null) return '';
  return n === 0 ? '0 rows' : n.toLocaleString() + ' rows';
}

// polyfill roundRect for older browsers
if (!CanvasRenderingContext2D.prototype.roundRect) {
  CanvasRenderingContext2D.prototype.roundRect = function(x,y,w,h,r) {
    this.beginPath();
    this.moveTo(x+r, y);
    this.lineTo(x+w-r, y); this.quadraticCurveTo(x+w, y, x+w, y+r);
    this.lineTo(x+w, y+h-r); this.quadraticCurveTo(x+w, y+h, x+w-r, y+h);
    this.lineTo(x+r, y+h); this.quadraticCurveTo(x, y+h, x, y+h-r);
    this.lineTo(x, y+r); this.quadraticCurveTo(x, y, x+r, y);
    this.closePath();
  };
}

})();
