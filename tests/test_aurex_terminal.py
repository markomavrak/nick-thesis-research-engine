import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aurex.terminal import AurexTerminal, ManualBlockActivity, SnapshotCache
from nick_engine.live_provider import CompanyLiveSnapshot, FilingSnapshot, NewsSnapshot
from nick_engine.models import CandidateCompany, Evidence, RotationSignal


def company(ticker="TEST") -> CandidateCompany:
    return CandidateCompany(
        ticker=ticker,
        name="Test Systems",
        sector="Photonics",
        industry="Optical Networking",
        market_cap_b=1.5,
        value_chain_layer="L8 connectivity: optical networking bottleneck",
        exposure="direct",
        thesis_keywords=("ai", "data", "center", "optical", "networking", "bottleneck"),
        summary="Seed summary.",
        catalysts=("AI optical orders", "Backlog acceleration"),
        risks=("Customer concentration",),
        invalidation_signals=("Orders weaken",),
        evidence=(
            Evidence("Investor relations", "https://example.com/ir", "2026-06-01"),
            Evidence("SEC filings", "https://example.com/sec", "2026-06-01"),
        ),
        liquidity="medium",
    )


class FakeClient:
    def snapshot(self, ticker):
        return CompanyLiveSnapshot(
            ticker=ticker,
            cik="0000000001",
            market_cap_b=1.8,
            price=18.0,
            relative_strength_pct=6.5,
            volume_ratio=2.7,
            filings=(
                FilingSnapshot(
                    form="10-Q",
                    filing_date="2026-06-01",
                    accession_number="0000000001-26-000001",
                    primary_document="test.htm",
                    url="https://example.com/filing",
                ),
            ),
            news=(
                NewsSnapshot(
                    title="Test Systems wins optical order",
                    url="https://example.com/news",
                    published_at="2026-06-02",
                ),
            ),
            observed_at="2026-06-03",
        )


class AurexTerminalTests(unittest.TestCase):
    def test_dashboard_payload_scores_live_candidates(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            terminal = AurexTerminal(
                companies=(company(),),
                rotation_signals={
                    "Photonics": RotationSignal("Photonics", "in", "Test rotation", "2026-06-03")
                },
                cache=SnapshotCache(client=FakeClient()),
                block_activity_path=Path(temporary_directory) / "blocks.json",
                now_fn=lambda: datetime(2026, 6, 3, tzinfo=timezone.utc),
            )

            payload = terminal.dashboard_payload(
                thesis="AI data center optical networking bottleneck",
                hide_researched=True,
            )

        self.assertEqual("Aurex Research Terminal", payload["app"])
        self.assertEqual(1, payload["summary"]["candidate_count"])
        self.assertEqual("TEST", payload["candidates"][0]["ticker"])
        self.assertGreaterEqual(payload["candidates"][0]["score"], 80)
        self.assertIn("intraday block feed", payload["source_status"]["intraday_limit"])

    def test_activity_signals_include_volume_price_and_manual_blocks(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            terminal = AurexTerminal(
                companies=(company(),),
                rotation_signals={},
                cache=SnapshotCache(client=FakeClient()),
                block_activity_path=Path(temporary_directory) / "blocks.json",
            )
            terminal.add_manual_block(
                ManualBlockActivity(
                    ticker="TEST",
                    observed_at="2026-06-03T09:31:00-04:00",
                    side="buy",
                    notional=2_500_000,
                    volume=100_000,
                    source="manual",
                    notes="Observed block print",
                )
            )

            signals = terminal.activity_signals()

        self.assertEqual("TEST", signals[0].ticker)
        self.assertEqual("high", signals[0].severity)
        self.assertIn("Unusual volume", " ".join(signals[0].flags))
        self.assertIn("Manual block tape", " ".join(signals[0].flags))
        self.assertEqual(1, signals[0].manual_block_count)


if __name__ == "__main__":
    unittest.main()
