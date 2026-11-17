#!/usr/bin/env python3
"""Preflight B3 isolated contour probe without creating false Egret metrics."""
import unittest
import cv2
import numpy as np

from run_engine001_v43p4_b3_contour_native_probe import (
    EXP, OWNER_RGB, select_native_ring_probes,
)
from run_engine001_v43p4_b3_contour_source import _footprint


class NativeRingPreflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        labels = np.zeros((240,150),np.int16)
        cv2.circle(labels,(37,44),24,4,-1)
        cv2.circle(labels,(113,44),27,5,-1)
        cv2.circle(labels,(34,164),29,6,-1)
        cv2.circle(labels,(108,167),31,7,-1)
        cls.labels=labels

    def test_all_four_owners_and_frozen_color(self):
        p,elig = select_native_ring_probes(self.labels)
        self.assertLessEqual(len(p),16)
        self.assertTrue(p)
        self.assertEqual(set(s["colorIndex"] for s in p),set(OWNER_RGB))
        self.assertEqual(len(elig),16)
        self.assertEqual(len({s["strokeId"] for s in p}),len(p))
        for path in p:
            self.assertEqual(path["colorRgb"],OWNER_RGB[path["colorIndex"]])
            self.assertIn(path["width"],(10,6,4,2))
            self.assertTrue(2<=len(path["points"])<=128)
            self.assertTrue(path["strokeId"].startswith("icon-"))
            self.assertTrue(all(155<=q["x"]<305 and 0<=q["y"]<240
                                for q in path["points"]))

    def test_deterministic_sample_and_3px_source_preflight(self):
        a,b=select_native_ring_probes(self.labels)
        self.assertEqual((a,b),select_native_ring_probes(self.labels))
        for s in a:
            mask = self.labels==s["colorIndex"]
            dist = cv2.distanceTransform(
                (~mask).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
            points=[(p["x"]-155,p["y"]) for p in s["points"]]
            ink=_footprint(points,s["width"])
            self.assertFalse(np.any(ink & (dist>3.0)))

    def test_bad_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"source labels"):
            select_native_ring_probes(np.zeros((240,149),np.int16))
        with self.assertRaisesRegex(ValueError,"sample size"):
            select_native_ring_probes(np.zeros((240,150),np.int16))


if __name__=="__main__":
    unittest.main()
