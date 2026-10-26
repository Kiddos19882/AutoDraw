import unittest

from models import DrawingPlan, Point, Stroke
from path_planning.stroke_optimizer import (
    StrokeOptimizationSettings,
    optimize_plan,
    render_plan_preview,
)


def point(x, y):
    return Point(float(x), float(y))


class StrokeOptimizerTests(unittest.TestCase):
    def test_simplification_removes_redundant_collinearish_points(self):
        stroke = Stroke("wavy", [point(5, 10), point(10, 10.1), point(15, 10), point(20, 10.05)])
        plan = DrawingPlan(50, 30, [stroke])
        result = optimize_plan(plan, StrokeOptimizationSettings(simplify_tolerance_px=0.5, reorder_strokes=False))
        optimized = result.optimized_plan.strokes[0]
        self.assertLess(len(optimized.points), len(stroke.points))
        self.assertEqual(optimized.points[0], stroke.points[0])
        self.assertEqual(optimized.points[-1], stroke.points[-1])

    def test_closed_stroke_remains_closed_and_valid(self):
        square_with_midpoints = [
            point(5, 5), point(10, 5), point(15, 5), point(15, 10),
            point(15, 15), point(10, 15), point(5, 15), point(5, 10),
        ]
        plan = DrawingPlan(30, 30, [Stroke("square", square_with_midpoints, closed=True)])
        result = optimize_plan(plan, StrokeOptimizationSettings(simplify_tolerance_px=1.0))
        optimized = result.optimized_plan.strokes[0]
        self.assertTrue(optimized.closed)
        self.assertGreaterEqual(len(optimized.points), 3)
        result.optimized_plan.validate_bounds()

    def test_reordering_reduces_pen_up_distance(self):
        first = Stroke("first", [point(10, 10), point(20, 10)])
        far = Stroke("far", [point(180, 10), point(190, 10)])
        near = Stroke("near", [point(22, 10), point(30, 10)])
        plan = DrawingPlan(200, 40, [first, far, near])
        result = optimize_plan(plan, StrokeOptimizationSettings(simplify_tolerance_px=0, reorder_strokes=True))
        self.assertLess(result.optimized_metrics.pen_up_distance_px, result.original_metrics.pen_up_distance_px)
        self.assertEqual(result.optimized_plan.strokes[0].name, "first")
        self.assertEqual(result.optimized_plan.strokes[1].name, "near")

    def test_reverse_open_stroke_starts_near_previous_endpoint(self):
        first = Stroke("first", [point(5, 5), point(20, 5)])
        second = Stroke("second", [point(80, 5), point(25, 5)])
        plan = DrawingPlan(100, 20, [first, second])
        result = optimize_plan(plan, StrokeOptimizationSettings(simplify_tolerance_px=0, reorder_strokes=True, reverse_open_strokes=True))
        self.assertEqual(result.optimized_plan.strokes[1].points[0], point(25, 5))

    def test_closed_stroke_can_rotate_start_point_without_changing_geometry(self):
        first = Stroke("first", [point(10, 10), point(11, 10)])
        closed = Stroke("closed", [point(50, 10), point(60, 10), point(60, 20), point(50, 20)], closed=True)
        plan = DrawingPlan(100, 40, [first, closed])
        result = optimize_plan(plan, StrokeOptimizationSettings(simplify_tolerance_px=0, reorder_strokes=True, rotate_closed_strokes=True))
        rotated = result.optimized_plan.strokes[1]
        self.assertTrue(rotated.closed)
        self.assertEqual(rotated.points[0], point(50, 10))
        self.assertEqual(set(rotated.points), set(closed.points))

    def test_short_strokes_are_diagnostic_only_by_default(self):
        tiny = Stroke("tiny", [point(2, 2), point(4, 2)])
        long = Stroke("long", [point(10, 10), point(30, 10)])
        plan = DrawingPlan(50, 30, [tiny, long])
        result = optimize_plan(plan, StrokeOptimizationSettings(
            simplify_tolerance_px=0, minimum_stroke_length_px=5, remove_short_strokes=False,
            reorder_strokes=False,
        ))
        self.assertEqual(result.short_strokes_detected, 1)
        self.assertEqual(result.short_strokes_removed, 0)
        self.assertEqual(result.optimized_plan.stroke_count, 2)

    def test_short_strokes_can_be_removed_when_explicitly_enabled(self):
        tiny = Stroke("tiny", [point(2, 2), point(4, 2)])
        long = Stroke("long", [point(10, 10), point(30, 10)])
        plan = DrawingPlan(50, 30, [tiny, long])
        result = optimize_plan(plan, StrokeOptimizationSettings(
            simplify_tolerance_px=0, minimum_stroke_length_px=5, remove_short_strokes=True,
            reorder_strokes=False,
        ))
        self.assertEqual(result.optimized_plan.stroke_count, 1)
        self.assertEqual(result.short_strokes_removed, 1)

    def test_removing_every_stroke_is_rejected(self):
        plan = DrawingPlan(20, 20, [Stroke("tiny", [point(2, 2), point(3, 2)])])
        with self.assertRaises(ValueError):
            optimize_plan(plan, StrokeOptimizationSettings(
                simplify_tolerance_px=0, minimum_stroke_length_px=10, remove_short_strokes=True,
            ))

    def test_compatible_open_strokes_can_be_merged_when_enabled(self):
        a = Stroke("a", [point(5, 10), point(15, 10)])
        b = Stroke("b", [point(15, 10), point(25, 10)])
        plan = DrawingPlan(40, 30, [a, b])
        result = optimize_plan(plan, StrokeOptimizationSettings(
            simplify_tolerance_px=0, reorder_strokes=False, merge_open_strokes=True,
            max_merge_gap_px=0.5, max_join_angle_deg=20,
        ))
        self.assertEqual(result.merged_stroke_pairs, 1)
        self.assertEqual(result.optimized_plan.stroke_count, 1)
        self.assertEqual(result.optimized_plan.strokes[0].points, [point(5, 10), point(15, 10), point(25, 10)])

    def test_incompatible_open_strokes_are_not_merged(self):
        a = Stroke("a", [point(5, 10), point(15, 10)])
        b = Stroke("b", [point(15, 10), point(15, 20)])
        plan = DrawingPlan(40, 30, [a, b])
        result = optimize_plan(plan, StrokeOptimizationSettings(
            simplify_tolerance_px=0, reorder_strokes=False, merge_open_strokes=True,
            max_merge_gap_px=1, max_join_angle_deg=20,
        ))
        self.assertEqual(result.merged_stroke_pairs, 0)
        self.assertEqual(result.optimized_plan.stroke_count, 2)

    def test_input_plan_is_not_mutated(self):
        stroke = Stroke("line", [point(1, 1), point(5, 1), point(10, 1)])
        plan = DrawingPlan(20, 20, [stroke])
        original_points = list(plan.strokes[0].points)
        optimize_plan(plan, StrokeOptimizationSettings(simplify_tolerance_px=1.0))
        self.assertEqual(plan.strokes[0].points, original_points)

    def test_preview_has_expected_size_and_rgb_mode(self):
        plan = DrawingPlan(80, 40, [Stroke("line", [point(5, 5), point(70, 35)])])
        preview = render_plan_preview(plan, max_dimension=30)
        self.assertLessEqual(max(preview.size), 30)
        self.assertEqual(preview.mode, "RGB")

    def test_invalid_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            StrokeOptimizationSettings(simplify_tolerance_px=-1)
        with self.assertRaises(ValueError):
            StrokeOptimizationSettings(max_join_angle_deg=100)


if __name__ == "__main__":
    unittest.main()
