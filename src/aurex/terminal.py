import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

from nick_engine.analyzer import analyze_thesis
from nick_engine.daily_digest import (
    ALREADY_RESEARCHED_TICKERS,
    HIDDEN_GEM_COMPANIES,
    MIN_AUREX_SCORE,
    MIN_EXPLOSIVE_SETUP_SCORE,
    MIN_NEAR_TERM_REASONS,
)
from nick_engine.fixtures import COMPANIES, ROTATION_SIGNALS
from nick_engine.live_provider import CompanyLiveSnapshot, PublicMarketDataClient
from nick_engine.models import CandidateCompany, Evidence, RankedCandidate, RotationSignal

from . import APP_NAME


DEFAULT_THESIS = "AI data center optical networking and memory bottlenecks with construction equipment demand"
DEFAULT_BLOCK_ACTIVITY_PATH = Path("data/block-activity.json")


@dataclass(frozen=True)
class SnapshotResult:
    ticker: str
    snapshot: Optional[CompanyLiveSnapshot]
    error: Optional[str]
    fetched_at: str


@dataclass(frozen=True)
class ActivitySignal:
    ticker: str
    score: int
    severity: str
    flags: tuple[str, ...]
    price: Optional[float]
    one_day_move_pct: Optional[float]
    volume_ratio: Optional[float]
    manual_block_count: int = 0
    manual_block_notional: float = 0.0
    source: str = "public daily OHLCV, SEC, Yahoo RSS, manual block tape"


@dataclass(frozen=True)
class ManualBlockActivity:
    ticker: str
    observed_at: str
    side: str
    notional: float
    volume: int
    source: str
    notes: str = ""


class SnapshotCache:
    def __init__(
        self,
        *,
        client: PublicMarketDataClient = None,
        ttl_seconds: int = 300,
        now_fn=None,
    ) -> None:
        self.client = client or PublicMarketDataClient()
        self.ttl_seconds = ttl_seconds
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._items: dict[str, SnapshotResult] = {}

    def get(self, ticker: str, *, refresh: bool = False) -> SnapshotResult:
        normalized = ticker.upper()
        now = self.now_fn()
        cached = self._items.get(normalized)
        if cached and not refresh:
            fetched_at = datetime.fromisoformat(cached.fetched_at)
            if (now - fetched_at).total_seconds() <= self.ttl_seconds:
                return cached
        try:
            snapshot = self.client.snapshot(normalized)
            result = SnapshotResult(
                ticker=normalized,
                snapshot=snapshot,
                error=None,
                fetched_at=now.isoformat(),
            )
        except Exception as error:  # noqa: BLE001 - provider failures should not kill the terminal.
            result = SnapshotResult(
                ticker=normalized,
                snapshot=None,
                error=str(error),
                fetched_at=now.isoformat(),
            )
        self._items[normalized] = result
        return result


class AurexTerminal:
    def __init__(
        self,
        *,
        companies: Sequence[CandidateCompany] = None,
        rotation_signals: dict[str, RotationSignal] = None,
        cache: SnapshotCache = None,
        block_activity_path: Path = DEFAULT_BLOCK_ACTIVITY_PATH,
        now_fn=None,
    ) -> None:
        self.companies = tuple(companies or self._default_universe())
        self.rotation_signals = rotation_signals or ROTATION_SIGNALS
        self.cache = cache or SnapshotCache()
        self.block_activity_path = Path(block_activity_path)
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _default_universe() -> tuple[CandidateCompany, ...]:
        deduped = {}
        for company in tuple(COMPANIES) + tuple(HIDDEN_GEM_COMPANIES):
            deduped.setdefault(company.ticker.upper(), company)
        return tuple(deduped.values())

    def _manual_blocks(self) -> tuple[ManualBlockActivity, ...]:
        if not self.block_activity_path.exists():
            return ()
        try:
            raw_items = json.loads(self.block_activity_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ()
        blocks = []
        for item in raw_items if isinstance(raw_items, list) else []:
            try:
                blocks.append(
                    ManualBlockActivity(
                        ticker=str(item.get("ticker", "")).upper(),
                        observed_at=str(item.get("observed_at", "")),
                        side=str(item.get("side", "unknown")),
                        notional=float(item.get("notional", 0) or 0),
                        volume=int(float(item.get("volume", 0) or 0)),
                        source=str(item.get("source", "manual")),
                        notes=str(item.get("notes", "")),
                    )
                )
            except (TypeError, ValueError):
                continue
        return tuple(block for block in blocks if block.ticker)

    def add_manual_block(self, activity: ManualBlockActivity) -> ManualBlockActivity:
        normalized = ManualBlockActivity(
            ticker=activity.ticker.strip().upper(),
            observed_at=activity.observed_at.strip() or self.now_fn().isoformat(),
            side=activity.side.strip().lower() or "unknown",
            notional=max(0.0, float(activity.notional)),
            volume=max(0, int(activity.volume)),
            source=activity.source.strip() or "manual",
            notes=activity.notes.strip(),
        )
        if not normalized.ticker:
            raise ValueError("ticker is required")
        self.block_activity_path.parent.mkdir(parents=True, exist_ok=True)
        existing = [asdict(item) for item in self._manual_blocks()]
        existing.append(asdict(normalized))
        self.block_activity_path.write_text(
            json.dumps(existing, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return normalized

    def _blocks_by_ticker(self) -> dict[str, tuple[ManualBlockActivity, ...]]:
        grouped: dict[str, list[ManualBlockActivity]] = {}
        for block in self._manual_blocks():
            grouped.setdefault(block.ticker, []).append(block)
        return {ticker: tuple(items) for ticker, items in grouped.items()}

    def _enrich_company(self, company: CandidateCompany, result: SnapshotResult) -> CandidateCompany:
        snapshot = result.snapshot
        if snapshot is None:
            return company

        evidence = list(company.evidence)
        catalysts = list(company.catalysts)
        risks = list(company.risks)
        invalidations = list(company.invalidation_signals)
        near_term_signals = list(company.near_term_signals)
        market_cap = snapshot.market_cap_b or company.market_cap_b

        if snapshot.price is not None:
            context = f"Live market context: last price ${snapshot.price:.2f}"
            if snapshot.relative_strength_pct is not None:
                context += f", one-session move {snapshot.relative_strength_pct:+.1f}%"
                if snapshot.relative_strength_pct >= 3:
                    near_term_signals.append(
                        f"Positive relative strength: one-session move {snapshot.relative_strength_pct:+.1f}%"
                    )
                if snapshot.relative_strength_pct <= -5:
                    risks.append("Negative recent relative strength")
            if snapshot.volume_ratio is not None:
                context += f", volume {snapshot.volume_ratio:.1f}x prior average"
                if snapshot.volume_ratio >= 1.5:
                    near_term_signals.append(
                        f"Volume expansion: {snapshot.volume_ratio:.1f}x prior average"
                    )
                if snapshot.volume_ratio < 0.5:
                    invalidations.append("Live volume is materially below prior average")
            summary = f"{company.summary} {context}."
        else:
            summary = company.summary

        if snapshot.filings:
            latest = snapshot.filings[0]
            catalysts.append(f"Latest SEC filing {latest.form}")
            near_term_signals.append(f"Fresh filing: latest {latest.form}")
            evidence.append(Evidence(f"SEC {latest.form} filing", latest.url, snapshot.observed_at))
        if snapshot.news:
            latest_news = snapshot.news[0]
            catalysts.append(f"Recent news: {latest_news.title}")
            near_term_signals.append(f"Fresh news: {latest_news.title}")
            evidence.append(
                Evidence(
                    latest_news.title,
                    latest_news.url,
                    latest_news.published_at or snapshot.observed_at,
                )
            )

        return CandidateCompany(
            ticker=company.ticker,
            name=company.name,
            sector=company.sector,
            industry=company.industry,
            market_cap_b=market_cap,
            value_chain_layer=company.value_chain_layer,
            exposure=company.exposure,
            thesis_keywords=company.thesis_keywords,
            summary=summary,
            catalysts=tuple(dict.fromkeys(catalysts)),
            risks=tuple(dict.fromkeys(risks)),
            invalidation_signals=tuple(dict.fromkeys(invalidations)),
            evidence=tuple(dict.fromkeys(evidence)),
            liquidity=company.liquidity,
            risk_flags=company.risk_flags,
            near_term_signals=tuple(dict.fromkeys(near_term_signals)),
            missing_information=(
                "Read the latest filing and transcript before acting",
                "Confirm live intraday tape with a paid market data feed",
                "Validate block activity from broker or exchange data",
            ),
        )

    def enriched_universe(
        self,
        *,
        refresh: bool = False,
        hide_researched: bool = False,
        max_symbols: int = 80,
    ) -> tuple[CandidateCompany, ...]:
        companies = []
        for company in self.companies[:max_symbols]:
            ticker = company.ticker.upper()
            if hide_researched and ticker in ALREADY_RESEARCHED_TICKERS:
                continue
            companies.append(self._enrich_company(company, self.cache.get(ticker, refresh=refresh)))
        return tuple(companies)

    def ranked_candidates(
        self,
        *,
        thesis: str = DEFAULT_THESIS,
        min_score: int = MIN_AUREX_SCORE,
        min_setup_score: int = MIN_EXPLOSIVE_SETUP_SCORE,
        max_market_cap_b: float = 15,
        hide_researched: bool = True,
        refresh: bool = False,
        limit: int = 25,
    ) -> tuple[RankedCandidate, ...]:
        report = analyze_thesis(
            thesis,
            self.enriched_universe(refresh=refresh, hide_researched=hide_researched),
            self.rotation_signals,
            max_market_cap_b=max_market_cap_b,
        )
        candidates = [
            candidate
            for candidate in report.candidates
            if candidate.score >= min_score
            and candidate.setup_score >= min_setup_score
            and len(candidate.setup_reasons) >= MIN_NEAR_TERM_REASONS
        ]
        return tuple(candidates[:limit])

    def activity_signals(
        self,
        *,
        refresh: bool = False,
        hide_researched: bool = False,
        limit: int = 30,
    ) -> tuple[ActivitySignal, ...]:
        blocks_by_ticker = self._blocks_by_ticker()
        signals = []
        for company in self.companies:
            ticker = company.ticker.upper()
            if hide_researched and ticker in ALREADY_RESEARCHED_TICKERS:
                continue
            result = self.cache.get(ticker, refresh=refresh)
            snapshot = result.snapshot
            blocks = blocks_by_ticker.get(ticker, ())
            flags = []
            score = 0
            price = move = volume_ratio = None
            if snapshot:
                price = snapshot.price
                move = snapshot.relative_strength_pct
                volume_ratio = snapshot.volume_ratio
                if volume_ratio is not None and volume_ratio >= 2:
                    flags.append(f"Unusual volume: {volume_ratio:.1f}x average")
                    score += 35
                elif volume_ratio is not None and volume_ratio >= 1.5:
                    flags.append(f"Volume expansion: {volume_ratio:.1f}x average")
                    score += 20
                if move is not None and abs(move) >= 5:
                    flags.append(f"Price impulse: {move:+.1f}%")
                    score += 25
                elif move is not None and abs(move) >= 3:
                    flags.append(f"Relative strength shift: {move:+.1f}%")
                    score += 12
                if snapshot.filings:
                    flags.append(f"Fresh SEC filing: {snapshot.filings[0].form}")
                    score += 12
                if snapshot.news:
                    flags.append(f"Fresh news: {snapshot.news[0].title}")
                    score += 10
            if result.error:
                flags.append("Live public-source refresh failed")
            block_notional = sum(block.notional for block in blocks)
            if blocks:
                flags.append(f"Manual block tape: {len(blocks)} item(s), ${block_notional:,.0f} notional")
                score += min(30, 10 + len(blocks) * 5)
            if not flags:
                continue
            severity = "high" if score >= 55 else "medium" if score >= 30 else "watch"
            signals.append(
                ActivitySignal(
                    ticker=ticker,
                    score=score,
                    severity=severity,
                    flags=tuple(flags),
                    price=price,
                    one_day_move_pct=move,
                    volume_ratio=volume_ratio,
                    manual_block_count=len(blocks),
                    manual_block_notional=block_notional,
                )
            )
        signals.sort(key=lambda item: (-item.score, item.ticker))
        return tuple(signals[:limit])

    def ticker_payload(self, ticker: str, *, refresh: bool = False) -> dict:
        normalized = ticker.upper()
        company = next((item for item in self.companies if item.ticker.upper() == normalized), None)
        if not company:
            raise KeyError(f"Unknown ticker: {normalized}")
        result = self.cache.get(normalized, refresh=refresh)
        enriched = self._enrich_company(company, result)
        ranked = analyze_thesis(
            " ".join(enriched.thesis_keywords),
            (enriched,),
            self.rotation_signals,
        ).candidates
        snapshot = result.snapshot
        return {
            "ticker": normalized,
            "company": asdict(enriched),
            "ranked": asdict(ranked[0]) if ranked else None,
            "snapshot": asdict(snapshot) if snapshot else None,
            "snapshot_error": result.error,
            "manual_blocks": [asdict(block) for block in self._blocks_by_ticker().get(normalized, ())],
            "generated_at": self.now_fn().isoformat(),
        }

    def dashboard_payload(
        self,
        *,
        thesis: str = DEFAULT_THESIS,
        hide_researched: bool = True,
        refresh: bool = False,
        limit: int = 20,
    ) -> dict:
        candidates = self.ranked_candidates(
            thesis=thesis,
            hide_researched=hide_researched,
            refresh=refresh,
            limit=limit,
        )
        activity = self.activity_signals(
            refresh=False,
            hide_researched=hide_researched,
            limit=limit,
        )
        return {
            "app": APP_NAME,
            "generated_at": self.now_fn().isoformat(),
            "thesis": thesis,
            "hide_researched": hide_researched,
            "source_status": {
                "live_price_volume": "Stooq daily OHLCV",
                "filings": "SEC company submissions and companyfacts",
                "news": "Yahoo Finance RSS",
                "block_activity": "manual tape import until a paid block-trade feed is connected",
                "intraday_limit": "No free intraday block feed is connected; unusual activity is daily-volume based.",
            },
            "metric_definitions": {
                "aurex_score": "Thesis fit + evidence + catalysts + rotation + liquidity - risk flags.",
                "setup_score": "Near-term signal stack: relative strength, volume, filings, news, catalysts, torque layer.",
                "activity_score": "Public volume/price impulse + fresh filings/news + manual block tape.",
                "hidden_gem_gate": "Default dashboard ranking excludes companies above $15B market cap.",
            },
            "summary": {
                "universe_count": len(self.companies),
                "candidate_count": len(candidates),
                "activity_count": len(activity),
                "researched_exclusion_count": len(ALREADY_RESEARCHED_TICKERS) if hide_researched else 0,
            },
            "candidates": [self._candidate_payload(candidate) for candidate in candidates],
            "activity": [asdict(item) for item in activity],
        }

    @staticmethod
    def _candidate_payload(candidate: RankedCandidate) -> dict:
        company = candidate.company
        return {
            "ticker": company.ticker,
            "name": company.name,
            "sector": company.sector,
            "industry": company.industry,
            "market_cap_b": company.market_cap_b,
            "value_chain_layer": company.value_chain_layer,
            "exposure": company.exposure,
            "score": candidate.score,
            "setup_score": candidate.setup_score,
            "risk_tier": candidate.risk_tier,
            "matched_keywords": candidate.matched_keywords,
            "setup_reasons": candidate.setup_reasons,
            "summary": company.summary,
            "catalysts": company.catalysts,
            "risks": company.risks,
            "invalidation_signals": company.invalidation_signals,
            "evidence": [asdict(item) for item in company.evidence],
        }
