"""E2 synthetic guards for ENGINE001_ANILINES_SEAM_REFERENCE_V16.

No human-authored ground truth exists in this fixture; never claim a semantic
quality PASS from these tests.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from run_engine001_seam_reference_v16 import (
    ROI, ROI_SHAPE, SOURCE_SHA, evaluate_mask, prepare_source_only,
    read_mask, read_review, validate_annotation,
)


class SeamReferenceV16Tests(unittest.TestCase):
    def example(self):
        positive = np.zeros(ROI_SHAPE, dtype=bool)
        negative = np.zeros(ROI_SHAPE, dtype=bool)
        positive[20, 20] = True
        negative[40, 40] = True
        return positive, negative

    def manifest(self):
        return {
            "annotation_id": "synthetic-only",
            "reviewer_id": "test-fixture",
            "annotation_version": "1",
            "reviewed_at": "2026-11-15",
            "blind_to_model_outputs": True,
            "source_sha256": SOURCE_SHA,
            "roi": list(ROI),
        }

    def test_one_pixel_is_supported_two_pixels_is_not(self):
        positive, negative = self.example()
        near = np.zeros(ROI_SHAPE, dtype=bool)
        near[20, 21] = True
        metrics = evaluate_mask(near, positive, negative)
        self.assertEqual(metrics["positive_recall_1px"], 1.0)
        far = np.zeros(ROI_SHAPE, dtype=bool)
        far[20, 22] = True
        metrics = evaluate_mask(far, positive, negative)
        self.assertEqual(metrics["positive_recall_1px"], 0.0)
        self.assertEqual(metrics["positive_gap_components"], 1)

    def test_negative_coverage_not_global_precision(self):
        positive, negative = self.example()
        candidate = np.zeros(ROI_SHAPE, dtype=bool)
        candidate[20, 20] = True
        candidate[40, 40] = True
        candidate[10, 10] = True  # Unknown pixel, not labeled false positive.
        m = evaluate_mask(candidate, positive, negative)
        self.assertEqual(m["nonseam_candidate_density"], 1.0)
        self.assertEqual(m["supported_candidate_fraction_on_labeled_pixels"], 0.5)
        self.assertIsNone(m["global_semantic_precision"])
        self.assertEqual(m["candidate_pixels"], 3)

    def test_missing_or_conflicting_annotations_fail(self):
        p, n = self.example()
        with self.assertRaises(ValueError):
            validate_annotation(self.manifest(), np.zeros_like(p), n)
        with self.assertRaises(ValueError):
            validate_annotation(self.manifest(), p, np.zeros_like(n))
        n[20, 21] = True
        with self.assertRaises(ValueError):
            validate_annotation(self.manifest(), p, n)

    def test_annotation_bad_shape_type_and_attestation(self):
        p, n = self.example()
        m = self.manifest()
        m["blind_to_model_outputs"] = False
        with self.assertRaises(ValueError):
            validate_annotation(m, p, n)
        with self.assertRaises(ValueError):
            validate_annotation(self.manifest(), p[:-1], n[:-1])
        with self.assertRaises(ValueError):
            evaluate_mask(np.zeros((100, 189), dtype=bool), p, n)
        with self.assertRaises(ValueError):
            evaluate_mask(np.zeros(ROI_SHAPE, dtype=np.uint8), p, n)

    def test_read_mask_and_manifest_sha_validation(self):
        p, n = self.example()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            def save(name, mask):
                path = folder/name
                Image.fromarray(mask.astype(np.uint8)*255, mode="L").save(path)
                return hashlib.sha256(path.read_bytes()).hexdigest()
            pos_sha = save("seams_positive.png", p)
            neg_sha = save("definite_nonseam.png", n)
            m = {**self.manifest(), "positive_sha256": pos_sha,
                 "negative_sha256": neg_sha}
            (folder/"annotation.json").write_text(json.dumps(m),encoding="utf-8")
            got, pos, neg = read_review(folder)
            self.assertEqual(got["annotation_id"], "synthetic-only")
            self.assertTrue(np.array_equal(pos, p))
            self.assertTrue(np.array_equal(neg, n))
            Image.fromarray(np.zeros((189,100,3), dtype=np.uint8),
                            mode="RGB").save(folder/"seams_positive.png")
            with self.assertRaises(ValueError):
                read_review(folder)

    def test_missing_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                read_review(Path(td))

    def test_prepare_source_only_pack_is_not_annotation(self):
        source = Path(__file__).resolve().parents[1]/"testImages"/"wV6VeZI9S1Y.png"
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)/"source-only"
            prepare_source_only(source, target)
            self.assertTrue((target/"reviewer_source_only.png").is_file())
            self.assertFalse((target/"annotation.json").exists())
            self.assertFalse((target/"seams_positive.png").exists())
            with Image.open(target/"reviewer_source_only.png") as im:
                self.assertEqual(im.size, (100,189))
            template = json.loads((target/"annotation.template.json").read_text())
            self.assertEqual(template["annotation_status"], "BLOCKED_NOT_ANNOTATED")
            self.assertFalse(template["blind_to_model_outputs"])
            with self.assertRaises(ValueError):
                prepare_source_only(source, target)


if __name__ == "__main__":
    unittest.main()
