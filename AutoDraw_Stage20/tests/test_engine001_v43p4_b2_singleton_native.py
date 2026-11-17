#!/usr/bin/env python3
"""B2 micro-stroke: source identity, selection and metrics only; no Egret proxy."""
import math
import unittest
import numpy as np

from run_engine001_v43p4_b2_singleton_native import (
    OWNERS, WIDTHS, make_strokes, native_metrics, select_singletons,
)


class SingletonMicroStrokeB2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        labels=np.full((240,460),-1,dtype=np.int16)
        for i,owner in enumerate(OWNERS):
            for j in range(3):
                labels[20+i*50,170+j*40]=owner
        cls.labels=labels

    def test_deterministic_source_owned_singletons(self):
        one=select_singletons(self.labels)
        self.assertEqual(one,select_singletons(self.labels))
        self.assertEqual(len(one),12)
        self.assertEqual([x["owner"] for x in one],[4]*3+[5]*3+[6]*3+[7]*3)
        for i,a in enumerate(one):
            self.assertEqual(self.labels[a["y"],a["x"]],a["owner"])
            for b in one[:i]:
                self.assertGreaterEqual(math.hypot(a["x"]-b["x"],a["y"]-b["y"]),15)

    def test_fractional_points_are_nonzero_bounded_and_width_valid(self):
        sample=select_singletons(self.labels)
        for width in WIDTHS:
            strokes=make_strokes(sample,width)
            self.assertEqual(len(strokes),12)
            self.assertEqual(sum(len(s["points"]) for s in strokes),24)
            for i,s in enumerate(strokes):
                self.assertEqual(s["strokeId"],f"icon-{i}")
                self.assertEqual(s["width"],width)
                a,b=s["points"]
                self.assertAlmostEqual(math.hypot(b["x"]-a["x"],b["y"]-a["y"]),.25)
                self.assertGreaterEqual(a["x"],156)
                self.assertLess(b["x"],305)
                self.assertGreaterEqual(a["y"],0)
                self.assertLess(b["y"],240)
        with self.assertRaisesRegex(ValueError,"unsupported"):
            make_strokes(sample,10)

    def test_incomplete_sample_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"shape/type"):
            select_singletons(np.zeros((4,4),np.int16))
        broken=np.full((240,460),-1,np.int16)
        broken[50,170]=4
        with self.assertRaisesRegex(ValueError,"BLOCKED_SAMPLE"):
            select_singletons(broken)

    def test_native_rgba_singleton_tiles_and_no_borrowed_classes(self):
        samples=select_singletons(self.labels)
        native_labels=np.repeat(np.repeat(self.labels,3,axis=0),3,axis=1)
        rgba={key:np.zeros((720,1380,4),dtype=np.uint8)
              for key in ("composite","color-4","color-5","color-6","color-7")}
        for s in samples:
            x,y=s["x"],s["y"]
            rgba[f"color-{s['owner']}"][3*y:3*y+3,3*x:3*x+3,3]=255
        measured=native_metrics(rgba,native_labels,samples)
        for alpha in ("24","128"):
            for owner in OWNERS:
                row=measured[alpha][str(owner)]
                self.assertEqual(row["samples_hit"],3)
                self.assertEqual(row["fraction_of_target_3x3_pixels_hit"],1.0)
                self.assertEqual(row["foreign_required_pixels"],0)
                self.assertEqual(row["outside_silhouette_beyond_3logicalpx"],0)


if __name__=="__main__":
    unittest.main()
