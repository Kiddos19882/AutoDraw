#!/usr/bin/env python3
"""ENGINE-001 S5-R2 E2 tests: original pixel research only, normal strokes."""
import unittest

import numpy as np

from engine001_bpred_s5r2_region_candidates import (
    build_region_candidates, BlockedS5R2)
from brush_footprint_geometry import swept_capsule_pixel_masks


def scene(indexes, region_ids=None, dots=()):
    game = np.asarray(indexes, dtype=np.int16)
    h, w = game.shape
    ids = np.asarray(region_ids, dtype=np.int32) if region_ids is not None else (
        np.where(game >= 0, 1, 0).astype(np.int32))
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[game >= 0, 3] = 255
    protected = np.zeros((h, w), dtype=bool)
    for y, x in dots:
        protected[y, x] = True
    return {"game_index": game, "paintable_id": ids, "original_rgba": rgba,
            "protected_original_dot": protected}


class S5R2Tests(unittest.TestCase):
    def test_one_pixel_width_one_normal_no_executor(self):
        a = scene([[-1, -1, -1], [-1, 4, -1], [-1, -1, -1]],
                  dots=((1, 1),))
        r = build_region_candidates(a)
        self.assertEqual(r["uncovered_potential_pixel_count"], 0)
        self.assertEqual(r["stroke_count"], 1)
        self.assertEqual(r["proposals"][0]["brush_value"], 1)
        self.assertEqual(r["protected_dot_potential_covered"], 1)
        self.assertEqual((r["drawing_mode"], r["smooth"]), ("normal", False))
        self.assertFalse(r["safe_to_execute"])
        self.assertFalse(r["admissible_for_gameplay"])

    def test_two_separate_region_ids_same_game_color(self):
        a = scene([[5] * 10 for _ in range(10)],
                  [[1] * 5 + [2] * 5 for _ in range(10)])
        r = build_region_candidates(a, max_trials=400)
        self.assertEqual(r["regions_total"], 2)
        self.assertGreaterEqual(r["regions_visited"], 1)
        for p in r["proposals"]:
            self.assertIs(p["smooth"], False)
            self.assertFalse(p["safe_to_execute"])
            footprint = swept_capsule_pixel_masks(
                p["points"], p["brush_value"], 1., 1., 10, 10)
            self.assertTrue(all(
                a["paintable_id"][y, x] == p["paintable_id"]
                and a["game_index"][y, x] == p["color_index"]
                for x, y in footprint["potential_cells"]))

    def test_protected_small_region_precedes_large(self):
        g = [[4] * 12 for _ in range(12)]
        regions = [[1] * 12 for _ in range(12)]
        g[0][0] = 5
        regions[0][0] = 2
        a = scene(g, regions, dots=((0,0),))
        r = build_region_candidates(a, max_trials=120)
        self.assertGreater(r["stroke_count"], 0)
        self.assertEqual(r["proposals"][0]["paintable_id"], 2)
        self.assertEqual(r["proposals"][0]["brush_value"], 1)

    def test_transparent_hole_never_accepted(self):
        g = [[3] * 16 for _ in range(16)]
        for y in range(6,10):
            for x in range(6,10):
                g[y][x] = -1
        a = scene(g, [[1 if v >= 0 else 0 for v in row] for row in g])
        r = build_region_candidates(a, max_trials=240)
        self.assertGreater(r["potential_covered_pixel_count"], 0)
        self.assertLessEqual(r["potential_covered_pixel_count"], r["visible_pixel_count"])
        for p in r["proposals"]:
            footprint = swept_capsule_pixel_masks(p["points"], p["brush_value"],
                                                  1., 1., 16,16)
            self.assertTrue(all(a["game_index"][y,x] == 3
                                for x,y in footprint["potential_cells"]))

    def test_deterministic_double(self):
        a = scene([[2] * 16 for _ in range(16)])
        first = build_region_candidates(a, max_trials=200)
        second = build_region_candidates(a, max_trials=200)
        self.assertEqual(first, second)
        self.assertEqual(first["result_sha256"], second["result_sha256"])

    def test_budget_and_truthful_partial(self):
        a = scene([[2] * 30 for _ in range(30)])
        r = build_region_candidates(a, max_strokes=1, max_trials=50)
        self.assertLessEqual(r["stroke_count"], 1)
        self.assertLessEqual(r["trials"], 50)
        self.assertGreater(r["uncovered_potential_pixel_count"], 0)
        self.assertEqual(r["status"], "PARTIAL")

    def test_negative_swatches_mixed_region_and_shapes(self):
        a = scene([[1, 2]], [[1, 1]])
        with self.assertRaises(BlockedS5R2):
            build_region_candidates(a)
        a = scene([[1, -1]])
        a["paintable_id"][0,1] = 1
        with self.assertRaises(BlockedS5R2):
            build_region_candidates(a)
        a = scene([[1]])
        a["protected_original_dot"] = np.zeros((2,2), dtype=bool)
        with self.assertRaises(BlockedS5R2):
            build_region_candidates(a)

    def test_invalid_budgets_fail_closed(self):
        a = scene([[1]])
        for kwargs in ({"max_trials": 0}, {"max_strokes": 0},
                       {"max_trials": True}, {"max_strokes": False}):
            with self.assertRaises(BlockedS5R2):
                build_region_candidates(a, **kwargs)


if __name__ == "__main__":
    unittest.main()
