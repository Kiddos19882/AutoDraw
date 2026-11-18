#!/usr/bin/env python3
"""E2 contracts for P4B7; synthetic fixtures never count as native evidence."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np
import run_engine001_b1r_p4b7_native_stroke_attribution as p


def strokes(count=8):
    return [
        {"strokeId": "icon-%d" % i, "width": 2, "colorIndex": 115,
         "colorRgb": 0x5A4941,
         "points": [{"x": 160.0+i, "y": 80.0},
                    {"x": 161.0+i, "y": 80.0}]}
        for i in range(count)]


class P4B7Contracts(unittest.TestCase):
    def test_01_id_and_frozen_scope(self):
        self.assertEqual(p.EXPERIMENT, "ENGINE001_B1R_P4B7_NATIVE_STROKE_ATTRIBUTION_V1")
        self.assertEqual(p.ARM, "G1_0")
        self.assertEqual(p.ALPHA_GATE, 24)
        self.assertEqual(p.EXPECTED_TARGETS, 2)
        self.assertEqual(p.MAX_SPLIT_REPLAYS, 48)
        self.assertEqual(p.MAX_LOO_REPLAYS, 12)

    def test_02_renumber_subset_stable_geometry(self):
        base=strokes()
        child=p.normalized_subset(base,(0,3,7))
        self.assertEqual([x["strokeId"] for x in child],
                         ["icon-0","icon-1","icon-2"])
        self.assertEqual(child[1]["points"],base[3]["points"])
        child[1]["points"][0]["x"]=999.
        self.assertNotEqual(child[1]["points"],base[3]["points"])

    def test_03_reject_duplicate_or_unsorted_index(self):
        for index in ((0,0),(2,1),(-1,), (8,), ()):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    p.normalized_subset(strokes(),index)

    def test_04_reject_width_and_nonfinite_source(self):
        a=strokes()
        a[0]["width"]=11
        with self.assertRaises(ValueError):
            p.normalized_subset(a,(0,))
        b=strokes()
        b[0]["points"][0]["x"]=float("nan")
        with self.assertRaises(ValueError):
            p.normalized_subset(b,(0,))

    def test_05_protected_targets_actual_backing_only(self):
        rgba=np.zeros(p.p4b5.BACKING,np.uint8)
        owner=np.zeros(p.p4b5.SHAPE,bool)
        protected=np.zeros(p.p4b5.SHAPE,bool)
        owner[40,10]=True
        protected[40,10]=True
        protected[40,11]=True
        y,x=120, (155+11)*3
        rgba[y,x,3]=24
        rgba[y,x+1,3]=23
        rgba[y,(155+10)*3,3]=255
        self.assertEqual(p.protected_targets(rgba,owner,protected),[(y,x)])

    def test_06_target_alpha_retains_raw_value(self):
        rgba=np.zeros(p.p4b5.BACKING,np.uint8)
        rgba[33,480,3]=25
        rgba[34,481,3]=128
        self.assertEqual(p.pixel_alpha(rgba,[(33,480),(34,481)]),[25,128])
        with self.assertRaises(ValueError):
            p.pixel_alpha(rgba,[(721,480)])

    def test_07_bisect_finds_both_contributors(self):
        weights=[0,130,0,0,0,75,0,0]
        def draw(indices,stage):
            self.assertTrue(stage.startswith("SPLIT_"))
            return [max(weights[i] for i in indices),
                    60 if 5 in indices else 0]
        t=p.split_trace(8,[130,60],draw,48)
        self.assertEqual(t["status"],"ATTRIBUTION_LEAVES_COMPLETE")
        self.assertEqual(sorted(t["leaves"]),[1,5])
        self.assertEqual(t["leaves"][1],[130,0])
        self.assertEqual(t["leaves"][5],[75,60])
        self.assertGreater(t["calls"],0)

    def test_08_overlap_is_possible_contributor_not_unique_cause(self):
        weights=[0,32,0,55]
        t=p.split_trace(4,[55],lambda ids,stage:[
            max(weights[i] for i in ids)],48)
        self.assertEqual(sorted(t["leaves"]),[1,3])
        self.assertEqual(p.necessary_pixels([55],[32]),[])
        self.assertEqual(p.necessary_pixels([55],[0]),[0])

    def test_09_split_budget_cap_not_false_pass(self):
        t=p.split_trace(8,[50],lambda ids,stage:[50],2)
        self.assertEqual(t["status"],"PARTIAL_NATIVE_SPLIT_LIMIT")
        self.assertEqual(t["calls"],2)

    def test_10_nonadditive_overlap_not_false_pass(self):
        t=p.split_trace(2,[24],lambda ids,stage:[0],4)
        self.assertEqual(t["status"],"PARTIAL_NONADDITIVE_NATIVE_ALPHA")

    def test_11_reject_malformed_native_vector(self):
        with self.assertRaises(ValueError):
            p.split_trace(2,[25],lambda ids,stage:[-1],48)

    def test_12_reject_model_as_accepted_native_target(self):
        for bad in ([],[0],[23],[257]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    p.split_trace(2,bad,lambda ids,stage:[0],48)

    def test_13_lost_pixel_means_required_in_full_replay(self):
        self.assertEqual(p.necessary_pixels([24,25],[23,25]),[0])
        self.assertEqual(p.necessary_pixels([255,24],[255,0]),[1])
        self.assertEqual(p.necessary_pixels([255,24],[255,24]),[])

    def test_14_validate_source_isolated_no_legacy_import(self):
        path=Path(p.__file__)
        tree=ast.parse(path.read_text("utf8"))
        deps=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):
                deps.extend(z.name for z in n.names)
        self.assertFalse(any("g32" in x.lower() or "v44" in x.lower()
                             for x in deps if x))

    def test_15_fail_closed_existing_output_contract(self):
        # No native rendering in E2. Verify runner has a hard existing-output guard.
        code=Path(p.__file__).read_text("utf8")
        self.assertIn('if output.exists():',code)
        self.assertIn('"BLOCKED_P4B7_OUTPUT_EXISTS"',code)

    def test_17_native_replay_reuses_one_session_but_fresh_egret_scene(self):
        import inspect
        from run_engine001_complex_holdout_v5 import native_batch
        hot = inspect.getsource(p.native_replay_in_session)
        self.assertIn("renderP4A2BrushWidths1to10Probe", hot)
        self.assertIn("read_webgl_result", hot)
        self.assertIn("BLOCKED_P4B7_NATIVE_BLANK_NONZERO", hot)
        self.assertIn("ENGINE001_B1R_P4A2_NATIVE_1_TO_10", hot)
        self.assertIn("BLOCKED_P4B7_NATIVE_CAPTURE_ALREADY_EXISTS", hot)
        self.assertEqual(p.ALPHA_GATE, 24)

    def test_16_native_renderer_and_parent_blob_fixed(self):
        self.assertEqual(p.RENDERER_BLOB,
                         "76d950e0a8911888a9df3b675b866519ecf7bba4")
        self.assertEqual(p.FROZEN_P4B6_BLOB,
                         "2f9ca1756da58e7062fcae6c6c64c83e4db79ea9")
        self.assertEqual(p.EXPECTED_STROKES,
                         {"E_SOBEL90":214, "F_SOBEL90_LAB12":212})


if __name__=="__main__":
    unittest.main()
