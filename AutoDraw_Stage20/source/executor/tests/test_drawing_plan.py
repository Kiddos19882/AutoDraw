import unittest

from models import DrawingPlan, Point, Stroke
from path_planning.test_shape import create_test_shape


class DrawingPlanTests(unittest.TestCase):
    def test_plan_has_expected_stroke_types(self):
        plan = create_test_shape(646, 323)
        self.assertEqual(plan.stroke_count, 12)
        self.assertTrue(any(stroke.closed for stroke in plan.strokes))
        self.assertTrue(any(len(stroke.points) > 2 and not stroke.closed for stroke in plan.strokes))
        self.assertGreater(plan.total_drawing_length_px, 0)
        self.assertGreater(plan.pen_up_distance_px, 0)

    def test_all_points_inside_canvas(self):
        plan = create_test_shape(646, 323)
        plan.validate_bounds()
        for stroke in plan.strokes:
            for point in stroke.points:
                self.assertGreaterEqual(point.x, 0)
                self.assertLessEqual(point.x, plan.width)
                self.assertGreaterEqual(point.y, 0)
                self.assertLessEqual(point.y, plan.height)

    def test_closed_stroke_includes_closing_edge_in_length(self):
        stroke = Stroke("square", [Point(0, 0), Point(10, 0), Point(10, 10), Point(0, 10)], closed=True)
        self.assertAlmostEqual(stroke.length_px, 40.0)

    def test_plan_json_round_trip(self):
        original = create_test_shape(646, 323)
        loaded = DrawingPlan.from_dict(original.to_dict())
        self.assertEqual(loaded.stroke_count, original.stroke_count)
        self.assertAlmostEqual(loaded.total_drawing_length_px, original.total_drawing_length_px)
        self.assertEqual(loaded.strokes[6].closed, True)

    def test_too_small_canvas_is_rejected(self):
        with self.assertRaises(ValueError):
            create_test_shape(400, 200)


if __name__ == "__main__":
    unittest.main()
