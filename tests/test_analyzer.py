import unittest

from nick_engine.analyzer import analyze_thesis, extract_keywords
from nick_engine.fixtures import COMPANIES, ROTATION_SIGNALS
from nick_engine.models import CandidateCompany, Evidence, RotationSignal


def company(
    *,
    ticker: str,
    market_cap_b: float,
    keywords: tuple[str, ...],
    exposure: str = "direct",
    liquidity: str = "high",
    risk_flags: tuple[str, ...] = (),
    catalysts: tuple[str, ...] = ("Demand growth",),
    evidence_count: int = 1,
    near_term_signals: tuple[str, ...] = (),
) -> CandidateCompany:
    return CandidateCompany(
        ticker=ticker,
        name=ticker,
        sector="Industrials",
        industry="Machinery",
        market_cap_b=market_cap_b,
        value_chain_layer="equipment",
        exposure=exposure,
        thesis_keywords=keywords,
        summary=f"{ticker} summary",
        catalysts=catalysts,
        risks=("Cyclical slowdown",),
        invalidation_signals=("Orders fall",),
        evidence=tuple(
            Evidence(
                title=f"Company evidence {index}",
                url=f"https://example.com/evidence-{index}",
                observed_at="2026-05-01",
            )
            for index in range(evidence_count)
        ),
        liquidity=liquidity,
        risk_flags=risk_flags,
        near_term_signals=near_term_signals,
    )


class ExtractKeywordsTests(unittest.TestCase):
    def test_extract_keywords_removes_noise_and_normalizes_plural_words(self):
        keywords = extract_keywords(
            "Find smaller public companies benefiting from construction equipment demand"
        )

        self.assertIn("construction", keywords)
        self.assertIn("equipment", keywords)
        self.assertIn("demand", keywords)
        self.assertNotIn("from", keywords)
        self.assertNotIn("companies", keywords)

    def test_extract_keywords_preserves_ai_as_a_meaningful_short_term(self):
        self.assertIn("ai", extract_keywords("AI data center demand"))


class AnalyzeThesisTests(unittest.TestCase):
    def test_direct_exposure_outranks_indirect_exposure(self):
        direct = company(ticker="DIR", market_cap_b=5, keywords=("construction", "equipment"))
        indirect = company(
            ticker="IND",
            market_cap_b=5,
            keywords=("construction", "equipment"),
            exposure="indirect",
        )

        report = analyze_thesis(
            "construction equipment demand",
            [indirect, direct],
            {"Industrials": RotationSignal("Industrials", "in", "Improving breadth", "2026-05-31")},
        )

        self.assertEqual(["DIR", "IND"], [item.company.ticker for item in report.candidates])
        self.assertGreater(
            report.candidates[0].score_breakdown["thesis_fit"],
            report.candidates[1].score_breakdown["thesis_fit"],
        )

    def test_rotation_in_scores_higher_than_rotation_out(self):
        industrial = company(ticker="IND", market_cap_b=5, keywords=("equipment",))
        software = CandidateCompany(
            **{
                **industrial.__dict__,
                "ticker": "SOFT",
                "name": "SOFT",
                "sector": "Software",
            }
        )

        report = analyze_thesis(
            "equipment",
            [software, industrial],
            {
                "Industrials": RotationSignal("Industrials", "in", "Improving breadth", "2026-05-31"),
                "Software": RotationSignal("Software", "out", "Weakening breadth", "2026-05-31"),
            },
        )

        self.assertEqual(["IND", "SOFT"], [item.company.ticker for item in report.candidates])
        self.assertEqual(15, report.candidates[0].score_breakdown["sector_rotation"])
        self.assertEqual(-10, report.candidates[1].score_breakdown["sector_rotation"])

    def test_market_cap_limit_filters_large_companies(self):
        small = company(ticker="SMALL", market_cap_b=4, keywords=("equipment",))
        large = company(ticker="LARGE", market_cap_b=150, keywords=("equipment",))

        report = analyze_thesis(
            "equipment",
            [small, large],
            {"Industrials": RotationSignal("Industrials", "neutral", "Mixed", "2026-05-31")},
            max_market_cap_b=10,
        )

        self.assertEqual(["SMALL"], [item.company.ticker for item in report.candidates])

    def test_low_liquidity_and_risk_flags_produce_three_of_three_risk(self):
        speculative = company(
            ticker="RISK",
            market_cap_b=0.4,
            keywords=("equipment",),
            liquidity="low",
            risk_flags=("pre-revenue", "customer concentration"),
        )

        report = analyze_thesis(
            "equipment",
            [speculative],
            {"Industrials": RotationSignal("Industrials", "neutral", "Mixed", "2026-05-31")},
        )

        self.assertEqual("3/3", report.candidates[0].risk_tier)

    def test_explosive_setup_score_requires_multiple_near_term_reasons(self):
        explosive = company(
            ticker="BOOM",
            market_cap_b=2,
            keywords=("construction", "equipment"),
            catalysts=("Backlog acceleration", "Equipment replacement cycle"),
            evidence_count=2,
            near_term_signals=("Volume expansion: 2.1x prior average", "Fresh 10-Q catalyst"),
        )
        slow = company(
            ticker="SLOW",
            market_cap_b=40,
            keywords=("construction", "equipment"),
            catalysts=("Long-term demand",),
            evidence_count=1,
        )

        report = analyze_thesis(
            "construction equipment demand",
            [slow, explosive],
            {"Industrials": RotationSignal("Industrials", "in", "Improving breadth", "2026-05-31")},
        )

        self.assertEqual("BOOM", report.candidates[0].company.ticker)
        self.assertGreaterEqual(report.candidates[0].setup_score, 60)
        self.assertGreaterEqual(len(report.candidates[0].setup_reasons), 2)
        self.assertTrue(
            any("Volume expansion" in reason for reason in report.candidates[0].setup_reasons)
        )
        self.assertLess(report.candidates[1].setup_score, report.candidates[0].setup_score)

    def test_construction_equipment_fixture_surfaces_smaller_second_order_names(self):
        report = analyze_thesis(
            "construction equipment demand will skyrocket",
            COMPANIES,
            ROTATION_SIGNALS,
            max_market_cap_b=15,
        )

        tickers = [item.company.ticker for item in report.candidates]
        self.assertIn("ASTE", tickers)
        self.assertIn("MTW", tickers)
        self.assertIn("HEES", tickers)
        self.assertNotIn("CAT", tickers)
        self.assertEqual("ASTE", tickers[0])

    def test_ai_optical_bottleneck_fixture_surfaces_nicks_photonics_watchlist(self):
        report = analyze_thesis(
            "AI data center optical networking bottleneck",
            COMPANIES,
            ROTATION_SIGNALS,
        )

        tickers = [item.company.ticker for item in report.candidates]
        self.assertIn("LITE", tickers)
        self.assertIn("COHR", tickers)
        self.assertIn("CIEN", tickers)
        self.assertIn("CRDO", tickers)
        self.assertNotIn("ASML", tickers)
        self.assertNotIn("MU", tickers)

    def test_ai_memory_bottleneck_fixture_surfaces_memory_names(self):
        report = analyze_thesis(
            "AI memory bandwidth HBM bottleneck",
            COMPANIES,
            ROTATION_SIGNALS,
        )

        tickers = [item.company.ticker for item in report.candidates]
        self.assertIn("MU", tickers)
        self.assertIn("SNDK", tickers)


if __name__ == "__main__":
    unittest.main()
