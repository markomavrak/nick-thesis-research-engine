from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class Evidence:
    title: str
    url: str
    observed_at: str


@dataclass(frozen=True)
class RotationSignal:
    sector: str
    direction: str
    rationale: str
    as_of: str


@dataclass(frozen=True)
class CandidateCompany:
    ticker: str
    name: str
    sector: str
    industry: str
    market_cap_b: float
    value_chain_layer: str
    exposure: str
    thesis_keywords: Tuple[str, ...]
    summary: str
    catalysts: Tuple[str, ...]
    risks: Tuple[str, ...]
    invalidation_signals: Tuple[str, ...]
    evidence: Tuple[Evidence, ...]
    liquidity: str
    risk_flags: Tuple[str, ...] = ()
    missing_information: Tuple[str, ...] = (
        "Refresh market capitalization",
        "Refresh sector rotation using price, volume, and breadth",
        "Read latest filing and earnings transcript",
    )


@dataclass(frozen=True)
class RankedCandidate:
    company: CandidateCompany
    matched_keywords: Tuple[str, ...]
    score: int
    score_breakdown: Dict[str, int]
    risk_tier: str


@dataclass(frozen=True)
class ThesisReport:
    thesis: str
    keywords: Tuple[str, ...]
    rotation_signals: Tuple[RotationSignal, ...]
    candidates: Tuple[RankedCandidate, ...]
    generated_at: str
    methodology: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
