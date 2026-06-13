import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from aurex.static_site import DEFAULT_PUBLIC_DOMAIN, write_static_site
from aurex.terminal import AurexTerminal, SnapshotCache
from nick_engine.models import CandidateCompany, Evidence, RotationSignal


class EmptySnapshotClient:
    def snapshot(self, ticker):
        return None


def public_test_company():
    return CandidateCompany(
        ticker="PUB",
        name="Public Systems",
        sector="Photonics",
        industry="Optical Networking",
        market_cap_b=1.2,
        value_chain_layer="L8 connectivity: optical networking bottleneck",
        exposure="direct",
        thesis_keywords=("ai", "data", "center", "optical", "networking", "bottleneck"),
        summary="Public static dashboard fixture.",
        catalysts=("AI optical orders", "Near-term customer qualification", "Capacity expansion"),
        risks=("Customer concentration",),
        invalidation_signals=("Orders weaken",),
        evidence=(Evidence("Investor relations", "https://example.com/ir", "2026-06-01"),),
        liquidity="medium",
        near_term_signals=("Fresh qualification language", "Volume expansion setup", "AI rack demand"),
    )


class StaticSiteTests(unittest.TestCase):
    def test_static_site_writes_pages_artifact_with_custom_domain(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            terminal = AurexTerminal(
                companies=(public_test_company(),),
                rotation_signals={
                    "Photonics": RotationSignal("Photonics", "in", "Rotation in", "2026-06-13")
                },
                cache=SnapshotCache(client=EmptySnapshotClient()),
                now_fn=lambda: datetime(2026, 6, 13, 9, 0, tzinfo=timezone.utc),
            )

            manifest = write_static_site(output_dir, terminal=terminal)

            self.assertEqual(DEFAULT_PUBLIC_DOMAIN, "aurex.archive.trading")
            self.assertEqual(output_dir / "index.html", manifest["index"])
            self.assertEqual("aurex.archive.trading\n", (output_dir / "CNAME").read_text())
            self.assertTrue((output_dir / "404.html").exists())
            self.assertTrue((output_dir / "robots.txt").exists())
            self.assertTrue((output_dir / "api" / "dashboard.json").exists())
            self.assertTrue((output_dir / "api" / "learning.json").exists())

    def test_static_site_payload_contains_dashboard_and_learning_data(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            write_static_site(
                output_dir,
                terminal=AurexTerminal(
                    companies=(public_test_company(),),
                    rotation_signals={
                        "Photonics": RotationSignal("Photonics", "in", "Rotation in", "2026-06-13")
                    },
                    cache=SnapshotCache(client=EmptySnapshotClient()),
                ),
            )

            dashboard = json.loads((output_dir / "api" / "dashboard.json").read_text())
            learning = json.loads((output_dir / "api" / "learning.json").read_text())

        self.assertEqual("Aurex Research Terminal", dashboard["app"])
        self.assertEqual("PUB", dashboard["candidates"][0]["ticker"])
        self.assertGreaterEqual(dashboard["candidates"][0]["score"], 80)
        self.assertEqual("AI Value Chain Learning Center", learning["title"])
        self.assertGreaterEqual(learning["module_count"], 8)

    def test_static_shell_uses_relative_json_and_no_local_api_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            write_static_site(output_dir)
            html = (output_dir / "index.html").read_text()

        self.assertIn('fetch("api/dashboard.json")', html)
        self.assertIn('fetch("api/learning.json")', html)
        self.assertNotIn('fetch("/api/dashboard', html)
        self.assertNotIn("127.0.0.1", html)
        self.assertNotIn("localhost", html)

    def test_pages_workflow_builds_static_site_for_aurex_domain(self):
        workflow = Path(".github/workflows/aurex-pages.yml").read_text()

        self.assertIn("actions/deploy-pages", workflow)
        self.assertIn("actions/upload-pages-artifact", workflow)
        self.assertIn("python3 -m aurex.static_site", workflow)
        self.assertIn("aurex.archive.trading", workflow)
        self.assertIn("PYTHONPATH=src python3 -m unittest discover -s tests -v", workflow)


if __name__ == "__main__":
    unittest.main()
