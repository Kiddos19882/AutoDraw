"""ENGINE001 V14 source and reporting regression fixtures (offline only)."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image
from run_engine001_line_extraction_v14_report import (
    SOURCE_SHA, check_source, evaluate, main,
)


class V14ReportTests(unittest.TestCase):
    def test_pinned_source_in_repo(self):
        source = Path(__file__).resolve().parents[1] / "testImages/wV6VeZI9S1Y.png"
        result = check_source(source)
        self.assertEqual(result["source_sha256"], SOURCE_SHA)

    def test_wrong_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"bad.png"
            Image.fromarray(np.zeros((320,200,3),dtype=np.uint8)).save(path)
            with self.assertRaises(ValueError):
                check_source(path)

    def test_shape_mismatch_is_fail_closed(self):
        source=np.full((320,200,3),255,dtype=np.uint8)
        with self.assertRaises(ValueError):
            evaluate(source,np.zeros((200,320),dtype=np.uint8))
        with self.assertRaises(ValueError):
            evaluate(source,np.zeros((320,200,3),dtype=np.uint8))

    def test_candidate_metrics_will_not_claim_true_seam_recall(self):
        source=np.full((320,200,3),255,dtype=np.uint8)
        source[80:200,110:130]=(40,40,40)
        generated=np.full((320,200),255,dtype=np.uint8)
        generated[90:180,120]=0
        result=evaluate(source,generated)
        self.assertEqual(result["ground_truth_seams"],"NOT_ANNOTATED")
        self.assertEqual(result["recognition"],"NOT_VALIDATED")
        self.assertGreater(result["roi_candidate_pixels"],0)
        self.assertGreaterEqual(result["roi_components_ge8"],1)


if __name__=="__main__":
    unittest.main()
