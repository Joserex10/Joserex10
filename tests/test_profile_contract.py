from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProfileContractTests(unittest.TestCase):
    def test_identity_is_semantic_markdown(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("# Jose Maria Vallejos", readme)
        self.assertIn("Product-focused Software Engineer", readme)
        self.assertIn("Building private, local-first tools.", readme)

    def test_readme_has_reduced_motion_and_no_fragile_widgets(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion: reduce", readme)
        forbidden_hosts = (
            "github-readme-stats",
            "github-profile-trophy",
            "readme-typing-svg",
            "github-readme-streak-stats",
            "komarev.com",
            "skillicons.dev",
        )
        for host in forbidden_hosts:
            self.assertNotIn(host, readme)

    def test_all_local_readme_assets_exist(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        references = set(re.findall(r'(?:src|srcset)="(assets/[^"]+)"', readme))
        self.assertGreaterEqual(len(references), 6)
        for reference in references:
            self.assertTrue((ROOT / reference).is_file(), reference)

    def test_svg_assets_are_valid_and_bounded(self) -> None:
        for path in (ROOT / "assets").glob("*.svg"):
            content = path.read_text(encoding="utf-8")
            ET.fromstring(content)
            self.assertLessEqual(path.stat().st_size, 150_000, path.name)
            self.assertNotRegex(content.lower(), r"<\s*script|foreignobject|\bhref\s*=|data\s*:")
            self.assertNotIn("infinite", content.lower())

    def test_raster_assets_meet_budget_and_are_png(self) -> None:
        for path in (ROOT / "assets").glob("*.png"):
            self.assertLessEqual(path.stat().st_size, 400_000, path.name)
            self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_workflow_actions_are_pinned_and_permissions_are_narrow(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "update-profile.yml").read_text(encoding="utf-8")
        uses = re.findall(r"uses:\s*([^\s]+)", workflow)
        self.assertEqual(len(uses), 2)
        for action in uses:
            self.assertRegex(action, r"^actions/[a-z-]+@[0-9a-f]{40}$")
        self.assertIn("permissions: {}", workflow)
        self.assertEqual(workflow.count("contents: write"), 1)
        self.assertIn('python-version: "3.14.6"', workflow)

    def test_generator_uses_current_github_api_version(self) -> None:
        generator = (ROOT / "scripts" / "generate_activity.py").read_text(encoding="utf-8")
        self.assertIn('"X-GitHub-Api-Version": "2026-03-10"', generator)


if __name__ == "__main__":
    unittest.main()
