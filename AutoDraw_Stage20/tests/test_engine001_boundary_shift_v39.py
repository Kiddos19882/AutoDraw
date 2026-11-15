#!/usr/bin/env python3
"""V39 immutable row-shift candidate tests; no native brush model."""
import unittest
import numpy as np
from run_engine001_boundary_shift_native_v39 import decide_shift,displaced

def stroke(y=5):
    return {"strokeId":"icon-0","width":2,"colorRgb":0x112233,
            "colorIndex":5,"points":[{"x":156.0,"y":float(y)},
                                     {"x":160.0,"y":float(y)}]}

class V39ShiftTests(unittest.TestCase):
    def setUp(self):
        self.labels=np.full((240,460),-1,np.int16)
        self.labels[5,156:161]=5
    def test_count_based_direction_and_no_shift_on_equal(self):
        s=stroke()
        self.labels[6,156:161]=5
        self.assertEqual(decide_shift(s,self.labels),1)
        self.labels[4,156:161]=5
        self.assertEqual(decide_shift(s,self.labels),0)
        self.labels[6,156:161]=-1
        self.assertEqual(decide_shift(s,self.labels),-1)
    def test_border_and_wrong_width_reject(self):
        self.assertEqual(decide_shift(stroke(239),self.labels),0)
        s=stroke();s["width"]=3
        with self.assertRaisesRegex(ValueError,"nonfrozen"):
            decide_shift(s,self.labels)
    def test_immutable_original_exact_contour(self):
        self.labels[6,156:161]=5
        s=stroke()
        detail={"strokeId":"detail-v18-B-0","width":1,"colorRgb":0x31262B,
                "colorIndex":100,"points":[{"x":159.0,"y":5.0},{"x":160.0,"y":5.0}]}
        base={"synthetic_vertices_NOT_CHALK":5682,"strokes":[
           {"layer":"paint","stroke":s},
           {"layer":"detail","stroke":detail}]}
        # Frozen full fill must contain exactly 1945 rows, so partial fixture is rejected.
        with self.assertRaisesRegex(ValueError,"resource count drift"):
            displaced(base,self.labels,0.25)
        self.assertEqual(s["points"][0]["y"],5.0)
        self.assertEqual(detail["points"][0]["y"],5.0)
    def test_invalid_amplitude(self):
        with self.assertRaisesRegex(ValueError,"invalid preregistered"):
            displaced({"strokes":[]},self.labels,0.4)

if __name__=="__main__":
    unittest.main()
