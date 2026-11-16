#!/usr/bin/env python3
"""V43-P3a2 large brush sizes: source-only candidate & no-op provenance."""
import unittest
import cv2
import numpy as np

from run_engine001_v43p3a2_width_audit import source_width_audit, sample_source_segment
from run_engine001_v43p3_oriented_source import SUPPORTED_WIDTHS, WIDTHS


class V43P3a2WidthsTests(unittest.TestCase):
    def test_original_protocol_widths_frozen(self):
        self.assertEqual(WIDTHS, (4, 6))
        self.assertEqual(SUPPORTED_WIDTHS, (4, 6, 10, 20, 30))

    def test_wide_audit_keeps_source_only_and_single_axis(self):
        mask = np.zeros((240, 460), dtype=np.bool_)
        mask[70:130, 160:303] = True
        distance = cv2.distanceTransform(
            np.pad(mask.astype(np.uint8), 1),
            cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
        result = source_width_audit(mask, distance)
        self.assertEqual(list(result), [str(w) for w in SUPPORTED_WIDTHS])
        for width in SUPPORTED_WIDTHS:
            trial = result[str(width)]
            self.assertEqual(trial, source_width_audit(mask, distance)[str(width)])
            self.assertFalse(trial["safe_to_execute"])
            self.assertTrue(all(not line["safe_to_execute"]
                                and line["width"] == width
                                for line in trial["candidate_strokes"]))

    def test_subpixel_diagnostic_source_only_and_detects_crossing(self):
        mask=np.zeros((240,460),dtype=np.bool_)
        mask[60:120,170:300]=True
        distance=cv2.distanceTransform(np.pad(mask.astype(np.uint8),1),
                                       cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[1:-1,1:-1]
        safe=sample_source_segment(mask,distance,
            [{"x":190.0,"y":90.0},{"x":250.0,"y":90.0}],10)
        self.assertEqual(safe["source_owner_violations"],0)
        self.assertEqual(safe["interior_margin_violations"],0)
        self.assertEqual(safe["proof_type"],
                         "SOURCE_CENTERLINE_ONLY_NOT_EGRET_FOOTPRINT")
        crossing=sample_source_segment(mask,distance,
            [{"x":170.0,"y":90.0},{"x":310.0,"y":90.0}],10)
        self.assertGreater(crossing["source_owner_violations"],0)
        with self.assertRaisesRegex(ValueError,"nonfinite"):
            sample_source_segment(mask,distance,
                [{"x":float("nan"),"y":90},{"x":250,"y":90}],10)

    def test_no_eligible_is_valid_result(self):
        mask = np.zeros((240, 460), dtype=np.bool_)
        mask[100, 200] = True
        distance = cv2.distanceTransform(
            np.pad(mask.astype(np.uint8), 1),
            cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
        result = source_width_audit(mask, distance)
        self.assertTrue(all(v["count"] == 0 for v in result.values()))


if __name__ == "__main__":
    unittest.main()
