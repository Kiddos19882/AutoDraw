from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from color_scanline import build_color_scanline_plan, validate_color_scanline_plan
from paint_budget_optimizer import fit_result_to_paint_budget
from paint_cost_model import DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT
from palette_quantization import PaletteQuantizationResult


PALETTE = {
    "profile_name": "Optimizer end-to-end stress test",
    "colors": [
        {"id": "black", "name": "Black", "rgb": [0, 0, 0], "hex": "#000000"},
        {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
        {"id": "green", "name": "Green", "rgb": [0, 255, 0], "hex": "#00FF00"},
        {"id": "blue", "name": "Blue", "rgb": [0, 0, 255], "hex": "#0000FF"},
        {"id": "white", "name": "White", "rgb": [255, 255, 255], "hex": "#FFFFFF"},
    ],
}


def _result_for(index_map: np.ndarray) -> PaletteQuantizationResult:
    indexes = np.asarray(index_map, dtype=np.int32)
    height, width = indexes.shape
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = np.where(indexes >= 0, 255, 0).astype(np.uint8)
    return PaletteQuantizationResult(
        image=Image.fromarray(rgba),
        index_map=indexes,
        report={"source_size": {"width": width, "height": height}},
    )


def _stress_maps() -> dict[str, np.ndarray]:
    height, width = 40, 80
    y, x = np.indices((height, width))
    random = np.random.default_rng(2026).integers(0, 5, size=(height, width), dtype=np.int32)

    checkerboard = ((x + y) % 2).astype(np.int32)
    vertical_stripes = ((x // 2 + y // 3) % 5).astype(np.int32)
    noisy = random
    transparent_height, transparent_width = 100, 160
    transparent_y, transparent_x = np.indices((transparent_height, transparent_width))
    transparent_noise = np.random.default_rng(2027).integers(
        0, 5, size=(transparent_height, transparent_width), dtype=np.int32
    )
    transparent_noise[(transparent_x + 2 * transparent_y) % 7 < 3] = -1

    # A mostly visible checkerboard with sparse transparent holes forces block
    # optimization to choose a visible color around some transparent pixels.
    transparent_checkerboard = ((transparent_x + transparent_y) % 2).astype(np.int32)
    transparent_checkerboard[(transparent_x * 13 + transparent_y * 7) % 19 == 0] = -1

    thin_detail = np.full((height, width), -1, dtype=np.int32)
    thin_detail[19, 2:78] = (np.arange(76, dtype=np.int32) // 2) % 5
    thin_detail[20, 10:70] = 0

    return {
        "checkerboard": checkerboard,
        "vertical_stripes": vertical_stripes,
        "noisy_palette": noisy,
        "transparent_noise": transparent_noise,
        "transparent_checkerboard": transparent_checkerboard,
        "thin_detail": thin_detail,
    }


class OptimizerEndToEndTests(unittest.TestCase):
    def test_optimizer_output_rebuilds_into_a_plan_that_keeps_both_budgets(self):
        paint_budget = 100_000
        target_percent = 75.0

        for case_name, source_indexes in _stress_maps().items():
            with self.subTest(case=case_name):
                optimized, row_step, row_offset, report = fit_result_to_paint_budget(
                    _result_for(source_indexes),
                    PALETTE,
                    paint_budget_px_equivalent=paint_budget,
                    target_usage_percent=target_percent,
                )

                self.assertTrue(report["game_point_constraint_applied"])
                self.assertTrue(report["game_point_target_met"])
                self.assertLessEqual(
                    report["estimated_game_points_after"],
                    report["target_point_count"],
                )
                self.assertLessEqual(
                    report["estimated_ink_after_px_equivalent"],
                    report["target_cost_px_equivalent"],
                )
                self.assertEqual(optimized.index_map.shape, source_indexes.shape)
                self.assertEqual(
                    (optimized.image.width, optimized.image.height),
                    (source_indexes.shape[1], source_indexes.shape[0]),
                )
                # Transparent input remains transparent in the executable index map.
                self.assertTrue(np.all(optimized.index_map[source_indexes < 0] == -1))
                self.assertGreaterEqual(row_step, 1)
                self.assertGreaterEqual(row_offset, 0)
                self.assertLess(row_offset, row_step)

                # Rebuild exactly what the UI hands onward after optimization.
                plan = build_color_scanline_plan(
                    optimized.index_map,
                    PALETTE,
                    source_report=optimized.report,
                    row_step_px=row_step,
                    row_offset_px=row_offset,
                    paint_stroke_overhead_px_equivalent=DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
                    paint_budget_px_equivalent=paint_budget,
                    plan_name="End-to-end optimizer regression",
                )
                validate_color_scanline_plan(plan)

                final_points = plan["summary"]["point_quota_estimate"]
                final_ink = plan["summary"]["paint_cost_estimate"]
                self.assertEqual(
                    final_points["estimated_point_count"],
                    report["estimated_game_points_after"],
                )
                self.assertEqual(
                    final_ink["estimated_total_ink_px_equivalent"],
                    report["estimated_ink_after_px_equivalent"],
                )
                self.assertLessEqual(final_points["estimated_point_count"], report["target_point_count"])
                self.assertLessEqual(final_ink["estimated_total_ink_px_equivalent"], report["target_cost_px_equivalent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
