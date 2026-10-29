from __future__ import annotations

import unittest

import numpy as np

from geometry_budget_optimizer import optimize_geometry_plan_to_budget
from geometry_color_plan import GeometryColorPlanError


PALETTE = [
    {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
    {"id": "blue", "name": "Blue", "rgb": [0, 0, 255], "hex": "#0000FF"},
]


class GeometryBudgetOptimizerTests(unittest.TestCase):
    def test_point_limited_checkerboard_reports_both_budgets_and_quality_loss(self):
        # Dense alternating pixels make stroke overhead and the point quota
        # binding constraints while leaving the paint budget deliberately loose.
        y, x = np.indices((64, 96))
        indexes = ((x + y) % 2).astype(np.int32)

        plan, report = optimize_geometry_plan_to_budget(
            indexes,
            PALETTE,
            mode="scanline",
            paint_budget_px_equivalent=100_000,
            target_usage_percent=75.0,
            stroke_overhead_px_equivalent=6.67,
            board_point_limit=3_000,
            point_safety_factor=0.85,
        )

        self.assertTrue(report["target_fits_at_scale"])
        self.assertTrue(report["fits_paint_budget"])
        self.assertTrue(report["fits_point_budget"])
        self.assertTrue(report["fits_budget"])
        self.assertFalse(report["needs_multi_board_split"])
        self.assertLessEqual(
            report["estimated_ink_after_px_equivalent"],
            report["target_cost_px_equivalent"],
        )
        self.assertLessEqual(
            report["estimated_game_points_after"],
            report["target_point_count"],
        )
        self.assertEqual(report["target_point_count"], 2_550)
        self.assertIn("quality_mismatch_pixel_count", report)
        self.assertIn("quality_pixel_accuracy_percent", report)
        self.assertIn("quality_coverage_percent", report)
        self.assertIn("quality_visible_pixel_accuracy_percent", report)
        self.assertIn("quality_uncovered_visible_pixel_count", report)
        self.assertIn("quality_painted_transparent_pixel_count", report)
        self.assertIn("quality_measure_scope", report)
        self.assertEqual(
            report["quality_measure_scope"],
            "programmatic_preview",
        )
        self.assertEqual(
            plan["generation"]["budget_optimization"]["fits_budget"],
            report["fits_budget"],
        )
        # The chosen plan should record any coarsening and its measured preview
        # mismatch rather than presenting it as lossless.
        if report["scale"] < 1.0:
            self.assertGreater(report["quality_mismatch_pixel_count"], 0)

    def test_unsupported_point_quota_is_rejected_before_candidate_search(self):
        indexes = np.asarray([[0, 1], [1, 0]], dtype=np.int32)
        with self.assertRaisesRegex(GeometryColorPlanError, "Лимит игровых точек"):
            optimize_geometry_plan_to_budget(
                indexes,
                PALETTE,
                mode="scanline",
                paint_budget_px_equivalent=10_000,
                board_point_limit=4_000,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
