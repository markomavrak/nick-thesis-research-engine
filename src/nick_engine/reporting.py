import json
from pathlib import Path
from typing import Tuple

from .models import RankedCandidate, ThesisReport


def _bullets(items: Tuple[str, ...]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- None recorded"


def _candidate_markdown(index: int, candidate: RankedCandidate) -> str:
    company = candidate.company
    score_breakdown = ", ".join(
        f"{name}={value:+d}" for name, value in candidate.score_breakdown.items()
    )
    evidence = "\n".join(
        f"- [{item.title}]({item.url}) (observed {item.observed_at})" for item in company.evidence
    )
    return f"""### {index}. {company.ticker} - {company.name}

**Score:** {candidate.score}  
**Risk tier:** {candidate.risk_tier}  
**Sector / industry:** {company.sector} / {company.industry}  
**Value-chain layer:** {company.value_chain_layer}  
**Exposure:** {company.exposure}  
**Approximate seed market cap:** ${company.market_cap_b:.1f}B  
**Matched thesis keywords:** {", ".join(candidate.matched_keywords)}  
**Score breakdown:** {score_breakdown}

{company.summary}

**Catalysts**
{_bullets(company.catalysts)}

**Risks**
{_bullets(company.risks)}

**Invalidation signals**
{_bullets(company.invalidation_signals)}

**Missing information to refresh**
{_bullets(company.missing_information)}

**Evidence**
{evidence}
"""


def render_markdown(report: ThesisReport) -> str:
    rotations = "\n".join(
        f"- **{signal.sector}: {signal.direction.upper()}** as of {signal.as_of}. {signal.rationale}"
        for signal in report.rotation_signals
    )
    if not rotations:
        rotations = "- No matching sector snapshots were found."
    candidates = "\n".join(
        _candidate_markdown(index, candidate)
        for index, candidate in enumerate(report.candidates, start=1)
    )
    if not candidates:
        candidates = "No matching companies were found in the configured universe."
    return f"""# Nick Thesis Research Report

> Research watchlist only. This report surfaces candidates and evidence; it is
> not a buy/sell recommendation. Seed market caps and sector snapshots are
> illustrative until a live data provider is configured.

## Thesis

{report.thesis}

**Extracted keywords:** {", ".join(report.keywords)}

## Framework

{report.methodology}

## Sector Rotation

{rotations}

## Ranked Watchlist

{candidates}
"""


def write_reports(report: ThesisReport, output_directory: Path) -> Tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "nick-thesis-report.json"
    markdown_path = output_directory / "nick-thesis-report.md"
    json_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path
