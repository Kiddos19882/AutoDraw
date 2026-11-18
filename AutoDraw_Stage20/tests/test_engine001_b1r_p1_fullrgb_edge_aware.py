#!/usr/bin/env python3
"""B1-R full-res original-only math/source/legacy-boundary synthetic contracts."""
import unittest
from pathlib import Path
import numpy as np
from run_engine001_b1r_p1_fullrgb_edge_aware import (
    EXPERIMENT, FULL_SHAPE, METHODS, original_outline_rgba, logical_rgb,
    logical_protection, filter_original, full_features, output_rgb,
    evaluate, check_source, compose_preview, run, ROIS_FULL
)

def source_fixture():
    a=np.full(FULL_SHAPE, 246, dtype=np.uint8)
    a[25:155,20:100]=[73,58,55]
    a[60:180,100:177]=[188,165,142]
    a[120:140,35:145]=[45,32,30]
    a[180:200,50:185]=[238,178,155]
    a[200:295,45:175]=[237,228,219]
    a[83:87,63:67]=[15,12,11]
    return a

class B1RP1Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=source_fixture()
        cls.f=full_features(cls.source)

    def test_full_source_only_features_are_deterministic(self):
        a=full_features(self.source)
        for key in ("protected","source_edges","new_outline"):
            self.assertTrue(np.array_equal(a[key],self.f[key]))
        self.assertTrue(a["protected"].any())
        self.assertTrue(a["new_outline"].any())

    def test_full_resolution_protected_pixels_remain_exact(self):
        for name in METHODS:
            out=filter_original(self.source,name,self.f["protected"])
            self.assertTrue(np.array_equal(out[self.f["protected"]],
                                           self.source[self.f["protected"]]))

    def test_logical_protection_restores_original_after_resize(self):
        original=logical_rgb(self.source)
        protected=logical_protection(self.f["protected"])
        self.assertEqual(protected.shape,(240,150))
        self.assertTrue(protected.any())
        for name in METHODS:
            full,out=output_rgb(self.source,name,self.f,original,protected)
            self.assertEqual(out.shape,original.shape)
            self.assertTrue(np.array_equal(out[protected],original[protected]))
            self.assertTrue(np.array_equal(full[self.f["protected"]],
                                           self.source[self.f["protected"]]))

    def test_native_old_outline_not_required_and_source_rgb_color_only(self):
        rgba=original_outline_rgba(self.source,self.f["new_outline"])
        self.assertEqual(rgba.shape,(320,200,4))
        self.assertTrue(np.array_equal(rgba[...,3]>0,self.f["new_outline"]))
        self.assertTrue(np.all(rgba[self.f["new_outline"],3]==185))
        colors=set(map(tuple,self.source.reshape(-1,3)))
        for v in np.unique(rgba[self.f["new_outline"],:3],axis=0):
            self.assertIn(tuple(v),colors)
        logical=logical_rgb(self.source)
        preview=compose_preview(logical,rgba)
        self.assertEqual(preview.size,(150,240))

    def test_important_original_rectangles_not_palette_maps(self):
        self.assertEqual(EXPERIMENT,"ENGINE001_B1R_P1_FULLRGB_EDGE_AWARE_A")
        self.assertIn("female_face_eyes",ROIS_FULL)
        self.assertEqual(set(METHODS),{"A_SOFT","A_MID"})

    def test_reject_unknown_filter_or_unsafe_dimensions(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_B1R_P1_FILTER_INPUT_OR_METHOD"):
            filter_original(self.source,"G32",self.f["protected"])
        with self.assertRaisesRegex(ValueError,"BLOCKED_B1R_P1_FEATURE_SOURCE"):
            full_features(self.source[:20])
        with self.assertRaisesRegex(ValueError,"BLOCKED_B1R_P1_RESIZE_SOURCE"):
            logical_rgb(self.source[:20])
        with self.assertRaisesRegex(ValueError,"BLOCKED_B1R_P1_FULL_PROTECTION_SHAPE"):
            logical_protection(self.f["protected"][:20])

    def test_original_sha_fail_closed_not_regenerated(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"synthetic.png"
            from PIL import Image
            Image.fromarray(self.source).save(p)
            with self.assertRaisesRegex(ValueError,"BLOCKED_B1R_P1_ORIGINAL_SHA"):
                check_source(p)

    def test_source_gates_are_not_equivalent_to_visual_game_pass(self):
        rgb=logical_rgb(self.source)
        full,out=output_rgb(self.source,"A_SOFT",self.f,rgb,
                            logical_protection(self.f["protected"]))
        metrics=evaluate(self.source,rgb,full,out,
                         self.f["protected"],logical_protection(self.f["protected"]))
        self.assertEqual(metrics["gates"]["full_protected_exact"],True)
        self.assertIn(metrics["status"],{"SOURCE_SCREEN_PASS_VISUAL_PENDING","SOURCE_GATE_FAIL"})
        self.assertIn("roughness_reduction",metrics["gates"])

if __name__=="__main__":
    unittest.main()
