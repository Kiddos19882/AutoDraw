#!/usr/bin/env python3
"""ENGINE-001 P4B2 synthetic native-missing boundary repair contracts."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4b2_native_edge_repair as p


def fixture():
    component=np.zeros((240,150),dtype=bool)
    component[65:120,45:100]=True
    full=component.copy()
    game=np.zeros((128,3),np.uint8)
    game[115]=(90,73,65)
    native=np.zeros((720,1380,4),np.uint8)
    # White ink inside target simulated only for contract, not quality evidence.
    native[65*3:120*3,(155+45)*3:(155+100)*3,3]=255
    # Keep true missed native RGB backing along source boundary x45.
    native[65*3:120*3,(155+45)*3:(155+46)*3,3]=0
    strokes=[
        {"strokeId":"icon-%d"%i,"width":3,"colorIndex":115,
         "colorRgb":0x5a4941,
         "points":[{"x":215.0,"y":70.0},{"x":225.0,"y":70.0}]}
        for i in range(177)
    ]
    return component,full,game,native,strokes


class P4B2Contracts(unittest.TestCase):
    def test_01_prereg_id_and_fixed_new_widths(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B2_NATIVE_EDGE_GAP_REPAIR_V1")
        self.assertEqual(p.CORRECTION_WIDTHS,(2,1))
        self.assertEqual(p.CONTOUR_CHORD_OFFSETS,(4,8))
        self.assertEqual(p.EDGE_MAX_DISTANCE,2.0)

    def test_02_original_p4b1_caps_and_gates_stay(self):
        self.assertEqual(p.MAX_TOTAL_STROKES,250)
        self.assertEqual(p.MAX_TOTAL_VERTICES,500)
        self.assertEqual(p.COVERAGE_GATE,.99)
        self.assertEqual(p.LEAKAGE_GATE,3.0)
        self.assertEqual(p.ALPHA_PRIMARY,24)

    def test_03_true_native_missing_backing_to_logical(self):
        comp,full,game,native,strokes=fixture()
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        self.assertEqual(missing.shape,(720,450))
        self.assertEqual(weights.shape,(240,150))
        self.assertGreater(meta["native_component_missing_backing_pixels"],0)
        self.assertTrue(elig[:,45].any())
        self.assertEqual(int(weights[80,45]),9)
        self.assertEqual(int(weights[80,60]),0)

    def test_04_flat_interior_no_eligible_when_not_missing(self):
        comp,full,game,native,strokes=fixture()
        native[:,(155+45)*3:(155+46)*3,3]=255
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        self.assertEqual(int(elig.sum()),0)
        self.assertEqual(meta["native_component_missing_backing_pixels"],0)

    def test_05_source_boundary_only_not_original_interior(self):
        comp,full,game,native,strokes=fixture()
        native[:,:,:,3]=0
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        self.assertTrue(elig[65,70])
        self.assertFalse(elig[90,70])
        self.assertGreater(meta["source_interior_gt2_missing_backing_pixels"],0)

    def test_06_wrong_native_shape_rejected(self):
        comp,full,game,native,strokes=fixture()
        for wrong in (native[1:,:,:],native.astype(np.float32)):
            with self.assertRaisesRegex(ValueError,"NATIVE_OR_COMPONENT_SHAPE"):
                p.boundary_missing(wrong,comp)

    def test_07_generates_short_source_contour_candidates(self):
        comp,full,game,native,strokes=fixture()
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        opts=p.repair_candidates(comp,full,elig)
        self.assertTrue(opts)
        self.assertTrue(all(x["width"] in (1,2) for x in opts))
        self.assertTrue(all(len(x["points"])==2 for x in opts))
        self.assertTrue(all(p.p4b1._source_centerline(x["points"],comp)
                            for x in opts))

    def test_08_rejects_eligible_outside_owner(self):
        comp,full,game,native,strokes=fixture()
        eligible=np.zeros_like(comp)
        eligible[30,30]=True
        with self.assertRaisesRegex(ValueError,"REPAIR_CANDIDATE_INPUT"):
            p.repair_candidates(comp,full,eligible)

    def test_09_greedy_rank_actual_backing_misses(self):
        comp,full,game,native,strokes=fixture()
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        selected,metrics=p.choose_corrections(
            comp,full,weights,elig,115,game,strokes)
        self.assertTrue(selected)
        self.assertTrue(metrics["greedy_ranking_uses_actual_native_alpha24_miss_weight"])
        self.assertEqual(selected[0]["strokeId"],"icon-177")
        self.assertTrue(all(s["colorIndex"]==115 for s in selected))
        self.assertTrue(all(s["width"] in (1,2) for s in selected))

    def test_10_never_exceeds_prespecified_original_budget(self):
        comp,full,game,native,strokes=fixture()
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        chosen,stats=p.choose_corrections(
            comp,full,weights,elig,115,game,strokes)
        self.assertLessEqual(len(chosen),73)
        self.assertLessEqual(stats["combined_stroke_count"],250)
        self.assertLessEqual(stats["combined_synthetic_vertices_NOT_CHALK"],500)
        self.assertEqual(stats["additional_vertices_NOT_CHALK"],2*len(chosen))

    def test_11_nearly_full_base_budget_only_one_correction(self):
        comp,full,game,native,strokes=fixture()
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        near=[{**s,"strokeId":"icon-%d"%i} for i,s in
              enumerate(strokes*2)][:249]
        selected,stats=p.choose_corrections(
            comp,full,weights,elig,115,game,near)
        self.assertLessEqual(len(selected),1)
        self.assertLessEqual(stats["combined_synthetic_vertices_NOT_CHALK"],500)

    def test_12_zero_real_misses_no_fabricated_correctives(self):
        comp,full,game,native,strokes=fixture()
        native[:,(155+45)*3:(155+46)*3,3]=255
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        selected,stats=p.choose_corrections(
            comp,full,weights,elig,115,game,strokes)
        self.assertEqual(selected,[])
        self.assertEqual(stats["additional_stroke_count"],0)

    def test_13_wrong_baseline_owner_rejected(self):
        comp,full,game,native,strokes=fixture()
        weights,elig,missing,meta=p.boundary_missing(native,comp)
        broken=[dict(s) for s in strokes]
        broken[0]["colorIndex"]=120
        with self.assertRaisesRegex(ValueError,"BASELINE_BUDGET_OR_COLOR"):
            p.choose_corrections(comp,full,weights,elig,115,game,broken)

    def test_14_no_mutation_of_original_color_area(self):
        comp,full,game,native,strokes=fixture()
        frozen=comp.copy()
        w,e,m,meta=p.boundary_missing(native,comp)
        p.choose_corrections(comp,full,w,e,115,game,strokes)
        self.assertTrue(np.array_equal(comp,frozen))
        self.assertTrue(np.array_equal(full,frozen))

    def test_15_original_RGB_overlay_only_diagnostic(self):
        comp,full,game,native,strokes=fixture()
        rgb=np.full((240,150,3),[90,73,65],np.uint8)
        out=p.overlay(rgb,comp,native)
        self.assertEqual(out.size,(450,720))

    def test_16_no_legacy_G32_or_V44_candidate_import(self):
        tree=ast.parse(Path(p.__file__).read_text(encoding="utf8"))
        direct=[name.name for node in ast.walk(tree)
                if isinstance(node,ast.Import) for name in node.names]
        imported=[node.module for node in ast.walk(tree)
                  if isinstance(node,ast.ImportFrom) and node.module]
        self.assertFalse(any("g32" in x.lower() or "v44" in x.lower() or
                             "p4c1" in x.lower() for x in direct+imported))
        self.assertIn("run_engine001_b1r_p4b1_hybrid_zone_coverage",direct)

    def test_17_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                p.run(Path(d),Path(d)/"missing.png",Path(d)/"bad.js",
                      Path(d)/"bad_renderer.js",Path(d))

    def test_18_deterministic_feedback_selection(self):
        comp,full,game,native,strokes=fixture()
        w,e,m,meta=p.boundary_missing(native,comp)
        a,da=p.choose_corrections(comp,full,w,e,115,game,strokes)
        b,db=p.choose_corrections(comp,full,w,e,115,game,strokes)
        self.assertEqual(a,b)
        self.assertEqual(da,db)

if __name__=="__main__":
    unittest.main()
