#!/usr/bin/env python3
"""P3b P0 native-mask subset proof: geometry samples and fail-closed evidence."""
import unittest

import numpy as np

from run_engine001_v43p3b_native_subset import (
    MAX_SAMPLE_PER_WIDTH, select_old_strokes, subset_result,
)


class P3bSubsetTests(unittest.TestCase):
    def test_whole_original_span_source_prefilter_never_trims(self):
        comp=np.zeros((240,460),dtype=np.bool_)
        comp[95:110,180:260]=True
        native=np.zeros((720,1380),dtype=np.uint8)
        native[285:330,540:780]=255
        strokes=[
            {"layer":"paint","stroke":{"strokeId":"icon-0","colorIndex":7,"width":2,
              "points":[{"x":180.0,"y":100.0},{"x":220.0,"y":100.0}]}},
            {"layer":"paint","stroke":{"strokeId":"icon-1","colorIndex":7,"width":2,
              "points":[{"x":150.0,"y":100.0},{"x":220.0,"y":100.0}]}},
            {"layer":"paint","stroke":{"strokeId":"icon-2","colorIndex":6,"width":2,
              "points":[{"x":180.0,"y":100.0},{"x":220.0,"y":100.0}]}},
        ]
        selection,meta=select_old_strokes({"strokes":strokes},comp,native)
        self.assertEqual([s["strokeId"] for s in selection],["icon-0"])
        self.assertEqual(meta["eligible_total"],1)
        self.assertEqual(len(selection),1)
        self.assertEqual(MAX_SAMPLE_PER_WIDTH,12)

    def test_native_subset_checks_all_owner_pixels_both_alpha_levels(self):
        owner=np.zeros((240,460),dtype=np.int16)
        owner[100,200]=7
        old=np.zeros((720,1380),dtype=np.uint8)
        oriented=np.zeros_like(old)
        old[300:303,600:603]=255
        oriented[300:303,600:603]=255
        ok=subset_result(old,oriented,owner)
        self.assertTrue(ok["potential_replacement_ONLY"])
        self.assertEqual(ok["alpha_thresholds"]["24"]["own_class_pixels_not_replaced"],0)
        oriented[300,600]=0
        bad=subset_result(old,oriented,owner)
        self.assertFalse(bad["potential_replacement_ONLY"])
        self.assertEqual(bad["alpha_thresholds"]["128"]["own_class_pixels_not_replaced"],1)

    def test_foreign_old_pixels_separately_reported_and_shape_rejected(self):
        owner=np.zeros((240,460),dtype=np.int16)
        owner[100,200]=7
        old=np.zeros((720,1380),dtype=np.uint8)
        oriented=np.zeros_like(old)
        old[300:303,600:603]=255
        old[305,605]=255
        oriented[300:303,600:603]=255
        result=subset_result(old,oriented,owner)
        self.assertEqual(result["alpha_thresholds"]["24"]["old_foreign_class_or_background_ink_pixels"],1)
        self.assertTrue(result["potential_replacement_ONLY"])
        with self.assertRaisesRegex(ValueError,"shape"):
            subset_result(old[:3],oriented,owner)


if __name__=="__main__":
    unittest.main()
