from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from palette_quantization import PaletteQuantizationResult
from paint_budget_optimizer import PaintBudgetOptimizationError, fit_result_to_paint_budget


PALETTE = {
    "profile_name": "Budget optimizer test",
    "colors": [
        {"id": "black", "name": "Black", "rgb": [0, 0, 0], "hex": "#000000"},
        {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
        {"id": "green", "name": "Green", "rgb": [0, 255, 0], "hex": "#00FF00"},
        {"id": "blue", "name": "Blue", "rgb": [0, 0, 255], "hex": "#0000FF"},
        {"id": "white", "name": "White", "rgb": [255, 255, 255], "hex": "#FFFFFF"},
    ],
}


def make_result(index_map: np.ndarray) -> PaletteQuantizationResult:
    height, width = index_map.shape
    image = Image.new("RGB", (width, height), "white")
    return PaletteQuantizationResult(
        image=image,
        index_map=np.asarray(index_map, dtype=np.int32),
        report={"source_size": {"width": width, "height": height}, "used_palette_color_count": 5},
    )


class PaintBudgetOptimizerTests(unittest.TestCase):
    def test_already_fitting_plan_keeps_map_and_uses_every_row(self):
        indexes = np.asarray([[0, 0, 1, 1], [2, 2, 3, 3]], dtype=np.int32)
        result, step, offset, report = fit_result_to_paint_budget(
            make_result(indexes), PALETTE, paint_budget_px_equivalent=1000,
            target_usage_percent=75,
        )
        np.testing.assert_array_equal(result.index_map, indexes)
        self.assertEqual((step, offset), (1, 0))
        self.assertLessEqual(report["estimated_ink_after_px_equivalent"], report["target_cost_px_equivalent"])
        self.assertEqual(report["changed_pixel_count"], 0)

    def test_complex_map_is_reduced_to_target_budget_with_fixed_dimensions(self):
        height, width = 48, 80
        y, x = np.indices((height, width))
        indexes = ((x // 2 + y // 2) % 5).astype(np.int32)
        result, step, offset, report = fit_result_to_paint_budget(
            make_result(indexes), PALETTE, paint_budget_px_equivalent=12000,
            target_usage_percent=75,
        )
        self.assertEqual(result.index_map.shape, indexes.shape)
        self.assertEqual(result.image.size, (width, height))
        self.assertLessEqual(report["estimated_ink_after_px_equivalent"], report["target_cost_px_equivalent"])
        self.assertLess(report["stroke_count_after"], report["stroke_count_before"])
        self.assertGreaterEqual(step, 1)
        self.assertGreaterEqual(offset, 0)
        self.assertLess(offset, step)
        self.assertTrue(report["enabled"])

    def test_transparent_top_rows_do_not_force_an_empty_plan(self):
        indexes = np.full((24, 40), -1, dtype=np.int32)
        indexes[14:24, 5:35] = 1
        result, step, offset, report = fit_result_to_paint_budget(
            make_result(indexes), PALETTE, paint_budget_px_equivalent=300,
            target_usage_percent=75,
        )
        self.assertGreater(np.count_nonzero(result.index_map >= 0), 0)
        self.assertLessEqual(report["estimated_ink_after_px_equivalent"], report["target_cost_px_equivalent"])
        self.assertTrue(0 <= offset < step)

    def test_output_preserves_partial_alpha_for_visible_pixels(self):
        indexes = np.asarray([[0, 1, -1]], dtype=np.int32)
        image = Image.new("RGBA", (3, 1), (0, 0, 0, 255))
        image.putpixel((0, 0), (0, 0, 0, 120))
        image.putpixel((1, 0), (255, 0, 0, 255))
        image.putpixel((2, 0), (255, 255, 255, 0))
        result = PaletteQuantizationResult(
            image=image,
            index_map=indexes,
            report={"source_size": {"width": 3, "height": 1}},
        )
        fitted, step, offset, report = fit_result_to_paint_budget(
            result, PALETTE, paint_budget_px_equivalent=1000, target_usage_percent=75,
        )
        self.assertEqual(fitted.image.getpixel((0, 0))[3], 120)
        self.assertEqual(fitted.image.getpixel((1, 0))[3], 255)
        self.assertEqual(fitted.image.getpixel((2, 0))[3], 0)
        self.assertEqual((step, offset), (1, 0))

    def test_rejects_fully_transparent_map(self):
        indexes = np.full((8, 8), -1, dtype=np.int32)
        with self.assertRaises(PaintBudgetOptimizationError):
            fit_result_to_paint_budget(make_result(indexes), PALETTE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
