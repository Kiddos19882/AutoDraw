import unittest

from analyze_brush_experiment_series import polyline_distance


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
