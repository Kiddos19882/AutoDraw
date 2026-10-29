import unittest

from analyze_brush_experiment_series import classify_brush_setting, polyline_distance


class BrushSettingStatusTests(unittest.TestCase):
    def test_legacy_experiments_are_not_treated_as_confirmed(self):
        self.assertEqual(classify_brush_setting({}), "legacy_unverified")
        self.assertEqual(classify_brush_setting(None), "legacy_unverified")

    def test_explicit_user_confirmation_is_recognized(self):
        self.assertEqual(
            classify_brush_setting({"brush_setup": {"status": "confirmed_by_user"}}),
            "confirmed_by_user",
        )

    def test_declined_and_pending_confirmation_are_distinguished(self):
        self.assertEqual(
            classify_brush_setting({"brush_setup": {"status": "declined_by_user"}}),
            "declined_by_user",
        )
        self.assertEqual(
            classify_brush_setting({"brush_setup": {"status": "awaiting_user_confirmation"}}),
            "pending_user_confirmation",
        )


class PolylineDistanceTests(unittest.TestCase):
    def test_nearby_parallel_lines_are_compared(self):
        first = [(0.0, 0.0), (100.0, 0.0)]
        second = [(0.0, 18.0), (100.0, 18.0)]
        self.assertAlmostEqual(polyline_distance(first, second), 18.0, places=5)

    def test_perpendicular_corner_is_not_overlap_candidate(self):
        horizontal = [(0.0, 0.0), (100.0, 0.0)]
        vertical = [(100.0, 0.0), (100.0, 100.0)]
        self.assertEqual(polyline_distance(horizontal, vertical), float("inf"))

    def test_parallel_lines_without_projection_overlap_are_ignored(self):
        first = [(0.0, 0.0), (10.0, 0.0)]
        second = [(20.0, 1.0), (30.0, 1.0)]
        self.assertEqual(polyline_distance(first, second), float("inf"))


if __name__ == "__main__":
    unittest.main()
