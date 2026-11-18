"""P4D1 source-only stroke-order E2 contracts, not native brush acceptance."""
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d1_interleaved_fill_contour_native as d
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as parent


def stroke(x, y, color=17, width=2):
    return {"strokeId": "icon-0", "colorIndex":color,
            "colorRgb": color*65793, "width": width,
            "points":[{"x":float(x), "y":float(y)},
                      {"x":float(x)+.25, "y":float(y)}]}


class P4D1Contracts(unittest.TestCase):
    def test_01_id_original_source_reuse(self):
        self.assertEqual(d.EXPERIMENT,
                         "ENGINE001_B1R_P4D1_INTERLEAVED_SOURCE_OUTLINE_EGRET_V1")
        self.assertEqual(d.SOURCE,parent.SOURCE)
        self.assertEqual(d.SOURCE_SHA,parent.SOURCE_SHA)
        self.assertEqual(d.METHODS,parent.METHODS)
        self.assertEqual(d.ARMS,parent.ARMS)
        self.assertEqual(d.STAGES,
                         ("BASELINE_FILL_THEN_CONTOUR","INTERLEAVED_LOCAL"))
        code=Path(d.__file__).read_text("utf8")
        self.assertNotIn("import run_engine001_color32_p4c1",code)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",code)
        self.assertIn("p4d0.adaptive_unbounded(index, game)",code)
        self.assertIn("p4d0.first_scanline(index, game)",code)
        self.assertIn("p4c0.source_joint_outline(index, original, game)",code)

    def test_02_order_preserves_both_stroke_multisets(self):
        fills=[stroke(160,20,1),stroke(180,20,2),stroke(200,40,3),
               stroke(220,60,4),stroke(240,80,5)]
        outline=[stroke(160,20,10,1),stroke(240,80,10,1),
                 stroke(200,40,10,1)]
        plan,meta=d.interleave_nearest_fill(fills,outline)
        self.assertEqual(len(plan),8)
        self.assertTrue(meta["stroke_counts_identical"])
        self.assertTrue(meta["source_paint_order_identical"])
        self.assertTrue(meta["all_strokes_retained"])
        self.assertEqual(meta["paint_strokes"],5)
        self.assertEqual(meta["contour_strokes"],3)
        self.assertEqual(Counter(map(d.signature,plan)),
                         Counter(map(d.signature,fills+outline)))
        self.assertEqual([s["strokeId"] for s in plan],
                         ["icon-"+str(i) for i in range(8)])
        self.assertEqual([s["colorIndex"] for s in plan],
                         [10,1,2,10,3,4,10,5])
        self.assertEqual(meta["contour_paint_transitions"],6)
        self.assertEqual(meta["unique_paint_anchor_slots"],3)

    def test_03_deterministic_and_does_not_mutate_inputs(self):
        fills=[stroke(155+i*15,30+i,3) for i in range(5)]
        contours=[stroke(155,30,19,1),stroke(215,34,19,1)]
        before=[d.signature(s) for s in fills+contours]
        a,t1=d.interleave_nearest_fill(fills,contours)
        b,t2=d.interleave_nearest_fill(fills,contours)
        self.assertEqual(a,b)
        self.assertEqual(t1,t2)
        self.assertEqual(before,[d.signature(s) for s in fills+contours])

    def test_04_contour_starts_before_nearby_paint_not_final_layer(self):
        fills=[stroke(160,20),stroke(180,20),stroke(200,20),stroke(220,20)]
        outline=[stroke(160,20,99,1),stroke(220,20,99,1)]
        plan,meta=d.interleave_nearest_fill(fills,outline)
        self.assertEqual(plan[0]["colorIndex"],99)
        self.assertEqual(plan[-2]["colorIndex"],99)
        self.assertEqual(plan[-1]["colorIndex"],17)
        self.assertGreater(meta["contour_paint_transitions"],1)

    def test_05_ties_choose_earliest_paint(self):
        fills=[stroke(160,20),stroke(180,20),stroke(200,20),stroke(220,20)]
        outline=[stroke(170,20,99,1),stroke(220,20,99,1)]
        plan,meta=d.interleave_nearest_fill(fills,outline)
        self.assertEqual(meta["first_paint_anchor"],0)
        self.assertEqual(meta["last_paint_anchor"],3)
        self.assertEqual(plan[0]["colorIndex"],99)

    def test_06_empty_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"EMPTY"):
            d.interleave_nearest_fill([], [stroke(160,20)])
        with self.assertRaisesRegex(ValueError,"EMPTY"):
            d.interleave_nearest_fill([stroke(160,20)], [])

    def test_07_outside_board_rejected(self):
        with self.assertRaisesRegex(ValueError,"COORDINATE"):
            d.interleave_nearest_fill([stroke(-1,20),stroke(190,10)],
                                      [stroke(190,10)])
        with self.assertRaisesRegex(ValueError,"COORDINATE"):
            d.interleave_nearest_fill([stroke(160,20),stroke(190,10)],
                                      [stroke(500,10)])

    def test_08_invalid_polyline_lengths_rejected(self):
        malformed=stroke(160,20)
        malformed["points"]=[{"x":160.,"y":20.}]
        with self.assertRaisesRegex(ValueError,"POINT_COUNT"):
            d.interleave_nearest_fill([malformed,stroke(190,10)],
                                      [stroke(190,10)])
        malformed=stroke(160,20)
        malformed["points"]=malformed["points"]*65
        with self.assertRaisesRegex(ValueError,"POINT_COUNT"):
            d.interleave_nearest_fill([malformed,stroke(190,10)],
                                      [stroke(190,10)])

    def test_09_identical_source_rgb_coordinates_and_width(self):
        fills=[stroke(155,0,7,1),stroke(180,1,8,10),
               stroke(205,2,3,5),stroke(230,3,11,2)]
        outline=[stroke(180,1,22,1),stroke(205,2,22,1)]
        plan,_=d.interleave_nearest_fill(fills,outline)
        self.assertEqual(sorted(s["width"] for s in plan),
                         sorted(s["width"] for s in fills+outline))
        self.assertEqual(Counter(d.signature(x) for x in plan),
                         Counter(d.signature(x) for x in fills+outline))

    def test_10_native_only_and_no_live_or_chalk_claims(self):
        code=Path(d.__file__).read_text("utf8")
        self.assertIn("with p4d0.patched_test_renderer(renderer)",code)
        self.assertIn("with p4b7.native_egret_session(workspace)",code)
        self.assertIn("renderP4A2BrushWidths1to10Probe(arguments[0]);",code)
        self.assertIn('\"production_promotion\":False',code)
        self.assertIn('\"exact_run_bound_CHALK\":None',code)
        self.assertIn('\"frozen_99_0protected_3logical\":\"NOT_MEASURED_COMPOSITE_ONLY\"',
                      code)
        self.assertEqual(d.P4D0_PARENT_BLOB,
                         "cf4f0b0b8a1fef5879067f41901f2806758e81bd")


if __name__=="__main__":
    unittest.main()
