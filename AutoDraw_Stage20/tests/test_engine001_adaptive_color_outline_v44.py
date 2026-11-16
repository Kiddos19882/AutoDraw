"""V44-P1 deterministic tests. Run: python -m unittest tests/test_engine001_adaptive_color_outline_v44.py"""
import unittest
import numpy as np
from PIL import Image

from engine001_adaptive_color_outline_v44 import (
    DARK, OFFSET, MIN_CONTRAST, contrast, contrast_guard,
    side_backgrounds, adaptive_recolor,
)


class AdaptiveColorOutlineV44Tests(unittest.TestCase):
    def test_bright_background_darkens_light_source(self):
        picked, decision = contrast_guard([230, 210, 150], [[240, 220, 150], [240, 220, 150]])
        self.assertIn(decision, ("darkened", "unresolved"))
        self.assertEqual(len(picked), 3)
        if decision == "darkened":
            self.assertGreaterEqual(contrast(picked, [240, 220, 150]), MIN_CONTRAST)

    def test_good_source_color_is_preserved(self):
        color = [38, 26, 40]
        picked, decision = contrast_guard(color, [[230, 200, 170], [200, 180, 150]])
        self.assertEqual(picked, color)
        self.assertEqual(decision, "source")

    def test_missing_sides_fails_closed(self):
        self.assertEqual(contrast_guard([220, 220, 220], None),
                         (list(DARK), "missing_sides"))

    def test_median_side_sampling_respects_roi(self):
        pixels = np.empty((240, 150, 3), dtype=np.uint8)
        pixels[:] = [210, 180, 140]
        img = Image.fromarray(pixels, "RGB")
        sides = side_backgrounds(img, [{"x": 170, "y": 50}, {"x": 175, "y": 50}])
        self.assertEqual(sides, [[210, 180, 140], [210, 180, 140]])
        self.assertIsNone(side_backgrounds(img, [{"x": 155, "y": 0}]))

    def test_adaptive_rgb_does_not_mutate_stroke_geometry(self):
        pixels = np.empty((240, 150, 3), dtype=np.uint8)
        pixels[:] = [200, 190, 170]
        img = Image.fromarray(pixels, "RGB")
        fill = {"layer": "paint", "stroke": {"strokeId": "paint", "width": 2, "colorRgb": 12}}
        detail = {"layer": "detail", "stroke": {
            "strokeId": "detail-v18-B-test", "width": 1, "colorRgb": 0x31262B,
            "points": [{"x": 180, "y": 80}, {"x": 200, "y": 80}]}}
        base = {"strokes": [fill] * 1945 + [detail] * 410,
                "synthetic_vertices_NOT_CHALK": 5682}
        for variant in ("A", "B", "C"):
            changed, report = adaptive_recolor(base, img, variant)
            self.assertEqual(len(report), 410)
            self.assertEqual(changed["strokes"][:1945], base["strokes"][:1945])
            for a, b in zip(base["strokes"][1945:], changed["strokes"][1945:]):
                self.assertEqual(a["stroke"]["points"], b["stroke"]["points"])
                self.assertEqual(a["stroke"]["strokeId"], b["stroke"]["strokeId"])
                self.assertEqual(a["stroke"]["width"], b["stroke"]["width"])
        self.assertEqual(base["strokes"][1945]["stroke"]["colorRgb"], 0x31262B)

    def test_invalid_roi_rejected(self):
        with self.assertRaisesRegex(ValueError, "ROI"):
            side_backgrounds(Image.new("RGB", (10, 10)),
                             [{"x": 170, "y": 50}, {"x": 175, "y": 50}])


if __name__ == "__main__":
    unittest.main()
