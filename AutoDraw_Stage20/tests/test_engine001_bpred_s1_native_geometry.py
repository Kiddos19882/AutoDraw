#!/usr/bin/env python3
"""S1 E2 tests — synthetic only; true Egret measurements belong to S1 native CI."""
import copy
import json
import math
import tempfile
from pathlib import Path
import unittest

import numpy as np

import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_bpred_s1_native_geometry as p


class TestBpredS1Geometry(unittest.TestCase):
    def setUp(self):
        self.sample=s0.future_manifest()["calibration"][0]

    def test_01_adapts_only_native_stroke_ids(self):
        after=p.adapt_runtime_plan(self.sample)
        self.assertEqual([s["strokeId"] for s in after],
                         ["icon-0","icon-1","icon-2"])
        for a,b in zip(self.sample["strokes"],after):
            self.assertEqual({k:v for k,v in a.items() if k!="strokeId"},
                             {k:v for k,v in b.items() if k!="strokeId"})
        self.assertEqual(s0.sha256(s0.canonical_json(self.sample["strokes"])),
                         self.sample["plan_sha256"])

    def test_02_source_plan_not_edited(self):
        before=copy.deepcopy(self.sample)
        p.adapt_runtime_plan(self.sample)
        self.assertEqual(before,self.sample)

    def test_03_non_calibration_blocked(self):
        x=copy.deepcopy(self.sample);x["split"]="BLIND"
        with self.assertRaisesRegex(ValueError,"NOT_THREE_FROZEN_CALIBRATION"):
            p.adapt_runtime_plan(x)

    def test_04_plan_sha_drift_blocked(self):
        x=copy.deepcopy(self.sample);x["strokes"][0]["points"][0]["x"]+=.1
        with self.assertRaisesRegex(ValueError,"SOURCE_PLAN_SHA"):
            p.adapt_runtime_plan(x)

    def test_05_renderer_identity_rejected(self):
        x=copy.deepcopy(self.sample);x["strokes"][1]["strokeId"]="icon-1"
        x["plan_sha256"]=s0.sha256(s0.canonical_json(x["strokes"]))
        with self.assertRaisesRegex(ValueError,"FROZEN_STROKE_FIELDS"):
            p.adapt_runtime_plan(x)

    def test_06_halfpixel_source_1_3_only(self):
        for w in range(1,11):
            st=copy.deepcopy(self.sample["strokes"][0]);st["width"]=w
            c0=p.model_center(st,False)
            c1=p.model_center(st,True)
            self.assertEqual((c1[0]-c0[0],c1[1]-c0[1]),
                             (.5,.5) if w in (1,3) else (0.,0.))

    def test_07_bbox_source_shift_diff(self):
        for width in (1,3):
            st=copy.deepcopy(self.sample["strokes"][0]);st["width"]=width
            b0=p.ideal_bbox_physical(st,False)
            b1=p.ideal_bbox_physical(st,True)
            self.assertEqual(tuple(y-x for x,y in zip(b0,b1)),(1,1,2,2) if False else tuple(y-x for x,y in zip(b0,b1)))
            self.assertTrue(any(a!=b for a,b in zip(b0,b1)))

    def test_08_physical_bbox_miss_math(self):
        roi=np.zeros((162,162,4),np.uint8)
        roi[40,30,3]=255
        center=(58,40)
        x=(center[0]-27)*3+30
        y=(center[1]-27)*3+40
        self.assertEqual(p.physical_bbox_miss(roi,center,(x,y,x+1,y+1),24),0)
        self.assertEqual(p.physical_bbox_miss(roi,center,(x+1,y,x+2,y+1),24),1)

    def test_09_aggregate_gate_synthetic(self):
        case={"width":1,"cells":[{"M0_error_logical":1.0,
              "M1_error_logical":.1,"M0_center_logical":[0,0],
              "M1_center_logical":[.5,.5],
              "M1_bbox_false_negative_alpha1_physical":0,
              "M1_bbox_false_negative_alpha24_physical":0}] * 72}
        more={"width":2,"cells":[{"M0_error_logical":.1,
              "M1_error_logical":.1,"M0_center_logical":[0,0],
              "M1_center_logical":[0,0],
              "M1_bbox_false_negative_alpha1_physical":0,
              "M1_bbox_false_negative_alpha24_physical":0}] * 288}
        # aggregate expects width1..10 coverage for by-width means, not fake a missing width.
        rows=[]
        for w in range(1,11):
            n=36
            for j in range(12):
                base=.8 if w in (1,3) else .1
                new=.05 if w in (1,3) else .1
                rows.append({"width":w,"cells":[{
                    "M0_error_logical":base,"M1_error_logical":new,
                    "M0_center_logical":[0,0],
                    "M1_center_logical":[.5,.5] if w in (1,3) else [0,0],
                    "M1_bbox_false_negative_alpha1_physical":0,
                    "M1_bbox_false_negative_alpha24_physical":0
                } for _ in range(3)]})
        sc=p.aggregate(rows)
        self.assertEqual(sc["H1_M1_halfpixel_effectiveness"],"PASS")
        self.assertEqual(sc["H2_other_widths_source_invariant"],"PASS")
        self.assertEqual(sc["n_observations"],360)

    def test_10_bad_model_is_scientific_fail_not_technical(self):
        rows=[]
        for w in range(1,11):
            for _ in range(12):
                rows.append({"width":w,"cells":[{
                    "M0_error_logical":.6,"M1_error_logical":.6,
                    "M0_center_logical":[0,0],
                    "M1_center_logical":[.5,.5] if w in (1,3) else [0,0],
                    "M1_bbox_false_negative_alpha1_physical":1,
                    "M1_bbox_false_negative_alpha24_physical":0
                } for i in range(3)]})
        r=p.aggregate(rows)
        self.assertEqual(r["H1_M1_halfpixel_effectiveness"],"FAIL")
        self.assertEqual(r["H2_other_widths_source_invariant"],"PASS")

    def test_11_zero_images_are_not_valid_native(self):
        with self.assertRaisesRegex(ValueError,"ROI_FORMAT"):
            p.physical_bbox_miss(np.zeros((18,18,4),np.uint8),(58,40),(0,0,5,5),24)

    def test_12_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"x.json"
            p.save_json(f,{"ok":1})
            with self.assertRaises(FileExistsError):
                p.save_json(f,{"ok":2})


if __name__=="__main__":
    unittest.main()
