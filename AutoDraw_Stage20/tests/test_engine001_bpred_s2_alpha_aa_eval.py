"""BPRED-S2v1 E2 synthetic math and metadata tests. NO native quality claims."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
import run_engine001_bpred_s2_alpha_aa_eval as s2
import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_b1r_p4d16_canvas_aa_density as p16

class TestBpredS2(unittest.TestCase):
    def test_01_three_models_pinned(self):
        self.assertEqual(s2.MODE_MAP,(("M0_NAIVE","naive"),("M1_EGRET_SHIFT","source_halfpixel"),
                        ("M2_AREA8","area8")))
    def test_02_real_shape_required(self):
        with self.assertRaisesRegex(ValueError,"ALPHA_ARRAY"):
            s2.alpha_metrics(np.zeros((3,3),np.uint8),np.zeros((3,3),np.uint8))
    def test_03_perfect_masks(self):
        a=np.zeros((162,162),np.uint8)
        a[80:88,60:66]=255
        r=s2.alpha_metrics(a,a)
        self.assertEqual(r["alpha24"]["IoU"],1.)
        self.assertEqual(r["alpha24"]["FP"],0)
        self.assertEqual(r["alpha24"]["FN"],0)
        self.assertEqual(r["alpha_MAE_union"],0.)
    def test_04_fp_and_fn_not_swapped(self):
        a=np.zeros((162,162),np.uint8)
        b=np.zeros_like(a)
        a[5,5]=255; b[5,6]=255
        m=s2.alpha_metrics(a,b)
        self.assertEqual(m["alpha24"]["TP"],0)
        self.assertEqual(m["alpha24"]["FP"],1)
        self.assertEqual(m["alpha24"]["FN"],1)
        self.assertEqual(m["alpha24"]["IoU"],0.)
    def test_05_subpixel_alpha(self):
        st=s0.future_manifest()["calibration"][0]["strokes"][0]
        w=st["width"]
        pts=st["points"]
        x=(58-27)*3;y=(40-27)*3
        m=p16.predict_alpha(pts,w,x,y,"area8")
        self.assertEqual(m.dtype,np.uint8)
        self.assertEqual(m.shape,(162,162))
        self.assertTrue(np.any(m>0))
    def test_06_models_differ_odd(self):
        st=s0.future_manifest()["calibration"][0]["strokes"][0]
        pts=st["points"];w=st["width"]
        a=p16.predict_alpha(pts,w,93,39,"naive")
        b=p16.predict_alpha(pts,w,93,39,"source_halfpixel")
        self.assertTrue(np.any(a!=b))
    def test_07_macro_uses_case_first(self):
        def m(iou):
            return {"alpha_MAE_union":.5,"alpha_MAE_all":.1,
                "exact_rgba_alpha_mask":False,
                "alpha1":{"IoU":iou,"TP":1,"FP":1,"FN":0,"exact_mask":False},
                "alpha24":{"IoU":iou,"TP":1,"FP":1,"FN":0,"exact_mask":False}}
        r=[{"cells":[{"models":{k:m(v) for k,_ in s2.MODE_MAP}} for _ in range(3)]}
            for v in (.3,.9)]
        self.assertAlmostEqual(s2.metric_mean(r,"M2_AREA8","IoU",24),.6)
    def test_08_hypotheses_fail_with_identical_models(self):
        def metric(mval):
            return {"alpha_MAE_union":1.,"alpha_MAE_all":1.,
                    "exact_rgba_alpha_mask":False,
                    "alpha1":{"IoU":mval,"TP":1,"FP":1,"FN":1,"exact_mask":False},
                    "alpha24":{"IoU":mval,"TP":1,"FP":1,"FN":1,"exact_mask":False}}
        cases=[]
        for w in range(1,11):
            for k in range(12):
                cases.append({"width":w,"angle_deg":s2.ANGLES[k//4],
                    "length_logical":s2.LENGTHS[(k//2)%2],
                    "phase_x":s2.PHASES[k%2][0],"phase_y":s2.PHASES[k%2][1],
                    "cells":[{"models":{name:metric(.9) for name,_ in s2.MODE_MAP}} for _ in range(3)]})
        out=s2.aggregate(cases)
        self.assertEqual(out["hypothesis_H1_M2_alpha24_macro_vs_M1"],"FAIL")
        self.assertEqual(out["hypothesis_H2_M2_alphaMAE_union_vs_M1"],"FAIL")
        self.assertEqual(out["hypothesis_H3_M1_odd_alpha24_vs_M0"],"FAIL")
        self.assertFalse(out["M2_pixel_exact_safe_calibration"])
    def test_09_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"test.json"
            s2.save_exclusive(path,{"test":"first"})
            with self.assertRaises(FileExistsError):
                s2.save_exclusive(path,{"test":"second"})
    def test_10_no_native_ledger_if_missing(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"SOURCE_REPORT_MISSING"):
                s2.source_files(Path(root))
    def test_11_empty_union_accuracy(self):
        a=np.zeros((162,162),np.uint8)
        z=s2.alpha_metrics(a,a)
        self.assertEqual(z["alpha_MAE_union"],0.)
        self.assertTrue(z["alpha24"]["exact_mask"])
    def test_12_threshold_behavior(self):
        a=np.zeros((162,162),np.uint8)
        b=np.zeros_like(a)
        a[4,4]=23;b[4,4]=24
        r=s2.alpha_metrics(a,b)
        self.assertEqual(r["alpha1"]["FP"],0)
        self.assertEqual(r["alpha24"]["FN"],1)

if __name__=="__main__":
    unittest.main()
