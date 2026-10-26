from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from image_processing import ProcessingSettings, process_image
from stage8_optimizer import analyze_plan, build_scanline_plan, load_json, save_plan
from stage9_quality import analyze_quality
from autodraw_project import create_project, export_drawing_plan, open_project
from models.drawing_plan import DrawingPlan


class Stage12PipelineTests(unittest.TestCase):
    def make_test_image(self) -> Image.Image:
        image = Image.new("RGB", (12, 8), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((2, 1, 8, 5), fill="black")
        draw.rectangle((4, 2, 6, 4), fill="white")
        return image

    def test_image_processing_returns_canvas_sized_outputs(self):
        source = self.make_test_image()
        result = process_image(
            source, 12, 8, "stretch", None,
            ProcessingSettings(brightness=0, contrast=1.0, denoise_level=0, threshold_mode="manual", threshold=128),
        )
        self.assertEqual(result.prepared_color.size, (12, 8))
        self.assertEqual(result.grayscale.size, (12, 8))
        self.assertEqual(result.binary_mask.size, (12, 8))
        self.assertEqual(result.binary_mask.mode, "L")
        self.assertEqual(result.fit_mode, "stretch")

    def test_crop_is_applied_before_fit(self):
        source = self.make_test_image()
        result = process_image(source, 6, 4, "stretch", (1, 1, 11, 7))
        self.assertEqual(result.prepared_color.size, (6, 4))
        self.assertEqual(result.crop_box, (1, 1, 11, 7))

    def test_invalid_crop_is_rejected(self):
        with self.assertRaises(ValueError):
            process_image(self.make_test_image(), 12, 8, "stretch", (0, 0, 0, 2))

    def test_scanline_plan_uses_stage6_canvas_schema(self):
        mask = Image.new("L", (8, 5), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((1, 1, 4, 1), fill=0)
        draw.rectangle((6, 3, 6, 3), fill=0)
        plan = build_scanline_plan(mask, row_step_px=1, threshold=127, foreground="dark")
        self.assertEqual(plan["canvas"], {"width": 8, "height": 5})
        self.assertIn("created_at", plan)
        self.assertEqual(plan["coordinate_system"], "local_canvas_pixels")
        self.assertGreaterEqual(len(plan["strokes"]), 2)
        for stroke in plan["strokes"]:
            self.assertGreaterEqual(len(stroke["points"]), 2)
            self.assertTrue(stroke["name"])

    def test_scanline_row_step_skips_rows_without_reordering(self):
        mask = Image.new("L", (8, 6), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((1, 1, 4, 1), fill=0)
        draw.rectangle((1, 2, 4, 2), fill=0)
        draw.rectangle((1, 3, 4, 3), fill=0)
        plan = build_scanline_plan(mask, row_step_px=2, threshold=127, foreground="dark")
        rows = [int(stroke["metadata"]["row_y"]) for stroke in plan["strokes"]]
        self.assertEqual(rows, sorted(rows))
        self.assertTrue(all(row % 2 == 0 for row in rows))

    def test_quality_report_is_calculated_for_plan(self):
        mask = Image.new("L", (6, 3), 255)
        ImageDraw.Draw(mask).rectangle((1, 1, 4, 1), fill=0)
        plan = build_scanline_plan(mask, row_step_px=1, threshold=127, foreground="dark")
        report, source, rendered, difference = analyze_quality(mask, plan, threshold=127, foreground="dark")
        self.assertTrue(report.dimensions_match)
        self.assertEqual(report.width, 6)
        self.assertEqual(report.height, 3)
        self.assertGreater(report.matched_pixels, 0)
        self.assertEqual(source.size, rendered.size)
        self.assertEqual(difference.size, source.size)

    def test_quality_rejects_different_dimensions(self):
        mask = Image.new("L", (6, 3), 255)
        plan = build_scanline_plan(Image.new("L", (5, 3), 255), row_step_px=1)
        with self.assertRaises(ValueError):
            analyze_quality(mask, plan)

    def test_empty_mask_has_no_drawing_strokes(self):
        mask = Image.new("L", (4, 4), 255)
        plan = build_scanline_plan(mask)
        self.assertEqual(plan["strokes"], [])
        self.assertEqual(analyze_plan(plan).stroke_count, 0)


class Stage12ProjectIntegrationTests(unittest.TestCase):
    def test_project_roundtrip_and_stage6_json_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            mask_path = root / "mask.png"
            plan_path = root / "plan.json"
            project_path = root / "sample.autodraw"
            exported = root / "exported_stage6.json"
            metadata_path = root / "processing_result.json"
            color_path = root / "prepared_color.png"
            gray_path = root / "grayscale.png"

            original = Image.new("RGB", (10, 6), "white")
            ImageDraw.Draw(original).rectangle((2, 2, 7, 3), fill="black")
            original.save(source)
            processed = process_image(original, 10, 6, "stretch")
            processed.binary_mask.save(mask_path)
            processed.prepared_color.save(color_path)
            processed.grayscale.save(gray_path)
            plan = build_scanline_plan(processed.binary_mask, row_step_px=1, threshold=127, foreground="dark")
            save_plan(plan_path, plan)
            metadata = {
                "schema_version": 1,
                "fit_mode": "stretch",
                "crop_box_original_pixels": None,
                "settings": {
                    "brightness": 0,
                    "contrast": 1.0,
                    "denoise_level": 0,
                    "threshold_mode": "otsu",
                    "requested_threshold": 128,
                    "threshold_used": processed.threshold_used,
                },
            }
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            created = create_project(
                project_path, source, mask_path, plan_path,
                project_name="Stage 12 integration",
                processing_metadata_path=metadata_path,
                prepared_color_path=color_path,
                grayscale_path=gray_path,
            )
            self.assertTrue(created.exists())
            bundle = open_project(created)
            self.assertEqual(bundle.name, "Stage 12 integration")
            self.assertEqual(bundle.canvas, (10, 6))
            self.assertIn("binary_mask", bundle.manifest["files"])
            self.assertIn("quality_report", bundle.manifest["files"])

            exported_path = export_drawing_plan(created, exported)
            self.assertTrue(exported_path.exists())
            loaded_dict = load_json(exported_path)
            self.assertEqual(loaded_dict["canvas"], {"width": 10, "height": 6})
            # Uses the same DrawingPlan model copied from the tested Stage 6 package.
            loaded_model = DrawingPlan.load(exported_path)
            self.assertEqual((loaded_model.width, loaded_model.height), (10, 6))
            self.assertGreater(loaded_model.stroke_count, 0)

    def test_plan_export_is_stage6_model_loadable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            mask = Image.new("L", (7, 4), 255)
            ImageDraw.Draw(mask).rectangle((1, 2, 5, 2), fill=0)
            plan = build_scanline_plan(mask, row_step_px=1)
            output = root / "plan.json"
            save_plan(output, plan)
            loaded = DrawingPlan.load(output)
            self.assertEqual(loaded.width, 7)
            self.assertEqual(loaded.height, 4)
            self.assertEqual(loaded.stroke_count, 1)

    def test_project_rejects_plan_mask_dimension_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.png"
            mask_path = root / "mask.png"
            plan_path = root / "plan.json"
            target = root / "bad.autodraw"
            Image.new("RGB", (8, 6), "white").save(source)
            Image.new("L", (8, 6), 255).save(mask_path)
            plan = build_scanline_plan(Image.new("L", (7, 6), 0))
            # Make the plan nonempty and Stage 6 compatible, but intentionally wrong dimensions.
            save_plan(plan_path, plan)
            with self.assertRaises(ValueError):
                create_project(target, source, mask_path, plan_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
