from __future__ import annotations

import unittest

from board_resource_model import (
    BOARD_ITEM_POINT_LIMITS,
    DEFAULT_POINT_SAFETY_FACTOR,
    MODEL_ID,
    STANDARD_BRUSH_PRESETS,
    create_board_resource_profile,
    estimate_calibrated_point_usage,
    get_board_point_limit,
)


class BoardResourceModelTests(unittest.TestCase):
    def test_engine_item_classes_map_to_known_point_quotas(self):
        self.assertEqual(get_board_point_limit("BoardItem0"), 3_000)
        self.assertEqual(get_board_point_limit("BoardItem1"), 6_000)
        self.assertEqual(get_board_point_limit("BoardItem2"), 6_000)
        self.assertEqual(get_board_point_limit("BoardItem3"), 12_000)
        self.assertEqual(get_board_point_limit("BoardItem4"), 12_000)
        self.assertEqual(len(BOARD_ITEM_POINT_LIMITS), 5)

    def test_unknown_engine_type_is_not_guessed(self):
        with self.assertRaisesRegex(ValueError, "Неизвестный тип доски"):
            get_board_point_limit("BoardItem5")

    def test_default_profiles_keep_a_fifteen_percent_reserve(self):
        expected = {3_000: 2_550, 6_000: 5_100, 12_000: 10_200}
        self.assertEqual(DEFAULT_POINT_SAFETY_FACTOR, 0.85)
        for limit, planning_budget in expected.items():
            with self.subTest(limit=limit):
                profile = create_board_resource_profile(limit)
                self.assertEqual(profile["model_id"], MODEL_ID)
                self.assertEqual(profile["point_limit"], limit)
                self.assertEqual(profile["planning_budget_points"], planning_budget)
                self.assertEqual(profile["reserved_points"], limit - planning_budget)
                self.assertTrue(profile["calibration_required_for_point_estimate"])

    def test_standard_brush_values_are_in_game_button_order(self):
        self.assertEqual(
            [(preset["id"], preset["value"]) for preset in STANDARD_BRUSH_PRESETS],
            [("large", 20), ("medium", 14), ("small", 7)],
        )
        # Returning a profile must not expose the module's shared preset dictionaries.
        profile = create_board_resource_profile(3_000)
        profile["standard_brushes"][0]["value"] = 1
        self.assertEqual(STANDARD_BRUSH_PRESETS[0]["value"], 20)

    def test_point_estimate_counts_path_samples_and_one_start_point_per_stroke(self):
        estimate = estimate_calibrated_point_usage(
            [10, 20, 0], points_per_path_px=0.5, max_points=12_000
        )
        # ceil(5) + ceil(10) + ceil(0) sampled points, plus three stroke starts.
        self.assertEqual(estimate["estimated_path_sample_points"], 15)
        self.assertEqual(estimate["estimated_stroke_start_points"], 3)
        self.assertEqual(estimate["estimated_point_count"], 18)
        self.assertEqual(estimate["risk_level"], "within_budget")
        self.assertEqual(estimate["point_limit"], 12_000)
        self.assertTrue(estimate["is_calibrated_estimate"])

    def test_estimate_warns_before_hard_limit_is_reached(self):
        estimate = estimate_calibrated_point_usage(
            [10_299], points_per_path_px=1.0, max_points=12_000
        )
        self.assertEqual(estimate["estimated_point_count"], 10_300)
        self.assertEqual(estimate["risk_level"], "near_limit")
        self.assertLess(estimate["estimated_point_count"], estimate["point_limit"])

    def test_estimate_reports_hard_limit_overrun(self):
        estimate = estimate_calibrated_point_usage(
            [12_000], points_per_path_px=1.0, max_points=12_000
        )
        self.assertEqual(estimate["estimated_point_count"], 12_001)
        self.assertEqual(estimate["risk_level"], "over_limit")

    def test_invalid_profiles_and_calibration_are_rejected(self):
        bad_profiles = [True, 0, -1, 2_000, 13_000, 3_000.0]
        for limit in bad_profiles:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                create_board_resource_profile(limit)

        bad_densities = [True, 0, -0.1, float("nan"), float("inf")]
        for density in bad_densities:
            with self.subTest(density=density), self.assertRaises(ValueError):
                estimate_calibrated_point_usage(
                    [1], points_per_path_px=density, max_points=3_000
                )

        with self.assertRaises(ValueError):
            estimate_calibrated_point_usage(
                [-1], points_per_path_px=0.5, max_points=3_000
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
