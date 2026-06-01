import json
import unittest
from datetime import datetime, timezone
from email.message import Message
from io import BytesIO
from urllib.error import URLError

from nick_engine.live_provider import LiveResearchProvider, PublicMarketDataClient
from nick_engine.models import CandidateCompany


class FakeResponse(BytesIO):
    def __init__(self, body: str, content_type: str = "application/json"):
        super().__init__(body.encode("utf-8"))
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def candidate(ticker="TEX") -> CandidateCompany:
    return CandidateCompany(
        ticker=ticker,
        name="Terex",
        sector="Industrials",
        industry="Construction Machinery",
        market_cap_b=4.0,
        value_chain_layer="second-order: materials processing and lifting equipment",
        exposure="direct",
        thesis_keywords=("construction", "equipment"),
        summary="Seed summary.",
        catalysts=("Fleet replacement cycle",),
        risks=("Cyclical end markets",),
        invalidation_signals=("Orders decline",),
        evidence=(),
        liquidity="medium",
        risk_flags=(),
    )


class LiveProviderTests(unittest.TestCase):
    def test_client_builds_live_snapshot_from_public_sources(self):
        calls = []

        def opener(request, timeout):
            url = request.full_url
            calls.append(url)
            if "company_tickers.json" in url:
                return FakeResponse(json.dumps({"0": {"ticker": "TEX", "cik_str": 97216, "title": "TEREX CORP"}}))
            if "submissions/CIK0000097216.json" in url:
                return FakeResponse(
                    json.dumps(
                        {
                            "filings": {
                                "recent": {
                                    "form": ["10-Q", "8-K"],
                                    "accessionNumber": ["0000097216-26-000001", "0000097216-26-000002"],
                                    "filingDate": ["2026-05-08", "2026-05-20"],
                                    "primaryDocument": ["tex-20260331.htm", "tex-8k.htm"],
                                }
                            }
                        }
                    )
                )
            if "companyfacts/CIK0000097216.json" in url:
                return FakeResponse(
                    json.dumps(
                        {
                            "facts": {
                                "dei": {
                                    "EntityCommonStockSharesOutstanding": {
                                        "units": {
                                            "shares": [
                                                {"end": "2026-05-01", "val": 65000000},
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    )
                )
            if "feeds.finance.yahoo.com" in url:
                return FakeResponse(
                    """<?xml version="1.0"?>
                    <rss><channel><item><title>Terex reports backlog growth</title>
                    <link>https://example.com/tex-news</link><pubDate>Mon, 01 Jun 2026 12:00:00 GMT</pubDate>
                    </item></channel></rss>""",
                    content_type="application/rss+xml",
                )
            if "stooq.com" in url:
                return FakeResponse(
                    "Date,Open,High,Low,Close,Volume\n"
                    "2026-05-29,40,41,39,40,1000\n"
                    "2026-06-01,44,45,43,44,3000\n",
                    content_type="text/csv",
                )
            raise AssertionError(url)

        client = PublicMarketDataClient(opener=opener)
        snapshot = client.snapshot("TEX")

        self.assertEqual("TEX", snapshot.ticker)
        self.assertEqual(44.0, snapshot.price)
        self.assertEqual(10.0, snapshot.relative_strength_pct)
        self.assertEqual(3.0, snapshot.volume_ratio)
        self.assertAlmostEqual(2.86, snapshot.market_cap_b, places=2)
        self.assertEqual("10-Q", snapshot.filings[0].form)
        self.assertEqual("Terex reports backlog growth", snapshot.news[0].title)
        self.assertTrue(any("companyfacts" in url for url in calls))

    def test_live_provider_enriches_company_without_losing_seed_thesis(self):
        def opener(request, timeout):
            url = request.full_url
            if "company_tickers.json" in url:
                return FakeResponse(json.dumps({"0": {"ticker": "TEX", "cik_str": 97216, "title": "TEREX CORP"}}))
            if "submissions" in url:
                return FakeResponse(
                    json.dumps(
                        {
                            "filings": {
                                "recent": {
                                    "form": ["10-Q"],
                                    "accessionNumber": ["0000097216-26-000001"],
                                    "filingDate": ["2026-05-08"],
                                    "primaryDocument": ["tex-20260331.htm"],
                                }
                            }
                        }
                    )
                )
            if "companyfacts" in url:
                return FakeResponse(json.dumps({"facts": {"dei": {}}}))
            if "feeds.finance.yahoo.com" in url:
                return FakeResponse("<rss><channel></channel></rss>", content_type="application/rss+xml")
            if "stooq.com" in url:
                return FakeResponse("Date,Open,High,Low,Close,Volume\n2026-06-01,44,45,43,44,3000\n")
            raise AssertionError(url)

        provider = LiveResearchProvider(
            base_companies=(candidate(),),
            base_rotation_signals={},
            client=PublicMarketDataClient(opener=opener),
            now=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )

        enriched = provider.companies()[0]

        self.assertEqual("TEX", enriched.ticker)
        self.assertIn("Live market context", enriched.summary)
        self.assertIn("Latest SEC filing 10-Q", enriched.catalysts)
        self.assertIn("SEC 10-Q filing", [item.title for item in enriched.evidence])
        self.assertIn("Live refresh market data before acting", enriched.missing_information)

    def test_live_provider_falls_back_to_seed_company_when_sources_fail(self):
        def opener(request, timeout):
            raise URLError("offline")

        seed = candidate()
        provider = LiveResearchProvider(
            base_companies=(seed,),
            base_rotation_signals={},
            client=PublicMarketDataClient(opener=opener),
        )

        self.assertEqual(seed, provider.companies()[0])


if __name__ == "__main__":
    unittest.main()
