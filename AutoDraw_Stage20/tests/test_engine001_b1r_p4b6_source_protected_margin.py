#!/usr/bin/env python3
"""ENGINE-001 P4B6 synthetic E2: protected original source centerline guards."""
import ast
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import run_engine001_b1r_p4b6_source_protected_margin as p


def synthetic():
    owner=np.zeros(p.SHAPE,bool)
    owner[60:140,39:110]=True
    protected=np.zeros(p.SHAPE,bool)
    protected[50:100,25:36]=True
    protected[150:190,90:105]=True
    def stroke(idx,width,x1,y1,x2,y2):
        return {
            "strokeId":"icon-%d"%idx,
            "width":width,"colorIndex":115,"colorRgb":0x493820,
            "points":[{"x":155+float(x1),"y":float(y1)},
                      {"x":155+float(x2),"y":float(y2)}],
        }
    baseline=[
        stroke(0,10,41,70,43,70), # nearest foreign x35 clearance6-5=1
        stroke(1,4,70,110,80,110),
        stroke(2,6,40,80,42,80), # nearest x35 clearance5-3=2
    ]
    return owner,protected,baseline


class P4B6Contracts(unittest.TestCase):
    def test_01_prereg_experiment(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B6_SOURCE_PROTECTED_MARGIN_V1")
        self.assertEqual(p.ARMS,{"G0_5":.5,"G1_0":1.0})

    def test_02_original_native_gates_not_modified(self):
        self.assertEqual(p.COVERAGE_GATE,.99)
        self.assertEqual(p.LEGACY_NATIVE_SPILL,3.0)
        self.assertEqual(p.MAX_STROKES,250)
        self.assertEqual(p.MAX_VERTICES,500)
        self.assertEqual(p.NATIVE_ALPHA,24)

    def test_03_source_distance_true_foreign_only(self):
        owner,prot,base=synthetic()
        d=p._guard_distance_map(owner,prot)
        self.assertEqual(d.shape,p.SHAPE)
        self.assertEqual(float(d[70,35]),0.0)
        self.assertGreater(float(d[70,70]),10.0)

    def test_04_minimum_clearance_subtracts_actual_half_width(self):
        owner,prot,base=synthetic()
        d=p._guard_distance_map(owner,prot)
        a=p.stroke_clearance(base[0],d)
        self.assertAlmostEqual(a,1.0,places=4)
        self.assertGreater(p.stroke_clearance(base[1],d),10)

    def test_05_prereg_margin_half_keeps_clearance_one(self):
        owner,prot,base=synthetic()
        retained,ledger=p.prune_with_margin(base,owner,prot,"G0_5")
        self.assertEqual(len(retained),len(base))
        self.assertEqual(len(ledger["dropped_original_geometry"]),0)

    def test_06_margin_one_excludes_equal_threshold(self):
        owner,prot,base=synthetic()
        retained,ledger=p.prune_with_margin(base,owner,prot,"G1_0")
        self.assertEqual(len(retained),len(base)-1)
        self.assertEqual(ledger["dropped_original_geometry"][0]
                         ["P4B5_pruned_id"],"icon-0")
        self.assertEqual([s["strokeId"] for s in retained],
                         ["icon-0","icon-1"])

    def test_07_source_original_survivors_geometry_not_mutated(self):
        owner,prot,base=synthetic()
        copied=[{"strokeId":s["strokeId"],"points":[dict(x) for x in s["points"]]}
                for s in base]
        retained,ledger=p.prune_with_margin(base,owner,prot,"G1_0")
        for previous,now in zip(copied,base):
            self.assertEqual(previous["strokeId"],now["strokeId"])
            self.assertEqual(previous["points"],now["points"])
        self.assertEqual(retained[0]["points"],base[1]["points"])
        self.assertEqual(retained[1]["points"],base[2]["points"])

    def test_08_deterministic_immutable_guard_filter(self):
        owner,prot,base=synthetic()
        self.assertEqual(p.prune_with_margin(base,owner,prot,"G1_0"),
                         p.prune_with_margin(base,owner,prot,"G1_0"))

    def test_09_invalid_masks_block(self):
        owner,prot,base=synthetic()
        with self.assertRaisesRegex(ValueError,"SOURCE_MASK_SHAPE"):
            p._guard_distance_map(owner[:-1],prot)
        with self.assertRaisesRegex(ValueError,"SOURCE_MASK_SHAPE"):
            p._guard_distance_map(owner,prot.astype(np.uint8))

    def test_10_no_foreign_protected_source_refused(self):
        owner,prot,base=synthetic()
        with self.assertRaisesRegex(ValueError,"NO_PROTECTED_FOREIGN"):
            p._guard_distance_map(owner,np.zeros_like(owner))

    def test_11_unbounded_and_nonfinite_points_refused(self):
        owner,prot,base=synthetic()
        d=p._guard_distance_map(owner,prot)
        for pts in (
            [(150,70),(150,80)],
            [(-1,70),(3,70)],
            [(float("nan"),70),(35,70)],
            [(35,240),(35,241)]
        ):
            with self.assertRaisesRegex(ValueError,"UNSAFE_SOURCE_POINTS"):
                p.clearance(pts,4,d)

    def test_12_non_integer_width_and_invalid_vertex_count(self):
        owner,prot,base=synthetic()
        d=p._guard_distance_map(owner,prot)
        for width in [0,11,1.5,True]:
            with self.assertRaisesRegex(ValueError,"CLEARANCE_INPUT"):
                p.clearance([(40,70),(41,70)],width,d)
        with self.assertRaisesRegex(ValueError,"CLEARANCE_INPUT"):
            p.clearance([(40,70)],2,d)

    def test_13_wrong_color_source_stroke_refused(self):
        owner,prot,base=synthetic()
        d=p._guard_distance_map(owner,prot)
        bad=dict(base[0]);bad["colorIndex"]=6
        with self.assertRaisesRegex(ValueError,"WRONG_SOURCE_RGB_OWNER"):
            p.stroke_clearance(bad,d)

    def test_14_catalog_with_threshold_source_original_only(self):
        owner,prot,base=synthetic()
        opts=[
            {"source_xy":[(41.,70.),(43.,70.)],
             "width":10,"projected_max_nonowner_distance_MODEL_ONLY":2.0},
            {"source_xy":[(70.,110.),(80.,110.)],
             "width":4,"projected_max_nonowner_distance_MODEL_ONLY":2.0},
        ]
        a=p.filter_candidate_margin(opts,owner,prot,"G0_5")
        b=p.filter_candidate_margin(opts,owner,prot,"G1_0")
        self.assertEqual(len(a),2)
        self.assertEqual(len(b),1)
        self.assertEqual(b[0]["width"],4)

    def test_15_reject_model_catalog_unpinned_3px_spill(self):
        owner,prot,base=synthetic()
        opts=[{"source_xy":[(70.,110.),(80.,110.)],
               "width":4,"projected_max_nonowner_distance_MODEL_ONLY":3.5}]
        with self.assertRaisesRegex(ValueError,"UNPINNED_MODEL_CANDIDATE"):
            p.filter_candidate_margin(opts,owner,prot,"G1_0")

    def test_16_fail_closed_incorrect_arm_or_empty_parent(self):
        owner,prot,base=synthetic()
        with self.assertRaisesRegex(ValueError,"PRUNE_INPUT"):
            p.prune_with_margin(base,owner,prot,"G2_0")
        with self.assertRaisesRegex(ValueError,"PRUNE_INPUT"):
            p.prune_with_margin([],owner,prot,"G0_5")

    def test_17_no_old_G32_P4c1_V44_imports(self):
        tree=ast.parse(Path(p.__file__).read_text(encoding="utf8"))
        names=[n.name for node in ast.walk(tree) if isinstance(node,ast.Import)
               for n in node.names]
        names += [node.module for node in ast.walk(tree)
                  if isinstance(node,ast.ImportFrom) and node.module]
        self.assertIn("run_engine001_b1r_p4b5_protected_baseline_rebalance",names)
        self.assertIn("run_engine001_b1r_p4b4_boundary_tolerance_sweep",names)
        self.assertFalse(any("v44" in x.lower() or "g32" in x.lower()
                             or "p4c1" in x.lower() for x in names))

    def test_18_existing_output_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                p.run(Path(d),Path(d)/"no.png",Path(d)/"no.js",
                      Path(d)/"no.renderer",Path(d))


if __name__=="__main__":
    unittest.main()
