#!/usr/bin/env python3
"""V37-P2 source-sample color logic only; native brush is tested by Egret."""
import unittest
import numpy as np
from PIL import Image
from run_engine001_local_fill_color_native_v37p2 import (
    source_samples,lower_median,recolor_paint)

def make_stroke():
    return {"strokeId":"icon-123","width":2,"colorIndex":5,
            "colorRgb":0xDCBDAc,"points":[{"x":155.0,"y":2.0},
                                         {"x":159.0,"y":2.0}]}

class V37P2Samples(unittest.TestCase):
    def setUp(self):
        self.rgb=np.full((240,150,3),255,dtype=np.uint8)
        for x in range(5):
            self.rgb[2,x]=[200+x,100+x,50+x]
        self.source=Image.fromarray(self.rgb,"RGB")
        self.labels=np.full((240,460),-1,dtype=np.int32)
        self.labels[2,155:160]=5
        self.warm=np.zeros((240,150),dtype=bool)
        self.warm[2,:4]=True

    def test_five_owned_and_four_warm_source_pixels(self):
        own,warm,coords=source_samples(make_stroke(),self.source,
            self.labels,self.warm)
        self.assertEqual(len(own),5)
        self.assertEqual(len(warm),4)
        self.assertEqual(coords,[[155,2],[156,2],[157,2],[158,2],[159,2]])
        self.assertEqual(lower_median(own),[202,102,52])
        self.assertEqual(lower_median(warm),[201,101,51])

    def test_ownership_filter_stays_fail_closed(self):
        self.labels[2,156:160]=-1
        own,warm,coords=source_samples(make_stroke(),self.source,
            self.labels,self.warm)
        self.assertEqual(len(own),1)
        self.assertEqual(coords,[[155,2]])
        with self.assertRaises(ValueError):
            lower_median([])

    def test_invalid_geometry_rejected(self):
        s=make_stroke();s["width"]=1
        with self.assertRaisesRegex(ValueError,"frozen native"):
            source_samples(s,self.source,self.labels,self.warm)

    def test_invalid_variant_rejected(self):
        with self.assertRaisesRegex(ValueError,"unknown candidate"):
            recolor_paint({"strokes":[]},self.source,self.labels,self.warm,"D")

if __name__=="__main__":unittest.main()
