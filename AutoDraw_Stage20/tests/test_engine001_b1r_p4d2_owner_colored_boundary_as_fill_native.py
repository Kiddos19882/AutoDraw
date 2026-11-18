"""P4D2: source color owner boundary-as-paint contracts (MODEL_ONLY unit geometry)."""
import unittest
from collections import Counter
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d2_owner_colored_boundary_as_fill_native as d
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0


def palette():
    arr = np.arange(128*3,dtype=np.uint8).reshape(128,3)
    arr[6] = 255
    return arr


def idx():
    arr=np.full((240,150),6,np.uint8)
    arr[2:6,5:9]=21
    arr[8:13,12:19]=34
    arr[13,13]=34
    return arr


def paint(owner,game,x,y=0,width=2):
    return p4d0._stroke(owner,game,x+.125,x+.375,y,width=width)


class P4D2UnitTests(unittest.TestCase):
    def test_01_id_and_no_global_dark_contour_source(self):
        self.assertEqual(d.EXPERIMENT,
                         "ENGINE001_B1R_P4D2_OWNER_COLORED_BOUNDARY_AS_FILL_NATIVE_V1")
        self.assertEqual(d.SOURCE,p4d0.SOURCE)
        self.assertEqual(d.METHODS,p4d0.METHODS)
        self.assertEqual(d.ARMS,p4d0.ARMS)
        code=Path(d.__file__).read_text("utf8")
        self.assertNotIn("source_joint_outline(",code)
        self.assertNotIn("import run_engine001_color32_p4c1",code)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",code)
        self.assertIn("p4d0.adaptive_unbounded(index,palette)",code)
        self.assertIn("p4d0.first_scanline(index,palette)",code)
        self.assertIn("p4d0.patched_test_renderer(renderer)",code)

    def test_02_boundary_is_inside_own_owner_not_whitespace(self):
        arr=idx()
        bound=d.owner_inner_boundary(arr)
        self.assertEqual(bound.dtype,np.bool_)
        self.assertFalse(np.any(bound[arr==6]))
        self.assertFalse(bound[3,6]) # 4x4 block center
        self.assertTrue(bound[2,6])
        self.assertTrue(bound[3,5])
        self.assertTrue(bound[5,7])
        self.assertTrue(bound[13,13]) # singleton

    def test_03_4_neighbor_outer_frame_counts_as_inner_edge(self):
        a=np.full((240,150),7,np.uint8)
        edge=d.owner_inner_boundary(a)
        self.assertTrue(edge[0,0])
        self.assertTrue(edge[239,149])
        self.assertFalse(edge[3,3])
        self.assertFalse(edge[120,75])
        self.assertEqual(int(edge.sum()),240*2+150*2-4)

    def test_04_runs_include_every_edge_source_pixel(self):
        a=idx()
        runs,edge=d.source_boundary_runs(a,palette())
        re=np.zeros_like(edge)
        for r in runs:
            re[r["y"],r["x0"]:r["x1"]+1]=True
            self.assertTrue(np.all(a[r["y"],r["x0"]:r["x1"]+1]==r["owner"]))
            self.assertEqual(r["stroke"]["width"],1)
            self.assertEqual(r["stroke"]["colorIndex"],r["owner"])
            self.assertEqual(r["stroke"]["colorRgb"],
                             d._rgbpack(palette()[r["owner"]]))
            self.assertEqual(len(r["stroke"]["points"]),2)
        self.assertTrue(np.array_equal(re,edge))
        self.assertTrue(all(r["owner"] in (21,34) for r in runs))

    def test_05_adaptive_colored_edges_locally_after_owner_fill(self):
        game=palette()
        a=idx()
        runs,_=d.source_boundary_runs(a,game)
        fill=[paint(21,game,5,2),paint(21,game,6,3),
              paint(34,game,12,8),paint(34,game,13,9)]
        plan=d.adaptive_owner_fill_with_edges(fill,runs,game)
        self.assertEqual(len(plan),len(fill)+len(runs))
        self.assertEqual(Counter(map(d.identity,plan)),
                         Counter(map(d.identity,fill+[r["stroke"] for r in runs])))
        self.assertEqual([p["colorIndex"] for p in plan[:2]],[21,21])
        self.assertEqual(plan[2]["colorIndex"],21)
        self.assertEqual(plan[2]["width"],1)
        self.assertEqual([p["colorIndex"] for p in plan[-2:]],[34,34])

    def test_06_adaptive_non_grouped_fails_closed(self):
        game=palette()
        runs,_=d.source_boundary_runs(idx(),game)
        parent=[paint(21,game,5,2),paint(34,game,12,8),
                paint(21,game,6,3)]
        with self.assertRaisesRegex(ValueError,"NOT_OWNER_GROUPED"):
            d.adaptive_owner_fill_with_edges(parent,runs,game)

    def test_07_scanline_still_topdown_left_to_right(self):
        a=idx()
        game=palette()
        parent=p4d0.first_scanline(a,game)
        runs,_=d.source_boundary_runs(a,game)
        result=d.scanline_fill_with_edges(parent,runs,a,game)
        self.assertEqual(len(result),len(parent)+len(runs))
        self.assertEqual(Counter(map(d.identity,result)),
                         Counter(map(d.identity,parent+[r["stroke"] for r in runs])))
        positions=[(float(s["points"][0]["y"]),float(s["points"][0]["x"]))
                   for s in result]
        # Boundary stroke naturally sits inside its same-color parent run.
        self.assertEqual([y for y,_ in positions],sorted(y for y,_ in positions))
        self.assertEqual({s["width"] for s in result},{1,2})

    def test_08_scanline_source_color_tamper_fails_closed(self):
        a=idx()
        game=palette()
        parent=p4d0.first_scanline(a,game)
        parent[0]["colorRgb"]=0
        runs,_=d.source_boundary_runs(a,game)
        with self.assertRaisesRegex(ValueError,"PAINT_RGB_MISMATCH"):
            d.scanline_fill_with_edges(parent,runs,a,game)

    def test_09_invalid_index_and_palette_fail_closed(self):
        a=idx()
        with self.assertRaisesRegex(ValueError,"INVALID_ORIGINAL_INDEX"):
            d.owner_inner_boundary(a[1:])
        with self.assertRaisesRegex(ValueError,"INVALID_ORIGINAL_INDEX"):
            d.owner_inner_boundary(a.astype(np.int16))
        with self.assertRaisesRegex(ValueError,"PALETTE"):
            d.source_boundary_runs(a,np.zeros((32,3),np.uint8))

    def test_10_no_foreign_added_boundary_color(self):
        a=idx()
        game=palette()
        entries,_=d.source_boundary_runs(a,game)
        self.assertGreater(len(entries),0)
        for e in entries:
            s=e["stroke"]
            self.assertEqual(s["colorIndex"],e["owner"])
            self.assertEqual(s["colorRgb"],d._rgbpack(game[e["owner"]]))
            self.assertNotEqual(e["owner"],6)

    def test_11_no_fake_owner_native_chalk_promotion(self):
        code=Path(d.__file__).read_text("utf8")
        self.assertIn('"production_promotion":False',code)
        self.assertIn('"exact_run_bound_CHALK":None',code)
        self.assertIn('"frozen_owner99_protected0_far3":"NOT_MEASURED_COMPOSITE_ONLY"',code)
        self.assertIn('p4b7.native_egret_session(workspace)',code)
        self.assertIn("renderP4A2BrushWidths1to10Probe(arguments[0]);",code)
        self.assertEqual(d.P4D0_PARENT_BLOB,
                         "cf4f0b0b8a1fef5879067f41901f2806758e81bd")


if __name__=="__main__":
    unittest.main()
