#!/usr/bin/env python3
"""AWEAK2 test one automatic source-Lab candidate. Pure synthetic, never a GT."""
import hashlib
import unittest

import numpy as np

from engine001_bpred_s4r1_generic_source_maps import generic_source_maps
from run_engine001_bpred_s4r1_aweak2_multiscale_lab_source_proposal import (
    source_multiscale_lab_proposal, compare_with_approx_marks, VERSION,
)
from engine001_bpred_s4r1_semref1_human_review_validation import CODES, FORBIDDEN


def fixture():
    rgba=np.empty((32,32,4),np.uint8)
    rgba[:,:,:3]=(80,20,100)
    rgba[:,16:,:3]=(30,70,100)
    rgba[:,:,3]=255
    source=generic_source_maps(rgba)
    core=np.zeros((32,32),bool)
    core[5:10,5:10] = source["unknown"][5:10,5:10]
    regions={
        "source_owner_status":"MISSING",
        "stroke_admission":FORBIDDEN,
        "source_rgba_sha256":hashlib.sha256(rgba.tobytes()).hexdigest(),
        "geometric_potential_core":core,
        "region_ids":np.ones((32,32),dtype=np.int32),
    }
    a=np.zeros((32,32,3),np.uint8)
    a[12,15]=CODES[1]
    a[5:10,5:10]=CODES[3]
    return rgba,source,regions,a


class TestOneFixedAWEAK2AutomaticCandidate(unittest.TestCase):
    def test_auto_warning_without_manual_mark_or_rgb_mutation(self):
        rgba,s,r,a=fixture()
        before=rgba.copy()
        d=source_multiscale_lab_proposal(rgba,s,r)
        self.assertEqual(d["version"],VERSION)
        self.assertFalse(d["human_mask_used_to_generate"])
        self.assertEqual(d["source_owner_status"],"MISSING")
        self.assertEqual(d["stroke_admission"],FORBIDDEN)
        np.testing.assert_array_equal(rgba,before)
        self.assertEqual(len(d["scales"]),2)
        self.assertEqual([x["sigma_source_pixels"] for x in d["scales"]],[1.0,3.0])
        self.assertGreater(np.count_nonzero(d["warning"]),0)

    def test_no_old_protection_removed_and_no_core_promoted(self):
        rgba,s,r,a=fixture()
        d=source_multiscale_lab_proposal(rgba,s,r)
        self.assertTrue(np.all(d["protected_trial"][s["protected"]]))
        self.assertFalse(np.any(d["core_trial"] & ~r["geometric_potential_core"]))
        self.assertFalse(np.any(d["core_trial"] & d["protected_trial"]))
        self.assertEqual(d["old_potential_core_pixels"],np.count_nonzero(r["geometric_potential_core"]))

    def test_all_source_region_mark_results_are_descriptive(self):
        rgba,s,r,a=fixture()
        d=source_multiscale_lab_proposal(rgba,s,r)
        m=compare_with_approx_marks(a,s,r,d)
        self.assertFalse(m["human_rgb_pixel_exact_ground_truth"])
        self.assertFalse(m["game128_owner_is_known"])
        self.assertEqual(m["stroke_admission"],FORBIDDEN)
        self.assertEqual(m["K_count_approx_critical_or_boundary"],1)
        self.assertEqual(m["I_count_human_visual_interior"],25)
        for rad in ("0","2","5"):
            k=m["K_near_source_protected_radii"][rad]
            self.assertGreaterEqual(k["trial_K_near"],k["baseline_K_near"])
            self.assertGreaterEqual(k["K_fraction_gain"],0)

    def test_proposal_does_not_depend_on_human_labels(self):
        rgba,s,r,a=fixture()
        x=source_multiscale_lab_proposal(rgba,s,r)
        a[:,:,:]=0
        a[20,20]=CODES[2]
        a[25:30,25:30]=CODES[3]
        y=source_multiscale_lab_proposal(rgba,s,r)
        np.testing.assert_array_equal(x["protected_trial"],y["protected_trial"])
        np.testing.assert_array_equal(x["core_trial"],y["core_trial"])

    def test_bad_owner_is_fail_closed(self):
        rgba,s,r,a=fixture()
        s["owner_status"]="SOURCE_BOUND"
        with self.assertRaisesRegex(ValueError,"SOURCE_PROVENANCE_OR_OWNER"):
            source_multiscale_lab_proposal(rgba,s,r)

    def test_bad_core_is_fail_closed(self):
        rgba,s,r,a=fixture()
        r["geometric_potential_core"][0,15]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_UNKNOWN_OR_CORE_GATE"):
            source_multiscale_lab_proposal(rgba,s,r)

    def test_input_changed_detected(self):
        rgba,s,r,a=fixture()
        rgba[0,0,0]+=1
        with self.assertRaisesRegex(ValueError,"SOURCE_PROVENANCE_OR_OWNER"):
            source_multiscale_lab_proposal(rgba,s,r)


if __name__=="__main__":
    unittest.main()
