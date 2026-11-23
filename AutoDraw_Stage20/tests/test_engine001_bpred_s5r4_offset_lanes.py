#!/usr/bin/env python3
"""S5-R4 source-only offset-lane safety and invariants; NOT native acceptance."""
import unittest
import numpy as np
from engine001_bpred_s5r4_offset_lanes import build_candidates
from engine001_bpred_s5r2_region_candidates import swept_capsule_pixel_masks, BlockedS5R2


def scene(game, ids=None, dots=()):
    a = np.asarray(game, dtype=np.int16)
    h, w = a.shape
    r = np.where(a >= 0, 1, 0).astype(np.int32) if ids is None else np.asarray(ids, np.int32)
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[a >= 0, 3] = 255
    protected = np.zeros((h, w), bool)
    for y, x in dots:
        protected[y, x] = True
    return dict(game_index=a, paintable_id=r,
                original_rgba=rgba, protected_original_dot=protected)


class S5R4OffsetLaneTest(unittest.TestCase):
    def assert_safe(self, arrays, result):
        self.assertEqual(result["drawing_mode"], "normal")
        self.assertFalse(result["smooth"])
        self.assertFalse(result["safe_to_execute"])
        self.assertFalse(result["admissible_for_gameplay"])
        self.assertEqual(result["source_owner_status"], "MISSING")
        self.assertEqual(result["native_calibration"], "UNVERIFIED")
        self.assertLessEqual(result["phase_trials"]["broad"], 1400)
        self.assertLessEqual(result["phase_trials"]["detail"], 600)
        self.assertLessEqual(result["phase_strokes"]["broad"], 80)
        self.assertLessEqual(result["phase_strokes"]["detail"], 120)
        h, w = arrays["game_index"].shape
        union = set()
        for item in result["proposals"]:
            self.assertFalse(item["smooth"])
            self.assertFalse(item["safe_to_execute"])
            f = swept_capsule_pixel_masks(item["points"], item["brush_value"],
                                          1., 1., w, h)
            for x, y in f["potential_cells"]:
                self.assertEqual(int(arrays["paintable_id"][y, x]), item["paintable_id"])
                self.assertEqual(int(arrays["game_index"][y, x]), item["color_index"])
                self.assertEqual(int(arrays["original_rgba"][y, x, 3]), 255)
            union.update(f["potential_cells"])
        self.assertEqual(len(union), result["potential_covered_pixel_count"])
        self.assertEqual(result["stroke_count"], len(result["proposals"]))
        self.assertEqual(result["trials"], sum(result["phase_trials"].values()))

    def test_repeated_long_lanes_rectangle(self):
        a = scene(np.full((48, 140), 4, np.int16), dots=((2, 2),))
        r = build_candidates(a)
        self.assert_safe(a, r)
        self.assertGreater(r["regions_with_multiple_accepted_lanes"], 0)
        self.assertTrue(any(abs(p["points"][1][0]-p["points"][0][0]) > 30
                            for p in r["proposals"] if p["phase"] == "broad"))
        self.assertEqual(r, build_candidates(a))

    def test_vertical_region(self):
        a = scene(np.full((100, 36), 8, np.int16))
        r = build_candidates(a)
        self.assert_safe(a, r)
        self.assertTrue(any(abs(p["points"][1][1]-p["points"][0][1]) > 20
                            for p in r["proposals"] if p["phase"] == "broad"))

    def test_donut_with_alpha_void(self):
        m = np.full((55, 70), 5, np.int16)
        m[14:40, 19:49] = -1
        a = scene(m)
        self.assert_safe(a, build_candidates(a))

    def test_two_same_swatch_separate_regions(self):
        m = np.full((40, 78), 7, np.int16)
        ids = np.ones(m.shape, np.int32)
        ids[:, 40:] = 2
        a = scene(m, ids)
        self.assert_safe(a, build_candidates(a))

    def test_tiny_protected_and_checker(self):
        m = np.full((26, 26), -1, np.int16)
        np.fill_diagonal(m, 3)
        a = scene(m, dots=((8, 8),))
        self.assert_safe(a, build_candidates(a))
        q = np.indices((13, 13)).sum(axis=0).astype(np.int16) % 2
        ids = np.arange(1, 170, dtype=np.int32).reshape(13, 13)
        a2 = scene(q, ids)
        self.assert_safe(a2, build_candidates(a2))

    def test_invalid_inputs_and_frozen_caps(self):
        a = scene(np.ones((8, 8), dtype=np.int16))
        for kw in ({"max_trials": 0}, {"max_trials": True}, {"max_strokes": 201},
                   {"max_strokes": 0}, {"max_trials": 2001}):
            with self.assertRaises(BlockedS5R2):
                build_candidates(a, **kw)
        invalid = scene(np.array([[1, 2]], np.int16),
                        np.array([[1, 1]], np.int32))
        with self.assertRaises(BlockedS5R2):
            build_candidates(invalid)


if __name__ == "__main__":
    unittest.main()
