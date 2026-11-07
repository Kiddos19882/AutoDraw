from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from autodraw_project import open_project
from color_scanline import load_color_scanline_plan
from generate_validation_corpus import CorpusGenerationError, generate_corpus


class ValidationCorpusGeneratorTests(unittest.TestCase):
    def _source_image(self, path: Path) -> None:
        image = Image.new("RGB", (16, 12), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((2, 2, 7, 8), fill="black")
        draw.rectangle((9, 3, 13, 6), fill="red")
        image.save(path, format="PNG")

    def _palette(self, path: Path) -> None:
        document = {
            "schema_version": 1,
            "colors": [
                {"id": "black", "name": "Black", "rgb": [0, 0, 0], "hex": "#000000"},
                {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
                {"id": "white", "name": "White", "rgb": [255, 255, 255], "hex": "#FFFFFF"},
            ],
        }
        path.write_text(json.dumps(document), encoding="utf-8")

    def test_generates_valid_autodraw_and_color_scanline_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "input"
            source_dir.mkdir()
            source = source_dir / "sample.png"
            palette_path = root / "palette.json"
            self._source_image(source)
            self._palette(palette_path)

            manifest = generate_corpus(
                source_dir,
                root / "data",
                palette_path=palette_path,
                canvas_width=32,
                canvas_height=24,
                fit_mode="contain",
            )

            self.assertEqual(manifest["unique_source_count"], 1)
            self.assertEqual(manifest["duplicate_source_count"], 0)
            self.assertEqual(manifest["protocol_eligibility"], "candidate_only_not_assessed")
            record = manifest["records"][0]
            self.assertGreater(record["drawing_plan_stroke_count"], 0)
            self.assertGreater(record["color_plan_stroke_count"], 0)

            project_path = root / "data" / record["project_path"]
            bundle = open_project(project_path)
            self.assertEqual(bundle.canvas, (32, 24))
            self.assertEqual(bundle.name, "sample")
            drawing_plan = bundle.json_file("drawing_plan")
            self.assertEqual(len(drawing_plan["strokes"]), record["drawing_plan_stroke_count"])

            color_plan_path = root / "data" / record["color_plan_path"]
            color_plan = load_color_scanline_plan(color_plan_path)
            self.assertEqual(color_plan["summary"]["stroke_count"], record["color_plan_stroke_count"])
            self.assertEqual(color_plan["canvas"], {"width": 32, "height": 24})

            manifest_path = root / "data" / "results" / "generated_validation_corpus_manifest.json"
            self.assertTrue(manifest_path.is_file())

    def test_identical_source_files_are_not_counted_as_independent_plans(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "input"
            source_dir.mkdir()
            self._source_image(source_dir / "first.png")
            (source_dir / "second.png").write_bytes((source_dir / "first.png").read_bytes())

            manifest = generate_corpus(
                source_dir,
                root / "data",
                palette_path=None,
                canvas_width=32,
                canvas_height=24,
            )

            self.assertEqual(manifest["unique_source_count"], 1)
            self.assertEqual(manifest["duplicate_source_count"], 1)
            self.assertEqual(
                manifest["duplicates"][0]["duplicate_of"],
                manifest["records"][0]["source"],
            )
            self.assertEqual(manifest["records"][0]["protocol_eligibility"], "candidate_only_not_assessed")

    def test_existing_outputs_require_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "input"
            source_dir.mkdir()
            self._source_image(source_dir / "sample.png")
            output = root / "data"

            generate_corpus(source_dir, output, palette_path=None, canvas_width=32, canvas_height=24)
            with self.assertRaisesRegex(CorpusGenerationError, "уже существует"):
                generate_corpus(source_dir, output, palette_path=None, canvas_width=32, canvas_height=24)

    def test_empty_input_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "input"
            source_dir.mkdir()
            with self.assertRaisesRegex(CorpusGenerationError, "нет поддерживаемых изображений"):
                generate_corpus(source_dir, root / "data", palette_path=None)


    def test_generates_from_repository_test_image_and_real_palette_profile(self):
        repo_root = Path(__file__).resolve().parents[3]
        source_dir = repo_root / "testImages"
        palette_path = repo_root / "data" / "palettes" / "profiles" / "Browser_palette.autodraw-palette.json"
        self.assertTrue((source_dir / "images.png").is_file())
        self.assertTrue(palette_path.is_file())

        # The repository fixture directory is intentionally expandable. The
        # 2026-11-07 image additions made the former "exactly one file"
        # assertion stale, even though generation itself is valid.
        sources = sorted(
            path for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
        )
        self.assertGreaterEqual(len(sources), 8)
        expected_hashes = {
            hashlib.sha256(path.read_bytes()).hexdigest() for path in sources
        }

        with tempfile.TemporaryDirectory() as temp:
            data_root = Path(temp) / "data"
            manifest = generate_corpus(
                source_dir,
                data_root,
                palette_path=palette_path,
                canvas_width=64,
                canvas_height=32,
                fit_mode="contain",
            )
            self.assertEqual(manifest["unique_source_count"], len(expected_hashes))
            self.assertEqual(
                manifest["duplicate_source_count"], len(sources) - len(expected_hashes)
            )
            records = manifest["records"]
            self.assertEqual({item["source_sha256"] for item in records}, expected_hashes)
            self.assertTrue(any(item["drawing_plan_stroke_count"] > 0 for item in records))
            self.assertTrue(any(item["color_plan_stroke_count"] > 0 for item in records))

            for record in records:
                self.assertEqual(record["protocol_eligibility"], "candidate_only_not_assessed")
                project_path = data_root / record["project_path"]
                color_plan_path = data_root / record["color_plan_path"]
                self.assertTrue(project_path.is_file(), record["source"])
                self.assertTrue(color_plan_path.is_file(), record["source"])
                project = open_project(project_path)
                self.assertEqual(project.canvas, (64, 32))
                self.assertEqual(
                    len(project.json_file("drawing_plan")["strokes"]),
                    record["drawing_plan_stroke_count"],
                )
                color_plan = load_color_scanline_plan(color_plan_path)
                self.assertEqual(
                    color_plan["summary"]["stroke_count"],
                    record["color_plan_stroke_count"],
                )


if __name__ == "__main__":
    unittest.main()
