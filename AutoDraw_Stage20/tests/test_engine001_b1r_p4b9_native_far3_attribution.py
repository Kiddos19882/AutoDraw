#!/usr/bin/env python3
"""P4B9 synthetic E2 checks; pixel proof requires real Egret E3."""
from pathlib import Path
import ast
import unittest
import numpy as np
import run_engine001_b1r_p4b9_native_far3_attribution as p

class P4B9Contract(unittest.TestCase):
    def test_01_prereg_and_gates(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B9_NATIVE_FAR3_ATTRIBUTION_V1")
        self.assertTrue((Path(__file__).parents[1]/"docs"/p.PREREG).exists())
        self.assertEqual(p.EXPECTED_FAR,{"E_SOBEL90":4,"F_SOBEL90_LAB12":2})
        self.assertEqual((p.ALPHA,p.SPILL_GATE,p.COVERAGE_GATE),(24,3.,.99))
        self.assertEqual((p.MAX_SPLIT,p.MAX_LOO),(64,16))
    def test_02_true_owner_backing_mask_distance_boundary(self):
        rgba=np.zeros(p.p4b5.BACKING,np.uint8)
        owner=np.zeros(p.p4b5.SHAPE,bool)
        owner[40:80,40:80]=True
        # One outside backing pixel >9 pixels from full owner, another <=9.
        rgba[150,(155+35)*3-8,3]=24
        rgba[150,(155+40)*3-7,3]=24
        targets=p.native_far3_targets(rgba,owner)
        self.assertIn((150,(155+35)*3-8),targets)
        self.assertNotIn((150,(155+40)*3-7),targets)
    def test_03_alpha24_gate_not_alpha1(self):
        rgba=np.zeros(p.p4b5.BACKING,np.uint8)
        owner=np.zeros(p.p4b5.SHAPE,bool)
        owner[30:90,30:70]=True
        pos=(150,(155+20)*3)
        rgba[pos[0],pos[1],3]=23
        self.assertEqual(p.native_far3_targets(rgba,owner),[])
        rgba[pos[0],pos[1],3]=24
        self.assertEqual(p.native_far3_targets(rgba,owner),[pos])
    def test_04_no_selected_component_only_mask(self):
        self.assertIn("p4b4.backing(full_owner)",Path(p.__file__).read_text("utf8"))
        self.assertIn("cv2.DIST_MASK_PRECISE",Path(p.__file__).read_text("utf8"))
    def test_05_invalid_shapes_and_dtypes_blocked(self):
        rgba=np.zeros((100,200,4),np.uint8)
        owner=np.zeros(p.p4b5.SHAPE,bool)
        with self.assertRaises(ValueError):
            p.native_far3_targets(rgba,owner)
        with self.assertRaises(ValueError):
            p.native_far3_targets(np.zeros(p.p4b5.BACKING,np.uint8),
                                  owner.astype(np.uint8))
        with self.assertRaises(ValueError):
            p.native_far3_targets(np.zeros(p.p4b5.BACKING,np.uint8),owner)
    def test_06_no_native_attribution_from_model_only(self):
        source=Path(p.__file__).read_text("utf8")
        for q in ("p4b6.run(","p4b8.surgery(","p4b7.native_egret_session",
                  "p4b7.native_replay_in_session",
                  "p4b7.split_trace","p4b7.necessary_pixels",
                  "BLOCKED_P4B9_TRUE_NATIVE_PARITY"):
            self.assertIn(q,source)
    def test_07_width_and_vertex_limits_unchanged(self):
        self.assertEqual((p.MAX_STROKES,p.MAX_VERTICES),(250,500))
        self.assertEqual(p.P4B8_BLOB,"9ddf8e2f745de4f78006b14c00e99e74c2f3cb67")
    def test_08_alpha_target_count_not_invented(self):
        self.assertIn("BLOCKED_P4B9_FROZEN_P4B8_TRIM50_DRIFT",
                      Path(p.__file__).read_text("utf8"))
    def test_09_drop_one_native_checked_only_after_grouping(self):
        self.assertIn("p4b7.normalized_subset(trim,indices)",Path(p.__file__).read_text("utf8"))
        self.assertIn("PARTIAL_TOO_MANY_CAUSAL_LEAVES",Path(p.__file__).read_text("utf8"))
    def test_10_no_old_legacy_generation(self):
        tree=ast.parse(Path(p.__file__).read_text("utf8"))
        deps=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):deps.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):deps.append(node.module)
        self.assertFalse(any("v44" in str(s).lower() or "g32" in str(s).lower()
                             for s in deps))
    def test_11_output_existing_fails_closed(self):
        self.assertIn("BLOCKED_P4B9_OUTPUT_EXISTS",Path(p.__file__).read_text("utf8"))
    def test_12_real_chalk_not_claimed(self):
        self.assertIn('"exact_game_CHALK":None',Path(p.__file__).read_text("utf8"))

if __name__=="__main__":
    unittest.main()
