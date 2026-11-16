#!/usr/bin/env python3
"""V43-P2a only: deterministic native wide-brush eligibility, not brush model."""
import unittest

import numpy as np

from test_engine001_endpoint_extension_v40p2 import plan
from run_engine001_native_wide_interior_v43p2a import select_interior


class V43NativeWidthSelectionTests(unittest.TestCase):
    def setUp(self):
        self.base=plan()  # reuse existing frozen full 410-contour fixture
        self.base["strokes"][0]["stroke"]["colorIndex"]=7
        self.mask=np.zeros((240,460),dtype=bool)
        self.mask[5,155:170]=True
        self.distance=np.zeros((240,460),dtype=np.float32)
        self.distance[5,155:170]=8.0

    def test_B_and_C_only_recolor_width_of_deep_dark_stroke(self):
        a,aa=select_interior(self.base,self.mask,self.distance,2,0.0)
        b,bb=select_interior(self.base,self.mask,self.distance,4,4.0)
        c,cc=select_interior(self.base,self.mask,self.distance,6,5.0)
        self.assertEqual(a,self.base)
        self.assertEqual(b["strokes"][0]["stroke"]["width"],4)
        self.assertEqual(c["strokes"][0]["stroke"]["width"],6)
        self.assertTrue(bb[0]["selected"])
        self.assertTrue(cc[0]["selected"])
        self.assertEqual(len(bb),1945)
        for variant in (b,c):
            self.assertEqual(variant["strokes"][1945:],self.base["strokes"][1945:])
            self.assertEqual(variant["strokes"][0]["stroke"]["points"],
                             self.base["strokes"][0]["stroke"]["points"])
            self.assertEqual(variant["synthetic_vertices_NOT_CHALK"],5682)
            self.assertEqual(variant["strokes"][1]["stroke"]["width"],2)
        self.assertEqual(self.base["strokes"][0]["stroke"]["width"],2)

    def test_shallow_component_not_selected(self):
        self.distance[5,155:170]=3.9
        b,j=select_interior(self.base,self.mask,self.distance,4,4.0)
        self.assertFalse(j[0]["selected"])
        self.assertEqual(b["strokes"][0]["stroke"]["width"],2)

    def test_wrong_source_component_not_selected(self):
        self.mask[5,155:170]=False
        b,j=select_interior(self.base,self.mask,self.distance,4,4.0)
        self.assertFalse(j[0]["selected"])

    def test_fail_closed_unknown_width_and_broken_resource(self):
        with self.assertRaisesRegex(ValueError,"unexpected native width"):
            select_interior(self.base,self.mask,self.distance,8,4.0)
        broken=dict(self.base)
        broken["synthetic_vertices_NOT_CHALK"]=5683
        with self.assertRaisesRegex(ValueError,"counts changed"):
            select_interior(broken,self.mask,self.distance,4,4.0)

if __name__=="__main__":
    unittest.main()
