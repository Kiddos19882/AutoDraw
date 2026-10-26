import unittest

from drawing.plan_transform import fit_plan_to_size
from models import DrawingPlan, Point, Stroke


def make_plan(width=100, height=50):
    return DrawingPlan(
        width=width,
        height=height,
        name="fixture",
        strokes=[
            Stroke("open", [Point(0, 0), Point(width, height)]),
            Stroke("closed", [Point(10, 10), Point(30, 10), Point(30, 30), Point(10, 30)], closed=True),
        ],
    )


class PlanTransformTests(unittest.TestCase):
    def test_same_size_preserves_coordinates(self):
        plan = make_plan()
        fitted, info = fit_plan_to_size(plan, 100, 50)
        self.assertTrue(info.is_identity)
        self.assertEqual(fitted.width, 100)
        self.assertEqual(fitted.height, 50)
        self.assertEqual(fitted.strokes[0].points, plan.strokes[0].points)

    def test_fit_preserves_aspect_and_centres_vertically(self):
        plan = make_plan(100, 50)
        fitted, info = fit_plan_to_size(plan, 200, 200, preserve_aspect_ratio=True)
        self.assertAlmostEqual(info.scale_x, 2.0)
        self.assertAlmostEqual(info.scale_y, 2.0)
        self.assertAlmostEqual(info.offset_x, 0.0)
        self.assertAlmostEqual(info.offset_y, 50.0)
        self.assertEqual((fitted.width, fitted.height), (200, 200))
        self.assertEqual(fitted.strokes[0].points[0], Point(0, 50))
        self.assertEqual(fitted.strokes[0].points[-1], Point(200, 150))
        fitted.validate_bounds()

    def test_non_uniform_fit_scales_x_and_y_independently(self):
        plan = make_plan(100, 50)
        fitted, info = fit_plan_to_size(plan, 300, 100, preserve_aspect_ratio=False)
        self.assertAlmostEqual(info.scale_x, 3.0)
        self.assertAlmostEqual(info.scale_y, 2.0)
        self.assertEqual(fitted.strokes[0].points[-1], Point(300, 100))
        fitted.validate_bounds()

    def test_input_plan_is_not_modified(self):
        plan = make_plan()
        original_points = [list(stroke.points) for stroke in plan.strokes]
        fit_plan_to_size(plan, 200, 200)
        self.assertEqual([stroke.points for stroke in plan.strokes], original_points)

    def test_closed_flag_and_metadata_are_preserved(self):
        plan = DrawingPlan(50, 50, [Stroke("square", [Point(5, 5), Point(20, 5), Point(20, 20)], closed=True, metadata={"kind": "test"})])
        fitted, _info = fit_plan_to_size(plan, 100, 100)
        self.assertTrue(fitted.strokes[0].closed)
        self.assertEqual(fitted.strokes[0].metadata, {"kind": "test"})

    def test_invalid_target_size_rejected(self):
        plan = make_plan()
        with self.assertRaises(ValueError):
            fit_plan_to_size(plan, 0, 100)
        with self.assertRaises(ValueError):
            fit_plan_to_size(plan, 100, -1)


if __name__ == "__main__":
    unittest.main()
