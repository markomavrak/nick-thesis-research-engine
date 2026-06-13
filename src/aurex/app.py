import argparse
import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import APP_NAME
from .learning import learning_payload
from .terminal import AurexTerminal, DEFAULT_BLOCK_ACTIVITY_PATH, DEFAULT_THESIS, ManualBlockActivity


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aurex Research Terminal</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #090a0d;
      --panel: #11151c;
      --panel-2: #171d27;
      --line: #2a3444;
      --text: #eef2f7;
      --muted: #96a0ad;
      --gold: #d6b46a;
      --green: #29c178;
      --red: #ff5c6c;
      --blue: #6aa9ff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      overflow-x: hidden;
      background:
        radial-gradient(circle at top left, rgba(214,180,106,.18), transparent 32rem),
        radial-gradient(circle at top right, rgba(106,169,255,.12), transparent 34rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      padding: 28px clamp(18px, 4vw, 54px) 18px;
      border-bottom: 1px solid rgba(214,180,106,.18);
    }
    .eyebrow {
      color: var(--gold);
      font-size: 12px;
      letter-spacing: .18em;
      text-transform: uppercase;
      font-weight: 700;
    }
    h1 { margin: 8px 0 6px; font-size: clamp(34px, 5vw, 68px); line-height: .95; }
    .subhead { color: var(--muted); max-width: 960px; line-height: 1.55; margin: 0; }
    main {
      display: grid;
      gap: 18px;
      grid-template-columns: minmax(0, 1.25fr) minmax(360px, .75fr);
      padding: 22px clamp(18px, 4vw, 54px) 54px;
    }
    @media (max-width: 1080px) { main { grid-template-columns: 1fr; } }
    .panel {
      background: linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.015)), var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 18px 80px rgba(0,0,0,.28);
      min-width: 0;
    }
    .controls {
      display: grid;
      gap: 12px;
      grid-template-columns: minmax(0, 1fr) 120px 140px auto;
      align-items: end;
    }
    @media (max-width: 840px) { .controls { grid-template-columns: 1fr; } }
    label { display: block; color: var(--muted); font-size: 12px; margin-bottom: 6px; }
    input, select, button, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #0d1118;
      color: var(--text);
      padding: 11px 12px;
      font: inherit;
      min-height: 44px;
    }
    textarea { min-height: 82px; resize: vertical; }
    button {
      cursor: pointer;
      background: linear-gradient(135deg, #d6b46a, #8f6a2b);
      color: #0b0c0e;
      border-color: rgba(214,180,106,.55);
      font-weight: 800;
    }
    button.secondary {
      background: #121821;
      color: var(--text);
      border-color: var(--line);
    }
    .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }
    .metric-cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    @media (max-width: 840px) { .cards { grid-template-columns: repeat(2, 1fr); } }
    .card { background: var(--panel-2); border: 1px solid var(--line); border-radius: 16px; padding: 14px; }
    .card strong { font-size: 24px; display: block; }
    .card span { color: var(--muted); font-size: 12px; }
    .section-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 0 0 12px; }
    .section-title h2 { margin: 0; font-size: 18px; }
    .status { color: var(--muted); font-size: 12px; }
    .table-scroll { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 11px 9px; border-bottom: 1px solid rgba(150,160,173,.14); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    tr.clickable { cursor: pointer; }
    tr.clickable:hover { background: rgba(214,180,106,.07); }
    .ticker { color: var(--gold); font-weight: 900; letter-spacing: .04em; }
    .pill {
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 3px 8px;
      color: var(--muted);
      font-size: 12px;
      margin: 2px 4px 2px 0;
      white-space: nowrap;
    }
    .score { color: var(--green); font-weight: 900; }
    .risk { color: var(--gold); font-weight: 700; }
    .high { color: var(--red); font-weight: 900; }
    .medium { color: var(--gold); font-weight: 900; }
    .watch { color: var(--blue); font-weight: 900; }
    .muted { color: var(--muted); }
    .detail h3 { margin: 0 0 6px; font-size: 28px; }
    .detail p { color: #d8dee7; line-height: 1.55; }
    .list { margin: 0; padding-left: 18px; color: #d8dee7; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 680px) { .grid-2 { grid-template-columns: 1fr; } }
    .source-box { font-size: 12px; color: var(--muted); line-height: 1.45; }
    .error { color: var(--red); }
    .learning-panel { grid-column: 1 / -1; }
    .learning-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }
    .learning-card {
      background: var(--panel-2);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
    }
    .learning-card h3 { margin: 0 0 8px; font-size: 16px; color: var(--gold); }
    .learning-card p { color: #d8dee7; line-height: 1.5; margin: 8px 0; }
    .learning-card a { color: var(--gold); text-decoration: none; }
    .learning-card a:hover { text-decoration: underline; }
    .term-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .term-card {
      border: 1px solid rgba(150,160,173,.2);
      border-radius: 12px;
      padding: 10px;
      background: #0d1118;
    }
    .term-card strong { color: var(--gold); display: block; margin-bottom: 4px; }
    details summary { cursor: pointer; color: var(--gold); font-weight: 800; margin-top: 14px; }
    @media (max-width: 640px) {
      header { padding: 22px 14px 14px; }
      h1 { font-size: clamp(38px, 15vw, 58px); }
      .subhead { font-size: 14px; }
      main { gap: 12px; padding: 14px 12px 36px; }
      .panel { border-radius: 16px; padding: 14px; }
      .cards, .metric-cards, .learning-grid, .term-grid { grid-template-columns: 1fr; }
      .section-title { align-items: flex-start; flex-direction: column; gap: 4px; }
      .pill { white-space: normal; overflow-wrap: anywhere; }
      .table-scroll { overflow: visible; }
      table, thead, tbody, tr, th, td { display: block; width: 100%; }
      thead { display: none; }
      tr {
        background: #0d1118;
        border: 1px solid rgba(150,160,173,.18);
        border-radius: 14px;
        margin-bottom: 10px;
        padding: 10px 12px;
      }
      td {
        display: grid;
        grid-template-columns: 104px minmax(0, 1fr);
        gap: 10px;
        border-bottom: 1px solid rgba(150,160,173,.12);
        padding: 8px 0;
      }
      td:last-child { border-bottom: 0; }
      td::before {
        content: attr(data-label);
        color: var(--muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
      }
      td.ticker { font-size: 18px; }
      td.ticker::before { color: var(--muted); }
      .detail h3 { font-size: 24px; line-height: 1.1; }
    }
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Aurex</div>
    <h1>Research Terminal</h1>
    <p class="subhead">Live public-source stock research, thesis scoring, setup detection, fresh filings/news, unusual daily volume, and manual block-tape tracking. It surfaces research targets; it does not issue buy/sell calls.</p>
  </header>
  <main>
    <section class="panel">
      <div class="controls">
        <div>
          <label for="thesis">Research thesis</label>
          <input id="thesis" value="AI data center optical networking and memory bottlenecks with construction equipment demand">
        </div>
        <div>
          <label for="limit">Rows</label>
          <select id="limit"><option>10</option><option selected>20</option><option>30</option></select>
        </div>
        <div>
          <label for="hideResearched">Universe</label>
          <select id="hideResearched"><option value="1" selected>New names</option><option value="0">All names</option></select>
        </div>
        <div>
          <button id="refresh">Refresh Live</button>
        </div>
      </div>
      <div class="cards">
        <div class="card"><strong id="universeCount">-</strong><span>Universe</span></div>
        <div class="card"><strong id="candidateCount">-</strong><span>80+ scored candidates</span></div>
        <div class="card"><strong id="activityCount">-</strong><span>Activity flags</span></div>
        <div class="card"><strong id="generatedAt">-</strong><span>Last refresh</span></div>
      </div>
    </section>

    <section class="panel">
      <div class="section-title">
        <h2>Source Status</h2>
        <span class="status">Auto-refresh every 5 min</span>
      </div>
      <div id="sourceStatus" class="source-box">Loading...</div>
    </section>

    <section class="panel learning-panel">
      <div class="section-title">
        <h2>Learning Center</h2>
        <span class="status">AI value chain, bottlenecks, definitions, videos</span>
      </div>
      <p id="learningSummary" class="muted">Loading AI value-chain reference library...</p>
      <div id="learningGrid" class="learning-grid"></div>
      <details>
        <summary>Open Glossary</summary>
        <div id="glossaryGrid" class="term-grid"></div>
      </details>
    </section>

    <section class="panel">
      <div class="section-title">
        <h2>High-Conviction Screen</h2>
        <span class="status">Click a row for deep dive</span>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Ticker</th><th>Company</th><th>Score</th><th>Setup</th><th>Risk</th><th>Why It Matters</th></tr></thead>
          <tbody id="candidateRows"></tbody>
        </table>
      </div>
    </section>

    <aside class="panel detail" id="detail">
      <div class="section-title"><h2>Deep Dive</h2><span class="status">Select a ticker</span></div>
      <p class="muted">Aurex will show live price/volume, filings, news, score breakdown, catalysts, risks, invalidation signals, and any manual block-tape entries.</p>
    </aside>

    <section class="panel">
      <div class="section-title">
        <h2>Unusual Activity Tape</h2>
        <span class="status">Daily public data + manual blocks</span>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr><th>Ticker</th><th>Severity</th><th>Score</th><th>Move</th><th>Volume</th><th>Flags</th></tr></thead>
          <tbody id="activityRows"></tbody>
        </table>
      </div>
    </section>

    <section class="panel">
      <div class="section-title">
        <h2>Manual Block Tape</h2>
        <span class="status">Until paid block feed is connected</span>
      </div>
      <div class="grid-2">
        <div>
          <label for="blockTicker">Ticker</label>
          <input id="blockTicker" placeholder="MTSI">
        </div>
        <div>
          <label for="blockSide">Side</label>
          <select id="blockSide"><option>unknown</option><option>buy</option><option>sell</option><option>sweep</option></select>
        </div>
        <div>
          <label for="blockNotional">Notional $</label>
          <input id="blockNotional" placeholder="2500000">
        </div>
        <div>
          <label for="blockVolume">Shares/contracts</label>
          <input id="blockVolume" placeholder="100000">
        </div>
      </div>
      <label for="blockNotes" style="margin-top:12px">Notes / source</label>
      <textarea id="blockNotes" placeholder="Saw block on IBKR / unusual options tape / dark-pool print..."></textarea>
      <button id="saveBlock" style="margin-top:10px">Save Block Activity</button>
      <p id="blockStatus" class="status"></p>
    </section>
  </main>
  <script>
    const $ = id => document.getElementById(id);
    let currentPayload = null;

    function fmtNum(value, digits = 0) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
    }
    function pct(value) {
      if (value === null || value === undefined) return "-";
      const n = Number(value);
      return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
    }
    function pill(text) { return `<span class="pill">${escapeHtml(text)}</span>`; }
    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
    }

    async function loadDashboard(refresh = false) {
      $("candidateRows").innerHTML = `<tr><td colspan="6" class="muted">Loading...</td></tr>`;
      const params = new URLSearchParams({
        thesis: $("thesis").value,
        hide_researched: $("hideResearched").value,
        limit: $("limit").value,
        refresh: refresh ? "1" : "0",
      });
      const response = await fetch(`/api/dashboard?${params.toString()}`);
      currentPayload = await response.json();
      renderDashboard(currentPayload);
    }

    async function loadLearning() {
      try {
        const response = await fetch("/api/learning");
        if (!response.ok) throw new Error(`Learning endpoint returned ${response.status}`);
        renderLearning(await response.json());
      } catch (error) {
        $("learningSummary").textContent = "Learning Center could not load.";
      }
    }

    function renderDashboard(payload) {
      $("universeCount").textContent = fmtNum(payload.summary.universe_count);
      $("candidateCount").textContent = fmtNum(payload.summary.candidate_count);
      $("activityCount").textContent = fmtNum(payload.summary.activity_count);
      $("generatedAt").textContent = new Date(payload.generated_at).toLocaleTimeString();
      $("sourceStatus").innerHTML = Object.entries(payload.source_status)
        .map(([k, v]) => `<div><strong>${escapeHtml(k.replaceAll("_", " "))}:</strong> ${escapeHtml(v)}</div>`)
        .join("");
      renderLearning(payload.learning_center);

      $("candidateRows").innerHTML = payload.candidates.length ? payload.candidates.map(item => `
        <tr class="clickable" onclick="loadTicker('${escapeHtml(item.ticker)}')">
          <td data-label="Ticker" class="ticker">${escapeHtml(item.ticker)}</td>
          <td data-label="Company">${escapeHtml(item.name)}<br><span class="muted">${escapeHtml(item.sector)} / ${escapeHtml(item.industry)}</span></td>
          <td data-label="Score" class="score">${item.score}</td>
          <td data-label="Setup">${item.setup_score}</td>
          <td data-label="Risk" class="risk">${escapeHtml(item.risk_tier)}</td>
          <td data-label="Why It Matters">${escapeHtml(item.value_chain_layer)}<br>${item.setup_reasons.slice(0, 2).map(pill).join("")}</td>
        </tr>`).join("") : `<tr><td colspan="6" class="muted">No candidates matched the current gate.</td></tr>`;

      $("activityRows").innerHTML = payload.activity.length ? payload.activity.map(item => `
        <tr class="clickable" onclick="loadTicker('${escapeHtml(item.ticker)}')">
          <td data-label="Ticker" class="ticker">${escapeHtml(item.ticker)}</td>
          <td data-label="Severity" class="${escapeHtml(item.severity)}">${escapeHtml(item.severity.toUpperCase())}</td>
          <td data-label="Score">${item.score}</td>
          <td data-label="Move">${pct(item.one_day_move_pct)}</td>
          <td data-label="Volume">${item.volume_ratio ? item.volume_ratio.toFixed(1) + "x" : "-"}</td>
          <td data-label="Flags">${item.flags.map(pill).join("")}</td>
        </tr>`).join("") : `<tr><td colspan="6" class="muted">No unusual activity flags from current sources.</td></tr>`;
    }

    function renderLearning(learning) {
      if (!learning) return;
      $("learningSummary").innerHTML = `
        ${escapeHtml(learning.subtitle)}<br>
        <strong>${escapeHtml(learning.research_loop)}</strong><br>
        ${learning.featured_terms.map(pill).join("")}
      `;
      $("learningGrid").innerHTML = learning.modules.map(module => `
        <article class="learning-card">
          <h3>${escapeHtml(module.title)}</h3>
          <p>${escapeHtml(module.plain_english)}</p>
          <p><strong>Why it matters:</strong> ${escapeHtml(module.why_it_matters)}</p>
          <p><strong>Stock research angle:</strong> ${escapeHtml(module.stock_research_angle)}</p>
          <div>${module.hard_terms.slice(0, 7).map(pill).join("")}</div>
          <h4>Questions to ask</h4>
          <ul class="list">${module.key_questions.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul>
          <h4>Watch / read</h4>
          <ul class="list">${module.videos.map(video => `<li><a href="${escapeHtml(video.url)}" target="_blank">${escapeHtml(video.title)}</a> <span class="muted">${escapeHtml(video.source)}</span></li>`).join("")}</ul>
        </article>
      `).join("");
      $("glossaryGrid").innerHTML = learning.glossary.map(term => `
        <div class="term-card">
          <strong>${escapeHtml(term.term)}</strong>
          <div>${escapeHtml(term.definition)}</div>
          <div class="muted">${escapeHtml(term.why_it_matters)}</div>
        </div>
      `).join("");
    }

    async function loadTicker(ticker) {
      $("detail").innerHTML = `<div class="section-title"><h2>Deep Dive</h2><span class="status">Loading ${ticker}...</span></div>`;
      const response = await fetch(`/api/ticker/${encodeURIComponent(ticker)}?refresh=0`);
      const payload = await response.json();
      const company = payload.company;
      const ranked = payload.ranked;
      const snapshot = payload.snapshot;
      $("detail").innerHTML = `
        <div class="section-title"><h2>Deep Dive</h2><span class="ticker">${escapeHtml(company.ticker)}</span></div>
        <h3>${escapeHtml(company.ticker)} - ${escapeHtml(company.name)}</h3>
        <p>${escapeHtml(company.summary)}</p>
        <div class="cards metric-cards">
          <div class="card"><strong>${ranked ? ranked.score : "-"}</strong><span>Aurex score</span></div>
          <div class="card"><strong>${ranked ? ranked.setup_score : "-"}</strong><span>Setup score</span></div>
          <div class="card"><strong>${snapshot && snapshot.price ? "$" + snapshot.price.toFixed(2) : "-"}</strong><span>Last price</span></div>
        </div>
        <p><strong>Layer:</strong> ${escapeHtml(company.value_chain_layer)}<br>
        <strong>Exposure:</strong> ${escapeHtml(company.exposure)} | <strong>Risk:</strong> ${ranked ? escapeHtml(ranked.risk_tier) : "-"}</p>
        ${payload.snapshot_error ? `<p class="error">Live snapshot error: ${escapeHtml(payload.snapshot_error)}</p>` : ""}
        <div class="grid-2">
          <div><h4>Catalysts</h4><ul class="list">${company.catalysts.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>
          <div><h4>Risks / invalidation</h4><ul class="list">${company.risks.concat(company.invalidation_signals).map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>
        </div>
        <h4>Evidence</h4>
        <ul class="list">${company.evidence.map(x => `<li><a href="${escapeHtml(x.url)}" target="_blank" style="color:var(--gold)">${escapeHtml(x.title)}</a> <span class="muted">${escapeHtml(x.observed_at)}</span></li>`).join("")}</ul>
        <h4>Manual block tape</h4>
        <ul class="list">${payload.manual_blocks.length ? payload.manual_blocks.map(x => `<li>${escapeHtml(x.observed_at)} | ${escapeHtml(x.side)} | $${fmtNum(x.notional)} | ${fmtNum(x.volume)} | ${escapeHtml(x.notes)}</li>`).join("") : "<li>No manual block entries.</li>"}</ul>
      `;
    }

    async function saveBlock() {
      const payload = {
        ticker: $("blockTicker").value,
        side: $("blockSide").value,
        notional: Number($("blockNotional").value || 0),
        volume: Number($("blockVolume").value || 0),
        source: "manual-terminal",
        notes: $("blockNotes").value,
      };
      const response = await fetch("/api/block-activity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        $("blockStatus").textContent = "Could not save block activity.";
        return;
      }
      $("blockStatus").textContent = `Saved ${payload.ticker.toUpperCase()} block activity.`;
      $("blockTicker").value = "";
      $("blockNotional").value = "";
      $("blockVolume").value = "";
      $("blockNotes").value = "";
      await loadDashboard(false);
    }

    $("refresh").addEventListener("click", () => loadDashboard(true));
    $("saveBlock").addEventListener("click", saveBlock);
    setInterval(() => loadDashboard(true), 5 * 60 * 1000);
    loadLearning();
    loadDashboard(false);
  </script>
</body>
</html>
"""


class AurexRequestHandler(BaseHTTPRequestHandler):
    terminal: AurexTerminal = None

    def log_message(self, format, *args):  # noqa: A003 - BaseHTTPRequestHandler API.
        return

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self) -> None:
        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API.
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html()
            return
        if parsed.path == "/api/dashboard":
            query = parse_qs(parsed.query)
            thesis = query.get("thesis", [DEFAULT_THESIS])[0] or DEFAULT_THESIS
            refresh = query.get("refresh", ["0"])[0] == "1"
            hide_researched = query.get("hide_researched", ["1"])[0] != "0"
            try:
                limit = int(query.get("limit", ["20"])[0])
            except ValueError:
                limit = 20
            self._send_json(
                self.terminal.dashboard_payload(
                    thesis=thesis,
                    hide_researched=hide_researched,
                    refresh=refresh,
                    limit=max(1, min(limit, 50)),
                )
            )
            return
        if parsed.path.startswith("/api/ticker/"):
            ticker = unquote(parsed.path.removeprefix("/api/ticker/")).upper()
            refresh = parse_qs(parsed.query).get("refresh", ["0"])[0] == "1"
            try:
                self._send_json(self.terminal.ticker_payload(ticker, refresh=refresh))
            except KeyError as error:
                self._send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
            return
        if parsed.path == "/api/block-activity":
            self._send_json({"items": [vars(item) for item in self.terminal._manual_blocks()]})
            return
        if parsed.path == "/api/learning":
            self._send_json(learning_payload())
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API.
        parsed = urlparse(self.path)
        if parsed.path != "/api/block-activity":
            self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            activity = self.terminal.add_manual_block(
                ManualBlockActivity(
                    ticker=str(payload.get("ticker", "")),
                    observed_at=str(payload.get("observed_at", "")),
                    side=str(payload.get("side", "unknown")),
                    notional=float(payload.get("notional", 0) or 0),
                    volume=int(float(payload.get("volume", 0) or 0)),
                    source=str(payload.get("source", "manual-terminal")),
                    notes=str(payload.get("notes", "")),
                )
            )
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self._send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"saved": vars(activity)}, HTTPStatus.CREATED)


def build_server(
    *,
    host: str,
    port: int,
    cache_seconds: int,
    block_activity_path: Path,
) -> ThreadingHTTPServer:
    AurexRequestHandler.terminal = AurexTerminal(
        block_activity_path=block_activity_path,
    )
    AurexRequestHandler.terminal.cache.ttl_seconds = cache_seconds
    return ThreadingHTTPServer((host, port), AurexRequestHandler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Run {APP_NAME}.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--cache-seconds", type=int, default=300)
    parser.add_argument("--block-activity-path", default=str(DEFAULT_BLOCK_ACTIVITY_PATH))
    parser.add_argument("--open", action="store_true", help="Open the terminal in the default browser.")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    server = build_server(
        host=args.host,
        port=args.port,
        cache_seconds=max(30, args.cache_seconds),
        block_activity_path=Path(args.block_activity_path),
    )
    url = f"http://{args.host}:{args.port}"
    print(f"{APP_NAME} running at {url}")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Aurex.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
