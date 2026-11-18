#!/usr/bin/env python3
"""B2 synthetic swatch component guards; original-source only, no native claims."""
import unittest
import numpy as np
from run_engine001_color_island_r2_p2_p2_b2_safe_cleanup import (
    VARIANTS,build_components,safe_cleanup,screen)

def fixture():
    p=np.full((32,3),80,dtype=np.uint8)
    p[30]=[255,255,255]
    p[31]=[27,27,27]
    original=np.full((240,150,3),80,np.uint8)
    labels=np.full((240,150),15,np.uint8)
    labels[90,75]=31
    protected=np.zeros((240,150),bool)
    return labels,original,protected,p

class B2OriginalSupportedTests(unittest.TestCase):
    def test_singleton_can_merge_to_large_source_supported_neighbor(self):
        labels,original,protected,p=fixture()
        for method in VARIANTS:
            with self.subTest(method=method):
                out,meta=safe_cleanup(labels,original,protected,p,method)
                self.assertEqual(int(out[90,75]),15)
                self.assertEqual(meta["accepted_region_count"],1)
                self.assertEqual(meta["changed_pixels"],1)
    def test_source_protection_prevents_donor_edit(self):
        labels,original,protected,p=fixture()
        protected[90,75]=True
        out,meta=safe_cleanup(labels,original,protected,p,"B2_SAFE12")
        self.assertTrue(np.array_equal(out,labels))
        self.assertEqual(meta["accepted_region_count"],0)
        self.assertEqual(meta["rejected_reasons"]["KEEP_ORIGINAL_PROTECTED"],1)
    def test_strong_source_seam_prevents_merge(self):
        labels,original,protected,p=fixture()
        original[90,75]=[240,240,240]
        out,meta=safe_cleanup(labels,original,protected,p,"B2_SAFE4")
        self.assertTrue(np.array_equal(out,labels))
        self.assertEqual(meta["accepted_region_count"],0)
    def test_reproducible_and_input_not_mutated(self):
        labels,original,protected,p=fixture()
        raw=labels.copy()
        a,m=safe_cleanup(labels,original,protected,p,"B2_SAFE12")
        b,n=safe_cleanup(labels,original,protected,p,"B2_SAFE12")
        self.assertTrue(np.array_equal(a,b))
        self.assertEqual(m,n)
        self.assertTrue(np.array_equal(labels,raw))
    def test_disallow_unregistered_methods_and_shapes(self):
        labels,original,protected,p=fixture()
        with self.assertRaisesRegex(ValueError,"BLOCKED_METHOD"):
            safe_cleanup(labels,original,protected,p,"B2_TUNED")
        with self.assertRaisesRegex(ValueError,"BLOCKED_INPUT_SHAPE"):
            safe_cleanup(labels[:20],original,protected,p,"B2_SAFE4")
    def test_strict_screen_fails_on_unmet_compaction(self):
        b=dict(mean_deltaE00=5.8,p95_deltaE00=17.7,excess_chroma_pixels=0,
            original_fixed_edge_fraction=.95,nonwhite_components4=1450,
            nonwhite_singletons=900,female_face_eyes_mean_deltaE00=7,
            male_face_eyes_mean_deltaE00=7,hands_orange_mean_deltaE00=7)
        g=dict(b,nonwhite_components4=1284,nonwhite_singletons=779)
        t=dict(b,nonwhite_components4=1400,nonwhite_singletons=850)
        gates=screen(t,b,g,True,10)
        self.assertTrue(gates["protected_labels"])
        self.assertFalse(gates["nonwhite_components"])
        self.assertFalse(gates["nonwhite_singletons"])
        self.assertFalse(all(gates.values()))

if __name__=="__main__":unittest.main()
