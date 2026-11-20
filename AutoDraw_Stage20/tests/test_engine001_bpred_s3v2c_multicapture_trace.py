#!/usr/bin/env python3
"""E2 S3v2c eight-plan and no-selector trace audit; actual Canvas requires E3."""
import unittest
import numpy as np

import run_engine001_bpred_s3v2c_multicapture_trace as trace


class FrozenS3v2cTests(unittest.TestCase):
    def test_01_frozen_eight_original_scenes(self):
        scenes = trace.frozen_samples()
        self.assertEqual(len(scenes), 8)
        self.assertEqual(set(s["width"] for s in scenes), {1, 10})
        self.assertEqual(set(s["relation"] for s in scenes),
                         {"CROSSING", "NEAR_PARALLEL_OVERLAP"})
        self.assertEqual(set(s["variant"] for s in scenes),
                         {"A_ONLY", "A_THEN_B"})
        self.assertEqual(len(set(s["sample_id"] for s in scenes)), 8)
        self.assertTrue(all(s["source_plan_sha256"] and
                            s["runtime_plan_sha256"] for s in scenes))

    def test_02_identical_snapshots_no_auto_selection(self):
        one = np.zeros((3, 4, 4), np.uint8)
        one[1, 2] = [80, 61, 53, 255]
        meta = {"node": {"x": 1, "y": 2, "width": 4, "height": 3},
                "transform": [3, 0, 0, 3, -3, -6],
                "drawDataCount": 2}
        rows = trace.compare_snapshots([one, one.copy()], [meta, dict(meta)])
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["same_rgba_pixel_values"])
        self.assertTrue(rows[0]["same_node_bounds"])
        self.assertTrue(rows[0]["same_canvas_transform"])
        self.assertEqual(rows[0]["RGBA_changed_pixels"], 0)

    def test_03_difference_is_reported_without_representative(self):
        one = np.zeros((3, 4, 4), np.uint8)
        other = one.copy()
        other[1, 2] = [197, 65, 145, 255]
        a = {"node": {"x": 0}, "transform": [3, 0, 0, 3, 0, 0],
             "drawDataCount": 1}
        b = {"node": {"x": 1}, "transform": [3, 0, 0, 3, 3, 0],
             "drawDataCount": 2}
        rows = trace.compare_snapshots([one, other], [a, b])
        self.assertEqual(rows[0]["RGBA_changed_pixels"], 1)
        self.assertFalse(rows[0]["same_rgba_pixel_values"])
        self.assertFalse(rows[0]["same_node_bounds"])
        self.assertFalse(rows[0]["same_draw_data_count"])
        self.assertNotIn("selected_capture", rows[0])

    def test_04_all_pairs_kept_no_position_based_preference(self):
        frames = [np.zeros((3, 3, 4), np.uint8) for _ in range(3)]
        rows = trace.compare_snapshots(frames,
               [{"node": {}, "transform": [], "drawDataCount": 1}] * 3)
        self.assertEqual([(x["first_capture"], x["second_capture"])
                          for x in rows], [(0, 1), (0, 2), (1, 2)])

    def test_05_different_shapes_are_not_forced_equal(self):
        a = np.zeros((2, 3, 4), np.uint8)
        b = np.zeros((3, 2, 4), np.uint8)
        rows = trace.compare_snapshots([a, b],
               [{"node": {}, "transform": [], "drawDataCount": 1}] * 2)
        self.assertFalse(rows[0]["same_canvas_shape"])
        self.assertFalse(rows[0]["same_rgba_pixel_values"])
        self.assertIsNone(rows[0]["RGBA_changed_pixels"])


if __name__ == "__main__":
    unittest.main()
