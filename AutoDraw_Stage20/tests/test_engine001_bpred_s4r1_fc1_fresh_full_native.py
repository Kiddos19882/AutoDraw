#!/usr/bin/env python3
"""FC1 synthetic regressions: fresh source/geometry, not old E/F data."""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

import numpy as np

import run_engine001_bpred_s4r1_fc1_fresh_full_native as fc1


class FreshFullChainTests(unittest.TestCase):
    @staticmethod
    def palette():
        game = np.array(
            [[(17 * i) % 256, (53 * i) % 256, (101 * i) % 256]
             for i in range(128)], dtype=np.uint8)
        game[6] = [255, 255, 255]
        return game

    @staticmethod
    def owners():
        idx = np.full((240, 150), fc1.WHITE, dtype=np.uint8)
        idx[20:95, 25:97] = 17
        idx[110:140, 102:104] = 27
        return idx

    def test_new_full_geometry_has_true_widths_and_all_current_owners(self):
        plan, report = fc1.new_adaptive_fill(self.owners(), self.palette())
        self.assertTrue(plan)
        self.assertEqual(set(s["colorIndex"] for s in plan), {17, 27})
        self.assertTrue(any(s["width"] > 1 for s in plan))
        self.assertTrue(any(s["width"] == 1 for s in plan))
        self.assertTrue(all(1 <= s["width"] <= 10 for s in plan))
        self.assertTrue(all(s["strokeId"] == f"icon-{i}"
                            for i, s in enumerate(plan)))
        self.assertEqual(set(report), {"17", "27"})
        self.assertEqual(report["17"]["source_pixels"], 75 * 72)
        self.assertEqual(report["27"]["source_pixels"], 30 * 2)

    def test_changing_only_fresh_owner_changes_entire_generated_plan(self):
        game = self.palette()
        source_index = self.owners()
        p1, _ = fc1.new_adaptive_fill(source_index, game)
        again, _ = fc1.new_adaptive_fill(source_index.copy(), game)
        self.assertEqual(p1, again)
        change = source_index.copy()
        change[20:95, 25:97] = 28
        p2, _ = fc1.new_adaptive_fill(change, game)
        self.assertNotEqual(p1, p2)
        self.assertIn(28, {x["colorIndex"] for x in p2})
        self.assertNotIn(17, {x["colorIndex"] for x in p2})

    def test_native_rgba_feedback_only_current_scene_and_current_owner(self):
        idx = np.full((240, 150), fc1.WHITE, dtype=np.uint8)
        idx[10, 20:23] = 31
        idx[10, 23:25] = 45
        native = np.zeros((720, 1380, 4), dtype=np.uint8)
        missing = fc1.native_missing_cells(native, idx)
        self.assertEqual(int(missing.sum()), 5)
        # Only the single fresh native painted cell has alpha>=24.
        native[10 * 3, (fc1.X0 + 20) * 3, 3] = 24
        missing = fc1.native_missing_cells(native, idx)
        self.assertEqual(int(missing.sum()), 4)
        repair = fc1.new_native_feedback_repair(missing, idx, self.palette())
        self.assertEqual({s["colorIndex"] for s in repair}, {31, 45})
        self.assertEqual(len(repair), 2)
        self.assertTrue(all(s["width"] == 1 for s in repair))

    def test_outside_native_frame_and_invalid_dimensions_fail_closed(self):
        with self.assertRaises(ValueError):
            fc1.make_stroke(12, self.palette(), 11, (155.0, 0.0), (156, 1))
        with self.assertRaises(ValueError):
            fc1.make_stroke(12, self.palette(), 2, (1.0, 0.0), (156, 1))
        with self.assertRaises(ValueError):
            fc1.new_adaptive_fill(np.zeros((1, 1), np.uint8), self.palette())
        with self.assertRaises(ValueError):
            fc1.native_missing_cells(
                np.zeros((240, 150, 4), np.uint8), self.owners())

    def test_fresh_contour_responds_to_current_image_not_old_cache(self):
        idx = self.owners()
        base = np.zeros((240, 150, 4), dtype=np.uint8)
        base[:, :, :3] = 120
        base[:, :, 3] = 255
        plan_flat, edges_flat = fc1.new_source_outline(
            base, idx, self.palette())
        changed = base.copy()
        changed[20:95, 25:97, :3] = 235
        plan_changed, edges_changed = fc1.new_source_outline(
            changed, idx, self.palette())
        self.assertEqual(int(edges_flat.sum()), 0)
        self.assertEqual(plan_flat, [])
        self.assertGreater(int(edges_changed.sum()), 0)
        self.assertTrue(plan_changed)

    def test_real_original_is_source_not_cached_rendered_target(self):
        original = Path(__file__).resolve().parents[1] / (
            "testImages/wV6VeZI9S1Y.png")
        raw = original.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         fc1.EXPECTED_ORIGINAL_SHA256)
        logical, original_info = fc1.fresh_logical_source(raw)
        self.assertEqual(logical.shape, (240, 150, 4))
        self.assertEqual(original_info["width"], 200)
        self.assertEqual(original_info["height"], 320)
        with self.assertRaises(ValueError):
            fc1.fresh_logical_source(raw + b"unexpected-image-trailer")

    def test_fresh_output_contains_no_historical_artistic_input_paths(self):
        self.assertEqual(fc1.ALLOWED_ARTISTIC_INPUTS,
                         ("original_bytes", "current_game128_palette"))
        self.assertEqual(fc1.WIDTH_PHASES, (10, 7, 5, 3, 1))


if __name__ == "__main__":
    unittest.main()
