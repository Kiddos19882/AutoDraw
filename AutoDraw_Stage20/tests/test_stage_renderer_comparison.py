import unittest
import numpy as np

from compare_stage_renderer_reference import (
    derive_stage_canvas_origin,
    predict_board_screen_origin,
    validate_board_origin_crosscheck,
    mask_metrics,
    build_change_mask,
    parse_css_matrix,
)


class StageRendererComparisonTests(unittest.TestCase):
    def test_stage_origin_uses_same_run_client_to_screen_offset(self):
        origin = derive_stage_canvas_origin(
            {"left": 0.0, "top": -0.5}, {"x": 0.0, "y": 163.0}
        )
        self.assertEqual(origin, {"x": 0.0, "y": 162.5})

    def test_same_run_css_transform_matches_independent_board_origin(self):
        origin = {"x": 0.0, "y": 162.5}
        placement = {"x": 1022.3749980926514, "y": 216.0}
        matrix = parse_css_matrix("matrix(0.487062, 0, 0, 0.487778, 0, 0)")
        predicted = predict_board_screen_origin(origin, placement, matrix)
        result = validate_board_origin_crosscheck(
            predicted, {"x": 498.0, "y": 267.8600712527889}, tolerance_px=1.0
        )
        self.assertTrue(result["passed"])
        self.assertAlmostEqual(predicted["x"], 497.960011321003, places=8)
        self.assertAlmostEqual(predicted["y"], 267.860048, places=8)

    def test_mask_metrics_count_overlap_and_symmetric_difference(self):
        observed = np.array([[1, 1, 1, 0]], dtype=bool)
        expected = np.array([[1, 0, 0, 1]], dtype=bool)
        metrics = mask_metrics(observed, expected)
        self.assertEqual(metrics["true_positive"], 1)
        self.assertEqual(metrics["false_positive"], 2)
        self.assertEqual(metrics["false_negative"], 1)
        self.assertEqual(metrics["symmetric_difference_pixels"], 3)
        self.assertAlmostEqual(metrics["iou"], 0.25)
        self.assertEqual(metrics["observed_bbox_xywh"], [0, 0, 3, 1])
        self.assertEqual(metrics["expected_bbox_xywh"], [0, 0, 4, 1])

    def test_rgb_change_mask_uses_explicit_common_baseline_and_strict_threshold(self):
        baseline = np.zeros((1, 2, 3), dtype=np.uint8)
        candidate = np.array([[[25, 25, 25], [24, 24, 24]]], dtype=np.uint8)
        mask = build_change_mask(candidate, baseline, threshold=24)
        self.assertEqual(mask.tolist(), [[True, False]])

    def test_rgb_change_mask_rejects_different_image_dimensions(self):
        with self.assertRaises(ValueError):
            build_change_mask(
                np.zeros((2, 2, 3), dtype=np.uint8),
                np.zeros((2, 3, 3), dtype=np.uint8),
                threshold=24,
            )

    def test_rejects_non_axis_aligned_css_transform(self):
        with self.assertRaises(ValueError):
            parse_css_matrix("matrix(0.5, 0.01, 0, 0.5, 0, 0)")


if __name__ == "__main__":
    unittest.main()
