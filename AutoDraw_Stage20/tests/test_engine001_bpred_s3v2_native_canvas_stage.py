#!/usr/bin/env python3
"""S3v2 deterministic instrumentation/geometry contract tests; native is E3."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

import run_engine001_bpred_s3v2_native_canvas_stage as s3v2
import run_engine001_bpred_s3_native_source_over as s3


def canvas_rgba(width=12, height=12):
    a = np.zeros((height, width, 4), np.uint8)
    a[6, 6] = [80, 61, 53, 255]
    return a


class BpredS3v2Contracts(unittest.TestCase):
    def test_01_pinned_source_same_s3_research(self):
        self.assertEqual(s3v2.PARENT_RUN, "44683117471")
        self.assertEqual(s3v2.PARENT_S3_BLOB,
                         "1bf56df9507f2a34fd16e68eef190229c3184ce5")
        self.assertEqual(s3v2.E0_BLOB,
                         "d8d703779f6364a3dda8e8edf9717fe0d065ef45")
        self.assertEqual((s3.manifest()["new_primary"],
                          s3.manifest()["replays"]), (80, 10))
        self.assertEqual(s3v2.BOARD_SHAPE, (720, 1380, 4))

    def test_02_true_original_node_negative_offset(self):
        node = {"x": -2, "y": -2, "width": 4, "height": 4}
        raster, meta = s3v2.source_stage_align(
            canvas_rgba(), node, [3, 0, 0, 3, 6, 6])
        self.assertEqual(raster.shape, s3v2.BOARD_SHAPE)
        np.testing.assert_array_equal(raster[0, 0], [80, 61, 53, 255])
        self.assertEqual(meta["node_origin_physical"], [-6, -6])
        self.assertEqual(meta["cropped_source_xy"], [6, 6])

    def test_03_true_original_node_positive_offset(self):
        node = {"x": 1, "y": 1, "width": 4, "height": 4}
        raster, meta = s3v2.source_stage_align(
            canvas_rgba(), node, [3, 0, 0, 3, -3, -3])
        np.testing.assert_array_equal(raster[9, 9], [80, 61, 53, 255])
        self.assertEqual(meta["pasted_native_xy"], [3, 3])

    def test_04_unsupported_transform_fail_closed(self):
        node = {"x": -2, "y": -2, "width": 4, "height": 4}
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_NATIVE_TRANSFORM"):
            s3v2.source_stage_align(canvas_rgba(), node, [3, 0, 0, 3, 0, 6])
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_NATIVE_TRANSFORM"):
            s3v2.source_stage_align(canvas_rgba(), node, [2, 0, 0, 3, 6, 6])

    def test_05_fractional_mapping_not_posthoc_fitted(self):
        node = {"x": -2.1, "y": -2, "width": 4, "height": 4}
        with self.assertRaisesRegex(ValueError, "NONINTEGER_PHYSICAL_NODE_ORIGIN"):
            s3v2.source_stage_align(
                canvas_rgba(), node, [3, 0, 0, 3, 6.3, 6])

    def test_06_unmatched_or_clipped_scene_fail_closed(self):
        node = {"x": 1000, "y": 1000, "width": 4, "height": 4}
        with self.assertRaisesRegex(ValueError, "CANVAS_NOT_OVERLAPPING"):
            s3v2.source_stage_align(
                canvas_rgba(), node, [3, 0, 0, 3, -3000, -3000])
        node = {"x": -2, "y": -2, "width": 4, "height": 4}
        extra = canvas_rgba()
        extra[0, 0] = [1, 1, 1, 255]
        with self.assertRaisesRegex(ValueError, "INK_OUTSIDE_NATIVE_BOARD"):
            s3v2.source_stage_align(extra, node, [3, 0, 0, 3, 6, 6])

    def test_07_s3_manifest_unchanged_before_canvas_capture(self):
        manifest = s3.manifest()
        self.assertEqual(len(manifest["scenes"]), 80)
        for scene in manifest["scenes"]:
            self.assertIn(scene["variant"], s3.VARIANTS)
            self.assertEqual(scene["runtime_plan_sha256"],
                             s3.digest(s3.canonical(scene["runtime_strokes"])))
        self.assertEqual(s3v2.PARENT_SHA,
                         "6dedf6ddfde36db17f07fc0aa00dd463dc525ca8")

    def test_08_parent_path_is_existing_s3_artifact_layout(self):
        root = Path("/tmp/immutable_parent")
        primary = s3v2.native_png_in_parent(root, "BPRED-S3-W01-CROSSING-A_ONLY")
        repeat = s3v2.native_png_in_parent(root, "BPRED-S3-REPLAY-W01", repeat=True)
        blank = s3v2.native_png_in_parent(root, "", blank=True)
        self.assertEqual(primary.name,
                         "BPRED-S3-W01-CROSSING-A_ONLY_REAL_EGRET.png")
        self.assertEqual(repeat.parent.name, "replays")
        self.assertEqual(blank.name, "S3_REAL_EGRET_BLANK.png")

    def test_09_frozen_stage_h1_does_not_accept_mismatch(self):
        p = np.zeros((1, 1, 4), np.uint8)
        p[0, 0] = [80, 61, 53, 255]
        q = p.copy()
        changed = q.copy()
        changed[0, 0, 0] = 87
        frames = {"A_ONLY": p, "B_ONLY": q,
                  "A_THEN_B": changed, "B_THEN_A": q}
        with patch.object(s3v2.p4d3, "roi", side_effect=lambda x, *_: x):
            row = s3v2.row_for(1, "CROSSING", frames, frames)
        self.assertEqual(row["stage_attribution"], "CANVAS_C0_MISMATCH_PRESENT")
        self.assertFalse(row["ordered_variants"]["A_THEN_B"]
                         ["source_over_original_C0_on_true_WebGL"]["frozen_H1_pass"])

    def test_10_reject_parent_without_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "FROZEN_PARENT_MISSING"):
                s3v2.verify_parent(Path(tmp))


if __name__ == "__main__":
    unittest.main()
