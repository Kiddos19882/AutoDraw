#!/usr/bin/env python3
"""ENGINE-001 P4b: frozen V44-B contour E3 over MODEL_ONLY raster backgrounds."""
import unittest

import numpy as np
from PIL import Image

from run_engine001_color32_s2b_p4b_v44b_hybrid import (
    BACKING_SIZE, ROI_BOX, compose, validate_original_detail_plan,
)


def fixture_plan():
    source=[]
    for i in range(1945):
        source.append({"layer":"paint","stroke":{
            "strokeId":f"icon-{i}", "width":2,
            "colorIndex":4, "colorRgb":0x1B1B1B,
            "points":[{"x":155.,"y":10.},{"x":156.,"y":10.}],
        }})
    for i in range(410):
        source.append({"layer":"detail","stroke":{
            "strokeId":f"detail-v18-B-{i}",
            "width":1,"colorIndex":100,"colorRgb":0x302D2A,
            "points":[{"x":155.,"y":10.} for _ in
                      range(5 if i<152 else 4)],
        }})
    # 152*5+258*4=1792 original detail vertices
    assert sum(len(x["stroke"]["points"]) for x in source[-410:])==1792
    return {"experiment":"ENGINE001_ADAPTIVE_COLOR_OUTLINE_V44_P1",
            "baseline":"V37-P2-C","plans":{"B":{"strokes":source}}}


class OriginalEgretHybridTests(unittest.TestCase):
    def test_exact_original410_last_only_and_width_one(self):
        diag=validate_original_detail_plan(fixture_plan())
        self.assertEqual(diag["original_contours_LAST"],410)
        self.assertEqual(diag["detail_vertices_NOT_CHALK"],1792)
        self.assertEqual(diag["native_width"],1)
        self.assertTrue(diag["geometry_color_order_unmodified"])

    def test_bad_first_original_detail_id_and_wrong_order_are_blocked(self):
        data=fixture_plan()
        data["plans"]["B"]["strokes"][-410]["stroke"]["strokeId"]="incorrect"
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4B_ORIGINAL_410_DETAIL_IDENTITY"):
            validate_original_detail_plan(data)
        data=fixture_plan()
        data["plans"]["B"]["strokes"][-411]["stroke"]["colorIndex"]=100
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4B_COLOR_100_CONTAINS_PAINT"):
            validate_original_detail_plan(data)

    def test_hybrid_backing_is_not_native_brush_or_game(self):
        raw=Image.new("RGB",(150,240),(250,170,140))
        detail=Image.new("RGBA",BACKING_SIZE,(0,0,0,0))
        alpha=np.array(detail)
        alpha[90:96,480:486,:]=[30,20,10,255]
        detail=Image.fromarray(alpha,"RGBA")
        before,after=compose(raw,detail)
        self.assertEqual(before.size,BACKING_SIZE)
        self.assertEqual(after.size,BACKING_SIZE)
        self.assertEqual(before.getpixel((0,100)),(255,255,255,255))
        self.assertEqual(before.getpixel((465,100)),(250,170,140,255))
        self.assertEqual(after.getpixel((483,93)),(30,20,10,255))
        self.assertEqual(after.getpixel((500,100)),(250,170,140,255))
        self.assertEqual(raw.getpixel((0,0)),(250,170,140))
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4B_NATIVE_CONTOUR_BACKING"):
            compose(raw,Image.new("RGBA",(450,720),(0,0,0,0)))


if __name__=="__main__":
    unittest.main()
