#!/usr/bin/env python3
"""V43-P3a only validates source geometry and provenance, NOT game brush alpha."""
import unittest
import cv2
import numpy as np

from run_engine001_v43p3_oriented_source import (
    WIDTHS, INTERIOR_MARGIN, oriented_source_candidates,
)


class OrientedSourceV43P3aTests(unittest.TestCase):
    def setUp(self):
        self.mask=np.zeros((240,460), dtype=np.bool_)
        self.mask[70:119, 180:285]=True
        self.distance=cv2.distanceTransform(
            np.pad(self.mask.astype(np.uint8),1),
            cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[1:-1,1:-1]

    def test_fixed_width_source_owned_interior_and_determinism(self):
        for width in WIDTHS:
            a=oriented_source_candidates(self.mask,self.distance,width)
            b=oriented_source_candidates(self.mask,self.distance,width)
            self.assertEqual(a,b)
            self.assertFalse(a["safe_to_execute"])
            self.assertGreater(a["count"],0)
            self.assertGreater(abs(a["axis_xy"][0]),abs(a["axis_xy"][1]))
            for stroke in a["candidate_strokes"]:
                self.assertEqual(stroke["width"],width)
                self.assertFalse(stroke["safe_to_execute"])
                self.assertEqual(len(stroke["points"]),2)
                for p in stroke["points"]:
                    x,y=int(p["x"]),int(p["y"])
                    self.assertTrue(0 <= x < 460 and 0 <= y < 240)
                    self.assertTrue(self.mask[y,x])
                    self.assertGreaterEqual(self.distance[y,x],
                                            width/2+INTERIOR_MARGIN)

    def test_tiny_component_returns_no_wide_lines(self):
        mask=np.zeros((240,460),dtype=np.bool_)
        mask[100,200]=True
        distance=cv2.distanceTransform(
            np.pad(mask.astype(np.uint8),1),cv2.DIST_L2,
            cv2.DIST_MASK_PRECISE)[1:-1,1:-1]
        for width in WIDTHS:
            self.assertEqual(oriented_source_candidates(mask,distance,width)["count"],0)

    def test_invalid_geometry_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):
            oriented_source_candidates(self.mask,self.distance,30)
        with self.assertRaisesRegex(ValueError,"source mask"):
            oriented_source_candidates(self.mask[:5],self.distance[:5],4)
        broken=self.distance.copy()
        broken[0,0]=float("nan")
        with self.assertRaisesRegex(ValueError,"source mask"):
            oriented_source_candidates(self.mask,broken,4)


if __name__=="__main__":
    unittest.main()
