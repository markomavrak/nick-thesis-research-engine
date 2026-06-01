import argparse
import html
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence, Type
from zoneinfo import ZoneInfo

from .analyzer import analyze_thesis
from .models import RankedCandidate, ThesisReport
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


def is_toronto_send_hour(now: datetime) -> bool:
    return now.astimezone(TORONTO).hour == 9


def _reports(provider: ResearchProvider) -> Sequence[tuple]:
    return tuple(
        (
            track,
            analyze_thesis(
                track.thesis,
                provider.companies(),
                provider.rotation_signals(),
                max_market_cap_b=track.max_market_cap_b,
            ),
        )
        for track in THESIS_TRACKS
    )


def _html_candidate(candidate: RankedCandidate) -> str:
    company = candidate.company
    catalysts = "".join(f"<li>{html.escape(item)}</li>" for item in company.catalysts)
    invalidations = "".join(
        f"<li>{html.escape(item)}</li>" for item in company.invalidation_signals
    )
    sources = "".join(
        f'<li><a href="{html.escape(item.url)}">{html.escape(item.title)}</a></li>'
        for item in company.evidence
    )
    return f"""
      <article style="border-top:1px solid #ddd;padding:12px 0">
        <h3 style="margin:0">{html.escape(company.ticker)} - {html.escape(company.name)}</h3>
        <p><strong>Score:</strong> {candidate.score} &nbsp; <strong>Risk:</strong> {candidate.risk_tier}<br>
        <strong>Layer:</strong> {html.escape(company.value_chain_layer)}<br>
        <strong>Exposure:</strong> {html.escape(company.exposure)}</p>
        <p>{html.escape(company.summary)}</p>
        <p><strong>Catalysts</strong></p><ul>{catalysts}</ul>
        <p><strong>Invalidation signals</strong></p><ul>{invalidations}</ul>
        <p><strong>Sources</strong></p><ul>{sources}</ul>
      </article>
    """


def _text_candidate(candidate: RankedCandidate) -> str:
    company = candidate.company
    catalysts = "; ".join(company.catalysts)
    invalidations = "; ".join(company.invalidation_signals)
    sources = ", ".join(item.url for item in company.evidence)
    return (
        f"{company.ticker} - {company.name} | score {candidate.score} | risk {candidate.risk_tier}\n"
        f"Layer: {company.value_chain_layer} | exposure: {company.exposure}\n"
        f"{company.summary}\nCatalysts: {catalysts}\nInvalidation: {invalidations}\nSources: {sources}"
    )


def _html_section(track: ThesisTrack, report: ThesisReport) -> str:
    candidates = "".join(_html_candidate(candidate) for candidate in report.candidates)
    return f"""
      <section style="margin:24px 0">
        <h2>{html.escape(track.title)}</h2>
        <p><strong>Thesis:</strong> {html.escape(track.thesis)}</p>
        {candidates or "<p>No configured candidates matched this thesis.</p>"}
      </section>
    """


def _text_section(track: ThesisTrack, report: ThesisReport) -> str:
    candidates = "\n\n".join(_text_candidate(candidate) for candidate in report.candidates)
    return f"{track.title}\nThesis: {track.thesis}\n\n{candidates or 'No configured candidates matched.'}"


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
        "Research watchlist only. This is a fixture-backed seed snapshot, not live market data "
        "and not a buy/sell recommendation."
    )
    return DailyDigest(
        subject=f"Nick Research Digest | Optical Networking Bottleneck | {date_label}",
        html=f"""
        <main style="font-family:Arial,sans-serif;max-width:760px;margin:auto;color:#161616">
          <h1>Nick Framework Daily Research</h1>
          <p>{html.escape(date_label)} | Snapshot: {html.escape(provider.as_of())}</p>
          <p><strong>{html.escape(notice)}</strong></p>
          {html_sections}
        </main>
        """,
        text=f"Nick Framework Daily Research\n{date_label} | Snapshot: {provider.as_of()}\n\n{notice}\n\n{text_sections}\n",
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
    from .providers import FixtureResearchProvider
    from .resend_client import ResendClient

    current_time = now or datetime.now(timezone.utc)
    if not force and not is_toronto_send_hour(current_time):
        return RunResult("skipped", "Skipped: outside Toronto 9 AM hour.")

    research_provider = provider or FixtureResearchProvider()
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
    response = client.send_digest(
        digest,
        to_email="marko@advertra.ca",
        send_date=local_date,
    )
    return RunResult("sent", f"Sent daily research digest: {response['id']}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send the daily Nick-framework research digest.")
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
