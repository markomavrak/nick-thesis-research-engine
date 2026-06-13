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
FRESH_CATALYST_TERMS = {
    "8-k",
    "10-k",
    "10-q",
    "accelerat",
    "backlog",
    "book-to-bill",
    "breakout",
    "contract",
    "earnings",
    "filing",
    "fresh",
    "guidance",
    "latest",
    "news",
    "order",
    "raise",
    "recent",
    "record",
    "revenue",
    "volume",
}
TORQUE_LAYER_TERMS = {
    "advanced packaging",
    "bottleneck",
    "hbm",
    "inspection",
    "metrology",
    "probe",
    "second-order",
    "testing",
}


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


def _contains_any(value: str, terms: set[str]) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in terms)


def _setup_profile(company: CandidateCompany, rotation: RotationSignal) -> tuple[int, tuple[str, ...]]:
    score = 0
    reasons = []

    for signal in company.near_term_signals:
        if signal not in reasons:
            reasons.append(signal)
        score += 10

    if rotation.direction == "in":
        reasons.append("Sector rotation is aligned with the thesis")
        score += 15

    if company.market_cap_b <= 5:
        reasons.append("Small/mid-cap torque: easier to re-rate on fresh demand")
        score += 16
    elif company.market_cap_b <= 15:
        reasons.append("Mid-cap torque: still small enough for a sharp re-rate")
        score += 8

    if company.exposure == "direct":
        reasons.append("Direct exposure to the target bottleneck or demand layer")
        score += 10

    if len(company.catalysts) >= 2:
        reasons.append("Multiple catalysts stacked in the same setup")
        score += 16

    if len(company.evidence) >= 2:
        reasons.append("Multiple source trail supports the setup")
        score += 10

    catalyst_text = " ".join(company.catalysts)
    if _contains_any(catalyst_text, FRESH_CATALYST_TERMS):
        reasons.append("Fresh catalyst language points to near-term repricing potential")
        score += 12

    layer_text = f"{company.value_chain_layer} {' '.join(company.thesis_keywords)}"
    if _contains_any(layer_text, TORQUE_LAYER_TERMS):
        reasons.append("Positioned in a bottleneck or second-order value-chain layer")
        score += 14

    if _contains_any(" ".join(company.thesis_keywords), TORQUE_LAYER_TERMS):
        reasons.append("Catalysts map to high-demand bottleneck keywords")
        score += 8

    if company.liquidity in {"high", "medium"}:
        score += 4

    return min(score, 100), tuple(dict.fromkeys(reasons))


def _score_candidate(
    company: CandidateCompany,
    matched_keywords: Sequence[str],
    rotation: RotationSignal,
) -> RankedCandidate:
    thesis_fit = min(65, len(matched_keywords) * 20 + (25 if company.exposure == "direct" else 10))
    evidence_quality = min(20, len(company.evidence) * 10)
    catalyst_strength = min(15, len(company.catalysts) * 8)
    sector_rotation = ROTATION_SCORES.get(rotation.direction, 0)
    liquidity = LIQUIDITY_SCORES.get(company.liquidity, 0)
    risk_penalty = -min(15, len(company.risk_flags) * 4)
    setup_score, setup_reasons = _setup_profile(company, rotation)
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
        setup_score=setup_score,
        setup_reasons=setup_reasons,
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
            "Research watchlist only. Aurex framework: sector rotation first, "
            "then value-chain exposure, bottlenecks, evidence, catalysts, liquidity, and risk."
        ),
    )
