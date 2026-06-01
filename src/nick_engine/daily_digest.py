import argparse
import html
import os
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence, Type
from zoneinfo import ZoneInfo

from .analyzer import analyze_thesis
from .models import CandidateCompany, Evidence, RankedCandidate, ThesisReport
from .providers import ResearchProvider


TORONTO = ZoneInfo("America/Toronto")


@dataclass(frozen=True)
class ThesisTrack:
    title: str
    thesis: str
    max_market_cap_b: float = None


@dataclass(frozen=True)
class DailyDigest:
    subject: str
    html: str
    text: str


@dataclass(frozen=True)
class RunResult:
    status: str
    message: str


THESIS_TRACKS = (
    ThesisTrack("Optical Networking Bottleneck", "AI data center optical networking bottleneck"),
    ThesisTrack("Memory / HBM Bottleneck", "AI memory bandwidth HBM bottleneck"),
    ThesisTrack(
        "Construction Equipment Demand",
        "construction equipment demand will skyrocket",
        max_market_cap_b=15,
    ),
)

DIGEST_RECIPIENTS = ("marko@advertra.ca", "ikeepitstream@gmail.com")
MIN_NICK_SCORE = 80
MIN_EXPLOSIVE_SETUP_SCORE = 60
MIN_NEAR_TERM_REASONS = 2
MAX_CANDIDATES_PER_THESIS = 3

ALREADY_RESEARCHED_TICKERS = frozenset(
    {
        "AAOI",
        "ACMR",
        "ADI",
        "AEHR",
        "ALMU",
        "AMAT",
        "AMD",
        "AMKR",
        "ARM",
        "ASX",
        "ASTS",
        "AXTI",
        "BB",
        "BE",
        "CASY",
        "CAT",
        "CBRS",
        "CCJ",
        "CIFR",
        "CIEN",
        "COHR",
        "COPX",
        "CPRX",
        "CRCL",
        "CRDO",
        "CRWD",
        "DELL",
        "DLLL",
        "DRAM",
        "FIX",
        "FN",
        "FWT",
        "GFS",
        "GLW",
        "GOOG",
        "GOOGL",
        "HLIT",
        "HIMX",
        "IE",
        "INTC",
        "IREN",
        "JBL",
        "LITE",
        "LNOK",
        "LWLG",
        "MRVL",
        "MU",
        "MULL",
        "NBIS",
        "NOK",
        "NOW",
        "NOWL",
        "NTES",
        "NVTS",
        "ON",
        "ONDS",
        "ONTO",
        "ORCL",
        "OSS",
        "OTGLY",
        "PANW",
        "PDFS",
        "PENG",
        "PL",
        "PLAB",
        "PLTU",
        "POWI",
        "POWL",
        "PUBR",
        "Q",
        "QCOM",
        "RIO",
        "RKLB",
        "RMBS",
        "SEI",
        "SIMO",
        "SITM",
        "SKYT",
        "SMH",
        "SNDK",
        "SNDU",
        "SPHR",
        "STX",
        "SUNB",
        "TATT",
        "TE",
        "TSM",
        "TSEM",
        "TTMI",
        "TTWO",
        "TXN",
        "UEC",
        "URI",
        "URNM",
        "VECO",
        "VIAV",
        "VRT",
        "WDCC",
        "WDCX",
        "WOLF",
    }
)

HIDDEN_GEM_AS_OF = "2026-06-01"


def _evidence(title: str, url: str) -> Evidence:
    return Evidence(title=title, url=url, observed_at=HIDDEN_GEM_AS_OF)


HIDDEN_GEM_COMPANIES = (
    CandidateCompany(
        ticker="TEX",
        name="Terex",
        sector="Industrials",
        industry="Construction Machinery",
        market_cap_b=4.0,
        value_chain_layer="second-order: materials processing and lifting equipment",
        exposure="direct",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery", "lifting"),
        summary=(
            "Smaller equipment manufacturer with exposure to aerial work platforms, "
            "materials processing, and construction fleet replacement."
        ),
        catalysts=("Fleet replacement cycle", "Infrastructure and materials-processing demand"),
        risks=("Cyclical end markets", "Dealer inventory swings"),
        invalidation_signals=("Orders decline", "Backlog converts at weaker margins"),
        evidence=(
            _evidence("Terex investor relations", "https://investors.terex.com/"),
            _evidence("Terex SEC filings", "https://www.sec.gov/edgar/browse/?CIK=97216"),
        ),
        liquidity="medium",
        risk_flags=("cyclical",),
    ),
    CandidateCompany(
        ticker="ALG",
        name="Alamo Group",
        sector="Industrials",
        industry="Industrial and Vegetation Management Equipment",
        market_cap_b=2.0,
        value_chain_layer="second-order: specialty infrastructure equipment",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "machinery"),
        summary=(
            "Specialty equipment maker tied to infrastructure maintenance, vegetation "
            "management, and municipal fleet replacement."
        ),
        catalysts=("Municipal infrastructure budgets", "Fleet replacement"),
        risks=("Niche demand", "Input-cost pressure"),
        invalidation_signals=("Municipal orders weaken", "Margins compress"),
        evidence=(
            _evidence("Alamo Group investor relations", "https://www.alamo-group.com/investor-relations/"),
            _evidence("Alamo Group SEC filings", "https://www.sec.gov/edgar/browse/?CIK=897077"),
        ),
        liquidity="medium",
        risk_flags=("niche market",),
    ),
    CandidateCompany(
        ticker="HRI",
        name="Herc Holdings",
        sector="Industrials",
        industry="Equipment Rental",
        market_cap_b=4.0,
        value_chain_layer="second-order: equipment rental",
        exposure="indirect",
        thesis_keywords=("construction", "equipment", "infrastructure", "rental"),
        summary=(
            "Equipment-rental operator that can benefit from construction activity "
            "without requiring contractors to buy machinery outright."
        ),
        catalysts=("Rental utilization", "Infrastructure project demand"),
        risks=("Financing costs", "Rental-rate pressure"),
        invalidation_signals=("Utilization declines", "Rental rates weaken"),
        evidence=(
            _evidence("Herc investor relations", "https://ir.hercrentals.com/"),
            _evidence("Herc SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1364479"),
        ),
        liquidity="medium",
        risk_flags=("leverage sensitivity",),
    ),
    CandidateCompany(
        ticker="ADTN",
        name="Adtran Holdings",
        sector="Photonics",
        industry="Optical Networking",
        market_cap_b=0.6,
        value_chain_layer="L8 connectivity: optical access and transport",
        exposure="direct",
        thesis_keywords=("ai", "data", "center", "optical", "networking", "photonics", "bottleneck"),
        summary=(
            "Smaller optical-networking vendor with access, transport, and fiber "
            "infrastructure exposure when bandwidth spending broadens beyond the obvious leaders."
        ),
        catalysts=("Fiber and optical transport upgrades", "Network capacity spending"),
        risks=("Carrier capex variability", "Small-cap execution risk"),
        invalidation_signals=("Carrier orders weaken", "Gross margins deteriorate"),
        evidence=(
            _evidence("Adtran investor relations", "https://investors.adtran.com/"),
            _evidence("Adtran SEC filings", "https://www.sec.gov/edgar/browse/?CIK=926282"),
        ),
        liquidity="medium",
        risk_flags=("small cap", "carrier capex sensitivity"),
    ),
    CandidateCompany(
        ticker="EXTR",
        name="Extreme Networks",
        sector="Photonics",
        industry="Cloud and Enterprise Networking",
        market_cap_b=2.5,
        value_chain_layer="L8 connectivity: cloud and enterprise networking",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "connectivity", "networking", "bottleneck"),
        summary=(
            "Networking vendor that can screen as a second-order beneficiary if "
            "AI-driven bandwidth spending broadens into campus, cloud, and enterprise networks."
        ),
        catalysts=("Network upgrade cycle", "Cloud and enterprise refresh demand"),
        risks=("Competitive switching pressure", "Indirect AI exposure"),
        invalidation_signals=("Bookings weaken", "Channel inventory rises"),
        evidence=(
            _evidence("Extreme Networks investor relations", "https://investor.extremenetworks.com/"),
            _evidence("Extreme Networks SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1078271"),
        ),
        liquidity="medium",
        risk_flags=("indirect exposure",),
    ),
    CandidateCompany(
        ticker="LASR",
        name="nLIGHT",
        sector="Photonics",
        industry="Laser Components",
        market_cap_b=0.5,
        value_chain_layer="L8 adjacency: photonics components",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "optical", "photonics", "bottleneck"),
        summary=(
            "Small photonics component company for monitoring when capital rotates "
            "from the obvious optical names into lower-liquidity photonics adjacencies."
        ),
        catalysts=("Photonics sector breadth", "Industrial and defense laser demand"),
        risks=("Indirect data-center exposure", "Low market capitalization"),
        invalidation_signals=("Photonics breadth weakens", "Revenue growth stalls"),
        evidence=(
            _evidence("nLIGHT investor relations", "https://investors.nlight.net/"),
            _evidence("nLIGHT SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1124796"),
        ),
        liquidity="low",
        risk_flags=("small cap", "indirect exposure"),
    ),
    CandidateCompany(
        ticker="FORM",
        name="FormFactor",
        sector="Semiconductors",
        industry="Semiconductor Test and Probe",
        market_cap_b=3.5,
        value_chain_layer="L5 packaging and testing: probe cards",
        exposure="indirect",
        thesis_keywords=("ai", "memory", "bandwidth", "hbm", "semiconductor", "testing", "bottleneck"),
        summary=(
            "Probe-card and test-interface supplier that can benefit when HBM and "
            "advanced packaging bottlenecks push spend into memory test infrastructure."
        ),
        catalysts=("HBM test intensity", "Advanced packaging complexity"),
        risks=("Semicap cyclicality", "Customer concentration"),
        invalidation_signals=("Memory capex weakens", "Probe-card demand slows"),
        evidence=(
            _evidence("FormFactor investor relations", "https://investors.formfactor.com/"),
            _evidence("FormFactor SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1039399"),
        ),
        liquidity="medium",
        risk_flags=("customer concentration",),
    ),
    CandidateCompany(
        ticker="CAMT",
        name="Camtek",
        sector="Semiconductors",
        industry="Semiconductor Inspection and Metrology",
        market_cap_b=4.0,
        value_chain_layer="L5 packaging and testing: inspection and metrology",
        exposure="indirect",
        thesis_keywords=("ai", "memory", "bandwidth", "hbm", "semiconductor", "packaging", "bottleneck"),
        summary=(
            "Inspection and metrology supplier tied to advanced packaging, where "
            "HBM and AI accelerators increase process complexity."
        ),
        catalysts=("Advanced packaging demand", "HBM manufacturing complexity"),
        risks=("Semicap multiple compression", "Order cyclicality"),
        invalidation_signals=("Advanced packaging orders slow", "Backlog declines"),
        evidence=(
            _evidence("Camtek investor relations", "https://www.camtek.com/investors/"),
            _evidence("Camtek SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1109138"),
        ),
        liquidity="medium",
        risk_flags=("semicap cyclicality",),
    ),
    CandidateCompany(
        ticker="MRAM",
        name="Everspin Technologies",
        sector="Semiconductors",
        industry="Specialty Memory",
        market_cap_b=0.1,
        value_chain_layer="L6 memory: specialty memory",
        exposure="indirect",
        thesis_keywords=("ai", "memory", "bandwidth", "semiconductor", "bottleneck"),
        summary=(
            "Micro-cap specialty memory name to monitor only as a high-risk memory "
            "breadth play, not as a direct HBM leader."
        ),
        catalysts=("Memory sector breadth", "Specialty memory design wins"),
        risks=("Micro-cap liquidity", "Indirect HBM exposure"),
        invalidation_signals=("Design wins fail to convert", "Cash burn rises"),
        evidence=(
            _evidence("Everspin investor relations", "https://investor.everspin.com/"),
            _evidence("Everspin SEC filings", "https://www.sec.gov/edgar/browse/?CIK=1438423"),
        ),
        liquidity="low",
        risk_flags=("micro cap", "indirect exposure"),
    ),
)


def is_toronto_send_hour(now: datetime) -> bool:
    return now.astimezone(TORONTO).hour == 9


def _fresh_companies(provider: ResearchProvider) -> tuple:
    fresh = {}
    for company in tuple(provider.companies()) + HIDDEN_GEM_COMPANIES:
        ticker = company.ticker.upper()
        if ticker not in ALREADY_RESEARCHED_TICKERS:
            fresh.setdefault(ticker, company)
    return tuple(fresh.values())


def _default_research_provider(environment: Mapping[str, str] = None) -> ResearchProvider:
    from .fixtures import COMPANIES, ROTATION_SIGNALS
    from .live_provider import LiveResearchProvider
    from .providers import FixtureResearchProvider

    values = environment if environment is not None else os.environ
    if values.get("NICK_RESEARCH_PROVIDER", "").lower() == "fixture":
        return FixtureResearchProvider()
    live_candidates = tuple(
        company
        for company in tuple(COMPANIES) + HIDDEN_GEM_COMPANIES
        if company.ticker.upper() not in ALREADY_RESEARCHED_TICKERS
    )
    return LiveResearchProvider(
        base_companies=live_candidates,
        base_rotation_signals=ROTATION_SIGNALS,
    )


def _reports(provider: ResearchProvider) -> Sequence[tuple]:
    companies = _fresh_companies(provider)
    reports = []
    for track in THESIS_TRACKS:
        report = analyze_thesis(
            track.thesis,
            companies,
            provider.rotation_signals(),
            max_market_cap_b=track.max_market_cap_b,
        )
        high_conviction = tuple(
            candidate
            for candidate in report.candidates
            if candidate.score >= MIN_NICK_SCORE
            and candidate.setup_score >= MIN_EXPLOSIVE_SETUP_SCORE
            and len(candidate.setup_reasons) >= MIN_NEAR_TERM_REASONS
        )[:MAX_CANDIDATES_PER_THESIS]
        reports.append((track, replace(report, candidates=high_conviction)))
    return tuple(reports)


def _score_breakdown_text(candidate: RankedCandidate) -> str:
    return ", ".join(
        f"{key.replace('_', ' ')} {value:+d}"
        for key, value in candidate.score_breakdown.items()
    )


def _score_color(value: int) -> str:
    if value >= 90:
        return "#16a34a"
    if value >= 75:
        return "#d6a431"
    return "#dc2626"


def _bar(label: str, value: int, maximum: int = 100) -> str:
    width = max(0, min(100, round((value / maximum) * 100)))
    color = _score_color(value)
    return f"""
      <div style="margin:10px 0">
        <div style="display:flex;justify-content:space-between;gap:12px;font-size:12px;color:#555;margin-bottom:5px">
          <span>{html.escape(label)}</span>
          <strong style="color:#111">{value}/{maximum}</strong>
        </div>
        <div style="height:9px;background:#eee5d6;border-radius:999px;overflow:hidden">
          <div style="width:{width}%;height:9px;background:{color};border-radius:999px"></div>
        </div>
      </div>
    """


def _setup_graphic(candidate: RankedCandidate) -> str:
    company = candidate.company
    catalyst_count = min(len(company.catalysts), 4)
    signal_count = min(len(candidate.setup_reasons), 4)
    evidence_count = min(len(company.evidence), 4)
    chips = "".join(
        f"""
        <td style="width:33.33%;padding:8px;border-right:{'1px solid #eadfcb' if label != 'Evidence' else '0'}">
          <div style="font-size:20px;font-weight:700;color:#111">{count}</div>
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#7a6a52">{label}</div>
        </td>
        """
        for label, count in (
            ("Catalysts", catalyst_count),
            ("Signals", signal_count),
            ("Evidence", evidence_count),
        )
    )
    return f"""
      <section style="background:linear-gradient(135deg,#151515,#2b2418);border-radius:14px;padding:14px;margin:14px 0;color:#fff">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:center">
          <div>
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:#d6b46a">Setup Dashboard</div>
            <div style="font-size:17px;font-weight:700;margin-top:3px">{html.escape(company.ticker)} explosive-readiness</div>
          </div>
          <div style="text-align:right">
            <div style="font-size:28px;font-weight:800;color:#fff">{candidate.setup_score}</div>
            <div style="font-size:11px;color:#d6b46a">Setup Score</div>
          </div>
        </div>
        <div style="background:#fff;border-radius:12px;padding:12px;margin-top:12px;color:#111">
          {_bar("Thesis Fit", candidate.score)}
          {_bar("Near-Term Setup", candidate.setup_score)}
          <table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;margin-top:10px;background:#faf7f0;border:1px solid #eadfcb;border-radius:10px;overflow:hidden">
            <tr>{chips}</tr>
          </table>
        </div>
      </section>
    """


def _deep_dive_paragraphs(candidate: RankedCandidate) -> tuple:
    company = candidate.company
    matched_terms = ", ".join(candidate.matched_keywords)
    catalysts = "; ".join(company.catalysts)
    risks = "; ".join(company.risks)
    invalidations = "; ".join(company.invalidation_signals)
    sources = "; ".join(f"{item.title}: {item.url}" for item in company.evidence)
    setup_reasons = "; ".join(candidate.setup_reasons)

    return (
        (
            f"Thesis fit: {company.ticker} scores {candidate.score} with risk "
            f"{candidate.risk_tier}. It maps to {company.value_chain_layer}, with "
            f"{company.exposure} exposure to the thesis through matched terms "
            f"{matched_terms}. score breakdown: {_score_breakdown_text(candidate)}."
        ),
        (
            f"Why it could move soon: Setup score {candidate.setup_score}. "
            f"{setup_reasons}."
        ),
        (
            f"Why it can work: {company.summary} The practical setup is {catalysts}. "
            f"The hidden-gem angle is that this is not the obvious mega-cap expression; "
            f"it is a smaller value-chain beneficiary that can re-rate if money rotates "
            f"from the headline names into the bottleneck layer."
        ),
        (
            f"What kills it: {risks}. The invalidation checklist is {invalidations}. "
            f"Source trail for deeper review: {sources}."
        ),
    )


def _html_candidate(candidate: RankedCandidate) -> str:
    company = candidate.company
    paragraphs = "".join(
        f"<p style=\"margin:10px 0 0;line-height:1.55\">{html.escape(paragraph)}</p>"
        for paragraph in _deep_dive_paragraphs(candidate)
    )
    return f"""
      <article style="border:1px solid #e6e1d8;border-radius:14px;padding:18px 20px;margin:16px 0;background:#fff">
        <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start">
          <div>
            <p style="margin:0 0 4px;color:#8a6f3f;font-size:12px;text-transform:uppercase;letter-spacing:.08em">Hidden Gem Candidate</p>
            <h3 style="margin:0;color:#111;font-size:22px">{html.escape(company.ticker)} - {html.escape(company.name)}</h3>
          </div>
          <div style="text-align:right;white-space:nowrap">
            <div style="font-size:24px;font-weight:700;color:#111">{candidate.score}</div>
            <div style="font-size:12px;color:#666">Score</div>
          </div>
        </div>
        <p style="margin:12px 0 0;line-height:1.5">
          <strong>Setup score:</strong> {candidate.setup_score} &nbsp;|&nbsp;
          <strong>Risk:</strong> {candidate.risk_tier} &nbsp;|&nbsp;
          <strong>Exposure:</strong> {html.escape(company.exposure)}<br>
          <strong>Layer:</strong> {html.escape(company.value_chain_layer)}
        </p>
        {_setup_graphic(candidate)}
        {paragraphs}
      </article>
    """


def _text_candidate(candidate: RankedCandidate) -> str:
    company = candidate.company
    paragraphs = "\n\n".join(_deep_dive_paragraphs(candidate))
    return (
        f"{company.ticker} - {company.name} | score {candidate.score} | "
        f"setup score {candidate.setup_score} | risk {candidate.risk_tier}\n"
        f"Layer: {company.value_chain_layer} | exposure: {company.exposure}\n"
        f"{paragraphs}"
    )


def _html_section(track: ThesisTrack, report: ThesisReport) -> str:
    candidates = "".join(_html_candidate(candidate) for candidate in report.candidates)
    return f"""
      <section style="margin:28px 0">
        <h2 style="font-size:24px;margin:0 0 6px;color:#111">{html.escape(track.title)}</h2>
        <p style="margin:0 0 14px;color:#555;line-height:1.5"><strong>Thesis:</strong> {html.escape(track.thesis)}</p>
        {candidates or "<p>No configured candidates matched this thesis.</p>"}
      </section>
    """


def _text_section(track: ThesisTrack, report: ThesisReport) -> str:
    candidates = "\n\n".join(_text_candidate(candidate) for candidate in report.candidates)
    return f"{track.title}\nThesis: {track.thesis}\n\n{candidates or 'No configured candidates matched.'}"


def _excluded_note() -> str:
    return (
        "Already researched tickers excluded from candidate output: "
        + ", ".join(sorted(ALREADY_RESEARCHED_TICKERS))
    )


def _digest_recipients(environment: Mapping[str, str] = None) -> tuple:
    values = environment if environment is not None else os.environ
    configured = values.get("DIGEST_RECIPIENTS", "")
    if not configured:
        return DIGEST_RECIPIENTS
    return tuple(
        recipient.strip()
        for recipient in configured.split(",")
        if recipient.strip()
    )


def build_daily_digest(
    provider: ResearchProvider,
    now: datetime = None,
) -> DailyDigest:
    generated_at = (now or datetime.now(timezone.utc)).astimezone(TORONTO)
    reports = _reports(provider)
    date_label = generated_at.strftime("%Y-%m-%d")
    html_sections = "".join(_html_section(track, report) for track, report in reports)
    text_sections = "\n\n---\n\n".join(_text_section(track, report) for track, report in reports)
    notice = (
        "Research watchlist only. This uses public-source live enrichment where available "
        "and remains a research screen, not a buy/sell recommendation."
    )
    excluded_note = _excluded_note()
    return DailyDigest(
        subject=f"Market Research Digest | Hidden Gems | {date_label}",
        html=f"""
        <main style="font-family:Arial,sans-serif;max-width:780px;margin:auto;color:#161616;background:#faf7f0;padding:28px">
          <section style="background:#111;color:#fff;border-radius:18px;padding:24px;margin-bottom:18px">
            <p style="margin:0 0 8px;color:#d6b46a;font-size:12px;text-transform:uppercase;letter-spacing:.1em">Daily Research Brief</p>
            <h1 style="margin:0;font-size:30px;line-height:1.15">Hidden Gem Stock Research</h1>
            <p style="margin:12px 0 0;color:#ddd">{html.escape(date_label)} | Snapshot: {html.escape(provider.as_of())} | Minimum score: {MIN_NICK_SCORE} | Setup gate: {MIN_EXPLOSIVE_SETUP_SCORE}</p>
          </section>
          <section style="background:#fff;border:1px solid #e6e1d8;border-radius:14px;padding:16px 18px;margin-bottom:18px">
            <p style="margin:0;line-height:1.5"><strong>{html.escape(notice)}</strong></p>
            <p style="font-size:13px;color:#666;margin:10px 0 0;line-height:1.45">{html.escape(excluded_note)}</p>
          </section>
          {html_sections}
        </main>
        """,
        text=(
            f"Hidden Gem Stock Research\n{date_label} | Snapshot: {provider.as_of()} | "
            f"Minimum score: {MIN_NICK_SCORE} | Setup gate: {MIN_EXPLOSIVE_SETUP_SCORE}\n\n"
            f"{notice}\n\n{excluded_note}\n\n{text_sections}\n"
        ),
    )


def run_daily_digest(
    *,
    now: datetime = None,
    dry_run: bool = False,
    force: bool = False,
    environment: Mapping[str, str] = None,
    output_directory: Path = Path("output/daily-digest"),
    provider: ResearchProvider = None,
    client_class: Type = None,
) -> RunResult:
    from .resend_client import ResendClient

    current_time = now or datetime.now(timezone.utc)
    if not force and not is_toronto_send_hour(current_time):
        return RunResult("skipped", "Skipped: outside Toronto 9 AM hour.")

    research_provider = provider or _default_research_provider(environment=environment)
    digest = build_daily_digest(research_provider, current_time)
    if dry_run:
        output_directory.mkdir(parents=True, exist_ok=True)
        preview_path = output_directory / "daily-stock-research-preview.html"
        preview_path.write_text(digest.html, encoding="utf-8")
        return RunResult("dry-run", f"Dry run preview written to {preview_path}.")

    values = environment if environment is not None else os.environ
    sender_class = client_class or ResendClient
    client = sender_class(
        api_key=values.get("RESEND_API_KEY", ""),
        from_email=values.get("RESEND_FROM_EMAIL", ""),
    )
    local_date = current_time.astimezone(TORONTO).date()
    responses = [
        client.send_digest(
            digest,
            to_email=recipient,
            send_date=local_date,
        )
        for recipient in _digest_recipients(values)
    ]
    sent_ids = ", ".join(response["id"] for response in responses)
    return RunResult("sent", f"Sent daily research digest: {sent_ids}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send the daily market research digest.")
    parser.add_argument("--dry-run", action="store_true", help="Write an HTML preview without sending.")
    parser.add_argument("--force", action="store_true", help="Run outside Toronto's 9 AM hour.")
    parser.add_argument(
        "--output-dir",
        default="output/daily-digest",
        help="Directory for dry-run preview output.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = run_daily_digest(
        dry_run=arguments.dry_run,
        force=arguments.force,
        output_directory=Path(arguments.output_dir),
    )
    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
