#!/usr/bin/env python3
"""Prospective S5-R5 source-content allocation: masks and frozen R4 default."""
import unittest
import numpy as np

import engine001_bpred_s5r4_offset_lanes as lanes
from engine001_bpred_s5r2_region_candidates import BlockedS5R2, swept_capsule_pixel_masks


def source_scene():
    game = np.full((90, 160), 6, dtype=np.int16)
    ids = np.ones_like(game, dtype=np.int32)
    # Two source owners with different game swatches.
    game[14:50, 14:62] = 23
    ids[14:50, 14:62] = 2
    game[48:79, 88:145] = 42
    ids[48:79, 88:145] = 3
    # Enclosed white detail, not exterior white background.
    game[25:37, 28:43] = 6
    ids[25:37, 28:43] = 4
    game[55:60, 105:113] = -1
    ids[55:60, 105:113] = 0
    rgba = np.zeros((*game.shape, 4), np.uint8)
    rgba[game >= 0, 3] = 255
    dots = np.zeros(game.shape, bool)
    dots[22, 20] = True
    dots[28, 30] = True
    edge = np.zeros(game.shape, bool)
    edge[:, 1:] |= ids[:, 1:] != ids[:, :-1]
    edge[1:, :] |= ids[1:, :] != ids[:-1, :]
    return dict(game_index=game, paintable_id=ids, original_rgba=rgba,
                protected_original_dot=dots, source_edge=edge)


class ContentLaneTests(unittest.TestCase):
    def check_safety(self, arr, result):
        self.assertFalse(result["smooth"])
        self.assertEqual(result["drawing_mode"], "normal")
        self.assertFalse(result["admissible_for_gameplay"])
        self.assertFalse(result["safe_to_execute"])
        self.assertLessEqual(result["phase_trials"]["broad"], 1400)
        self.assertLessEqual(result["phase_trials"]["detail"], 600)
        self.assertLessEqual(result["phase_strokes"]["broad"], 80)
        self.assertLessEqual(result["phase_strokes"]["detail"], 120)
        visited = set()
        for stroke in result["proposals"]:
            potential = swept_capsule_pixel_masks(
                stroke["points"], stroke["brush_value"], 1., 1.,
                arr["game_index"].shape[1], arr["game_index"].shape[0])["potential_cells"]
            for x, y in potential:
                self.assertEqual(int(arr["paintable_id"][y, x]), stroke["paintable_id"])
                self.assertEqual(int(arr["game_index"][y, x]), stroke["color_index"])
                self.assertEqual(int(arr["original_rgba"][y, x, 3]), 255)
            visited.update(potential)
        self.assertEqual(len(visited), result["potential_covered_pixel_count"])
        self.assertEqual(result["modeled_white6_covered"] + result["modeled_nonwhite6_covered"],
                         len(visited))

    def test_content_mode_has_multiple_nonwhite_regions_and_enclosed_white(self):
        arr = source_scene()
        r = lanes.build_candidates(arr, allocation="content_s5r5")
        self.check_safety(arr, r)
        self.assertGreaterEqual(r["covered_region_groups"]["nonwhite"], 2)
        self.assertGreaterEqual(r["covered_region_groups"]["enclosed_white6"], 1)
        self.assertGreater(r["modeled_source_edge_covered"], 0)
        self.assertEqual(r["method_provenance"]["Medial_Axis"], "NOT_IMPLEMENTED")
        self.assertEqual(r, lanes.build_candidates(arr, allocation="content_s5r5"))

    def test_r4_default_is_byte_identical_to_explicit_area(self):
        arr = source_scene()
        self.assertEqual(lanes.build_candidates(arr),
                         lanes.build_candidates(arr, allocation="area"))

    def test_content_mode_requires_genuine_source_edge(self):
        arr = source_scene()
        del arr["source_edge"]
        with self.assertRaises(BlockedS5R2):
            lanes.build_candidates(arr, allocation="content_s5r5")
        arr["source_edge"] = np.zeros((2, 2), bool)
        with self.assertRaises(BlockedS5R2):
            lanes.build_candidates(arr, allocation="content_s5r5")

    def test_budget_and_mode_rejection(self):
        arr = source_scene()
        for kw in ({"allocation": "bad"}, {"allocation": "content_s5r5", "max_trials": 0},
                   {"allocation": "content_s5r5", "max_strokes": 201}):
            with self.assertRaises(BlockedS5R2):
                lanes.build_candidates(arr, **kw)


if __name__ == "__main__":
    unittest.main()
