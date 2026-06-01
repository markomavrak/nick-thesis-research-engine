import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from nick_engine.daily_digest import (
    ALREADY_RESEARCHED_TICKERS,
    DIGEST_RECIPIENTS,
    MIN_EXPLOSIVE_SETUP_SCORE,
    MIN_NICK_SCORE,
    MIN_NEAR_TERM_REASONS,
    build_daily_digest,
    is_toronto_send_hour,
    run_daily_digest,
)
from nick_engine.daily_digest import _reports
from nick_engine.providers import FixtureResearchProvider


class DailyDigestTests(unittest.TestCase):
    def test_digest_contains_all_three_thesis_tracks_and_ranked_names(self):
        digest = build_daily_digest(FixtureResearchProvider())

        self.assertIn("Market Research Digest", digest.subject)
        self.assertIn("Optical Networking Bottleneck", digest.html)
        self.assertIn("Memory / HBM Bottleneck", digest.html)
        self.assertIn("Construction Equipment Demand", digest.html)
        self.assertIn("ADTN", digest.html)
        self.assertIn("FORM", digest.html)
        self.assertIn("TEX", digest.html)
        self.assertIn("Research watchlist only", digest.text)

    def test_digest_uses_deep_dive_paragraphs_tied_to_thesis(self):
        digest = build_daily_digest(FixtureResearchProvider())

        self.assertIn("Thesis fit:", digest.text)
        self.assertIn("Why it can work:", digest.text)
        self.assertIn("What kills it:", digest.text)
        self.assertIn("matched terms", digest.text)
        self.assertIn("score breakdown", digest.text)

    def test_digest_email_copy_does_not_mention_nick(self):
        digest = build_daily_digest(FixtureResearchProvider())

        self.assertNotIn("Nick", digest.subject)
        self.assertNotIn("Nick", digest.html)
        self.assertNotIn("Nick", digest.text)
        self.assertIn("Market Research Digest", digest.subject)
        self.assertIn("Hidden Gem Stock Research", digest.html)

    def test_digest_filters_to_high_scoring_hidden_gems(self):
        reports = _reports(FixtureResearchProvider())

        self.assertEqual(80, MIN_NICK_SCORE)
        for _, report in reports:
            self.assertTrue(report.candidates)
            self.assertLessEqual(len(report.candidates), 3)
            for candidate in report.candidates:
                self.assertGreaterEqual(candidate.score, MIN_NICK_SCORE)
                self.assertGreaterEqual(candidate.setup_score, MIN_EXPLOSIVE_SETUP_SCORE)
                self.assertGreaterEqual(len(candidate.setup_reasons), MIN_NEAR_TERM_REASONS)
                self.assertNotIn(candidate.company.ticker, ALREADY_RESEARCHED_TICKERS)

        construction_tickers = [item.company.ticker for item in reports[2][1].candidates]
        self.assertEqual(["ASTE", "TEX", "MTW"], construction_tickers)
        self.assertNotIn("HRI", construction_tickers)

    def test_digest_excludes_already_researched_tickers(self):
        digest = build_daily_digest(FixtureResearchProvider())

        self.assertIn("CAT", ALREADY_RESEARCHED_TICKERS)
        self.assertIn("MU", ALREADY_RESEARCHED_TICKERS)
        self.assertNotIn("CAT - Caterpillar", digest.text)
        self.assertNotIn("MU - Micron Technology", digest.text)
        self.assertNotIn("LITE - Lumentum", digest.text)
        self.assertIn("Already researched tickers excluded", digest.text)

    def test_digest_explains_why_candidates_can_move_soon(self):
        digest = build_daily_digest(FixtureResearchProvider())

        self.assertIn("Why it could move soon:", digest.text)
        self.assertIn("Setup score", digest.text)
        self.assertIn("Small/mid-cap torque", digest.text)
        self.assertIn("why it could move soon", digest.html.lower())
        self.assertIn("Setup Dashboard", digest.html)
        self.assertIn("Near-Term Setup", digest.html)
        self.assertIn("Thesis Fit", digest.html)

    def test_digest_has_two_recipients_configured(self):
        self.assertEqual(
            ("marko@advertra.ca", "ikeepitstream@gmail.com"),
            DIGEST_RECIPIENTS,
        )

    def test_toronto_send_hour_handles_winter_utc_offset(self):
        now = datetime(2026, 1, 5, 14, 12, tzinfo=timezone.utc)

        self.assertTrue(is_toronto_send_hour(now))

    def test_toronto_send_hour_handles_summer_utc_offset(self):
        now = datetime(2026, 6, 1, 13, 12, tzinfo=timezone.utc)

        self.assertTrue(is_toronto_send_hour(now))

    def test_toronto_send_hour_rejects_other_hours(self):
        now = datetime(2026, 6, 1, 14, 12, tzinfo=timezone.utc)

        self.assertFalse(is_toronto_send_hour(now))

    def test_scheduled_run_skips_outside_toronto_send_hour(self):
        result = run_daily_digest(
            now=datetime(2026, 6, 1, 14, 12, tzinfo=timezone.utc),
            dry_run=False,
            force=False,
            environment={},
        )

        self.assertEqual("skipped", result.status)
        self.assertIn("outside Toronto 9 AM hour", result.message)

    def test_dry_run_writes_preview_without_resend_credentials(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = run_daily_digest(
                now=datetime(2026, 6, 1, 14, 12, tzinfo=timezone.utc),
                dry_run=True,
                force=True,
                environment={},
                output_directory=Path(temporary_directory),
                provider=FixtureResearchProvider(),
            )

            preview = Path(temporary_directory) / "daily-stock-research-preview.html"

            self.assertEqual("dry-run", result.status)
            self.assertTrue(preview.exists())
            self.assertIn("Hidden Gem Stock Research", preview.read_text())

    def test_live_run_sends_to_both_recipients(self):
        captured = {"recipients": [], "send_dates": []}

        class FakeClient:
            def __init__(self, *, api_key, from_email):
                captured["api_key"] = api_key
                captured["from_email"] = from_email

            def send_digest(self, digest, *, to_email, send_date):
                captured["recipients"].append(to_email)
                captured["send_dates"].append(send_date.isoformat())
                return {"id": f"email_{len(captured['recipients'])}"}

        result = run_daily_digest(
            now=datetime(2026, 6, 1, 13, 12, tzinfo=timezone.utc),
            dry_run=False,
            force=False,
            environment={
                "RESEND_API_KEY": "re_test",
                "RESEND_FROM_EMAIL": "research@example.com",
            },
            provider=FixtureResearchProvider(),
            client_class=FakeClient,
        )

        self.assertEqual("sent", result.status)
        self.assertEqual(
            ["marko@advertra.ca", "ikeepitstream@gmail.com"],
            captured["recipients"],
        )
        self.assertEqual(["2026-06-01", "2026-06-01"], captured["send_dates"])
        self.assertIn("email_1", result.message)
        self.assertIn("email_2", result.message)


if __name__ == "__main__":
    unittest.main()
