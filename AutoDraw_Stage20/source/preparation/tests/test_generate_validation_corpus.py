from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
