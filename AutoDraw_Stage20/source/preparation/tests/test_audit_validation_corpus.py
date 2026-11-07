from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from audit_validation_corpus import audit_corpus
from generate_validation_corpus import generate_corpus


class ValidationCorpusAuditTests(unittest.TestCase):
    def test_offline_geometry_inventory_never_approves_domain(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "images"
            source.mkdir()
            image = Image.new("RGB", (24, 16), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((2, 2, 16, 10), fill="black")
            image.save(source / "shape.png")
            manifest = generate_corpus(
                source, root / "data", palette_path=None,
                canvas_width=24, canvas_height=16,
            )
            report = audit_corpus(root / "data" / "results" /
                                  "generated_validation_corpus_manifest.json")
            self.assertEqual(report["source_count"], 1)
            self.assertEqual(report["schema_valid_records"], 1)
            self.assertEqual(report["schema_invalid_records"], 0)
            self.assertTrue(report["not_a_CHALK_measurement"])
            self.assertEqual(report["predictor_domain_eligibility"], "not_assessed")
            record = report["records"][0]
            self.assertEqual(record["monochrome_N"],
                             manifest["records"][0]["drawing_plan_stroke_count"])
            self.assertEqual(record["horizontal_strokes"], record["monochrome_N"])
            self.assertEqual(record["predictor_domain_eligibility"], "not_assessed")

    def test_manifest_path_must_stay_within_corpus(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            results = root / "results"
            results.mkdir()
            (results / "generated_validation_corpus_manifest.json").write_text(
                json.dumps({
                    "protocol_eligibility": "candidate_only_not_assessed",
                    "records": [{
                        "project_path": "../outside.autodraw",
                        "source": "unsafe.png",
                        "drawing_plan_stroke_count": 1,
                    }],
                }), encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Путь выходит"):
                audit_corpus(results / "generated_validation_corpus_manifest.json")


if __name__ == "__main__":
    unittest.main()
