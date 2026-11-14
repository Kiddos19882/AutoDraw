"""Regressions for source-bound color holdout and safe V5 width selection."""
import unittest
import numpy as np

from run_engine001_complex_holdout_v5 import (
    fingerprint, brush_mask, v5_selective, classify_composite,
    LOGICAL_SIZE, NATIVE_SIZE, MAX_CLASS_CROSS_FRACTION
)


class ComplexHoldoutV5Tests(unittest.TestCase):
    def test_git_blob_fingerprint_well_formed(self):
        raw=b"source bytes"
        git_sha, sha=fingerprint(raw)
        self.assertEqual(len(git_sha),40)
        self.assertEqual(len(sha),64)
        self.assertNotEqual(git_sha,sha)

    def test_source_brush_geometric_preview(self):
        points=[{"x":25.5,"y":35.5},{"x":95.5,"y":35.5}]
        narrow=brush_mask(points,4)
        wide=brush_mask(points,6)
        self.assertEqual(narrow.shape,(NATIVE_SIZE[1],NATIVE_SIZE[0]))
        self.assertGreater(wide.sum(),narrow.sum())

    def test_color_safety_rejects_conflict(self):
        labels=np.zeros((NATIVE_SIZE[1],NATIVE_SIZE[0]),dtype=np.uint8)
        labels[:,70:120]=1
        own=labels==1
        st=[{"strokeId":"icon-0","width":4,
             "points":[{"x":25.0,"y":50.0},{"x":38.0,"y":50.0}]}]
        chosen,decisions=v5_selective(st,own,labels,1)
        self.assertEqual(chosen[0]["width"],4)
        self.assertEqual(decisions["rejected"],1)

    def test_safe_expansion_can_upgrade_interior(self):
        labels=np.ones((NATIVE_SIZE[1],NATIVE_SIZE[0]),dtype=np.uint8)
        points=[{"x":100.0,"y":60.0},{"x":170.0,"y":60.0}]
        chosen,decisions=v5_selective(
            [{"strokeId":"icon-0","width":4,"points":points}],
            labels==1,labels,1)
        self.assertEqual(chosen[0]["width"],6)
        self.assertEqual(decisions["upgraded"],1)

    def test_rgb_classification_explicitly_diagnostic(self):
        img=np.zeros((2,2,4),dtype=np.uint8)
        img[0,0]=[60,40,40,255]
        img[0,1]=[252,252,252,255]
        img[1,0]=[200,150,100,255]
        img[1,1]=[0,0,0,0]
        out=classify_composite(
            img,{0:(255,255,255),1:(60,40,40),2:(200,150,100)},0)
        self.assertEqual(out.tolist(),[[1,0],[2,0]])


if __name__=="__main__":
    unittest.main()
