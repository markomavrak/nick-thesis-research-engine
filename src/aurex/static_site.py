import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .learning import learning_payload
from .terminal import AurexTerminal, DEFAULT_THESIS, SnapshotCache


DEFAULT_PUBLIC_DOMAIN = "aurex.archive.trading"
DEFAULT_OUTPUT_DIR = Path("public")


class OfflineSnapshotClient:
    def snapshot(self, ticker):
        return None


def public_terminal() -> AurexTerminal:
    return AurexTerminal(
        cache=SnapshotCache(client=OfflineSnapshotClient()),
        now_fn=lambda: datetime.now(timezone.utc),
    )


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def static_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aurex Public Research Terminal</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #07080b;
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
      background:
        radial-gradient(circle at top left, rgba(214,180,106,.22), transparent 34rem),
        radial-gradient(circle at top right, rgba(106,169,255,.13), transparent 36rem),
        var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header { padding: 30px clamp(18px, 4vw, 58px) 18px; border-bottom: 1px solid rgba(214,180,106,.18); }
    .eyebrow { color: var(--gold); font-size: 12px; letter-spacing: .2em; text-transform: uppercase; font-weight: 800; }
    h1 { margin: 8px 0 8px; font-size: clamp(38px, 6vw, 76px); line-height: .92; }
    .subhead { color: var(--muted); max-width: 1020px; line-height: 1.55; margin: 0; }
    main { display: grid; gap: 18px; grid-template-columns: minmax(0, 1.25fr) minmax(360px, .75fr); padding: 22px clamp(18px, 4vw, 58px) 58px; }
    @media (max-width: 1080px) { main { grid-template-columns: 1fr; } }
    .panel { background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.015)), var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 18px; box-shadow: 0 18px 80px rgba(0,0,0,.28); }
    .full { grid-column: 1 / -1; }
    .cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px; }
    @media (max-width: 840px) { .cards { grid-template-columns: repeat(2, 1fr); } }
    .card { background: var(--panel-2); border: 1px solid var(--line); border-radius: 16px; padding: 14px; }
    .card strong { font-size: 24px; display: block; }
    .card span { color: var(--muted); font-size: 12px; }
    .section-title { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin: 0 0 12px; }
    .section-title h2 { margin: 0; font-size: 18px; }
    .status, .muted { color: var(--muted); }
    .status { font-size: 12px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 11px 9px; border-bottom: 1px solid rgba(150,160,173,.14); text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }
    tr.clickable { cursor: pointer; }
    tr.clickable:hover { background: rgba(214,180,106,.07); }
    .ticker { color: var(--gold); font-weight: 900; letter-spacing: .04em; }
    .score { color: var(--green); font-weight: 900; }
    .risk { color: var(--gold); font-weight: 700; }
    .high { color: var(--red); font-weight: 900; }
    .medium { color: var(--gold); font-weight: 900; }
    .watch { color: var(--blue); font-weight: 900; }
    .pill { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; padding: 3px 8px; color: var(--muted); font-size: 12px; margin: 2px 4px 2px 0; white-space: nowrap; }
    .list { margin: 0; padding-left: 18px; color: #d8dee7; }
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    @media (max-width: 680px) { .grid-2 { grid-template-columns: 1fr; } }
    .detail h3 { margin: 0 0 6px; font-size: 28px; }
    .detail p { color: #d8dee7; line-height: 1.55; }
    .source-box { font-size: 12px; color: var(--muted); line-height: 1.45; }
    .learning-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
    .learning-card { background: var(--panel-2); border: 1px solid var(--line); border-radius: 16px; padding: 14px; }
    .learning-card h3 { margin: 0 0 8px; font-size: 16px; color: var(--gold); }
    .learning-card p { color: #d8dee7; line-height: 1.5; margin: 8px 0; }
    .learning-card a, .detail a { color: var(--gold); text-decoration: none; }
    .learning-card a:hover, .detail a:hover { text-decoration: underline; }
    .term-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin-top: 12px; }
    .term-card { border: 1px solid rgba(150,160,173,.2); border-radius: 12px; padding: 10px; background: #0d1118; }
    .term-card strong { color: var(--gold); display: block; margin-bottom: 4px; }
    details summary { cursor: pointer; color: var(--gold); font-weight: 800; margin-top: 14px; }
    .notice { border: 1px solid rgba(214,180,106,.26); background: rgba(214,180,106,.08); color: #ead8a7; border-radius: 14px; padding: 12px; line-height: 1.45; }
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Aurex</div>
    <h1>Public Research Terminal</h1>
    <p class="subhead">Thesis scoring, hidden-gem screening, AI value-chain fluency, public-source trail, and asymmetric setup tracking. This public surface is regenerated by GitHub Actions; the private local terminal remains the live operator console.</p>
  </header>
  <main>
    <section class="panel">
      <div class="section-title"><h2>Snapshot</h2><span id="generatedAt" class="status">Loading...</span></div>
      <div class="notice">Research surface only. No buy/sell calls, no position sizing, no personalized financial advice.</div>
      <div class="cards">
        <div class="card"><strong id="universeCount">-</strong><span>Universe</span></div>
        <div class="card"><strong id="candidateCount">-</strong><span>80+ scored candidates</span></div>
        <div class="card"><strong id="activityCount">-</strong><span>Activity flags</span></div>
        <div class="card"><strong id="learningCount">-</strong><span>Learning modules</span></div>
      </div>
    </section>

    <section class="panel">
      <div class="section-title"><h2>Source Status</h2><span class="status">Public Pages build</span></div>
      <div id="sourceStatus" class="source-box">Loading...</div>
    </section>

    <section class="panel full">
      <div class="section-title"><h2>High-Conviction Screen</h2><span class="status">Click a row for deep dive</span></div>
      <div style="overflow:auto">
        <table>
          <thead><tr><th>Ticker</th><th>Company</th><th>Score</th><th>Setup</th><th>Risk</th><th>Why It Matters</th></tr></thead>
          <tbody id="candidateRows"></tbody>
        </table>
      </div>
    </section>

    <aside class="panel detail" id="detail">
      <div class="section-title"><h2>Deep Dive</h2><span class="status">Select a ticker</span></div>
      <p class="muted">Aurex will show thesis fit, setup score, catalysts, risks, invalidation checks, and evidence links from the generated public snapshot.</p>
    </aside>

    <section class="panel">
      <div class="section-title"><h2>Unusual Activity Tape</h2><span class="status">Public snapshot</span></div>
      <div style="overflow:auto">
        <table>
          <thead><tr><th>Ticker</th><th>Severity</th><th>Score</th><th>Move</th><th>Volume</th><th>Flags</th></tr></thead>
          <tbody id="activityRows"></tbody>
        </table>
      </div>
    </section>

    <section class="panel full">
      <div class="section-title"><h2>Learning Center</h2><span class="status">AI value chain, bottlenecks, definitions, videos</span></div>
      <p id="learningSummary" class="muted">Loading AI value-chain reference library...</p>
      <div id="learningGrid" class="learning-grid"></div>
      <details>
        <summary>Open Glossary</summary>
        <div id="glossaryGrid" class="term-grid"></div>
      </details>
    </section>
  </main>
  <script>
    const $ = id => document.getElementById(id);
    let currentDashboard = null;

    function fmtNum(value, digits = 0) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
      return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
    }
    function pct(value) {
      if (value === null || value === undefined) return "-";
      const n = Number(value);
      return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
    }
    function escapeHtml(value) {
      return String(value ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
    }
    function pill(text) { return `<span class="pill">${escapeHtml(text)}</span>`; }
    async function fetchJson(path) {
      const response = await fetch(path);
      if (!response.ok) throw new Error(`${path} returned ${response.status}`);
      return response.json();
    }

    function renderDashboard(payload) {
      currentDashboard = payload;
      $("universeCount").textContent = fmtNum(payload.summary.universe_count);
      $("candidateCount").textContent = fmtNum(payload.summary.candidate_count);
      $("activityCount").textContent = fmtNum(payload.summary.activity_count);
      $("generatedAt").textContent = new Date(payload.generated_at).toLocaleString();
      $("sourceStatus").innerHTML = Object.entries(payload.source_status)
        .map(([k, v]) => `<div><strong>${escapeHtml(k.replaceAll("_", " "))}:</strong> ${escapeHtml(v)}</div>`)
        .join("");
      $("candidateRows").innerHTML = payload.candidates.length ? payload.candidates.map(item => `
        <tr class="clickable" onclick="showCandidate('${escapeHtml(item.ticker)}')">
          <td class="ticker">${escapeHtml(item.ticker)}</td>
          <td>${escapeHtml(item.name)}<br><span class="muted">${escapeHtml(item.sector)} / ${escapeHtml(item.industry)}</span></td>
          <td class="score">${item.score}</td>
          <td>${item.setup_score}</td>
          <td class="risk">${escapeHtml(item.risk_tier)}</td>
          <td>${escapeHtml(item.value_chain_layer)}<br>${item.setup_reasons.slice(0, 3).map(pill).join("")}</td>
        </tr>`).join("") : `<tr><td colspan="6" class="muted">No candidates matched the current gate.</td></tr>`;
      $("activityRows").innerHTML = payload.activity.length ? payload.activity.map(item => `
        <tr class="clickable" onclick="showCandidate('${escapeHtml(item.ticker)}')">
          <td class="ticker">${escapeHtml(item.ticker)}</td>
          <td class="${escapeHtml(item.severity)}">${escapeHtml(item.severity.toUpperCase())}</td>
          <td>${item.score}</td>
          <td>${pct(item.one_day_move_pct)}</td>
          <td>${item.volume_ratio ? item.volume_ratio.toFixed(1) + "x" : "-"}</td>
          <td>${item.flags.map(pill).join("")}</td>
        </tr>`).join("") : `<tr><td colspan="6" class="muted">No unusual activity flags from current public snapshot.</td></tr>`;
    }

    function renderLearning(learning) {
      $("learningCount").textContent = learning.module_count;
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

    function showCandidate(ticker) {
      const item = (currentDashboard?.candidates || []).find(candidate => candidate.ticker === ticker);
      if (!item) {
        $("detail").innerHTML = `<div class="section-title"><h2>Deep Dive</h2><span class="ticker">${escapeHtml(ticker)}</span></div><p class="muted">This ticker is present in the activity tape but not in the current candidate list.</p>`;
        return;
      }
      $("detail").innerHTML = `
        <div class="section-title"><h2>Deep Dive</h2><span class="ticker">${escapeHtml(item.ticker)}</span></div>
        <h3>${escapeHtml(item.ticker)} - ${escapeHtml(item.name)}</h3>
        <p>${escapeHtml(item.summary)}</p>
        <div class="cards" style="grid-template-columns: repeat(3, 1fr)">
          <div class="card"><strong>${item.score}</strong><span>Aurex score</span></div>
          <div class="card"><strong>${item.setup_score}</strong><span>Setup score</span></div>
          <div class="card"><strong>${escapeHtml(item.risk_tier)}</strong><span>Risk tier</span></div>
        </div>
        <p><strong>Layer:</strong> ${escapeHtml(item.value_chain_layer)}<br>
        <strong>Exposure:</strong> ${escapeHtml(item.exposure)} | <strong>Market cap:</strong> $${fmtNum(item.market_cap_b, 2)}B</p>
        <div class="grid-2">
          <div><h4>Catalysts</h4><ul class="list">${item.catalysts.map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>
          <div><h4>Risks / invalidation</h4><ul class="list">${item.risks.concat(item.invalidation_signals).map(x => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>
        </div>
        <h4>Evidence</h4>
        <ul class="list">${item.evidence.map(x => `<li><a href="${escapeHtml(x.url)}" target="_blank">${escapeHtml(x.title)}</a> <span class="muted">${escapeHtml(x.observed_at)}</span></li>`).join("")}</ul>
      `;
    }

    async function boot() {
      try {
        const [dashboard, learning] = await Promise.all([
          fetch("api/dashboard.json").then(r => {
            if (!r.ok) throw new Error(`dashboard returned ${r.status}`);
            return r.json();
          }),
          fetch("api/learning.json").then(r => {
            if (!r.ok) throw new Error(`learning returned ${r.status}`);
            return r.json();
          }),
        ]);
        renderDashboard(dashboard);
        renderLearning(learning);
      } catch (error) {
        $("sourceStatus").textContent = `Could not load public AUREX payload: ${error.message}`;
      }
    }
    boot();
  </script>
</body>
</html>
"""


def write_static_site(
    output_dir: Path,
    *,
    terminal: AurexTerminal = None,
    domain: str = DEFAULT_PUBLIC_DOMAIN,
    thesis: str = DEFAULT_THESIS,
    limit: int = 20,
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    api_dir = output_dir / "api"

    terminal = terminal or public_terminal()
    dashboard = terminal.dashboard_payload(thesis=thesis, hide_researched=True, refresh=False, limit=limit)
    learning = learning_payload()

    index_path = output_dir / "index.html"
    html = static_html()
    index_path.write_text(html, encoding="utf-8")
    (output_dir / "404.html").write_text(html, encoding="utf-8")
    (output_dir / "CNAME").write_text(f"{domain}\n", encoding="utf-8")
    (output_dir / "robots.txt").write_text("User-agent: *\nDisallow:\n", encoding="utf-8")
    _write_json(api_dir / "dashboard.json", dashboard)
    _write_json(api_dir / "learning.json", learning)
    _write_json(
        output_dir / "site-manifest.json",
        {
            "app": "Aurex Public Research Terminal",
            "domain": domain,
            "generated_at": dashboard["generated_at"],
            "routes": {
                "index": "/",
                "dashboard": "/api/dashboard.json",
                "learning": "/api/learning.json",
            },
        },
    )
    return {
        "index": index_path,
        "dashboard": api_dir / "dashboard.json",
        "learning": api_dir / "learning.json",
        "cname": output_dir / "CNAME",
        "manifest": output_dir / "site-manifest.json",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the static public AUREX site for GitHub Pages.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--domain", default=DEFAULT_PUBLIC_DOMAIN)
    parser.add_argument("--thesis", default=DEFAULT_THESIS)
    parser.add_argument("--limit", type=int, default=20)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    manifest = write_static_site(
        Path(args.output_dir),
        domain=args.domain,
        thesis=args.thesis,
        limit=max(1, min(args.limit, 50)),
    )
    print(f"Generated AUREX public site at {Path(args.output_dir).resolve()}")
    for name, path in manifest.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
