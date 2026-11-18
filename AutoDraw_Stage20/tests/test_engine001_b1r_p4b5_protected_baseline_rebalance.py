#!/usr/bin/env python3
"""P4B5 original protected baseline pruning E2, not E3 native quality."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np
import run_engine001_b1r_p4b5_protected_baseline_rebalance as p


def fixture():
    comp=np.zeros((240,150),bool)
    comp[70:130,45:110]=True
    owner=comp.copy()
    protected=np.zeros((240,150),bool)
    protected[68:70,55:90]=True
    # One wide source-model risk and one safe original line.
    risky={
      "strokeId":"icon-0","width":9,"colorIndex":115,"colorRgb":0x5a4941,
      "points":[{"x":155+60.,"y":70.},{"x":155+80.,"y":70.}]
    }
    safe={
      "strokeId":"icon-1","width":1,"colorIndex":115,"colorRgb":0x5a4941,
      "points":[{"x":155+60.,"y":100.},{"x":155+80.,"y":100.}]
    }
    return comp,owner,protected,[risky,safe]


class P4B5Contracts(unittest.TestCase):
    def test_01_prereg_identity_and_protected_safety(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B5_PROTECTED_BASELINE_REBALANCE_V1")
        self.assertEqual(p.COVERAGE_GATE,.99)
        self.assertEqual(p.SPILL_GATE,3.0)

    def test_02_unchanged_250_500_limits(self):
        self.assertEqual(p.MAX_STROKES,250)
        self.assertEqual(p.MAX_VERTICES,500)
        self.assertEqual(p.ALPHA,24)

    def test_03_model_risky_vs_safe_source_strokes(self):
        comp,owner,protected,strokes=fixture()
        a=p.original_safety_model(strokes[0],comp,owner,protected)
        b=p.original_safety_model(strokes[1],comp,owner,protected)
        self.assertGreater(a,0)
        self.assertEqual(b,0)

    def test_04_stable_prune_removes_only_risky_line(self):
        comp,owner,protected,strokes=fixture()
        survivor,removed,mapping=p.prune_original_baseline(
            strokes,comp,owner,protected)
        self.assertEqual(len(removed),1)
        self.assertEqual(removed[0]["original_id"],"icon-0")
        self.assertEqual(removed[0]["original_order"],0)
        self.assertEqual(len(survivor),1)
        self.assertEqual(survivor[0]["strokeId"],"icon-0")
        self.assertEqual(survivor[0]["points"],strokes[1]["points"])
        self.assertEqual(mapping[0]["original_id"],"icon-1")
        self.assertEqual(mapping[0]["new_id"],"icon-0")

    def test_05_original_baseline_bytes_not_mutated(self):
        comp,owner,protected,strokes=fixture()
        import copy
        before=copy.deepcopy(strokes)
        p.prune_original_baseline(strokes,comp,owner,protected)
        self.assertEqual(before,strokes)

    def test_06_fail_closed_bad_stroke_width(self):
        comp,owner,protected,strokes=fixture()
        bad=dict(strokes[0]);bad["width"]=11
        with self.assertRaisesRegex(ValueError,"ORIGINAL_STROKE_OR_SOURCE"):
            p.original_safety_model(bad,comp,owner,protected)

    def test_07_fail_closed_bad_source_shape(self):
        comp,owner,protected,strokes=fixture()
        with self.assertRaisesRegex(ValueError,"ORIGINAL_STROKE_OR_SOURCE"):
            p.original_safety_model(strokes[0],comp[:-1],owner,protected)

    def test_08_fail_closed_bad_color_owner(self):
        comp,owner,protected,strokes=fixture()
        bad=dict(strokes[0]);bad["colorIndex"]=127
        with self.assertRaisesRegex(ValueError,"ORIGINAL_STROKE_OR_SOURCE"):
            p.original_safety_model(bad,comp,owner,protected)

    def test_09_reject_source_oob_coordinate(self):
        comp,owner,protected,strokes=fixture()
        bad={**strokes[0],"points":[{"x":550.0,"y":70.},
                                    {"x":556.0,"y":70.}]}
        with self.assertRaisesRegex(ValueError,"STROKE_COORDINATE_DRIFT"):
            p.original_safety_model(bad,comp,owner,protected)

    def test_10_reject_original_baseline_all_removed(self):
        comp,owner,protected,strokes=fixture()
        with self.assertRaisesRegex(ValueError,"PRUNED_ALL_BASELINE"):
            p.prune_original_baseline([strokes[0],strokes[0]],
                                      comp,owner,protected)

    def test_11_stroke_list_must_have_two_elements_min(self):
        comp,owner,protected,strokes=fixture()
        with self.assertRaisesRegex(ValueError,"BASELINE_INPUT"):
            p.prune_original_baseline([strokes[1]],
                                      comp,owner,protected)

    def test_12_stroke_order_preserved_after_prune(self):
        comp,owner,protected,strokes=fixture()
        third={
          **strokes[1],"strokeId":"icon-2",
          "points":[{"x":155+49.,"y":110.},{"x":155+65.,"y":110.}]
        }
        kept,removed,mapping=p.prune_original_baseline(
            [strokes[1],strokes[0],third],comp,owner,protected)
        self.assertEqual([m["original_order"] for m in mapping],[0,2])
        self.assertEqual([s["strokeId"] for s in kept],["icon-0","icon-1"])
        self.assertEqual(kept[-1]["points"],third["points"])

    def test_13_real_native_metric_dimensions(self):
        comp,owner,protected,strokes=fixture()
        native={
            "blank":np.zeros((720,1380,4),np.uint8),
            "composite":np.zeros((720,1380,4),np.uint8),
            "color-115":np.zeros((720,1380,4),np.uint8),
        }
        scores,blank=p.source_metrics(native,comp,owner,protected)
        self.assertEqual(blank,0)
        self.assertEqual(scores["24"]["native_component_coverage"],0)
        self.assertEqual(scores["24"]["native_protected_foreign_face_eyes_hands_pixels"],0)

    def test_14_invalid_native_metadata_fail_closed(self):
        comp,owner,protected,strokes=fixture()
        with self.assertRaisesRegex(ValueError,"NATIVE_REPLAY_DICT"):
            p.source_metrics({"blank":np.zeros((720,1380,4),np.uint8)},
                             comp,owner,protected)

    def test_15_source_only_imports_never_legacy(self):
        tree=ast.parse(Path(p.__file__).read_text("utf8"))
        names=[n.name for node in ast.walk(tree)
               if isinstance(node,ast.Import) for n in node.names]
        names += [node.module for node in ast.walk(tree)
                  if isinstance(node,ast.ImportFrom) and node.module]
        self.assertFalse(any("g32" in x.lower() or "v44" in x.lower()
                             or "p4c1" in x.lower() for x in names))
        self.assertIn("run_engine001_b1r_p4b4_boundary_tolerance_sweep",names)
        self.assertIn("run_engine001_b1r_p4b2_native_edge_repair",names)

    def test_16_existing_output_fail_closed_before_any_input(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                p.run(Path(d),Path(d)/"absent.png",Path(d)/"absent.js",
                      Path(d)/"absent.renderer",Path(d))

    def test_17_true_native_capture_shape_constant(self):
        self.assertEqual(p.BACKING,(720,1380,4))
        self.assertEqual(p.SHAPE,(240,150))
        self.assertEqual(p.SOURCE,"C_192_D_COMPONENT24")
        self.assertEqual(p.METHODS,("E_SOBEL90","F_SOBEL90_LAB12"))

if __name__=="__main__":
    unittest.main()
