from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from generate_validation_corpus import generate_corpus
from screen_candidate_corpus import safe_child, screen

class CandidateCorpusScreenTests(unittest.TestCase):
    def prepare(self, root, label, shape):
        images = root / label / "images"
        images.mkdir(parents=True)
        image = Image.new("RGB", (40, 24), "white")
        draw = ImageDraw.Draw(image)
        if shape == "box":
            draw.rectangle((3, 3, 25, 15), fill="black")
        else:
            draw.ellipse((9, 2, 30, 22), fill="red")
        image.save(images / "sample.png")
        data = root / label / "data"
        generate_corpus(images, data, palette_path=None, canvas_width=40, canvas_height=24)
        return (label, data / "results/generated_validation_corpus_manifest.json", images)

    def test_same_image_does_not_approve_or_count_as_independent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = self.prepare(root, "first", "box")
            b = self.prepare(root, "second", "box")
            r = screen([a, b])
            self.assertEqual(r["source_count"], 2)
            self.assertEqual(len(r["source_exact_duplicate_groups"]), 1)
            self.assertEqual(len(r["geometry_exact_duplicate_groups"]), 1)
            self.assertEqual(r["perceptual_review_pair_count"], 1)
            self.assertIsNone(r["independent_plan_count"])
            self.assertEqual(r["predictor_domain_eligibility"], "not_assessed")

    def test_different_shapes_not_exact_equal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            r = screen([self.prepare(root, "first", "box"),
                        self.prepare(root, "second", "circle")])
            self.assertEqual(r["source_exact_duplicate_groups"], [])
            self.assertEqual(r["geometry_exact_duplicate_groups"], [])
            self.assertEqual(len(r["records"]), 2)

    def test_mismatched_source_hash_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            a = self.prepare(root, "first", "box")
            Image.new("RGB", (20, 20), "green").save(a[2] / "sample.png")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                screen([a])

    def test_color_plan_summary_preserves_singleton_and_switch_counters(self):
        import hashlib
        import json
        from screen_candidate_corpus import color_plan_metadata
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "color.json"
            plan = {
                "plan_type": "autodraw_color_scanline_plan",
                "summary": {
                    "stroke_count": 4, "single_pixel_stroke_count": 2,
                    "color_switch_count": 3, "used_palette_color_count": 2,
                },
            }
            path.write_text(json.dumps(plan), encoding="utf-8")
            sha = hashlib.sha256(json.dumps(
                plan, ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest()
            result = color_plan_metadata(path, sha, 4)
            self.assertEqual(result["single_pixel_source_runs"], 2)
            self.assertEqual(result["color_switches_in_plan"], 3)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                color_plan_metadata(path, "0" * 64, 4)
            with self.assertRaisesRegex(ValueError, "stroke count mismatch"):
                color_plan_metadata(path, sha, 5)

    def test_path_traversal_and_duplicate_labels_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                safe_child(root, "../secret")
            a = self.prepare(root, "first", "box")
            with self.assertRaisesRegex(ValueError, "unique"):
                screen([a, a])

if __name__ == "__main__":
    unittest.main()
