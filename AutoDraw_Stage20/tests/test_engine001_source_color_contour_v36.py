#!/usr/bin/env python3
"""V36 color-only candidate tests; native width1 acceptance is a separate CI."""
import unittest
import numpy as np
from PIL import Image
from run_engine001_source_color_contour_native_v36 import medians_for_path,recolor

def base_plan():
    paint={"strokeId":"icon-0","width":2,"colorIndex":5,"colorRgb":0xAABBCC,
           "points":[{"x":156.0,"y":1.0},{"x":157.0,"y":1.0}]}
    contour={"strokeId":"detail-v18-B-0","width":1,"colorIndex":100,
             "colorRgb":0x31262B,"points":[{"x":155.0,"y":0.0},
                                             {"x":156.0,"y":0.0}]}
    # Recolor expects frozen 297 detail routes: small synthetic tests validate
    # the sampler and reject drift, not the complete production count.
    return {"paint_strokes":1,"detail_strokes":1,"synthetic_vertices_NOT_CHALK":4,
            "strokes":[{"layer":"paint","stroke":paint},
                       {"layer":"detail","stroke":contour}]}

class V36ContourTests(unittest.TestCase):
    def test_lower_median_source_coordinates(self):
        a=np.full((240,150,3),255,np.uint8)
        a[0,0]=[10,20,30];a[0,1]=[110,120,130]
        src=Image.fromarray(a,"RGB")
        self.assertEqual(medians_for_path(src,[
            {"x":155.0,"y":0.0},{"x":156.0,"y":0.0}]),[10,20,30])
    def test_source_bounds_and_nonfinite_fail_closed(self):
        src=Image.new("RGB",(150,240),"white")
        for x in [154.9,305.0,float("nan"),float("inf")]:
            with self.subTest(x=x),self.assertRaises(ValueError):
                medians_for_path(src,[{"x":x,"y":1.0}])
    def test_plan_count_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"count/vertex drift"):
            recolor(base_plan(),Image.new("RGB",(150,240),"white"),"B")
    def test_invalid_variant_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid candidate"):
            recolor(base_plan(),Image.new("RGB",(150,240),"white"),"Q")

if __name__=="__main__":unittest.main()
