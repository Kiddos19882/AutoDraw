from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from color_scanline import (
    COLOR_SCANLINE_PLAN_TYPE,
    ColorScanlinePlanError,
    build_color_scanline_plan,
    load_color_scanline_plan,
    render_color_scanline_preview,
    save_color_scanline_plan,
    validate_color_scanline_plan,
)


PALETTE = {
    "profile_name": "Unit test palette",
    "colors": [
        {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
        {"id": "green", "name": "Green", "rgb": [0, 255, 0], "hex": "#00FF00"},
        {"id": "blue", "name": "Blue", "rgb": [0, 0, 255], "hex": "#0000FF"},
    ],
}


class ColorScanlinePlanTests(unittest.TestCase):
    def build(self, values, **kwargs):
        return build_color_scanline_plan(np.asarray(values, dtype=np.int32), PALETTE, **kwargs)

    def test_builds_segments_in_top_down_then_left_to_right_order(self):
        plan = self.build([
            [0, 0, 1, 1],
            [2, -1, 2, 2],
            [1, 1, 1, 0],
        ])
        coords = [
            (s["points"][0]["y"], s["points"][0]["x"], s["points"][1]["x"], s["color"]["palette_index"])
            for s in plan["strokes"]
        ]
        self.assertEqual(coords, [
            (0.0, 0.0, 1.0, 0), (0.0, 2.0, 3.0, 1),
            (1.0, 0.0, 0.0, 2), (1.0, 2.0, 3.0, 2),
            (2.0, 0.0, 2.0, 1), (2.0, 3.0, 3.0, 0),
        ])

    def test_merges_only_contiguous_pixels_with_same_palette_index(self):
        plan = self.build([[0, 0, 0, 1, 1, 0, 0]])
        self.assertEqual([(s["metadata"]["x_start"], s["metadata"]["x_end"], s["color"]["palette_index"])
                          for s in plan["strokes"]], [(0, 2, 0), (3, 4, 1), (5, 6, 0)])

    def test_transparency_splits_same_color_into_two_runs(self):
        plan = self.build([[0, 0, -1, 0, 0]])
        self.assertEqual(len(plan["strokes"]), 2)
        self.assertEqual(plan["summary"]["visible_pixel_count"], 4)
        self.assertEqual(plan["summary"]["transparent_pixel_count"], 1)

    def test_single_pixel_is_preserved_without_crossing_adjacent_color(self):
        plan = self.build([[0, 1, 2]])
        self.assertEqual(len(plan["strokes"]), 3)
        for stroke in plan["strokes"]:
            self.assertEqual(stroke["points"][0], stroke["points"][1])
            self.assertTrue(stroke["metadata"]["single_pixel"])
        self.assertEqual(plan["summary"]["single_pixel_stroke_count"], 3)

    def test_color_switch_count_tracks_ordered_transitions(self):
        plan = self.build([[0, 0, 1, 1, 0, 0, 0]])
        self.assertEqual(plan["summary"]["color_switch_count"], 2)
        self.assertEqual(plan["summary"]["color_selection_count_estimate"], 3)

    def test_summary_pixel_counts_equal_the_nontransparent_index_map(self):
        values = [[0, 0, -1, 2], [1, 1, 2, -1]]
        plan = self.build(values)
        self.assertEqual(sum(c["pixel_count"] for c in plan["summary"]["used_colors"]), 6)
        self.assertEqual(plan["summary"]["visible_pixel_count"], 6)
        self.assertEqual(plan["summary"]["stroke_count"], len(plan["strokes"]))
        self.assertEqual(plan["summary"]["point_count"], 2 * len(plan["strokes"]))

    def test_plan_records_canvas_source_and_generation_rule(self):
        plan = self.build([[0, 1]], source_name="sample.png", source_report={"mean_delta_e_2000": 1.25})
        self.assertEqual(plan["plan_type"], COLOR_SCANLINE_PLAN_TYPE)
        self.assertEqual(plan["canvas"], {"width": 2, "height": 1})
        self.assertEqual(plan["source"]["name"], "sample.png")
        self.assertEqual(plan["source"]["mean_delta_e_2000"], 1.25)
        self.assertEqual(plan["generation"]["row_order"], "top_to_bottom")
        self.assertEqual(plan["generation"]["stroke_order"], "left_to_right_within_row")

    def test_rejects_non_2d_index_map(self):
        with self.assertRaises(ColorScanlinePlanError):
            build_color_scanline_plan(np.asarray([0, 1]), PALETTE)

    def test_rejects_non_integer_index_map(self):
        with self.assertRaises(ColorScanlinePlanError):
            build_color_scanline_plan(np.asarray([[0.0, 1.0]]), PALETTE)

    def test_rejects_palette_index_outside_palette(self):
        with self.assertRaises(ColorScanlinePlanError):
            build_color_scanline_plan(np.asarray([[0, 3]], dtype=np.int32), PALETTE)

    def test_rejects_empty_transparent_image(self):
        with self.assertRaisesRegex(ColorScanlinePlanError, "нет непрозрачных"):
            build_color_scanline_plan(np.asarray([[-1, -1]], dtype=np.int32), PALETTE)

    def test_rejects_duplicate_palette_colors(self):
        palette = {"colors": [PALETTE["colors"][0], {**PALETTE["colors"][0], "id": "duplicate"}]}
        with self.assertRaises(ColorScanlinePlanError):
            build_color_scanline_plan(np.asarray([[0]], dtype=np.int32), palette)

    def test_rejects_nonpositive_stroke_limit(self):
        with self.assertRaises(ColorScanlinePlanError):
            build_color_scanline_plan(np.asarray([[0]], dtype=np.int32), PALETTE, max_strokes=0)

    def test_rejects_plan_over_stroke_limit(self):
        with self.assertRaisesRegex(ColorScanlinePlanError, "лимит 1 штрихов"):
            build_color_scanline_plan(np.asarray([[0, 1, 0]], dtype=np.int32), PALETTE, max_strokes=1)

    def test_rejects_out_of_order_or_overlapping_strokes(self):
        plan = self.build([[0, 1, 2]])
        plan["strokes"][1], plan["strokes"][2] = plan["strokes"][2], plan["strokes"][1]
        with self.assertRaisesRegex(ColorScanlinePlanError, "Порядок штрихов нарушен"):
            validate_color_scanline_plan(plan)

    def test_rejects_mismatching_stroke_color(self):
        plan = self.build([[0, 0]])
        plan["strokes"][0]["color"]["hex"] = "#00FF00"
        with self.assertRaisesRegex(ColorScanlinePlanError, "не совпадает"):
            validate_color_scanline_plan(plan)

    def test_rejects_modified_geometry_when_summary_is_stale(self):
        plan = self.build([[0, 0, 0]])
        plan["strokes"][0]["points"][1]["x"] = 1.0
        with self.assertRaises(ColorScanlinePlanError):
            validate_color_scanline_plan(plan)

    def test_save_and_load_round_trip(self):
        plan = self.build([[0, 0, 1], [2, -1, 2]])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "color-plan.json"
            saved = save_color_scanline_plan(path, plan)
            loaded = load_color_scanline_plan(saved)
        self.assertEqual(loaded["strokes"], plan["strokes"])
        self.assertEqual(loaded["summary"], plan["summary"])

    def test_save_does_not_overwrite_existing_plan_when_validation_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "color-plan.json"
            path.write_text("keep", encoding="utf-8")
            invalid = {"plan_type": "bad"}
            with self.assertRaises(ColorScanlinePlanError):
                save_color_scanline_plan(path, invalid)
            self.assertEqual(path.read_text(encoding="utf-8"), "keep")

    def test_load_rejects_bad_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ColorScanlinePlanError):
                load_color_scanline_plan(path)

    def test_preview_uses_each_stroke_palette_color(self):
        plan = self.build([[0, 1]])
        preview = render_color_scanline_preview(plan)
        self.assertEqual(preview.mode, "RGBA")
        self.assertEqual(preview.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(preview.getpixel((1, 0)), (0, 255, 0, 255))

    def test_preview_has_transparent_background_for_skipped_pixels(self):
        plan = self.build([[0, -1, 1]])
        preview = render_color_scanline_preview(plan)
        self.assertEqual(preview.getpixel((1, 0))[3], 0)



    def test_row_offset_can_start_sampling_after_transparent_top_rows(self):
        plan = self.build(
            [[-1, -1, -1], [-1, -1, -1], [0, 0, 0], [0, 1, 1], [-1, -1, -1]],
            row_step_px=3,
            row_offset_px=2,
        )
        self.assertEqual(plan["generation"]["row_step_px"], 3)
        self.assertEqual(plan["generation"]["row_offset_px"], 2)
        self.assertEqual(sorted({int(stroke["points"][0]["y"]) for stroke in plan["strokes"]}), [2])
        self.assertEqual(plan["summary"]["visible_pixel_count"], 3)
        validate_color_scanline_plan(plan)

    def test_rejects_invalid_row_offset(self):
        for step, offset in ((1, 1), (3, -1), (3, 3), (2, True)):
            with self.subTest(step=step, offset=offset), self.assertRaises(ColorScanlinePlanError):
                self.build([[0, 0], [1, 1], [0, 0]], row_step_px=step, row_offset_px=offset)

    def test_row_step_two_draws_only_even_rows_and_counts_skipped_visible_pixels(self):
        values = [
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [2, -1, 2, 2],
            [0, 0, 0, 0],
        ]
        plan = self.build(values, row_step_px=2)
        self.assertEqual(plan["generation"]["row_step_px"], 2)
        self.assertEqual(sorted({int(stroke["points"][0]["y"]) for stroke in plan["strokes"]}), [0, 2])
        summary = plan["summary"]
        self.assertEqual(summary["visible_pixel_count"], 7)
        self.assertEqual(summary["source_visible_pixel_count"], 15)
        self.assertEqual(summary["omitted_by_row_step_pixel_count"], 8)
        self.assertEqual(summary["transparent_pixel_count"], 1)
        self.assertEqual(summary["source_visible_pixel_count"],
                         summary["visible_pixel_count"] + summary["omitted_by_row_step_pixel_count"])

    def test_row_step_survives_save_load(self):
        plan = self.build([[0, 0], [1, 1], [2, 2], [0, 0]], row_step_px=3)
        with tempfile.TemporaryDirectory() as temp:
            path = save_color_scanline_plan(Path(temp) / "step3.json", plan)
            loaded = load_color_scanline_plan(path)
        self.assertEqual(loaded["generation"]["row_step_px"], 3)
        self.assertEqual([int(stroke["points"][0]["y"]) for stroke in loaded["strokes"]], [0, 3])
        self.assertEqual(loaded["summary"]["omitted_by_row_step_pixel_count"], 4)

    def test_rejects_invalid_row_step(self):
        for step in (0, -1, True, 1.5):
            with self.subTest(step=step), self.assertRaises(ColorScanlinePlanError):
                self.build([[0, 1]], row_step_px=step)

    def test_validator_rejects_stroke_on_row_skipped_by_step(self):
        plan = self.build([[0], [0], [0]], row_step_px=2)
        plan["strokes"][1]["points"][0]["y"] = 1.0
        plan["strokes"][1]["points"][1]["y"] = 1.0
        plan["strokes"][1]["metadata"]["row_y"] = 1
        with self.assertRaisesRegex(ColorScanlinePlanError, "пропущенной шагом"):
            validate_color_scanline_plan(plan)

    def test_default_row_step_one_preserves_all_original_pixels(self):
        plan = self.build([[0, 1], [2, -1]])
        self.assertEqual(plan["generation"]["row_step_px"], 1)
        self.assertEqual(plan["summary"]["visible_pixel_count"], 3)
        self.assertEqual(plan["summary"]["source_visible_pixel_count"], 3)
        self.assertEqual(plan["summary"]["omitted_by_row_step_pixel_count"], 0)
        self.assertEqual(plan["summary"]["transparent_pixel_count"], 1)

    def test_plan_records_rare_color_optimization_summary(self):
        index_map = np.asarray([[0, 0, 1, 0]], dtype=np.int32)
        merge = {
            "enabled": True,
            "min_pixel_count": 20,
            "min_percentage": 0.05,
            "max_delta_e_2000": 8.0,
            "rare_color_count_merged": 2,
            "remapped_pixel_count": 7,
            "estimated_scanline_strokes_before": 9,
            "estimated_scanline_strokes_after": 4,
            "estimated_scanline_strokes_reduced": 5,
        }
        plan = build_color_scanline_plan(
            index_map, PALETTE,
            source_report={"rare_color_merge": merge},
        )
        self.assertEqual(plan["source"]["rare_color_merge"]["remapped_pixel_count"], 7)
        self.assertEqual(plan["source"]["rare_color_merge"]["estimated_scanline_strokes_reduced"], 5)

if __name__ == "__main__":
    unittest.main(verbosity=2)
