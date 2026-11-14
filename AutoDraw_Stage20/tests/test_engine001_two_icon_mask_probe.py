"""Synthetic gates for pinned two-icon mask probe; browser is tested in CI."""
import unittest
import numpy as np
from run_engine001_two_icon_mask_probe import safe_interior, plan_strokes, compare


class IconCompositeMaskTests(unittest.TestCase):
    def test_erosion_removes_outer_boundary(self):
        a = np.zeros((240, 460), dtype=bool)
        a[40:50, 50:70] = True
        e = safe_interior(a)
        self.assertFalse(e[40, 60])
        self.assertTrue(e[41, 51])
        self.assertFalse(e[41, 50])

    def test_fixed_scanline_no_out_of_board_or_duplicate_vertices(self):
        a = np.zeros((240, 460), dtype=bool)
        a[40:80, 50:120] = True
        a[120:180, 260:370] = True
        strokes = plan_strokes(a)
        self.assertGreater(len(strokes), 0)
        self.assertTrue(all(s["width"] == 2 and len(s["points"]) == 2 for s in strokes))
        self.assertTrue(all(0 <= p["x"] < 460 and 0 <= p["y"] < 240
                            for s in strokes for p in s["points"]))
        self.assertTrue(all(s["points"][0]["x"] < s["points"][1]["x"] for s in strokes))

    def test_compare_exact(self):
        a = np.zeros((6, 7), dtype=bool)
        a[1:4, 1:5] = True
        self.assertEqual(compare(a, a)["iou"], 1)
        self.assertEqual(compare(a, a)["outside_target_pixels"], 0)

    def test_compare_extra_and_missing(self):
        a = np.zeros((6, 7), dtype=bool)
        b = np.zeros_like(a)
        a[2, 3] = a[2, 4] = True
        b[2, 3] = b[2, 5] = True
        c = compare(a, b)
        self.assertEqual((c["covered_target_pixels"], c["uncovered_target_pixels"],
                          c["outside_target_pixels"]), (1, 1, 1))
        self.assertAlmostEqual(c["iou"], 1/3)

    def test_empty_mask_fails_closed(self):
        with self.assertRaises(ValueError):
            plan_strokes(np.zeros((240, 460), dtype=bool))


if __name__ == "__main__":
    unittest.main()
