import unittest

import cv2
import numpy as np
from PIL import Image, ImageDraw

from models import DrawingPlan
from path_planning.contour_planner import ContourSettings, extract_contours, render_contour_preview


class ContourPlannerTests(unittest.TestCase):
    def test_black_foreground_on_white_mask_creates_plan(self):
        mask = Image.new("L", (100, 60), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((10, 10, 40, 40), fill=0)

        result = extract_contours(mask, ContourSettings())

        self.assertIsNotNone(result.plan)
        self.assertEqual(result.plan.width, 100)
        self.assertEqual(result.plan.height, 60)
        self.assertEqual(result.contours_found, 1)
        self.assertEqual(result.plan.stroke_count, 1)
        self.assertTrue(result.plan.strokes[0].closed)
        result.plan.validate_bounds()

    def test_white_foreground_on_black_mask_creates_plan(self):
        mask = Image.new("L", (80, 50), 0)
        ImageDraw.Draw(mask).ellipse((20, 10, 50, 40), fill=255)

        result = extract_contours(mask, ContourSettings(foreground_mode="light"))

        self.assertIsNotNone(result.plan)
        self.assertEqual(result.plan.stroke_count, 1)
        self.assertTrue(result.plan.strokes[0].closed)

    def test_all_contours_includes_inner_boundary(self):
        mask = Image.new("L", (80, 80), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((10, 10, 65, 65), fill=0)
        draw.rectangle((25, 25, 50, 50), fill=255)

        external = extract_contours(mask, ContourSettings(retrieval_mode="external"))
        all_contours = extract_contours(mask, ContourSettings(retrieval_mode="all"))

        self.assertEqual(external.contours_found, 1)
        self.assertEqual(all_contours.contours_found, 2)
        self.assertEqual(all_contours.plan.stroke_count, 2)

    def test_minimum_contour_length_filters_small_components(self):
        mask = Image.new("L", (100, 40), 255)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((5, 5, 9, 9), fill=0)       # small component
        draw.rectangle((25, 5, 70, 20), fill=0)   # larger component

        unfiltered = extract_contours(mask, ContourSettings(min_contour_length_px=0))
        filtered = extract_contours(mask, ContourSettings(min_contour_length_px=30))

        self.assertEqual(unfiltered.plan.stroke_count, 2)
        self.assertEqual(filtered.plan.stroke_count, 1)
        self.assertEqual(filtered.skipped_by_length, 1)

    def test_blank_mask_returns_no_plan(self):
        mask = Image.new("L", (32, 24), 255)
        result = extract_contours(mask)
        self.assertIsNone(result.plan)
        self.assertEqual(result.contours_found, 0)
        self.assertEqual(result.contours_kept, 0)

    def test_contour_points_are_inside_mask(self):
        array = np.full((70, 120), 255, dtype=np.uint8)
        cv2.line(array, (5, 5), (105, 60), 0, thickness=3)
        result = extract_contours(Image.fromarray(array), ContourSettings(epsilon_percent=0.1))
        self.assertIsNotNone(result.plan)
        result.plan.validate_bounds()
        for stroke in result.plan.strokes:
            for point in stroke.points:
                self.assertGreaterEqual(point.x, 0)
                self.assertLessEqual(point.x, 120)
                self.assertGreaterEqual(point.y, 0)
                self.assertLessEqual(point.y, 70)

    def test_plan_json_round_trip(self):
        mask = Image.new("L", (60, 40), 255)
        ImageDraw.Draw(mask).rectangle((8, 5, 48, 30), fill=0)
        result = extract_contours(mask)
        self.assertIsNotNone(result.plan)
        loaded = DrawingPlan.from_dict(result.plan.to_dict())
        self.assertEqual(loaded.stroke_count, result.plan.stroke_count)
        self.assertAlmostEqual(loaded.total_drawing_length_px, result.plan.total_drawing_length_px)

    def test_preview_preserves_dimensions_and_has_color_overlay(self):
        mask = Image.new("L", (50, 40), 255)
        ImageDraw.Draw(mask).rectangle((10, 10, 30, 30), fill=0)
        result = extract_contours(mask)
        preview = render_contour_preview(mask, result.plan)
        self.assertEqual(preview.size, mask.size)
        self.assertEqual(preview.mode, "RGB")
        self.assertNotEqual(preview.getpixel((10, 10))[0], preview.getpixel((10, 10))[1])

    def test_invalid_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            ContourSettings(min_contour_length_px=-1)
        with self.assertRaises(ValueError):
            ContourSettings(epsilon_percent=11)
        with self.assertRaises(ValueError):
            ContourSettings(retrieval_mode="unknown")


if __name__ == "__main__":
    unittest.main()
