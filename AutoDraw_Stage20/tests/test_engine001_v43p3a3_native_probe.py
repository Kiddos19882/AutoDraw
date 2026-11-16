#!/usr/bin/env python3
"""P3a3 route identity and alpha metric tests; native capture is Windows CI."""
import unittest

import numpy as np

from run_engine001_v43p3a3_native_probe import (
    make_probe_strokes, native_footprint_metrics,
)


class V43P3a3ProbeTests(unittest.TestCase):
    def test_frozen_first_three_routes_only(self):
        data={"width":20,"candidate_strokes":[
            {"width":20,"points":[{"x":170+i,"y":100},{"x":180+i,"y":100}],
             "safe_to_execute":False} for i in range(5)]}
        strokes=make_probe_strokes(data,20)
        self.assertEqual(len(strokes),3)
        self.assertEqual([s["strokeId"] for s in strokes],
                         ["icon-0","icon-1","icon-2"])
        self.assertTrue(all(s["colorIndex"]==7 and s["width"]==20
                            for s in strokes))
        self.assertNotEqual(id(strokes[0]["points"]),id(data["candidate_strokes"][0]["points"]))
        with self.assertRaisesRegex(ValueError,"width"):
            make_probe_strokes(data,30)

    def test_empty_width_is_valid_not_fabricated(self):
        self.assertEqual(make_probe_strokes({"width":30,"candidate_strokes":[]},30),[])

    def test_native_alpha_metrics_tolerance_and_shapes(self):
        owner=np.zeros((240,460),dtype=np.int16)
        component=np.zeros((240,460),dtype=np.bool_)
        owner[20:60,200:250]=7
        component[20:60,200:250]=True
        native=np.zeros((720,1380),dtype=np.uint8)
        native[90:93,690:693]=255  # inside class7
        native[90:93,780:783]=255  # outside class7, far from component
        result=native_footprint_metrics(native,owner,component)
        self.assertEqual(result["24"]["native_backing_ink_pixels"],18)
        self.assertEqual(result["128"]["native_backing_ink_pixels"],18)
        self.assertEqual(result["24"]["native_ink_inside_owner7"],9)
        self.assertEqual(result["24"]["native_ink_outside_component_more_than_3logical_px"],9)
        with self.assertRaisesRegex(ValueError,"scale"):
            native_footprint_metrics(native[:3],owner,component)


if __name__=="__main__":
    unittest.main()
