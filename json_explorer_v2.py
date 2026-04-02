#!/usr/bin/env python3
"""
JSON Explorer v2 — Browse a directory of report_*.json files in the browser.

Usage:
    python json_explorer_v2.py                        # looks for ./analyses/
    python json_explorer_v2.py --dir /path/to/analyses
    python json_explorer_v2.py --dir ./analyses --port 8080
"""

import argparse
import json
import re
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

# ─────────────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>JSON Explorer v2</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Syne:wght@400;700;800&display=swap');

:root {
  --bg:       #0b0d12;
  --panel:    #10131a;
  --panel2:   #13161f;
  --border:   #1c2030;
  --border2:  #252a3a;
  --accent:   #00e5ff;
  --accent2:  #7b61ff;
  --danger:   #ff4d6d;
  --success:  #00e096;
  --warn:     #ffb627;
  --text:     #c8cfe0;
  --muted:    #4e5770;
  --key:      #7b9cff;
  --str:      #80ffb4;
  --num:      #ffd080;
  --bool:     #ff9f7b;
  --null:     #ff6b8a;
  --mono:     'JetBrains Mono', monospace;
  --display:  'Syne', sans-serif;
  --files-w:  260px;
  --keys-w:   220px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--mono);
  font-size: 13px;
  height: 100vh;
  display: grid;
  grid-template-rows: 52px 1fr;
  grid-template-columns: var(--files-w) var(--keys-w) 1fr;
  overflow: hidden;
}

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

/* ══════════════════════════════════════════════
   HEADER
══════════════════════════════════════════════ */
header {
  grid-column: 1 / -1;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 18px;
  z-index: 10;
}
header h1 {
  font-family: var(--display);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: #fff;
  white-space: nowrap;
  flex-shrink: 0;
}
header h1 span { color: var(--accent); }
header h1 sup {
  font-size: 10px;
  color: var(--accent2);
  font-weight: 700;
  margin-left: 2px;
  vertical-align: super;
}

#active-file {
  font-size: 11px;
  color: var(--muted);
  padding: 3px 10px;
  background: var(--bg);
  border-radius: 4px;
  border: 1px solid var(--border);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 220px;
  flex-shrink: 0;
}

/* in-report search bar */
#search-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 7px;
  max-width: 460px;
  margin-left: auto;
}
#search {
  flex: 1;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 11px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 12px;
  outline: none;
  transition: border-color .18s;
}
#search:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(0,229,255,.08); }
#search::placeholder { color: var(--muted); }
#search-info { font-size: 11px; color: var(--muted); white-space: nowrap; min-width: 56px; text-align: right; }
.hbtn {
  background: var(--border);
  border: none;
  border-radius: 5px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 11px;
  padding: 4px 9px;
  cursor: pointer;
  transition: background .13s, color .13s;
  white-space: nowrap;
  flex-shrink: 0;
}
.hbtn:hover { background: var(--accent); color: #000; }

/* ══════════════════════════════════════════════
   COLUMN 1 — FILE BROWSER
══════════════════════════════════════════════ */
#files-panel {
  background: var(--panel);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
#files-header {
  padding: 10px 12px 8px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
#files-header .panel-title {
  font-family: var(--display);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 7px;
}
#file-search {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 5px 9px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 11px;
  outline: none;
  transition: border-color .15s;
}
#file-search:focus { border-color: var(--accent2); }
#file-search::placeholder { color: var(--muted); }
#file-count {
  font-size: 10px;
  color: var(--muted);
  margin-top: 5px;
}

#file-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all .13s;
  font-size: 11.5px;
  color: var(--text);
  user-select: none;
}
.file-item:hover { background: var(--border); }
.file-item.active {
  border-left-color: var(--accent2);
  background: rgba(123,97,255,.08);
  color: #fff;
}
.file-item .ficon { color: var(--muted); flex-shrink: 0; font-size: 10px; }
.file-item.active .ficon { color: var(--accent2); }
.file-item .fname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-item .fsize { font-size: 10px; color: var(--muted); flex-shrink: 0; }
.file-item.loading { opacity: .5; pointer-events: none; }

/* sort bar */
#sort-bar {
  display: flex;
  gap: 4px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.sort-btn {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 3px;
  border: 1px solid var(--border2);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-family: var(--mono);
  transition: all .13s;
}
.sort-btn:hover { border-color: var(--accent2); color: var(--text); }
.sort-btn.active { background: var(--accent2); border-color: var(--accent2); color: #fff; }

/* ══════════════════════════════════════════════
   COLUMN 2 — KEY SIDEBAR (per report)
══════════════════════════════════════════════ */
#keys-panel {
  background: var(--panel2);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
#keys-header {
  padding: 10px 12px 8px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  font-family: var(--display);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: var(--muted);
}
#key-list { flex: 1; overflow-y: auto; padding: 4px 0; }

.key-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all .12s;
  font-size: 11.5px;
  color: var(--text);
}
.key-item:hover { background: var(--border); }
.key-item.active {
  border-left-color: var(--accent);
  background: rgba(0,229,255,.05);
  color: var(--accent);
}
.key-item .kdot {
  width: 5px; height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.key-item .kname { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.key-item .kbadge {
  font-size: 9px;
  color: var(--muted);
  background: var(--bg);
  border-radius: 3px;
  padding: 1px 4px;
  flex-shrink: 0;
}
.dot-object  { background: var(--key); }
.dot-array   { background: var(--accent2); }
.dot-string  { background: var(--str); }
.dot-number  { background: var(--num); }
.dot-boolean { background: var(--bool); }
.dot-null    { background: var(--null); }

/* ══════════════════════════════════════════════
   COLUMN 3 — MAIN / JSON TREE
══════════════════════════════════════════════ */
#main {
  overflow-y: auto;
  padding: 18px 20px 60px;
  position: relative;
}

/* Breadcrumb */
#breadcrumb {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 14px;
}
.crumb { cursor: pointer; color: var(--accent); transition: opacity .1s; }
.crumb:hover { opacity: .7; text-decoration: underline; }
.crumb-sep { color: var(--border2); }

/* Stats cards */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
  margin-bottom: 18px;
}
.stat-card {
  background: var(--panel2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 11px 13px;
}
.stat-card .slabel { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px; }
.stat-card .svalue { font-family: var(--display); font-size: 19px; font-weight: 800; color: var(--accent); line-height: 1; }

/* Placeholder */
.placeholder {
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  height: 70%;
  gap: 12px; color: var(--muted);
  text-align: center;
}
.placeholder .icon { font-size: 44px; opacity: .2; }
.placeholder p { font-size: 12px; line-height: 1.6; }

/* ── JSON tree ── */
.tree { line-height: 1.9; }
.node { display: flex; align-items: flex-start; gap: 3px; }
.toggle {
  cursor: pointer; user-select: none;
  color: var(--muted); width: 13px; flex-shrink: 0;
  margin-top: 2px; font-size: 9px; transition: color .1s;
}
.toggle:hover { color: var(--accent); }
.children {
  padding-left: 20px;
  border-left: 1px solid var(--border);
  margin-left: 3px;
}
.children.hidden { display: none; }

.k  { color: var(--key); }
.s  { color: var(--str); }
.n  { color: var(--num); }
.b  { color: var(--bool); }
.nl { color: var(--null); }
.colon { color: var(--muted); margin: 0 3px; }
.meta  { font-size: 10px; color: var(--muted); margin-left: 3px; }

.str-full { display: none; }
.str-short { cursor: pointer; }
.str-short:hover { color: #fff; }
.str-short.expanded + .str-full { display: inline; }
.str-short.expanded { display: none; }

/* search highlights */
mark {
  background: rgba(255,182,39,.3);
  color: var(--warn);
  border-radius: 2px;
  padding: 0 1px;
}
mark.current { background: var(--warn); color: #000; }

/* copy-path fab */
#copy-btn {
  position: fixed;
  bottom: 18px; right: 18px;
  background: var(--accent2);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: var(--mono);
  font-size: 11px;
  cursor: pointer;
  transition: background .18s;
  z-index: 20;
  display: none;
}
#copy-btn:hover { background: var(--accent); color: #000; }

/* loading spinner */
.spinner {
  display: inline-block;
  width: 14px; height: 14px;
  border: 2px solid var(--border2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin .6s linear infinite;
  vertical-align: middle;
  margin-right: 6px;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* section title in main */
.section-title {
  font-family: var(--display);
  font-size: 20px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 16px;
}

.tag-row { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 10px; }
.tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 4px;
  border: 1px solid var(--border2);
  cursor: pointer;
  color: var(--text);
  background: var(--panel2);
  transition: all .12s;
}
.tag:hover { border-color: var(--accent); color: var(--accent); }
</style>
</head>
<body>

<!-- ── HEADER ── -->
<header>
  <h1>JSON <span>Explorer</span><sup>v2</sup></h1>
  <div id="active-file">No file selected</div>
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search within report… (Ctrl+F)" autocomplete="off" disabled>
    <span id="search-info"></span>
    <button class="hbtn" id="prev-match" title="Previous match">↑</button>
    <button class="hbtn" id="next-match" title="Next match">↓</button>
    <button class="hbtn" onclick="expandAll()">Expand all</button>
    <button class="hbtn" onclick="collapseAll()">Collapse all</button>
  </div>
</header>

<!-- ── COLUMN 1: FILE BROWSER ── -->
<div id="files-panel">
  <div id="files-header">
    <div class="panel-title">📁 Reports</div>
    <input id="file-search" type="text" placeholder="Filter by number or name…" autocomplete="off">
    <div id="file-count">Loading…</div>
  </div>
  <div id="sort-bar">
    <button class="sort-btn active" data-sort="num" onclick="setSort('num',this)">ID ↑</button>
    <button class="sort-btn" data-sort="name" onclick="setSort('name',this)">Name</button>
    <button class="sort-btn" data-sort="size" onclick="setSort('size',this)">Size</button>
  </div>
  <div id="file-list"></div>
</div>

<!-- ── COLUMN 2: KEY SIDEBAR ── -->
<div id="keys-panel">
  <div id="keys-header">Keys</div>
  <div id="key-list">
    <div class="placeholder" style="height:100%;padding:20px;font-size:11px;text-align:center;color:var(--muted)">
      Select a report to see its keys
    </div>
  </div>
</div>

<!-- ── COLUMN 3: MAIN VIEWER ── -->
<main id="main">
  <div class="placeholder">
    <div class="icon">⟨⟩</div>
    <p>Select a report from the file browser<br>to start exploring.</p>
  </div>
</main>

<button id="copy-btn" onclick="copyPath()">⎘ Copy path</button>

<script>
// ════════════════════════════════════════════════════════════
//  STATE
// ════════════════════════════════════════════════════════════
let ALL_FILES   = [];          // [{name, size, num}]
let CURR_DATA   = null;        // loaded JSON data
let CURR_FILE   = null;        // filename string
let CURR_KEY    = null;        // active top-level key
let CURR_PATH   = [];
let SORT_BY     = 'num';
let searchMatches = [], searchIdx = 0;

// ════════════════════════════════════════════════════════════
//  BOOT
// ════════════════════════════════════════════════════════════
async function boot() {
  const r = await fetch('/files');
  ALL_FILES = await r.json();
  renderFileList();
}

// ════════════════════════════════════════════════════════════
//  FILE LIST
// ════════════════════════════════════════════════════════════
function renderFileList(filter = '') {
  const q = filter.trim().toLowerCase();
  let files = ALL_FILES.filter(f =>
    !q || f.name.toLowerCase().includes(q) || String(f.num).includes(q)
  );

  // sort
  files = [...files].sort((a, b) => {
    if (SORT_BY === 'num')  return a.num - b.num;
    if (SORT_BY === 'name') return a.name.localeCompare(b.name);
    if (SORT_BY === 'size') return b.size - a.size;
    return 0;
  });

  const list = document.getElementById('file-list');
  list.innerHTML = '';
  document.getElementById('file-count').textContent =
    `${files.length} of ${ALL_FILES.length} reports`;

  files.forEach(f => {
    const el = document.createElement('div');
    el.className = 'file-item' + (f.name === CURR_FILE ? ' active' : '');
    el.dataset.name = f.name;
    el.innerHTML = `
      <span class="ficon">▸</span>
      <span class="fname">${esc(f.name)}</span>
      <span class="fsize">${fmtSize(f.size)}</span>`;
    el.onclick = () => loadFile(f.name);
    list.appendChild(el);
  });
}

document.getElementById('file-search').addEventListener('input', e => {
  renderFileList(e.target.value);
});

function setSort(key, btn) {
  SORT_BY = key;
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderFileList(document.getElementById('file-search').value);
}

// ════════════════════════════════════════════════════════════
//  LOAD A FILE
// ════════════════════════════════════════════════════════════
async function loadFile(name) {
  if (name === CURR_FILE) return;

  // mark loading
  document.querySelectorAll('.file-item').forEach(el => {
    el.classList.toggle('active', el.dataset.name === name);
  });

  // reset right panels
  CURR_DATA = null; CURR_KEY = null; CURR_PATH = [];
  clearSearch();
  document.getElementById('search').disabled = true;
  document.getElementById('active-file').textContent = name;
  document.getElementById('copy-btn').style.display = 'none';
  document.getElementById('main').innerHTML =
    `<div class="placeholder"><div class="icon"><span class="spinner"></span></div><p>Loading ${esc(name)}…</p></div>`;
  document.getElementById('key-list').innerHTML =
    `<div style="padding:16px;font-size:11px;color:var(--muted)">Loading…</div>`;

  const r = await fetch(`/report?name=${encodeURIComponent(name)}`);
  if (!r.ok) {
    document.getElementById('main').innerHTML =
      `<div class="placeholder"><p style="color:var(--danger)">Failed to load ${esc(name)}</p></div>`;
    return;
  }

  CURR_DATA = await r.json();
  CURR_FILE = name;
  document.getElementById('search').disabled = false;
  buildKeyList();
  showReportOverview();
}

// ════════════════════════════════════════════════════════════
//  KEY LIST (column 2)
// ════════════════════════════════════════════════════════════
function buildKeyList() {
  const list = document.getElementById('key-list');
  list.innerHTML = '';

  // "Overview" entry
  const ov = mkKeyItem('📊 Overview', 'object', null, '__overview__');
  ov.classList.add('active');
  list.appendChild(ov);

  const div = document.createElement('div');
  div.style.cssText = 'font-size:9px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;padding:8px 12px 3px;';
  div.textContent = 'Top-level keys';
  list.appendChild(div);

  for (const [k, v] of Object.entries(CURR_DATA)) {
    list.appendChild(mkKeyItem(k, typeOf(v), v, k));
  }
}

function mkKeyItem(label, type, val, key) {
  const el = document.createElement('div');
  el.className = 'key-item';
  el.dataset.key = key;

  const dot = document.createElement('span');
  dot.className = `kdot dot-${type}`;

  const name = document.createElement('span');
  name.className = 'kname';
  name.textContent = label;

  el.appendChild(dot);
  el.appendChild(name);

  if (val !== null && typeof val === 'object') {
    const cnt = Array.isArray(val) ? val.length : Object.keys(val).length;
    const badge = document.createElement('span');
    badge.className = 'kbadge';
    badge.textContent = Array.isArray(val) ? `[${cnt}]` : `{${cnt}}`;
    el.appendChild(badge);
  }

  el.onclick = () => {
    document.querySelectorAll('.key-item').forEach(e => e.classList.remove('active'));
    el.classList.add('active');
    clearSearch();
    if (key === '__overview__') showReportOverview();
    else renderSection(key);
  };
  return el;
}

// ════════════════════════════════════════════════════════════
//  REPORT OVERVIEW
// ════════════════════════════════════════════════════════════
function showReportOverview() {
  CURR_KEY = null; CURR_PATH = [];
  document.getElementById('copy-btn').style.display = 'none';

  const types = {};
  function walk(v) {
    const t = typeOf(v);
    types[t] = (types[t] || 0) + 1;
    if (t === 'object') Object.values(v).forEach(walk);
    else if (t === 'array') v.forEach(walk);
  }
  walk(CURR_DATA);

  const fileInfo = ALL_FILES.find(f => f.name === CURR_FILE) || {};
  const topKeys  = Object.keys(CURR_DATA).length;

  document.getElementById('main').innerHTML = `
    <div class="section-title">${esc(CURR_FILE)}</div>
    <div class="stats-grid">
      <div class="stat-card"><div class="slabel">File size</div><div class="svalue">${fmtSize(fileInfo.size||0)}</div></div>
      <div class="stat-card"><div class="slabel">Top keys</div><div class="svalue">${topKeys}</div></div>
      <div class="stat-card"><div class="slabel">Objects</div><div class="svalue" style="color:var(--key)">${types.object||0}</div></div>
      <div class="stat-card"><div class="slabel">Arrays</div><div class="svalue" style="color:var(--accent2)">${types.array||0}</div></div>
      <div class="stat-card"><div class="slabel">Strings</div><div class="svalue" style="color:var(--str)">${types.string||0}</div></div>
      <div class="stat-card"><div class="slabel">Numbers</div><div class="svalue" style="color:var(--num)">${types.number||0}</div></div>
    </div>
    <div style="font-size:12px;color:var(--muted);margin:14px 0 8px;font-family:var(--display);font-weight:700;letter-spacing:.5px;">Jump to key</div>
    <div class="tag-row" id="key-tags"></div>
  `;

  const tagRow = document.getElementById('key-tags');
  Object.keys(CURR_DATA).forEach(k => {
    const t = document.createElement('span');
    t.className = 'tag';
    t.textContent = k;
    t.onclick = () => {
      document.querySelectorAll('.key-item').forEach(el => {
        el.classList.toggle('active', el.dataset.key === k);
      });
      renderSection(k);
    };
    tagRow.appendChild(t);
  });
}

// ════════════════════════════════════════════════════════════
//  SECTION RENDERER
// ════════════════════════════════════════════════════════════
function renderSection(key) {
  CURR_KEY = key;
  CURR_PATH = [key];
  clearSearch();
  document.getElementById('copy-btn').style.display = 'block';

  const val = CURR_DATA[key];
  const main = document.getElementById('main');
  main.innerHTML = '';
  main.appendChild(makeBreadcrumb([key]));

  const tree = document.createElement('div');
  tree.className = 'tree';
  tree.appendChild(buildNode(val, key, [key]));
  main.appendChild(tree);
}

function makeBreadcrumb(path) {
  const bc = document.createElement('div');
  bc.id = 'breadcrumb';
  let html = `<span class="crumb" onclick="showReportOverview()">root</span>`;
  path.forEach((p, i) => {
    html += `<span class="crumb-sep">/</span><span class="crumb" onclick="crumbClick(${i})">${esc(String(p))}</span>`;
  });
  bc.innerHTML = html;
  return bc;
}

function crumbClick(idx) {
  // For now just re-render the section root
  renderSection(CURR_PATH[0]);
}

// ════════════════════════════════════════════════════════════
//  JSON TREE
// ════════════════════════════════════════════════════════════
function buildNode(val, label, path) {
  const t = typeOf(val);
  const wrap = document.createElement('div');

  if (t === 'object' || t === 'array') {
    const isArr = t === 'array';
    const count = isArr ? val.length : Object.keys(val).length;
    const [open, close] = isArr ? ['[', ']'] : ['{', '}'];

    const row = document.createElement('div');
    row.className = 'node';

    const tog = document.createElement('span');
    tog.className = 'toggle';
    tog.textContent = '▾';

    const lbl = document.createElement('span');
    if (label !== null) {
      lbl.innerHTML = `<span class="k">"${esc(String(label))}"</span><span class="colon">:</span>`;
    }
    lbl.innerHTML += `${open}<span class="meta">${count} ${isArr ? 'items' : 'keys'}</span>`;

    row.appendChild(tog);
    row.appendChild(lbl);

    const children = document.createElement('div');
    children.className = 'children';

    let rendered = false;
    const doRender = () => {
      if (rendered) return;
      rendered = true;
      const entries = isArr
        ? val.map((v, i) => [i, v])
        : Object.entries(val);
      entries.forEach(([k, v]) => {
        children.appendChild(buildNode(v, isArr ? null : k, [...path, k]));
      });
      const closeEl = document.createElement('div');
      closeEl.style.color = 'var(--muted)';
      closeEl.textContent = close;
      children.appendChild(closeEl);
    };

    tog.onclick = () => {
      doRender();
      const hidden = children.classList.toggle('hidden');
      tog.textContent = hidden ? '▸' : '▾';
    };

    if (count > 25) {
      children.classList.add('hidden');
      tog.textContent = '▸';
    } else {
      doRender();
    }

    wrap.appendChild(row);
    wrap.appendChild(children);

  } else {
    const row = document.createElement('div');
    row.className = 'node';
    const span = document.createElement('span');

    let lh = label !== null
      ? `<span class="k">"${esc(String(label))}"</span><span class="colon">:</span>`
      : '';

    if (t === 'string') {
      const MAX = 140;
      const escaped = esc(val);
      if (val.length > MAX) {
        span.innerHTML = `${lh}<span class="s str-short" onclick="this.classList.toggle('expanded')">"${escaped.slice(0,MAX)}<span style="color:var(--muted)">… (${val.length} chars)</span>"</span><span class="s str-full">"${escaped}"</span>`;
      } else {
        span.innerHTML = `${lh}<span class="s">"${escaped}"</span>`;
      }
    } else if (t === 'number') {
      span.innerHTML = `${lh}<span class="n">${val}</span>`;
    } else if (t === 'boolean') {
      span.innerHTML = `${lh}<span class="b">${val}</span>`;
    } else {
      span.innerHTML = `${lh}<span class="nl">null</span>`;
    }

    row.appendChild(span);
    wrap.appendChild(row);
  }

  return wrap;
}

// ════════════════════════════════════════════════════════════
//  IN-REPORT SEARCH
// ════════════════════════════════════════════════════════════
let _searchTimer;
document.getElementById('search').addEventListener('input', e => {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => doSearch(e.target.value.trim()), 280);
});
document.getElementById('prev-match').onclick = () => stepSearch(-1);
document.getElementById('next-match').onclick = () => stepSearch(1);
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'f' && !e.target.matches('#file-search')) {
    e.preventDefault();
    document.getElementById('search').focus();
    document.getElementById('search').select();
  }
});

function doSearch(q) {
  document.querySelectorAll('mark').forEach(m => { m.outerHTML = m.innerHTML; });
  searchMatches = []; searchIdx = 0;
  if (!q) { document.getElementById('search-info').textContent = ''; return; }

  const main = document.getElementById('main');
  const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let n;
  while ((n = walker.nextNode())) nodes.push(n);

  const re = new RegExp(escRe(q), 'gi');
  nodes.forEach(node => {
    if (!re.test(node.textContent)) return;
    re.lastIndex = 0;
    const frag = document.createDocumentFragment();
    let last = 0, m;
    while ((m = re.exec(node.textContent)) !== null) {
      frag.appendChild(document.createTextNode(node.textContent.slice(last, m.index)));
      const mark = document.createElement('mark');
      mark.textContent = m[0];
      searchMatches.push(mark);
      frag.appendChild(mark);
      last = re.lastIndex;
    }
    frag.appendChild(document.createTextNode(node.textContent.slice(last)));
    node.parentNode.replaceChild(frag, node);
  });

  const total = searchMatches.length;
  document.getElementById('search-info').textContent = total ? `1/${total}` : 'No matches';
  if (total) {
    searchMatches[0].classList.add('current');
    searchMatches[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

function stepSearch(dir) {
  if (!searchMatches.length) return;
  searchMatches[searchIdx].classList.remove('current');
  searchIdx = (searchIdx + dir + searchMatches.length) % searchMatches.length;
  searchMatches[searchIdx].classList.add('current');
  searchMatches[searchIdx].scrollIntoView({ behavior: 'smooth', block: 'center' });
  document.getElementById('search-info').textContent = `${searchIdx+1}/${searchMatches.length}`;
}

function clearSearch() {
  document.getElementById('search').value = '';
  document.getElementById('search-info').textContent = '';
  searchMatches = []; searchIdx = 0;
}

// ════════════════════════════════════════════════════════════
//  EXPAND / COLLAPSE ALL
// ════════════════════════════════════════════════════════════
function expandAll() {
  document.querySelectorAll('#main .children.hidden').forEach(c => {
    c.classList.remove('hidden');
    const tog = c.previousSibling?.querySelector?.('.toggle');
    if (tog) tog.textContent = '▾';
  });
}
function collapseAll() {
  document.querySelectorAll('#main .children:not(.hidden)').forEach(c => {
    c.classList.add('hidden');
    const tog = c.previousSibling?.querySelector?.('.toggle');
    if (tog) tog.textContent = '▸';
  });
}

// ════════════════════════════════════════════════════════════
//  COPY PATH
// ════════════════════════════════════════════════════════════
function copyPath() {
  const path = (CURR_FILE ? CURR_FILE + ' > ' : '') + CURR_PATH.join('.');
  navigator.clipboard.writeText(path);
  const btn = document.getElementById('copy-btn');
  btn.textContent = '✓ Copied!';
  setTimeout(() => btn.textContent = '⎘ Copy path', 1600);
}

// ════════════════════════════════════════════════════════════
//  UTILS
// ════════════════════════════════════════════════════════════
function typeOf(v) {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  return typeof v;
}
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}
function escRe(s) { return s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'); }
function fmtSize(b) {
  if (b < 1024) return b + ' B';
  if (b < 1024*1024) return (b/1024).toFixed(1) + ' KB';
  return (b/1024/1024).toFixed(1) + ' MB';
}

boot();
</script>
</body>
</html>
"""

# ─────────────────────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    analyses_dir: Path = None

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        qs     = parse_qs(parsed.query)

        if parsed.path == '/':
            self._send(200, 'text/html; charset=utf-8', HTML.encode())

        elif parsed.path == '/files':
            # Return sorted list of report_*.json files with metadata
            files = []
            for p in sorted(self.analyses_dir.glob('*.json')):
                num_match = re.search(r'(\d+)', p.stem)
                num = int(num_match.group(1)) if num_match else 0
                files.append({
                    'name': p.name,
                    'size': p.stat().st_size,
                    'num':  num,
                })
            self._send(200, 'application/json', json.dumps(files).encode())

        elif parsed.path == '/report':
            name = unquote(qs.get('name', [''])[0])
            # Security: only allow names that look like report files inside the dir
            safe_name = Path(name).name
            target = self.analyses_dir / safe_name
            if not target.exists() or not target.is_file():
                self._send(404, 'text/plain', b'Not found')
                return
            try:
                data = json.loads(target.read_text(encoding='utf-8'))
                self._send(200, 'application/json; charset=utf-8',
                           json.dumps(data, ensure_ascii=False).encode())
            except Exception as e:
                self._send(500, 'text/plain', str(e).encode())
        else:
            self._send(404, 'text/plain', b'Not found')

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='JSON Explorer v2 — browse a directory of JSON reports in the browser')
    parser.add_argument('--dir',  default='analyses',
                        help='Path to the analyses directory (default: ./analyses)')
    parser.add_argument('--port', type=int, default=7777,
                        help='Port to listen on (default: 7777)')
    parser.add_argument('--no-browser', action='store_true',
                        help='Do not auto-open the browser')
    args = parser.parse_args()

    d = Path(args.dir).resolve()
    if not d.exists() or not d.is_dir():
        print(f'Error: directory not found — {d}', file=sys.stderr)
        sys.exit(1)

    files = list(d.glob('*.json'))
    if not files:
        print(f'Warning: no .json files found in {d}')

    Handler.analyses_dir = d

    server = HTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{args.port}'
    print(f'\n  JSON Explorer v2')
    print(f'  Directory : {d}')
    print(f'  Reports   : {len(files)} JSON files')
    print(f'  URL       : {url}')
    print(f'\n  Press Ctrl+C to stop.\n')

    if not args.no_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
