#!/usr/bin/env python3
"""Synthetic contracts for pretrained semantic-only S5-P1 preflight."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from run_engine001_color32_s5p1_oneformer import (
    MODEL_ID, REVISION, preview_labels, run, validate_labels,
)


class OneFormerSemanticContracts(unittest.TestCase):
    def test_immutable_revision(self):
        self.assertEqual(MODEL_ID, "shi-labs/oneformer_ade20k_swin_tiny")
        self.assertEqual(REVISION, "05f2812b1eccf9909b3897777450f8d68148cafc")

    def test_semantic_map_multiple_classes(self):
        arr = np.zeros((240, 150), np.int64)
        arr[:, 75:] = 1
        stats = validate_labels(arr)
        self.assertEqual(stats["feasibility_gate"], "PASS")
        self.assertEqual(stats["label_count"], 2)
        self.assertEqual(stats["boundary_pixel_count"], 240)
        self.assertEqual(preview_labels(arr).shape, (240, 150, 3))

    def test_degenerate_all_one_label_fails_feasibility(self):
        arr = np.zeros((240, 150), np.int64)
        self.assertEqual(validate_labels(arr)["feasibility_gate"], "FAIL")

    def test_disallow_unverified_labels(self):
        with self.assertRaisesRegex(ValueError, "SHAPE_OR_DTYPE"):
            validate_labels(np.zeros((240, 150), float))
        with self.assertRaisesRegex(ValueError, "SHAPE_OR_DTYPE"):
            validate_labels(np.zeros((240, 149), np.int64))
        with self.assertRaisesRegex(ValueError, "LABEL_RANGE"):
            validate_labels(np.full((240, 150), 255, np.int32))
        with self.assertRaisesRegex(ValueError, "LABEL_RANGE"):
            validate_labels(np.full((240, 150), -1, np.int32))

    def test_no_output_overwrite_before_network_or_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frozen"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "NO_OVERWRITE"):
                run(Path(directory) / "missing.png", output)


if __name__ == "__main__":
    unittest.main()
