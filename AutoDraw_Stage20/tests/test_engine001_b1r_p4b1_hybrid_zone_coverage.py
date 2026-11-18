#!/usr/bin/env python3
"""P4B1 source-only owner zone geometry; native gates remain E3, never MODEL_ONLY."""
import ast
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p


def fixture():
    e = np.full(p.LOGICAL_SHAPE, 6, np.uint8)
    f = e.copy()
    e[70:115, 38:90] = 115
    f[71:114, 39:89] = 115
    # Additional isolated owner island cannot exceed intersection winner.
    e[180:193, 100:108] = 127
    f[180:193, 100:108] = 127
    swatches = np.asarray([6, 115, 127] + list(range(10, 39)),
                          np.int16)
    game = np.zeros((128, 3), np.uint8)
    game[6] = [255, 255, 255]
    game[115] = [70, 30, 60]
    game[127] = [230, 170, 130]
    return e, f, swatches, game


class P4B1Contracts(unittest.TestCase):
    def test_01_prereg_id_and_strategies(self):
        self.assertEqual(p.EXPERIMENT,
                         "ENGINE001_B1R_P4B1_HYBRID_OWNER_COVERAGE_V1")
        self.assertEqual(p.STRATEGIES,
                         ("A_ORIENTED", "B_CONTOUR_HYBRID"))
        self.assertEqual(p.WIDTHS, tuple(range(10, 0, -1)))

    def test_02_native_limits_and_gates_immutable(self):
        self.assertEqual(p.MAX_STROKES, 250)
        self.assertEqual(p.MAX_VERTICES, 500)
        self.assertEqual(p.MAX_POINTS_PER_STROKE, 128)
        self.assertEqual(p.NATIVE_COMPONENT_COVERAGE_GATE, .99)
        self.assertEqual(p.LEAKAGE_MAX_LOGICAL, 3.0)
        self.assertEqual(p.ALPHA_GATES, (24, 128))

    def test_03_four_orientations(self):
        self.assertEqual(p.DIRECTIONS,
                         {"HORIZONTAL": (1,0), "DIAG_DOWN": (1,1),
                          "VERTICAL": (0,1), "DIAG_UP": (-1,1)})

    def test_04_deterministic_common_source_owner_and_both_EF(self):
        e, f, swatches, game = fixture()
        info, masks = p.choose_common_source_owner(e, f, swatches)
        self.assertEqual(info["engine_index"],115)
        self.assertTrue(masks[p.METHODS[0]].sum() > 2100)
        self.assertTrue(masks[p.METHODS[1]].sum() > 2000)
        self.assertEqual(info, p.choose_common_source_owner(e,f,swatches)[0])

    def test_05_common_source_owner_all_white_fail_closed(self):
        e,f,s,g=fixture()
        e[:]=6;f[:]=6
        with self.assertRaisesRegex(ValueError,"NO_COMMON_NONWHITE_REGION"):
            p.choose_common_source_owner(e,f,s)

    def test_06_unsupported_index_and_wrong_shapes_blocked(self):
        e,f,s,g=fixture()
        with self.assertRaisesRegex(ValueError,"INDEX_OR_PALETTE"):
            p.choose_common_source_owner(e[:-1],f,s)
        e[11,12]=250
        with self.assertRaisesRegex(ValueError,"INDEX_OR_PALETTE"):
            p.choose_common_source_owner(e,f,s)

    def test_07_oriented_candidates_in_source(self):
        e,f,s,g=fixture()
        info, masks=p.choose_common_source_owner(e,f,s)
        component=masks[p.METHODS[0]]
        outside=cv2.distanceTransform((~component).astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        c=p._candidate_oriented(component,component,outside,4)
        self.assertTrue(c)
        self.assertTrue(all(x["vertices"]==2 for x in c))
        self.assertEqual(set(x["kind"] for x in c), {"oriented"})
        self.assertTrue(all(x["width"]==4 for x in c))

    def test_08_ring_candidates_in_source(self):
        e,f,s,g=fixture()
        info,masks=p.choose_common_source_owner(e,f,s)
        component=masks[p.METHODS[0]]
        outside=cv2.distanceTransform((~component).astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        candidates=p._candidate_rings(component,component,outside,6)
        self.assertTrue(candidates)
        self.assertTrue(all(x["kind"]=="contour_ring" for x in candidates))
        self.assertTrue(all(x["vertices"]<=128 for x in candidates))

    def test_09_both_planners_use_actual_engine_swatch(self):
        e,f,s,g=fixture()
        info, masks=p.choose_common_source_owner(e,f,s)
        comp=masks[p.METHODS[0]]
        for strategy in p.STRATEGIES:
            strokes, details=p.plan_component(comp,e==115,115,g,strategy)
            self.assertTrue(strokes)
            self.assertGreater(details["candidate_count_MODEL_ONLY"],0)
            self.assertLessEqual(details["strokes_count"],250)
            self.assertLessEqual(details["synthetic_vertices_NOT_CHALK"],500)
            self.assertTrue(all(x["colorIndex"]==115 for x in strokes))
            self.assertTrue(all(x["colorRgb"]==(70<<16)|(30<<8)|60
                                for x in strokes))
            self.assertTrue(all(1<=x["width"]<=10 for x in strokes))
            self.assertTrue(all(
                2<=len(x["points"])<=128 for x in strokes
            ))

    def test_10_current_original_source_not_mutated(self):
        e,f,s,g=fixture()
        freeze_e=e.copy()
        freeze_f=f.copy()
        info,masks=p.choose_common_source_owner(e,f,s)
        p.plan_component(masks[p.METHODS[0]],e==115,115,g,
                         "A_ORIENTED")
        self.assertTrue(np.array_equal(e,freeze_e))
        self.assertTrue(np.array_equal(f,freeze_f))

    def test_11_wrong_source_and_strategy_blocked(self):
        e,f,s,g=fixture()
        info,masks=p.choose_common_source_owner(e,f,s)
        m=masks[p.METHODS[0]]
        for bad in ("SOMETHING", "", 5):
            with self.assertRaisesRegex(ValueError,"PLAN_INPUT"):
                p.plan_component(m,e==115,115,g,bad)
        with self.assertRaisesRegex(ValueError,"PLAN_INPUT"):
            p.plan_component(m[:-1],e==115,115,g,"A_ORIENTED")

    def test_12_model_nonowner_far_rejected(self):
        e,f,s,g=fixture()
        info,masks=p.choose_common_source_owner(e,f,s)
        m=masks[p.METHODS[0]]
        outside=cv2.distanceTransform((~m).astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        candidate=p._model_candidate(
            [(20.,70.),(80.,70.)],10,m,m,outside,"oriented","H")
        self.assertIsNone(candidate)

    def test_13_board_ROI_only_at_155_and_scale3(self):
        e,f,s,g=fixture()
        owner=p._board_backing(e==115)
        self.assertEqual(owner.shape,(720,1380))
        self.assertTrue(owner[80*3,(155+40)*3])
        self.assertFalse(owner[80*3,40*3])
        self.assertFalse(owner[80*3,(155+95)*3])

    def test_14_native_zero_ink_has_zero_coverage(self):
        e,f,s,g=fixture()
        info,masks=p.choose_common_source_owner(e,f,s)
        blank=np.zeros(p.BACKING_SHAPE,np.uint8)
        scores, blank_count=p.native_metrics(blank,blank,
            masks[p.METHODS[0]],e==115)
        self.assertEqual(blank_count,0)
        self.assertEqual(scores["24"]["native_nonzero_ink_backing_pixels"],0)
        self.assertEqual(scores["24"]["native_component_coverage"],0)

    def test_15_native_far_leakage_is_measured(self):
        e,f,s,g=fixture()
        info,masks=p.choose_common_source_owner(e,f,s)
        native=np.zeros(p.BACKING_SHAPE,np.uint8)
        native[80*3,(155+42)*3,3]=255
        native[80*3,(155+100)*3,3]=255
        blank=np.zeros_like(native)
        scores,_=p.native_metrics(native,blank,masks[p.METHODS[0]],e==115)
        self.assertEqual(scores["24"]["native_beyond3logicalpx_other_color_pixels"],1)

    def test_16_empty_output_must_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                p.run(Path(d),Path(d)/"bad.png",Path(d)/"bad.js",
                      Path(d)/"renderer.js",Path(d))

    def test_17_no_legacy_source_imports(self):
        tree=ast.parse(Path(p.__file__).read_text(encoding="utf8"))
        direct=[name.name for node in ast.walk(tree)
                if isinstance(node,ast.Import) for name in node.names]
        from_imports=[node.module for node in ast.walk(tree)
                if isinstance(node,ast.ImportFrom) and node.module]
        self.assertFalse(any("g32" in x.lower() or "v44" in x.lower()
                         or "p4c1" in x.lower() for x in direct+from_imports))
        self.assertIn("run_engine001_b1r_p3d_source_edge_mask_ablation",direct)
        self.assertIn("run_engine001_complex_holdout_v5",from_imports)

    def test_18_deterministic_region_model(self):
        e,f,s,g=fixture()
        info,masks=p.choose_common_source_owner(e,f,s)
        m=masks[p.METHODS[0]]
        a,da=p.plan_component(m,e==115,115,g,"A_ORIENTED")
        b,db=p.plan_component(m,e==115,115,g,"A_ORIENTED")
        self.assertEqual(a,b)
        self.assertEqual(da,db)

if __name__ == "__main__":
    unittest.main()
