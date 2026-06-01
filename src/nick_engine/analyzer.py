import re
from datetime import datetime, timezone
from typing import Iterable, Mapping, Optional, Sequence, Tuple

from .models import (
    CandidateCompany,
    RankedCandidate,
    RotationSignal,
    ThesisReport,
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "benefit",
    "benefiting",
    "beyond",
    "companies",
    "company",
    "find",
    "for",
    "from",
    "is",
    "of",
    "public",
    "smaller",
    "that",
    "the",
    "to",
    "will",
    "with",
}

ROTATION_SCORES = {"in": 15, "neutral": 0, "out": -10}
LIQUIDITY_SCORES = {"high": 8, "medium": 4, "low": 0}
BROAD_CONTEXT_TERMS = {"ai", "bottleneck", "center", "data", "demand"}


def _normalize_word(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
        return word[:-1]
    return word


def extract_keywords(thesis: str) -> Tuple[str, ...]:
    words = re.findall(r"[a-z0-9]+", thesis.lower())
    normalized = {_normalize_word(word) for word in words if word not in STOP_WORDS}
    return tuple(sorted(word for word in normalized if len(word) > 2 or word == "ai"))


def _risk_tier(company: CandidateCompany) -> str:
    risk_points = len(company.risk_flags)
    if company.liquidity == "low":
        risk_points += 2
    elif company.liquidity == "medium":
        risk_points += 1
    if company.market_cap_b < 1:
        risk_points += 1
    if risk_points >= 3:
        return "3/3"
    if risk_points >= 1:
        return "2/3"
    return "1/3"


def _score_candidate(
    company: CandidateCompany,
    matched_keywords: Sequence[str],
    rotation: RotationSignal,
) -> RankedCandidate:
    thesis_fit = min(45, len(matched_keywords) * 12 + (12 if company.exposure == "direct" else 4))
    evidence_quality = min(15, len(company.evidence) * 5)
    catalyst_strength = min(10, len(company.catalysts) * 4)
    sector_rotation = ROTATION_SCORES.get(rotation.direction, 0)
    liquidity = LIQUIDITY_SCORES.get(company.liquidity, 0)
    risk_penalty = -min(15, len(company.risk_flags) * 4)
    breakdown = {
        "thesis_fit": thesis_fit,
        "evidence_quality": evidence_quality,
        "catalyst_strength": catalyst_strength,
        "sector_rotation": sector_rotation,
        "liquidity": liquidity,
        "risk_penalty": risk_penalty,
    }
    return RankedCandidate(
        company=company,
        matched_keywords=tuple(sorted(matched_keywords)),
        score=sum(breakdown.values()),
        score_breakdown=breakdown,
        risk_tier=_risk_tier(company),
    )


def analyze_thesis(
    thesis: str,
    companies: Iterable[CandidateCompany],
    rotation_signals: Mapping[str, RotationSignal],
    *,
    max_market_cap_b: Optional[float] = None,
    sector_hints: Sequence[str] = (),
) -> ThesisReport:
    keywords = extract_keywords(thesis)
    search_terms = set(keywords) | {term.lower() for term in sector_hints}
    minimum_matches = 2 if len(keywords) >= 2 else 1
    neutral = RotationSignal("Unknown", "neutral", "No sector snapshot available", "unknown")
    ranked = []
    used_sectors = set()

    for company in companies:
        if max_market_cap_b is not None and company.market_cap_b > max_market_cap_b:
            continue
        company_terms = {_normalize_word(term.lower()) for term in company.thesis_keywords}
        matched = sorted(search_terms & company_terms)
        if len(matched) < minimum_matches:
            continue
        if len(keywords) >= 2 and not (set(matched) - BROAD_CONTEXT_TERMS):
            continue
        rotation = rotation_signals.get(company.sector, neutral)
        used_sectors.add(company.sector)
        ranked.append(_score_candidate(company, matched, rotation))

    ranked.sort(key=lambda candidate: (-candidate.score, candidate.company.ticker))
    relevant_rotations = tuple(
        rotation_signals[sector] for sector in sorted(used_sectors) if sector in rotation_signals
    )
    return ThesisReport(
        thesis=thesis,
        keywords=keywords,
        rotation_signals=relevant_rotations,
        candidates=tuple(ranked),
        generated_at=datetime.now(timezone.utc).isoformat(),
        methodology=(
            "Research watchlist only. Nick framework: sector rotation first, "
            "then value-chain exposure, bottlenecks, evidence, catalysts, liquidity, and risk."
        ),
    )
