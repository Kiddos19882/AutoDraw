#!/usr/bin/env python3
"""BPRED-S2v5 synthetic diagnostics, NOT Egret proof."""
from __future__ import annotations
import copy
import tempfile
from pathlib import Path
import unittest
import numpy as np

import run_engine001_bpred_s2v5_fp_diagnostic as x
import run_engine001_bpred_s2v4_native_core as v4


class S2v5Diagnostics(unittest.TestCase):
    def test_01_two_fps_exact_coordinates_pred128_real23(self):
        p=np.zeros((162,162),dtype=np.uint8)
        a=np.zeros_like(p)
        p[5,6]=128
        a[5,6]=23
        p[8,2]=255
        a[8,2]=0
        p[3,1]=127
        a[3,1]=0
        self.assertEqual(x.fp_coordinates(p,a),[(5,6,128,23),(8,2,255,0)])

    def test_02_alpha24_real_is_not_fp(self):
        p=np.zeros((162,162),np.uint8)
        a=np.zeros_like(p)
        p[1,2]=128;a[1,2]=24
        self.assertEqual(x.fp_coordinates(p,a),[])

    def test_03_invalid_shapes_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"MALFORMED_NATIVE_ALPHA_PAIR"):
            x.fp_coordinates(np.zeros((10,10),np.uint8),np.zeros((10,10),np.uint8))

    def test_04_capsule_center_inside(self):
        s=v4.prepare_scene(4,22,9,(1,11))["runtime"][0]
        pts=s["points"]
        midx=(pts[0]["x"]+pts[1]["x"])/2
        midy=(pts[0]["y"]+pts[1]["y"])/2
        result=x.signed_capsule_margin_logical(s,round(3*midx),round(3*midy))
        self.assertGreater(result,1.0)

    def test_05_capsule_far_outside(self):
        s=v4.prepare_scene(4,22,9,(1,11))["runtime"][0]
        result=x.signed_capsule_margin_logical(s,0,0)
        self.assertLess(result,0.0)

    def test_06_invalid_capsule_width_blocked(self):
        s=v4.prepare_scene(4,22,9,(1,11))["runtime"][0].copy()
        s["width"]=11
        with self.assertRaisesRegex(ValueError,"CAPSULE_INPUT"):
            x.signed_capsule_margin_logical(s,100,100)

    def test_07_nearest_real_alpha24_distance(self):
        a=np.zeros((162,162),np.uint8)
        a[10,10]=24
        self.assertEqual(x.native_neighbor_distance_physical(a,13,14),5.)

    def test_08_no_real_alpha24_fail_closed(self):
        a=np.zeros((162,162),np.uint8)
        with self.assertRaisesRegex(ValueError,"EMPTY_NATIVE_FOREGROUND"):
            x.native_neighbor_distance_physical(a,4,4)

    def test_09_strata_gate_catches_narrow_group(self):
        width={}
        for w in range(1,11):
            ratio=.79 if w==2 else .96
            width[str(w)]={"M2":{"TP":100},"M5":{"TP":int(100*ratio)},
                           "retained_TP_ratio":int(100*ratio)/100}
        angle={str(a):{"M2":{"TP":100},"M5":{"TP":94},
                       "retained_TP_ratio":.94} for a in (22,111,241)}
        got=x.failing_strata({"per_width":width,"per_angle":angle})
        self.assertEqual([(s["group"],s["key"]) for s in got["failures"]],[("width",2)])

    def test_10_strata_gate_catches_angle(self):
        w={str(i):{"M2":{"TP":10},"M5":{"TP":10},
                   "retained_TP_ratio":1.0} for i in range(1,11)}
        a={str(i):{"M2":{"TP":100},"M5":{"TP":80 if i==241 else 90},
                   "retained_TP_ratio":.8 if i==241 else .9} for i in (22,111,241)}
        got=x.failing_strata({"per_width":w,"per_angle":a})
        self.assertEqual([(s["group"],s["key"]) for s in got["failures"]],[("angle",241)])

    def test_11_incorrect_ratio_blocked(self):
        w={str(i):{"M2":{"TP":10},"M5":{"TP":10},
                   "retained_TP_ratio":1.0} for i in range(1,11)}
        a={str(i):{"M2":{"TP":10},"M5":{"TP":10},
                   "retained_TP_ratio":1.0} for i in (22,111,241)}
        w["1"]["retained_TP_ratio"]=.8
        with self.assertRaisesRegex(ValueError,"STRATA_DENOMINATOR_OR_RATIO"):
            x.failing_strata({"per_width":w,"per_angle":a})

    def test_12_bad_sample_id_fails_closed(self):
        for s in ("foo","BPRED-S2V4-W01/../../secret","BPRED-S2V4-W01\\bar"):
            with self.assertRaisesRegex(ValueError,"INVALID_SAMPLE_ID|SAMPLE_PATH_TRAVERSAL"):
                x.safe_id(s)

    def test_13_source_fail_closed(self):
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaisesRegex(ValueError,"MISSING_ORIGINAL_REPORT"):
                x.read_source(Path(p))

    def test_14_do_not_overwrite_raw(self):
        with tempfile.TemporaryDirectory() as p:
            path=Path(p)/"diag.json"
            x.write_once(path,{"first":True})
            with self.assertRaises(FileExistsError):
                x.write_once(path,{"second":True})


if __name__=="__main__":
    unittest.main()
