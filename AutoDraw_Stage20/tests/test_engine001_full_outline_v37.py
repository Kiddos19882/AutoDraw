#!/usr/bin/env python3
"""V37-P1 frozen full 410-contour trial: static color-only contract tests."""
import unittest
from pathlib import Path
from PIL import Image
from run_engine001_full_outline_native_v37 import (
    full_recolor, frozen_full_outline)

def fixture():
    one={"layer":"paint","stroke":{"strokeId":"icon-1","width":2,
         "colorIndex":5,"colorRgb":0xAABBCC,
         "points":[{"x":155.0,"y":0.0},{"x":155.25,"y":0.0}]}}
    details=[{"layer":"detail","stroke":{
         "strokeId":f"detail-v18-B-{i}","width":1,"colorIndex":100,
         "colorRgb":0x31262B,"points":[{"x":155.0,"y":0.0},{"x":156.0,"y":0.0}]}}
         for i in range(410)]
    return {"strokes":[one]+details,"synthetic_vertices_NOT_CHALK":5682,
            "paint_strokes":1945,"detail_strokes":410}

class FullOutlineTests(unittest.TestCase):
    def test_reject_wrong_total_stroke_count(self):
        with self.assertRaisesRegex(ValueError,"complete contour"):
            full_recolor(fixture(),Image.new("RGB",(150,240),"white"),"A")
    def test_reject_unknown_candidate(self):
        with self.assertRaisesRegex(ValueError,"candidate"):
            full_recolor(fixture(),Image.new("RGB",(150,240),"white"),"D")
    def test_source_bounded_sampler_failure(self):
        x=fixture()
        x["strokes"][1]["stroke"]["points"][0]["x"]=154.0
        with self.assertRaisesRegex(ValueError,"outside source ROI"):
            full_recolor(x,Image.new("RGB",(150,240),"white"),"C")
if __name__=="__main__":unittest.main()
