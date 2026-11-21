#!/usr/bin/env python3
"""S4R1 CR1 raw original RGB reference synthetic contracts; no game-native proof."""
import hashlib
import unittest

import numpy as np
from engine001_bpred_s4r1_original_rgb_pair_reference import (
    THRESHOLD, STROKE_FORBIDDEN, raw_contrast_endpoints, score_original_rgb_reference
)


def source(h=5,w=6):
    rgba=np.zeros((h,w,4),np.uint8)
    rgba[:,:,:3]=[12,12,12]
    rgba[:,:,3]=255
    return rgba


def bound(rgba, protected=None, core=None):
    h,w=rgba.shape[:2]
    if protected is None:protected=np.zeros((h,w),bool)
    if core is None:core=np.zeros((h,w),bool)
    return ({
        "owner_status":"MISSING",
        "stroke_admission":STROKE_FORBIDDEN,
        "semantic_detail_status":"UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL",
        "source_rgb":rgba[:,:,:3].copy(),"source_alpha":rgba[:,:,3].copy(),
        "protected":protected,"unknown":~protected,
        "candidate_interior":np.zeros((h,w),bool),
    },{
        "source_rgba_sha256":hashlib.sha256(rgba.tobytes()).hexdigest(),
        "source_owner_status":"MISSING",
        "stroke_admission":STROKE_FORBIDDEN,
        "geometric_potential_core":core,
    })


class RawOriginalReference(unittest.TestCase):
    def test_exact_threshold_31_not_32(self):
        self.assertEqual(THRESHOLD,32)
        a=source(1,2)
        a[0,1,0]=43
        self.assertFalse(raw_contrast_endpoints(a).any())
        a[0,1,0]=44
        self.assertEqual(raw_contrast_endpoints(a).tolist(),[[True,True]])

    def test_signed_arithmetic_handles_255_and_zero(self):
        a=source(1,2)
        a[0,0,:3]=0
        a[0,1,:3]=255
        self.assertEqual(int(raw_contrast_endpoints(a).sum()),2)

    def test_vertical_and_horizontal_both_endpoints(self):
        a=source(3,3)
        a[1,1,0]=60
        m=raw_contrast_endpoints(a)
        self.assertTrue(m[1,1])
        self.assertEqual(int(m.sum()),5)
        self.assertFalse(m[0,0])

    def test_diagonal_only_does_not_connect(self):
        a=source(2,2)
        a[0,0,:3]=0
        a[1,1,:3]=0
        a[0,1,:3]=40
        a[1,0,:3]=40
        # Every cardinal pair contrasts; this checks direct endpoints not
        # wrongly merging diagonal pixels into one independent connection.
        self.assertEqual(int(raw_contrast_endpoints(a).sum()),4)
        a=source(2,2)
        a[0,0,:3]=0
        a[1,1,:3]=0
        a[0,1,:3]=0
        a[1,0,:3]=0
        self.assertEqual(int(raw_contrast_endpoints(a).sum()),0)

    def test_nonopaque_pair_excluded(self):
        a=source(1,3)
        a[0,1,0]=100
        a[0,1,3]=128
        self.assertEqual(int(raw_contrast_endpoints(a).sum()),0)
        a[0,1,3]=255
        self.assertEqual(int(raw_contrast_endpoints(a).sum()),3)

    def test_uniform_not_applicable(self):
        a=source()
        sm,rg=bound(a)
        result=score_original_rgb_reference(a,sm,rg)
        self.assertEqual(result["status"],"NOT_APPLICABLE_NO_OPAQUE_RGB_CONTRAST_PAIRS")
        self.assertIsNone(result["protected_fraction_on_raw_contrast_reference"])
        self.assertEqual(result["source_game_owner_status"],"MISSING")

    def test_known_missed_pairs_fail_but_strokes_forbidden(self):
        a=source(1,3)
        a[0,1,0]=100
        sm,rg=bound(a)
        result=score_original_rgb_reference(a,sm,rg)
        self.assertEqual(result["source_contrast_endpoints"],3)
        self.assertEqual(result["source_contrast_unprotected_endpoints"],3)
        self.assertIn("DIAGNOSTIC_FAIL",result["status"])
        self.assertEqual(result["stroke_admission"],STROKE_FORBIDDEN)
        self.assertEqual(result["semantic_critical_recall"],"NOT_READY_NO_INDEPENDENT_HUMAN_LABELS")

    def test_protected_all_exact_endpoints_source_only_pass(self):
        a=source(1,3)
        a[0,1,0]=100
        sm,rg=bound(a,protected=np.ones((1,3),bool))
        result=score_original_rgb_reference(a,sm,rg)
        self.assertEqual(result["source_contrast_unprotected_endpoints"],0)
        self.assertIn("PASS_RAW_RGB",result["status"])
        self.assertEqual(result["source_color_owner_accuracy"],
                         "UNKNOWN_NO_CANONICAL_OWNER_REFERENCE")

    def test_tamper_original_provenance_fail_closed(self):
        a=source(1,3)
        sm,rg=bound(a)
        a[0,1,0]=100
        with self.assertRaisesRegex(ValueError,"ORIGINAL_SOURCE_REGION_PROVENANCE"):
            score_original_rgb_reference(a,sm,rg)
        sm,rg=bound(a)
        sm["source_rgb"][0,0,0]=200
        with self.assertRaisesRegex(ValueError,"ORIGINAL_RGB_ALPHA_MISMATCH"):
            score_original_rgb_reference(a,sm,rg)

    def test_unknown_and_core_invariants_fail(self):
        a=source()
        sm,rg=bound(a)
        sm["candidate_interior"][0,0]=True
        with self.assertRaisesRegex(ValueError,"UNKNOWN_NOT_ADMISSIBLE"):
            score_original_rgb_reference(a,sm,rg)
        sm,rg=bound(a,protected=np.ones((5,6),bool),
                    core=np.ones((5,6),bool))
        with self.assertRaisesRegex(ValueError,"UNKNOWN_NOT_ADMISSIBLE"):
            score_original_rgb_reference(a,sm,rg)

    def test_wrong_array_type_or_empty_source_fail(self):
        with self.assertRaisesRegex(ValueError,"INVALID_ORIGINAL_RGBA"):
            raw_contrast_endpoints(np.zeros((0,3,4),np.uint8))
        with self.assertRaisesRegex(ValueError,"INVALID_ORIGINAL_RGBA"):
            raw_contrast_endpoints(source()[:,:,:3])


if __name__=="__main__":
    unittest.main()
