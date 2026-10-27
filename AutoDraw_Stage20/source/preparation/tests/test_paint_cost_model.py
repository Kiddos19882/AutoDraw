from __future__ import annotations

import copy
import unittest

import numpy as np

from color_scanline import ColorScanlinePlanError, build_color_scanline_plan, validate_color_scanline_plan
from paint_cost_model import (
    CALIBRATION_OBSERVATIONS,
    CALIBRATED_BUDGET_HIGH_PX_EQUIVALENT,
    CALIBRATED_BUDGET_LOW_PX_EQUIVALENT,
    DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
    DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    estimate_color_plan_paint_cost,
    estimate_paint_cost,
    fit_model_to_calibration_observations,
)


PALETTE = {
    "profile_name": "Paint cost test",
    "colors": [
        {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
        {"id": "blue", "name": "Blue", "rgb": [0, 0, 255], "hex": "#0000FF"},
    ],
}


class PaintCostModelTests(unittest.TestCase):
    def test_default_model_matches_the_four_real_observations(self):
        self.assertEqual(len(CALIBRATION_OBSERVATIONS), 4)
        fitted = fit_model_to_calibration_observations()
        self.assertAlmostEqual(fitted["stroke_overhead_px_equivalent"], 6.6738, places=3)
        self.assertAlmostEqual(fitted["paint_budget_px_equivalent"], 25648.82, places=1)
        self.assertEqual(fitted["minimum_reconstructed_budget_px_equivalent"], 25610.28)
        self.assertEqual(fitted["maximum_reconstructed_budget_px_equivalent"], 25729.89)

    def test_four_completed_observation_costs_fall_in_observed_calibration_band(self):
        for row in CALIBRATION_OBSERVATIONS:
            estimate = estimate_paint_cost(
                row["visible_path_px"], row["completed_strokes"],
                stroke_overhead_px_equivalent=DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
                paint_budget_px_equivalent=DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
            )
            total = estimate["estimated_total_ink_px_equivalent"]
            self.assertGreaterEqual(total, CALIBRATED_BUDGET_LOW_PX_EQUIVALENT - 1)
            self.assertLessEqual(total, CALIBRATED_BUDGET_HIGH_PX_EQUIVALENT + 1)

    def test_model_calculates_path_plus_per_stroke_overhead(self):
        estimate = estimate_paint_cost(1000, 100)
        self.assertEqual(estimate["effective_path_length_px"], 1000)
        self.assertEqual(estimate["estimated_stroke_overhead_px_equivalent"], 667.0)
        self.assertEqual(estimate["estimated_total_ink_px_equivalent"], 1667.0)
        self.assertAlmostEqual(estimate["estimated_usage_percent"], 1667 / 25650 * 100, places=3)
        self.assertEqual(estimate["risk_level"], "lower")

    def test_single_pixel_strokes_count_one_pixel_of_executor_path_each(self):
        estimate = estimate_paint_cost(0, 10, 10)
        self.assertEqual(estimate["single_pixel_extra_path_px"], 10.0)
        self.assertEqual(estimate["effective_path_length_px"], 10.0)
        self.assertEqual(estimate["estimated_total_ink_px_equivalent"], 76.7)

    def test_over_budget_state_is_explicit(self):
        estimate = estimate_paint_cost(30000, 100)
        self.assertEqual(estimate["risk_level"], "over_budget")
        self.assertIn("Выше", estimate["risk_label"])
        self.assertLess(estimate["estimated_remaining_px_equivalent"], 0)

    def test_zero_stroke_overhead_is_allowed_for_custom_calibration(self):
        estimate = estimate_paint_cost(100, 10, stroke_overhead_px_equivalent=0)
        self.assertEqual(estimate["estimated_total_ink_px_equivalent"], 100)

    def test_invalid_inputs_are_rejected(self):
        bad_cases = [
            (-1, 1, 0, 6.67, 25650),
            (1, -1, 0, 6.67, 25650),
            (1, 1, 2, 6.67, 25650),
            (1, 1, 0, -1, 25650),
            (1, 1, 0, 6.67, 0),
            (float("nan"), 1, 0, 6.67, 25650),
        ]
        for path, strokes, singles, overhead, budget in bad_cases:
            with self.subTest(path=path, strokes=strokes, singles=singles, overhead=overhead, budget=budget):
                with self.assertRaises(ValueError):
                    estimate_paint_cost(
                        path, strokes, singles,
                        stroke_overhead_px_equivalent=overhead,
                        paint_budget_px_equivalent=budget,
                    )

    def test_plan_uses_model_and_persists_estimate(self):
        plan = build_color_scanline_plan(
            np.asarray([[0, 0, 1]], dtype=np.int32), PALETTE,
            paint_stroke_overhead_px_equivalent=8.0,
            paint_budget_px_equivalent=100.0,
        )
        self.assertEqual(plan["generation"]["paint_cost_model"]["stroke_overhead_px_equivalent"], 8.0)
        estimate = plan["summary"]["paint_cost_estimate"]
        self.assertEqual(estimate["stroke_count"], plan["summary"]["stroke_count"])
        self.assertEqual(estimate["estimated_budget_px_equivalent"], 100.0)
        self.assertEqual(estimate["estimated_total_ink_px_equivalent"], 18.0)  # 1px drawn path + 1px singleton + 2 strokes x 8
        validate_color_scanline_plan(plan)

    def test_plan_estimator_uses_stored_summary_and_adjusts_single_pixels(self):
        plan = build_color_scanline_plan(np.asarray([[0, 1]], dtype=np.int32), PALETTE)
        estimate = estimate_color_plan_paint_cost(plan)
        self.assertEqual(estimate["stroke_count"], 2)
        self.assertEqual(estimate["single_pixel_extra_path_px"], 2.0)
        self.assertGreater(estimate["estimated_total_ink_px_equivalent"], 2 * DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT)

    def test_color_plan_reports_shared_pool_and_per_color_estimates(self):
        plan = build_color_scanline_plan(np.asarray([[0, 0, 1, 1, 1]], dtype=np.int32), PALETTE)
        estimate = plan["summary"]["paint_cost_estimate"]
        self.assertEqual(len(estimate["per_color_estimates"]), 2)
        self.assertEqual(estimate["per_color_estimates"][0]["hex"], "#FF0000")
        self.assertEqual(estimate["per_color_estimates"][0]["drawing_length_px"], 1.0)
        self.assertEqual(estimate["per_color_estimates"][1]["drawing_length_px"], 2.0)
        self.assertEqual(estimate["highest_use_color"]["hex"], "#0000FF")
        summed_per_color = sum(item["estimated_total_ink_px_equivalent"] for item in estimate["per_color_estimates"])
        self.assertAlmostEqual(summed_per_color, estimate["estimated_total_ink_px_equivalent"], places=3)

    def test_per_color_cost_includes_executor_single_pixel_expansion(self):
        plan = build_color_scanline_plan(np.asarray([[0, 1]], dtype=np.int32), PALETTE)
        estimate = plan["summary"]["paint_cost_estimate"]
        for color in estimate["per_color_estimates"]:
            self.assertEqual(color["single_pixel_stroke_count"], 1)
            self.assertEqual(color["drawing_length_px"], 0.0)
            self.assertEqual(color["estimated_total_ink_px_equivalent"], 7.67)

    def test_estimate_documents_shared_engine_point_quota_semantics(self):
        plan = build_color_scanline_plan(
            np.asarray([[0, 1, 0]], dtype=np.int32), PALETTE
        )
        estimate = plan["summary"]["paint_cost_estimate"]

        self.assertEqual(estimate["resource_basis"], "frame_sampled_unique_game_points")
        self.assertIn("shared stored-coordinate quota", estimate["resource_semantics_note"])
        self.assertIn("общая для всего рисунка", estimate["resource_scope_note"])
        self.assertEqual(len(estimate["per_color_estimates"]), 2)

    def test_tampered_cost_estimate_is_rejected(self):
        plan = build_color_scanline_plan(np.asarray([[0, 0, 1]], dtype=np.int32), PALETTE)
        tampered = copy.deepcopy(plan)
        tampered["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"] += 100
        with self.assertRaises(ColorScanlinePlanError):
            validate_color_scanline_plan(tampered)

    def test_older_plan_without_cost_model_stays_compatible(self):
        plan = build_color_scanline_plan(np.asarray([[0, 0, 1]], dtype=np.int32), PALETTE)
        old_format = copy.deepcopy(plan)
        old_format["generation"].pop("paint_cost_model")
        old_format["summary"].pop("paint_cost_estimate")
        self.assertIs(validate_color_scanline_plan(old_format), old_format)

    def test_plan_validation_rejects_missing_model_params_if_estimate_is_present(self):
        plan = build_color_scanline_plan(np.asarray([[0, 1]], dtype=np.int32), PALETTE)
        bad = copy.deepcopy(plan)
        bad["generation"].pop("paint_cost_model")
        with self.assertRaises(ColorScanlinePlanError):
            validate_color_scanline_plan(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
