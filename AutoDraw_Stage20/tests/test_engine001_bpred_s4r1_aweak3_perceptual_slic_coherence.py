#!/usr/bin/env python3
"""AWEAK3 synthetic source-only fail-closed tests, never human/owner/native GT."""
import hashlib
import unittest

import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_generic_source_maps import generic_source_maps
from engine001_bpred_s4r1_semref1_human_review_validation import CODES, FORBIDDEN
from run_engine001_bpred_s4r1_aweak3_perceptual_slic_coherence import (
    coherence_trial, compare_weak_mark_tradeoff,
)


def fixture(right_rgb=(100,100,100)):
    rgba=np.empty((32,32,4),dtype=np.uint8)
    rgba[:,:,:3]=(100,100,100)
    rgba[:,16:,:3]=right_rgb
    rgba[:,:,3]=255
    src=generic_source_maps(rgba)
    labels=np.ones((32,32),np.int32)
    labels[:,16:]=2
    border=np.zeros((32,32),bool)
    border[:,15:17]=True
    disagree=np.zeros((32,32),bool)
    warning=src["source_edge"]|border|disagree
    core=~src["protected"]&~ndimage.binary_dilation(warning,iterations=1)&~src["exact_white_evidence"]
    region={
        "source_owner_status":"MISSING",
        "stroke_admission":FORBIDDEN,
        "source_rgba_sha256":hashlib.sha256(rgba.tobytes()).hexdigest(),
        "region_ids":labels,
        "representatives":[
            {"region_id":1,"source_rgb":[100,100,100]},
            {"region_id":2,"source_rgb":list(right_rgb)},
        ],
        "region_boundary":border,
        "region_color_uncertain":disagree,
        "source_region_warning":warning,
        "geometric_potential_core":core,
    }
    a=np.zeros((32,32,3),dtype=np.uint8)
    a[5:27,15]=CODES[1]  # visual important boundary marker, subjective
    a[5:27,19:25]=CODES[3]
    return rgba,src,region,a


class TestAWEAK3PerceptualCoherence(unittest.TestCase):
    def test_similar_region_medoids_restore_only_hypothetical_core(self):
        rgba,src,reg,a=fixture()
        before=rgba.copy()
        d=coherence_trial(rgba,src,reg)
        self.assertEqual(d["weak_region_pair_count"],1)
        self.assertEqual(d["strong_region_pair_count"],0)
        self.assertGreater(d["newly_unexcluded_core_pixels"],0)
        self.assertTrue(np.all(d["trial_core"][reg["geometric_potential_core"]]))
        self.assertFalse(np.any(d["trial_core"] & src["protected"]))
        np.testing.assert_array_equal(rgba,before)
        self.assertFalse(d["human_mark_input_to_generator"])
        self.assertEqual(d["stroke_admission"],FORBIDDEN)

    def test_large_region_lab_difference_keeps_border(self):
        rgba,src,reg,a=fixture(right_rgb=(5,5,5))
        d=coherence_trial(rgba,src,reg)
        self.assertEqual(d["strong_region_pair_count"],1)
        self.assertEqual(d["weak_region_pair_count"],0)
        np.testing.assert_array_equal(d["trial_core"],reg["geometric_potential_core"])
        self.assertEqual(d["newly_unexcluded_core_pixels"],0)

    def test_human_marks_not_generator_input_and_proxy_harm_reported(self):
        rgba,src,reg,a=fixture()
        d=coherence_trial(rgba,src,reg)
        m=compare_weak_mark_tradeoff(a,reg,d)
        self.assertGreater(m["I_visual_marked_pixels"],0)
        self.assertGreater(m["K_visual_marked_pixels"],0)
        self.assertGreater(m["K_newly_in_core_warning"],0)
        self.assertFalse(m["human_rgb_equality_assumed"])
        self.assertEqual(m["stroke_admission"],FORBIDDEN)
        a[:]=CODES[0]
        d2=coherence_trial(rgba,src,reg)
        np.testing.assert_array_equal(d["trial_core"],d2["trial_core"])

    def test_mismatch_source_hash_fails(self):
        rgba,src,reg,a=fixture()
        rgba[0,0,0]+=1
        with self.assertRaisesRegex(ValueError,"INVALID_ORIGINAL_PROVENANCE"):
            coherence_trial(rgba,src,reg)

    def test_wrong_existing_p2_border_fails(self):
        rgba,src,reg,a=fixture()
        reg["region_boundary"][:]=False
        with self.assertRaisesRegex(ValueError,"P2_SOURCE_BORDER_MISMATCH"):
            coherence_trial(rgba,src,reg)

    def test_fake_p2_oldcore_fails(self):
        rgba,src,reg,a=fixture()
        reg["geometric_potential_core"][:]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_UNKNOWN_OR_REGION_MAP|P2_GEOMETRIC_CORE_MISMATCH"):
            coherence_trial(rgba,src,reg)

    def test_no_human_interior_fails_evaluator(self):
        rgba,src,reg,a=fixture()
        d=coherence_trial(rgba,src,reg)
        a[a[:,:,1]==255]=CODES[0]  # all magenta and green are marked in channel1=0/255
        with self.assertRaisesRegex(ValueError,"NO_HUMAN_VISUAL_SUPPORT"):
            compare_weak_mark_tradeoff(a,reg,d)


if __name__=="__main__":
    unittest.main()
