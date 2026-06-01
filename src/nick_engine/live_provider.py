import csv
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from io import StringIO
from typing import Callable, Mapping, Optional, Sequence
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .models import CandidateCompany, Evidence, RotationSignal


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
YAHOO_NEWS_RSS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
STOOQ_DAILY_URL = "https://stooq.com/q/d/l/?s={ticker}.us&i=d"
EDGAR_DOCUMENT_URL = "https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession_no_dashes}/{document}"
USER_AGENT = "nick-thesis-research-engine/1.0 marko@advertra.ca"


@dataclass(frozen=True)
class FilingSnapshot:
    form: str
    filing_date: str
    accession_number: str
    primary_document: str
    url: str


@dataclass(frozen=True)
class NewsSnapshot:
    title: str
    url: str
    published_at: str


@dataclass(frozen=True)
class PriceSnapshot:
    price: Optional[float]
    previous_price: Optional[float]
    relative_strength_pct: Optional[float]
    latest_volume: Optional[int]
    average_volume: Optional[float]
    volume_ratio: Optional[float]


@dataclass(frozen=True)
class CompanyLiveSnapshot:
    ticker: str
    cik: Optional[str]
    market_cap_b: Optional[float]
    price: Optional[float]
    relative_strength_pct: Optional[float]
    volume_ratio: Optional[float]
    filings: tuple[FilingSnapshot, ...]
    news: tuple[NewsSnapshot, ...]
    observed_at: str


class PublicMarketDataClient:
    def __init__(
        self,
        *,
        opener: Callable = urlopen,
        timeout: int = 8,
        now: datetime = None,
    ) -> None:
        self.opener = opener
        self.timeout = timeout
        self.now = now or datetime.now(timezone.utc)
        self._ticker_cik_cache: Optional[dict[str, str]] = None

    def snapshot(self, ticker: str) -> CompanyLiveSnapshot:
        normalized_ticker = ticker.upper()
        cik = self._cik_for_ticker(normalized_ticker)
        filings = self._recent_filings(cik) if cik else ()
        price = self._price_snapshot(normalized_ticker)
        shares = self._shares_outstanding(cik) if cik else None
        market_cap_b = None
        if price.price is not None and shares:
            market_cap_b = (price.price * shares) / 1_000_000_000
        return CompanyLiveSnapshot(
            ticker=normalized_ticker,
            cik=cik,
            market_cap_b=market_cap_b,
            price=price.price,
            relative_strength_pct=price.relative_strength_pct,
            volume_ratio=price.volume_ratio,
            filings=filings,
            news=self._news(normalized_ticker),
            observed_at=self.now.date().isoformat(),
        )

    def _get_text(self, url: str, *, content_type: str = "application/json") -> str:
        request = Request(
            url,
            headers={
                "Accept": content_type,
                "User-Agent": USER_AGENT,
            },
        )
        with self.opener(request, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    def _get_json(self, url: str) -> object:
        return json.loads(self._get_text(url))

    def _cik_for_ticker(self, ticker: str) -> Optional[str]:
        if self._ticker_cik_cache is None:
            data = self._get_json(SEC_TICKERS_URL)
            self._ticker_cik_cache = {
                item["ticker"].upper(): str(item["cik_str"]).zfill(10)
                for item in data.values()
            }
        return self._ticker_cik_cache.get(ticker)

    def _recent_filings(self, cik: str, limit: int = 3) -> tuple[FilingSnapshot, ...]:
        data = self._get_json(SEC_SUBMISSIONS_URL.format(cik=cik))
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        documents = recent.get("primaryDocument", [])
        filings = []
        for form, accession, filing_date, document in zip(forms, accessions, dates, documents):
            if form not in {"10-K", "10-Q", "8-K"}:
                continue
            filings.append(
                FilingSnapshot(
                    form=form,
                    filing_date=filing_date,
                    accession_number=accession,
                    primary_document=document,
                    url=EDGAR_DOCUMENT_URL.format(
                        cik_unpadded=str(int(cik)),
                        accession_no_dashes=accession.replace("-", ""),
                        document=document,
                    ),
                )
            )
            if len(filings) >= limit:
                break
        return tuple(filings)

    def _shares_outstanding(self, cik: str) -> Optional[float]:
        data = self._get_json(SEC_COMPANYFACTS_URL.format(cik=cik))
        units = (
            data.get("facts", {})
            .get("dei", {})
            .get("EntityCommonStockSharesOutstanding", {})
            .get("units", {})
        )
        observations = units.get("shares") or units.get("USD/shares") or []
        valid = [item for item in observations if item.get("val") is not None and item.get("end")]
        if not valid:
            return None
        latest = sorted(valid, key=lambda item: item["end"])[-1]
        return float(latest["val"])

    def _news(self, ticker: str, limit: int = 3) -> tuple[NewsSnapshot, ...]:
        text = self._get_text(
            YAHOO_NEWS_RSS_URL.format(ticker=quote(ticker)),
            content_type="application/rss+xml",
        )
        root = ElementTree.fromstring(text)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            published = (item.findtext("pubDate") or "").strip()
            if published:
                try:
                    published = parsedate_to_datetime(published).date().isoformat()
                except (TypeError, ValueError, IndexError):
                    pass
            if title and url:
                items.append(NewsSnapshot(title=title, url=url, published_at=published))
        return tuple(items)

    def _price_snapshot(self, ticker: str) -> PriceSnapshot:
        text = self._get_text(
            STOOQ_DAILY_URL.format(ticker=quote(ticker.lower())),
            content_type="text/csv",
        )
        rows = [
            row
            for row in csv.DictReader(StringIO(text))
            if row.get("Close") not in {None, "", "N/D"}
        ]
        if not rows:
            return PriceSnapshot(None, None, None, None, None, None)
        latest = rows[-1]
        previous = rows[-2] if len(rows) > 1 else None
        latest_close = float(latest["Close"])
        previous_close = float(previous["Close"]) if previous else None
        relative_strength = None
        if previous_close:
            relative_strength = round(((latest_close / previous_close) - 1) * 100, 2)
        latest_volume = int(float(latest.get("Volume") or 0))
        prior_volumes = [int(float(row.get("Volume") or 0)) for row in rows[:-1] if row.get("Volume")]
        average_volume = sum(prior_volumes) / len(prior_volumes) if prior_volumes else None
        volume_ratio = round(latest_volume / average_volume, 2) if average_volume else None
        return PriceSnapshot(
            price=latest_close,
            previous_price=previous_close,
            relative_strength_pct=relative_strength,
            latest_volume=latest_volume,
            average_volume=average_volume,
            volume_ratio=volume_ratio,
        )


class LiveResearchProvider:
    def __init__(
        self,
        *,
        base_companies: Sequence[CandidateCompany],
        base_rotation_signals: Mapping[str, RotationSignal],
        client: PublicMarketDataClient = None,
        now: datetime = None,
    ) -> None:
        self.base_companies = tuple(base_companies)
        self.base_rotation_signals = base_rotation_signals
        self.client = client or PublicMarketDataClient(now=now)
        self.now = now or datetime.now(timezone.utc)
        self._companies: Optional[tuple[CandidateCompany, ...]] = None

    def companies(self) -> Sequence[CandidateCompany]:
        if self._companies is None:
            self._companies = tuple(self._enrich_or_fallback(company) for company in self.base_companies)
        return self._companies

    def rotation_signals(self) -> Mapping[str, RotationSignal]:
        return self.base_rotation_signals

    def as_of(self) -> str:
        return f"live-public-sources-{self.now.date().isoformat()}"

    def _enrich_or_fallback(self, company: CandidateCompany) -> CandidateCompany:
        try:
            return self._enrich(company, self.client.snapshot(company.ticker))
        except Exception:
            return company

    def _enrich(self, company: CandidateCompany, snapshot: CompanyLiveSnapshot) -> CandidateCompany:
        evidence = list(company.evidence)
        catalysts = list(company.catalysts)
        risks = list(company.risks)
        invalidations = list(company.invalidation_signals)
        market_cap = company.market_cap_b

        if snapshot.market_cap_b:
            market_cap = snapshot.market_cap_b
        if snapshot.price is not None:
            context = f"Live market context: last price ${snapshot.price:.2f}"
            if snapshot.relative_strength_pct is not None:
                context += f", one-session move {snapshot.relative_strength_pct:+.1f}%"
            if snapshot.volume_ratio is not None:
                context += f", volume {snapshot.volume_ratio:.1f}x prior average"
            summary = f"{company.summary} {context}."
        else:
            summary = company.summary

        if snapshot.filings:
            latest = snapshot.filings[0]
            catalysts.append(f"Latest SEC filing {latest.form}")
            evidence.append(
                Evidence(
                    title=f"SEC {latest.form} filing",
                    url=latest.url,
                    observed_at=snapshot.observed_at,
                )
            )
        if snapshot.news:
            latest_news = snapshot.news[0]
            catalysts.append(f"Recent news: {latest_news.title}")
            evidence.append(
                Evidence(
                    title=latest_news.title,
                    url=latest_news.url,
                    observed_at=latest_news.published_at or snapshot.observed_at,
                )
            )
        if snapshot.relative_strength_pct is not None and snapshot.relative_strength_pct < -5:
            risks.append("Negative recent relative strength")
        if snapshot.volume_ratio is not None and snapshot.volume_ratio < 0.5:
            invalidations.append("Live volume is materially below prior average")

        return replace(
            company,
            market_cap_b=market_cap,
            summary=summary,
            catalysts=tuple(dict.fromkeys(catalysts)),
            risks=tuple(dict.fromkeys(risks)),
            invalidation_signals=tuple(dict.fromkeys(invalidations)),
            evidence=tuple(dict.fromkeys(evidence)),
            missing_information=(
                "Live refresh market data before acting",
                "Read full latest SEC filing",
                "Verify transcript and guidance context",
            ),
        )
