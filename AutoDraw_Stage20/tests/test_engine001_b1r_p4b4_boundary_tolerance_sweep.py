#!/usr/bin/env python3
"""ENGINE-001 P4B4 fixed 3.0/3.5/4.0 tolerance E2 contracts. No native claims."""
import ast
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p


def fixture():
    comp=np.zeros(p.LOGICAL,bool)
    comp[70:125,45:110]=True
    full=comp.copy()
    weights=np.zeros(p.LOGICAL,np.int16)
    weights[70,46:105]=9
    weights[80,45]=8
    eligible=(weights>0)&comp
    protected=np.zeros_like(comp)
    protected[68,55:90]=True
    game=np.zeros((128,3),np.uint8)
    game[115]=[90,73,65]
    baseline=[{
        "strokeId":"icon-%d"%i,
        "width":2,"colorIndex":115,
        "colorRgb":0x5A4941,
        "points":[{"x":205.0,"y":75.0},{"x":210.0,"y":75.0}],
    } for i in range(177)]
    return comp,full,weights,eligible,protected,game,baseline


class P4B4Contracts(unittest.TestCase):
    def test_01_experiment_and_fixed_arms(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B4_BOUNDARY_TOLERANCE_SWEEP_V1")
        self.assertEqual(p.ARMS,{"T3_0":3.0,"T3_5":3.5,"T4_0":4.0})
        self.assertEqual(p.COVERAGE_GATE,.99)
        self.assertEqual(p.LEGACY_GATE,3.0)

    def test_02_all_brush_widths_candidate_1_to10(self):
        self.assertEqual(p.CANDIDATE_WIDTHS,tuple(range(10,0,-1)))
        self.assertEqual(p.CORRECTION_MODES,("H","V"))

    def test_03_existing_caps_unchanged(self):
        self.assertEqual(p.MAX_STROKES,250)
        self.assertEqual(p.MAX_VERTICES,500)
        self.assertEqual(p.EDGE_DISTANCE,2.0)
        self.assertEqual(p.NATIVE_ALPHA,24)

    def test_04_source_roi_truth_and_not_empty(self):
        m=p.source_critical_rois()
        self.assertEqual(m.shape,(240,150))
        self.assertEqual(m.dtype,np.bool_)
        self.assertTrue(m.any())

    def test_05_invalid_source_inputs_fail_closed(self):
        c,f,w,e,prot,g,base=fixture()
        for args in (
            (c[:-1],f,w,e,prot),
            (c,f,w,e.astype(np.uint8),prot),
            (c,f,w[:-1],e,prot),
            (c,f,w,e,prot[:-1]),
        ):
            with self.assertRaisesRegex(ValueError,"INVALID_SOURCE_OWNER"):
                p.original_component_inputs(*args)

    def test_06_candidate_catalog_nonempty_and_bounded(self):
        c,f,w,e,prot,g,base=fixture()
        options=p.candidate_catalog(c,f,w,e,prot)
        self.assertGreater(len(options),0)
        self.assertTrue(all(1<=x["width"]<=10 for x in options))
        self.assertTrue(all(
            x["projected_max_nonowner_distance_MODEL_ONLY"]<=4.
            for x in options))
        self.assertTrue(all(x["vertices"]==2 for x in options))

    def test_07_model_admission_nested_no_gate_mutation(self):
        c,f,w,e,prot,g,base=fixture()
        cat=p.candidate_catalog(c,f,w,e,prot)
        counts=[
            len([x for x in cat if x["projected_max_nonowner_distance_MODEL_ONLY"]<=bound])
            for bound in (3.0,3.5,4.0)
        ]
        self.assertEqual(counts,sorted(counts))

    def test_08_all_three_arms_deterministic_and_budget_safe(self):
        c,f,w,e,prot,g,base=fixture()
        cat=p.candidate_catalog(c,f,w,e,prot)
        for arm in p.ARMS:
            x,a=p.choose_from_catalog(cat,w,base,g,arm)
            y,b=p.choose_from_catalog(cat,w,base,g,arm)
            self.assertEqual(x,y)
            self.assertEqual(a,b)
            self.assertTrue(x)
            self.assertLessEqual(a["cumulative_strokes"],250)
            self.assertLessEqual(a["cumulative_vertices_NOT_CHALK"],500)
            self.assertTrue(all(s["colorIndex"]==115 for s in x))

    def test_09_original_baseline_unchanged(self):
        c,f,w,e,prot,g,base=fixture()
        before=[dict(s) for s in base]
        cat=p.candidate_catalog(c,f,w,e,prot)
        for arm in p.ARMS:
            p.choose_from_catalog(cat,w,base,g,arm)
        self.assertEqual(base,before)

    def test_10_invalid_arm_and_game_palette_fail_closed(self):
        c,f,w,e,prot,g,base=fixture()
        cat=p.candidate_catalog(c,f,w,e,prot)
        with self.assertRaisesRegex(ValueError,"SELECTION_INPUT"):
            p.choose_from_catalog(cat,w,base,g,"T5")
        with self.assertRaisesRegex(ValueError,"SELECTION_INPUT"):
            p.choose_from_catalog(cat,w,base,g[:10],"T3_0")

    def test_11_protected_foreign_source_candidates_rejected(self):
        c,f,w,e,prot,g,base=fixture()
        outside=cv2.distanceTransform((~f).astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        x=p._candidate([(68.125,70.),(68.375,70.)],10,c,f,outside,prot,"H")
        self.assertIsNone(x)

    def test_12_invalid_candidate_geometry_refused(self):
        c,f,w,e,prot,g,base=fixture()
        outside=cv2.distanceTransform((~f).astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        with self.assertRaisesRegex(ValueError,"CANDIDATE_WIDTH"):
            p._candidate([(70.,70.),(70.25,70.)],11,c,f,outside,prot,"H")
        self.assertIsNone(p._candidate(
            [(20.,20.),(20.25,20.)],2,c,f,outside,prot,"H"))

    def test_13_native_blank_and_true_zero_coverage(self):
        c,f,w,e,prot,g,base=fixture()
        rgba=np.zeros(p.BACKING,np.uint8)
        scored,blank=p.native_diagnostics(rgba,rgba,c,f,prot)
        self.assertEqual(blank,0)
        self.assertEqual(scored["24"]["native_component_coverage"],0)
        self.assertEqual(scored["24"]["native_foreign_distance_gt_T3_0"],0)

    def test_14_native_far_pixels_and_protected_ROI_real_alpha(self):
        c,f,w,e,prot,g,base=fixture()
        rgba=np.zeros(p.BACKING,np.uint8)
        rgba[80*3,(155+60)*3,3]=255
        rgba[70*3,(155+44)*3,3]=255
        rgba[68*3,(155+65)*3,3]=255
        scored,_=p.native_diagnostics(rgba,np.zeros_like(rgba),c,f,prot)
        self.assertEqual(scored["24"]["native_protected_foreign_face_eyes_hands_pixels"],1)
        self.assertGreater(scored["24"]["native_any_foreign_color_backing_pixels"],0)

    def test_15_native_distance_order_monotone(self):
        c,f,w,e,prot,g,base=fixture()
        rgba=np.zeros(p.BACKING,np.uint8)
        rgba[80*3,(155+41)*3,3]=255
        scored,_=p.native_diagnostics(rgba,np.zeros_like(rgba),c,f,prot)
        s=scored["24"]
        self.assertGreaterEqual(s["native_foreign_distance_gt_T3_0"],
                                s["native_foreign_distance_gt_T3_5"])
        self.assertGreaterEqual(s["native_foreign_distance_gt_T3_5"],
                                s["native_foreign_distance_gt_T4_0"])

    def test_16_invalid_native_shape_and_source_overwrite(self):
        c,f,w,e,prot,g,base=fixture()
        with self.assertRaisesRegex(ValueError,"NATIVE_GROUND_TRUTH_SHAPE"):
            p.native_diagnostics(np.zeros((100,100,4),np.uint8),
                                 np.zeros(p.BACKING,np.uint8),c,f,prot)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"OUTPUT_ALREADY_EXISTS"):
                p.run(Path(d),Path(d)/"no.png",Path(d)/"no.js",
                      Path(d)/"no.renderer",Path(d))

    def test_17_source_only_no_legacy_candidate_import(self):
        tree=ast.parse(Path(p.__file__).read_text(encoding="utf8"))
        names=[x.name for node in ast.walk(tree) if isinstance(node,ast.Import)
               for x in node.names]
        names += [node.module for node in ast.walk(tree)
                  if isinstance(node,ast.ImportFrom) and node.module]
        self.assertIn("run_engine001_b1r_p4b1_hybrid_zone_coverage",names)
        self.assertIn("run_engine001_b1r_p4b2_native_edge_repair",names)
        self.assertFalse(any("v44" in s.lower() or "g32" in s.lower()
                             or "p4c1" in s.lower() for s in names))

if __name__=="__main__":
    unittest.main()
