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

    def test_each_learning_module_has_visual_metadata(self):
        payload = learning_payload()

        for module in payload["modules"]:
            self.assertTrue(module["icon"])
            self.assertTrue(module["visual_title"])
            self.assertTrue(module["visual_caption"])
            self.assertGreaterEqual(len(module["visual_nodes"]), 3)

        module_icons = {module["icon"] for module in payload["modules"]}
        self.assertIn("wafer", module_icons)
        self.assertIn("package", module_icons)
        self.assertIn("optics", module_icons)

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

    def test_app_shell_uses_tabbed_workflow_navigation(self):
        self.assertIn('class="app-nav"', app.HTML)
        self.assertIn('data-tab-target="researchTab"', app.HTML)
        self.assertIn('data-tab-target="learningTab"', app.HTML)
        self.assertIn('id="researchTab"', app.HTML)
        self.assertIn('id="learningTab"', app.HTML)
        self.assertIn('class="tab-panel active"', app.HTML)
        self.assertIn("function switchTab", app.HTML)
        self.assertIn("Research Workflow", app.HTML)
        self.assertIn("Screen candidates", app.HTML)
        self.assertIn("Open deep dive", app.HTML)
        self.assertIn("Check activity tape", app.HTML)

    def test_app_shell_has_visual_learning_cards_and_richer_deep_dive(self):
        self.assertIn("learning-visual", app.HTML)
        self.assertIn("moduleIconSvg", app.HTML)
        self.assertIn("visual_nodes", app.HTML)
        self.assertIn("Thesis Fit", app.HTML)
        self.assertIn("Setup Intelligence", app.HTML)
        self.assertIn("Catalysts", app.HTML)
        self.assertIn("Invalidation", app.HTML)

    def test_app_shell_has_phone_first_responsive_layout(self):
        self.assertIn("overflow-x: hidden", app.HTML)
        self.assertIn("@media (max-width: 640px)", app.HTML)
        self.assertIn(".table-scroll", app.HTML)
        self.assertIn("td::before", app.HTML)
        self.assertIn("content: attr(data-label)", app.HTML)
        self.assertIn("min-height: 44px", app.HTML)
        self.assertIn(".metric-cards", app.HTML)
        self.assertIn('data-label="Ticker"', app.HTML)
        self.assertIn('data-label="Why It Matters"', app.HTML)
        self.assertIn('class="cards metric-cards"', app.HTML)
        self.assertNotIn('style="grid-template-columns: repeat(3, 1fr)"', app.HTML)


if __name__ == "__main__":
    unittest.main()
