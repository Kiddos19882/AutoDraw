#!/usr/bin/env python3
"""NEURAL-S1 deterministic source-region adapter tests (NOT neural inference)."""
import unittest
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np

from run_engine001_color32_neural_s1 import (
    BG, MAX_MASKS, apply_masks, source_metrics, source_gate,
    _load_mask_archive, EXP, FROZEN_SAM2_SOURCE_SHA,
    FROZEN_SAM2_TINY_CHECKPOINT_SHA,
)
from run_engine001_palette32_region_study import SOURCE_SHA


class NeuralS1SourceContracts(unittest.TestCase):
    def setUp(self):
        self.palette = np.zeros((32, 3), dtype=np.uint8)
        self.palette[BG] = [255, 255, 255]
        self.palette[3] = [255, 0, 0]
        self.palette[4] = [0, 255, 0]
        self.rgb = np.full((240, 150, 3), 255, np.uint8)
        self.rgb[20:50, 30:70] = [250, 0, 0]
        self.g = np.full((240, 150), BG, np.uint8)
        self.g[20:50, 30:70] = 3

    def test_neural_mask_changes_only_original_nonbackground(self):
        m = np.zeros((240, 150), bool)
        m[10:60, 20:80] = True
        out, info = apply_masks(
            self.rgb, self.palette, self.g, [(0.9, 0.96, int(m.sum()), "m0", m)])
        self.assertTrue(np.all(out[self.g == BG] == BG))
        self.assertEqual(info["accepted_masks"], 1)
        self.assertEqual(out[35, 35], 3)

    def test_protected_edges_are_exactly_preserved(self):
        m = np.zeros((240, 150), bool)
        m[20:50, 30:70] = True
        self.rgb[20:50, 30:70] = [0, 255, 0]
        protected = np.zeros(self.g.shape, bool)
        protected[35, 35] = True
        out, stats = apply_masks(
            self.rgb, self.palette, self.g, [(0.9, 0.96, int(m.sum()), "m0", m)],
            protected)
        self.assertEqual(out[35, 35], 3)
        self.assertEqual(out[35, 36], 4)
        self.assertEqual(stats["restored_protected_pixels"], 1)

    def test_invalid_mask_shape_rejected(self):
        bad = np.zeros((240, 149), bool)
        with self.assertRaisesRegex(ValueError, "BLOCKED_NEURAL_S1_MASK_SHAPE"):
            apply_masks(self.rgb, self.palette, self.g, [(0.9, 0.9, 10, "bad", bad)])

    def test_baseline_diagnostics_and_source_gates_are_not_native(self):
        protected = np.zeros(self.g.shape, bool)
        metrics = source_metrics(self.rgb, self.g, self.palette, protected, self.g)
        self.assertGreater(metrics["components4_non_background"], 0)
        self.assertEqual(metrics["g32_protected_pixels_changed"], 0)
        self.assertTrue(source_gate(metrics, metrics, edge_protected=True)[
            "palette_le32"])
        self.assertFalse(source_gate(metrics, metrics, edge_protected=True)[
            "component_reduction_ge25pct"])

    def test_real_mask_archive_manifest_fails_on_wrong_checkpoint_or_code(self):
        with tempfile.TemporaryDirectory() as work:
            root = Path(work)
            a = np.zeros((240, 150), dtype=np.bool_)
            a[20:45, 35:60] = True
            file = root / "masks.npz"
            manifest_path = root / "manifest.json"
            np.savez_compressed(file, mask_0000=a)
            manifest = {
                "experiment": EXP,
                "source_sha256": SOURCE_SHA,
                "mask_shape_hw": [240, 150],
                "model": "SAM2.1_HIERA_TINY",
                "parameters": {
                    "points_per_side": 8, "points_per_batch": 8,
                    "crop_n_layers": 0, "pred_iou_thresh": 0.8,
                    "stability_score_thresh": 0.95
                },
                "mask_archive_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "model_checkpoint_sha256": FROZEN_SAM2_TINY_CHECKPOINT_SHA,
                "sam2_git_sha": FROZEN_SAM2_SOURCE_SHA,
                "masks": [{
                    "key": "mask_0000",
                    "area": int(a.sum()),
                    "sha256": hashlib.sha256(a.tobytes()).hexdigest(),
                    "predicted_iou": 0.99,
                    "stability_score": 0.99
                }]
            }
            def write():
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            write()
            masks, loaded = _load_mask_archive(file, manifest_path)
            self.assertEqual(len(masks), 1)
            self.assertEqual(masks[0][3], "mask_0000")
            self.assertEqual(loaded["sam2_git_sha"], FROZEN_SAM2_SOURCE_SHA)
            for key in ("model_checkpoint_sha256", "sam2_git_sha"):
                original = manifest[key]
                manifest[key] = "0" * len(original)
                write()
                with self.assertRaisesRegex(
                        ValueError, "BLOCKED_NEURAL_S1_MODEL_OR_ARCHIVE_IDENTITY"):
                    _load_mask_archive(file, manifest_path)
                manifest[key] = original
            manifest["mask_archive_sha256"] = "0" * 64
            write()
            with self.assertRaisesRegex(
                    ValueError, "BLOCKED_NEURAL_S1_MODEL_OR_ARCHIVE_IDENTITY"):
                _load_mask_archive(file, manifest_path)

    def test_frozen_resource_caps_not_changed_by_adapter(self):
        self.assertEqual(MAX_MASKS, 32)
        self.assertEqual(BG, 30)


if __name__ == "__main__":
    unittest.main()
