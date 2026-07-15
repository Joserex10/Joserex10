from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_activity as generator  # noqa: E402


class GenerateActivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = ROOT / "tests" / "fixtures" / "github_snapshot.json"
        cls.payload = json.loads(cls.fixture_path.read_text(encoding="utf-8"))
        cls.now = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)

    def test_renders_deterministic_valid_svg(self) -> None:
        svg = generator.render_svg(self.payload, self.now)
        generator.validate_svg(svg)
        ET.fromstring(svg)
        self.assertIn("1 public shipping signal in the last 30 complete UTC days", svg)
        self.assertIn("DocuFlow v2.2.0 · 2026-01-14", svg)
        self.assertIn("2026-07-14T12:00:00Z", svg)

    def test_xml_escapes_untrusted_release_tag(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["Joserex10/DocuFlow"]["releases"][0]["tag_name"] = "v2<&quot;"
        svg = generator.render_svg(payload, self.now)
        generator.validate_svg(svg)
        self.assertIn("v2&lt;&amp;quot;", svg)
        self.assertNotIn("v2<&quot;", svg)

    def test_rejects_external_release_url(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["Joserex10/DocuFlow"]["releases"][0]["html_url"] = "https://example.com/release"
        with self.assertRaisesRegex(ValueError, "github.com"):
            generator.render_svg(payload, self.now)

    def test_rejects_oversized_text(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["Joserex10/DocuFlow"]["releases"][0]["tag_name"] = "x" * 101
        with self.assertRaisesRegex(ValueError, "exceeds"):
            generator.render_svg(payload, self.now)

    def test_atomic_write_preserves_valid_output_shape(self) -> None:
        svg = generator.render_svg(self.payload, self.now)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "activity.svg"
            self.assertTrue(generator.atomic_write(output, svg))
            self.assertEqual(output.read_text(encoding="utf-8"), svg)
            later_svg = generator.render_svg(self.payload, datetime(2026, 7, 14, 18, 0, tzinfo=UTC))
            self.assertFalse(generator.atomic_write(output, later_svg))
            self.assertEqual(output.read_text(encoding="utf-8"), svg)


if __name__ == "__main__":
    unittest.main()
