from __future__ import annotations

import unittest

from engine_point_calibration import (
    DEFAULT_EXECUTOR_POINT_DELAY_MS,
    DEFAULT_EXECUTOR_POINT_STEP_PX,
    GAME_ENGINE_DEFAULT_FRAME_RATE_FPS,
    build_engine_point_calibration_report,
    estimate_point_quota_usage,
    estimate_theoretical_points_per_path_px,
)


class EnginePointCalibrationTests(unittest.TestCase):
    def test_default_executor_profile_matches_nominal_frame_sampling(self):
        self.assertEqual(GAME_ENGINE_DEFAULT_FRAME_RATE_FPS, 48.0)
        self.assertEqual(DEFAULT_EXECUTOR_POINT_STEP_PX, 2.0)
        self.assertEqual(DEFAULT_EXECUTOR_POINT_DELAY_MS, 10)
        self.assertAlmostEqual(
            estimate_theoretical_points_per_path_px(),
            0.24,
            places=6,
        )

    def test_theoretical_sampling_density_scales_with_delay_and_step(self):
        self.assertAlmostEqual(
            estimate_theoretical_points_per_path_px(point_delay_ms=20),
            0.48,
            places=6,
        )
        self.assertAlmostEqual(
            estimate_theoretical_points_per_path_px(point_step_px=4),
            0.12,
            places=6,
        )

    def test_observed_cutoffs_are_consistent_with_a_6000_point_board(self):
        report = build_engine_point_calibration_report()
        inference = report["point_limit_inference"]
        fit = report["observed_cutoff_fit"]

        self.assertEqual(report["observed_cutoff_fit"]["observation_count"], 4)
        self.assertEqual(inference["selected_limit"], 6_000)
        self.assertTrue(inference["is_inferred"])
        self.assertEqual(inference["consistency"], "strong")
        self.assertLess(inference["nearest_limit_deviation_percent"], 3.0)
        self.assertLess(fit["budget_spread_percent"], 0.5)
        self.assertLess(report["validation"]["max_abs_empirical_residual_points"], 20.0)
        self.assertFalse(report["validation"]["historic_executor_profile_was_recorded"])

    def test_explicit_calibration_board_limit_is_not_marked_as_inferred(self):
        report = build_engine_point_calibration_report(calibration_point_limit=6_000)
        self.assertEqual(report["point_limit_inference"]["selected_limit"], 6_000)
        self.assertFalse(report["point_limit_inference"]["is_inferred"])
        self.assertTrue(report["point_limit_inference"]["is_verified_from_observation_metadata"])

    def test_estimator_predicts_the_calibrated_long_stroke_observation(self):
        estimate = estimate_point_quota_usage(
            25_350,
            39,
            board_point_limit=6_000,
            safety_factor=1.0,
        )
        self.assertEqual(estimate["estimated_point_count"], 5_991)
        self.assertEqual(estimate["risk_level"], "within_budget")
        self.assertEqual(estimate["calibration_point_limit"], 6_000)
        self.assertTrue(estimate["calibration_point_limit_is_inferred"])

    def test_estimator_detects_observed_short_stroke_overrun(self):
        estimate = estimate_point_quota_usage(
            22_700,
            454,
            board_point_limit=6_000,
            safety_factor=1.0,
        )
        self.assertEqual(estimate["estimated_point_count"], 6_019)
        self.assertEqual(estimate["risk_level"], "over_limit")

    def test_estimator_scales_path_sampling_for_different_executor_timing(self):
        default = estimate_point_quota_usage(
            1_000, 100, board_point_limit=6_000, safety_factor=1.0
        )
        slower = estimate_point_quota_usage(
            1_000,
            100,
            board_point_limit=6_000,
            point_delay_ms=20,
            safety_factor=1.0,
        )
        self.assertGreater(slower["estimated_point_count"], default["estimated_point_count"])
        self.assertAlmostEqual(
            slower["points_per_path_px"],
            default["points_per_path_px"] * 2,
            places=5,
        )

    def test_estimator_handles_single_pixel_strokes(self):
        estimate = estimate_point_quota_usage(
            0,
            10,
            board_point_limit=3_000,
            single_pixel_stroke_count=10,
        )
        self.assertGreater(estimate["effective_path_length_px"], 0)
        self.assertEqual(estimate["stroke_count"], 10)
        self.assertEqual(estimate["board_point_limit"], 3_000)

    def test_invalid_estimator_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            estimate_theoretical_points_per_path_px(point_step_px=0)
        with self.assertRaises(ValueError):
            estimate_theoretical_points_per_path_px(point_delay_ms=0)
        with self.assertRaises(ValueError):
            estimate_point_quota_usage(1, 1, board_point_limit=4_000)
        with self.assertRaises(ValueError):
            estimate_point_quota_usage(-1, 1, board_point_limit=3_000)
        with self.assertRaises(ValueError):
            estimate_point_quota_usage(1, -1, board_point_limit=3_000)
        with self.assertRaises(ValueError):
            estimate_point_quota_usage(1, 1, board_point_limit=3_000, single_pixel_stroke_count=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
