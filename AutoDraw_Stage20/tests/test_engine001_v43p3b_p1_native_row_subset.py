#!/usr/bin/env python3
"""V43-P3b/P1 isolated native row intersection selection, never full paint."""
import unittest
import numpy as np

from run_engine001_v43p3b_p1_native_row_subset import rank_old_strokes
from run_engine001_v43p3b_native_subset import MAX_SAMPLE_PER_WIDTH


def original_fixture():
    paint=[]
    for i in range(1945):
        color=7 if i in (2,5,8) else 6
        paint.append({"layer":"paint","stroke":{
            "strokeId":f"icon-{i}","colorIndex":color,"colorRgb":0x31262B,
            "width":2,
            "points":[{"x":180.0,"y":110.0},{"x":190.0,"y":110.0}]}})
    detail=[{"layer":"detail","stroke":{"strokeId":f"detail-v18-B-{i}",
            "width":1,"colorRgb":0x31262B,
            "points":[{"x":180,"y":100},{"x":190,"y":100}]}}
            for i in range(410)]
    return {"paint_strokes":1945,"detail_strokes":410,
            "synthetic_vertices_NOT_CHALK":5682,
            "strokes":paint+detail}


class NativeRowRankingTests(unittest.TestCase):
    def test_ranking_uses_native_row_pixels_and_order_tiebreak(self):
        p=original_fixture()
        native=np.zeros((720,1380),dtype=np.uint8)
        native[330:333,540:543]=255  # x180 y110 intersects all 3 source class7
        selected,meta=rank_old_strokes(p,native)
        self.assertEqual(meta["eligible_positive_score"],3)
        self.assertEqual(meta["selected_IDs_in_ranking_order"],
                         ["icon-2","icon-5","icon-8"])
        self.assertEqual([x["native_candidate_row_alpha24_score"]
                          for x in selected],[9,9,9])
        self.assertEqual(MAX_SAMPLE_PER_WIDTH,12)

    def test_partial_old_line_overlap_is_eligible_not_auto_replaced(self):
        p=original_fixture()
        native=np.zeros((720,1380),dtype=np.uint8)
        native[330,570]=24  # one ink pixel near end of x180..190
        selected,meta=rank_old_strokes(p,native)
        self.assertEqual(meta["eligible_positive_score"],3)
        self.assertTrue(all(x["native_candidate_row_alpha24_score"]==1 for x in selected))
        self.assertEqual(meta["selection"],
                         "P1_REAL_NATIVE_INK_SOURCE_ROW_RANKING_NOT_FULL_REPLACEMENT")

    def test_frozen_plan_and_native_shape_fail_closed(self):
        p=original_fixture()
        native=np.zeros((720,1380),dtype=np.uint8)
        with self.assertRaisesRegex(ValueError,"shape/type"):
            rank_old_strokes(p,native[:2])
        broken=dict(p,paint_strokes=1944)
        with self.assertRaisesRegex(ValueError,"counts"):
            rank_old_strokes(broken,native)
        p["strokes"][2]["stroke"]["points"][0]["x"]=150
        with self.assertRaisesRegex(ValueError,"geometry"):
            rank_old_strokes(p,native)


if __name__=="__main__":
    unittest.main()
