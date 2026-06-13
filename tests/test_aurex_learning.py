import unittest

from aurex import app
from aurex.learning import GLOSSARY, LEARNING_MODULES, learning_payload
from aurex.terminal import AurexTerminal, SnapshotCache
from nick_engine.models import CandidateCompany, Evidence


class EmptySnapshotClient:
    def snapshot(self, ticker):
        return None


def learning_test_company():
    return CandidateCompany(
        ticker="LEARN",
        name="Learning Systems",
        sector="Photonics",
        industry="Education",
        market_cap_b=1.0,
        value_chain_layer="reference",
        exposure="indirect",
        thesis_keywords=("ai", "data", "center", "optical", "networking", "bottleneck"),
        summary="Learning fixture.",
        catalysts=("Reference library", "Operator fluency"),
        risks=("None",),
        invalidation_signals=("None",),
        evidence=(Evidence("Example", "https://example.com", "2026-06-01"),),
        liquidity="medium",
    )


class AurexLearningTests(unittest.TestCase):
    def test_learning_payload_covers_ai_value_chain_and_hard_terms(self):
        payload = learning_payload()
        module_titles = {module["title"] for module in payload["modules"]}
        glossary_terms = {term["term"].lower() for term in payload["glossary"]}

        self.assertIn("AI Compute And Cluster Architecture", module_titles)
        self.assertIn("Wafers And Front-End Manufacturing", module_titles)
        self.assertIn("Advanced Packaging And Chiplets", module_titles)
        self.assertIn("HBM And The Memory Bandwidth Wall", module_titles)
        self.assertIn("Optics, Lasers, Silicon Photonics, And CPO", module_titles)
        self.assertIn("Power, Cooling, And The Rack Constraint", module_titles)

        for hard_term in ("wafer", "die", "interposer", "tsv", "hbm", "cpo", "laser"):
            self.assertIn(hard_term, glossary_terms)

        self.assertGreaterEqual(len(LEARNING_MODULES), 8)
        self.assertGreaterEqual(len(GLOSSARY), 25)

    def test_each_learning_module_is_actionable_for_stock_research(self):
        for module in learning_payload()["modules"]:
            self.assertTrue(module["why_it_matters"])
            self.assertTrue(module["stock_research_angle"])
            self.assertGreaterEqual(len(module["key_questions"]), 3)
            self.assertGreaterEqual(len(module["hard_terms"]), 3)
            self.assertGreaterEqual(len(module["videos"]), 1)
            for video in module["videos"]:
                self.assertTrue(video["title"])
                self.assertTrue(video["url"].startswith("https://"))

    def test_terminal_dashboard_exposes_learning_center(self):
        payload = AurexTerminal(
            companies=(learning_test_company(),),
            cache=SnapshotCache(client=EmptySnapshotClient()),
        ).dashboard_payload(limit=1)

        self.assertIn("learning_center", payload)
        self.assertEqual("AI Value Chain Learning Center", payload["learning_center"]["title"])
        self.assertGreaterEqual(payload["learning_center"]["module_count"], 8)
        self.assertIn("Wafer", " ".join(payload["learning_center"]["featured_terms"]))

    def test_app_shell_has_learning_center_mount_points(self):
        self.assertIn("Learning Center", app.HTML)
        self.assertIn("learning-grid", app.HTML)
        self.assertIn("renderLearning", app.HTML)
        self.assertIn("async function loadLearning", app.HTML)
        self.assertIn('fetch("/api/learning")', app.HTML)


if __name__ == "__main__":
    unittest.main()
