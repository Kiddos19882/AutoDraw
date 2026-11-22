#!/usr/bin/env python3
"""S5-R1 E2 synthetic regression: model-only, no runtime admission."""
import unittest

import numpy as np

from engine001_bpred_s5r1_offline_candidates import build_candidates, BlockedS5


def scene(indexes, regions=None):
    game = np.array(indexes, dtype=np.int16)
    h, w = game.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[game >= 0, 3] = 255
    if regions is None:
        regions = np.where(game >= 0, 1, 0).astype(np.int32)
    else:
        regions = np.array(regions, dtype=np.int32)
    return {"game_index": game, "paintable_id": regions, "original_rgba": rgba,
            "protected_original_dot": np.zeros((h, w), dtype=bool)}


class S5R1Tests(unittest.TestCase):
    def test_single_original_dot_is_non_executable(self):
        s = scene([[-1, -1, -1], [-1, 4, -1], [-1, -1, -1]])
        r = build_candidates(s, max_seed_trials=1000)
        self.assertEqual(r["stroke_count"], 1)
        self.assertEqual(r["uncovered_potential_pixel_count"], 0)
        self.assertEqual(r["proposals"][0]["brush_value"], 1)
        self.assertFalse(r["safe_to_execute"])
        self.assertFalse(r["admissible_for_gameplay"])
        self.assertEqual(r["drawing_mode"], "normal")
        self.assertIs(r["smooth"], False)
        self.assertTrue(all(p["drawing_mode"] == "normal" and p["smooth"] is False
                            for p in r["proposals"]))

    def test_deterministic_double(self):
        s = scene([[2]*7 for _ in range(7)])
        a, b = build_candidates(s), build_candidates(s)
        self.assertEqual(a, b)
        self.assertEqual(a["result_sha256"], b["result_sha256"])

    def test_two_colors_never_mixed_in_proposals(self):
        s = scene([[1]*5+[2]*5 for _ in range(5)],
                  [[1]*5+[2]*5 for _ in range(5)])
        r = build_candidates(s, max_seed_trials=2000)
        self.assertGreater(r["stroke_count"], 0)
        self.assertTrue(all(p["color_index"] in (1,2) for p in r["proposals"]))
        self.assertTrue(all(p["safe_to_execute"] is False for p in r["proposals"]))

    def test_same_color_different_region_is_separate(self):
        s = scene([[5]*6 for _ in range(6)],
                  [[1]*3+[2]*3 for _ in range(6)])
        r = build_candidates(s)
        self.assertTrue(all(p["paintable_id"] in (1, 2) for p in r["proposals"]))

    def test_invalid_alpha_owner_fail_closed(self):
        s = scene([[3, -1]])
        s["paintable_id"][0,1] = 2
        with self.assertRaises(BlockedS5):
            build_candidates(s)

    def test_wrong_shape_and_range_fail_closed(self):
        s = scene([[3]])
        s["game_index"][0,0] = 128
        with self.assertRaises(BlockedS5):
            build_candidates(s)
        s = scene([[3]])
        s["protected_original_dot"] = np.zeros((2,2), dtype=bool)
        with self.assertRaises(BlockedS5):
            build_candidates(s)

    def test_arbitrary_direction_and_zero_direction(self):
        s = scene([[4]*8 for _ in range(8)])
        r = build_candidates(s, directions=((0.25, 0.9682458366),), max_strokes=3)
        self.assertGreaterEqual(r["stroke_count"], 1)
        self.assertEqual(r["status"], "PARTIAL")
        with self.assertRaises(BlockedS5):
            build_candidates(s, directions=((0.,0.),))

    def test_uncovered_without_exhaustion_still_partial(self):
        # Regression for CI45079897646: no budget exhaustion is NOT
        # equivalent to all source pixels being covered.
        s = scene([[4] * 8 for _ in range(8)])
        r = build_candidates(s, directions=((0.25, 0.9682458366),),
                             max_strokes=1000, max_seed_trials=5000)
        self.assertLess(r["trials"], 5000)
        self.assertGreater(r["uncovered_potential_pixel_count"], 0)
        self.assertEqual(r["status"], "PARTIAL")
        self.assertIs(r["smooth"], False)

    def test_explicit_budgets_and_no_runtime(self):
        s = scene([[2]*10 for _ in range(10)])
        r = build_candidates(s, max_strokes=1, max_seed_trials=50)
        self.assertLessEqual(r["stroke_count"], 1)
        self.assertEqual(r["status"], "PARTIAL")
        for p in r["proposals"]:
            self.assertEqual(p["status"], "MODEL_ONLY_NON_EXECUTABLE")
            self.assertFalse(p["safe_to_execute"])


if __name__ == "__main__":
    unittest.main()
