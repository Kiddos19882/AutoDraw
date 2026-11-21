#!/usr/bin/env python3
"""Synthetic independent contract tests for bounded SAM2 NH1; no fake neural run."""
import unittest

import numpy as np

from engine001_bpred_s4r1_generic_source_maps import generic_source_maps
from run_engine001_bpred_s4r1_nh1_sam2_variants import (
    AUTO_VARIANTS, SAMPLES, SOURCE_PROMPT_SEPARATION,
    choose_source_prompts, mask_metrics, original_to_model_rgb,
)


def sample(h=32,w=32):
    rgba = np.zeros((h,w,4),np.uint8)
    rgba[:,:,:3] = (20,25,30)
    rgba[:,w//2:,:3] = (190,120,80)
    rgba[:,:,3] = 255
    return rgba


def labels_and_reps(rgba):
    h,w=rgba.shape[:2]
    labels=np.ones((h,w),np.int32)
    labels[:,w//2:]=2
    core=np.ones((h,w),bool)
    core[:,w//2-1:w//2+1] = False
    rep=[
        {"region_id":1,"pixels":h*(w//2),
         "source_pixel_xy":[2,2],"source_rgb":[20,25,30]},
        {"region_id":2,"pixels":h*(w-w//2),
         "source_pixel_xy":[w-3,h-3],"source_rgb":[190,120,80]},
    ]
    return {"region_ids":labels,"geometric_potential_core":core,"representatives":rep}


class NH1SyntheticContracts(unittest.TestCase):
    def test_frozen_variants_and_scope(self):
        self.assertEqual(len(SAMPLES),2)
        self.assertEqual({r[1] for r in SAMPLES},{"KNOWN_CONTROL","DEV"})
        self.assertFalse(any("HELDOUT" in str(s) for s in SAMPLES))
        self.assertEqual(AUTO_VARIANTS["A0_original_auto8_strict"]["points_per_side"],8)
        self.assertEqual(AUTO_VARIANTS["A1_original_auto16_open"]["points_per_side"],16)
        self.assertEqual(AUTO_VARIANTS["A2_original_auto16_crop1"]["crop_n_layers"],1)
        self.assertEqual(AUTO_VARIANTS["A2_original_auto16_crop1"]["crop_n_points_downscale_factor"],2)
        self.assertEqual(AUTO_VARIANTS["A0_original_auto8_strict"]["stability_score_thresh"],.95)

    def test_original_alpha_only_model_composite(self):
        rgba=sample()
        rgba[0,0,:]=[4,100,200,0]
        rgba[0,1,:]=[4,100,200,127]
        before=rgba.copy()
        view=original_to_model_rgb(rgba)
        self.assertEqual(view.shape,rgba.shape[:2]+(3,))
        self.assertEqual(view[0,0].tolist(),[255,255,255])
        self.assertTrue(np.all(view[0,1]>rgba[0,1,:3]))
        self.assertTrue(np.array_equal(rgba,before))

    def test_bad_rgba_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"RGBA"):
            original_to_model_rgb(sample()[:,:,:3])

    def test_prompts_deterministic_from_regions_not_hand_roi(self):
        rgba=sample()
        m=generic_source_maps(rgba)
        r=labels_and_reps(rgba)
        p1=choose_source_prompts(r,m)
        p2=choose_source_prompts(r,m)
        self.assertEqual(p1,p2)
        self.assertEqual(len(p1),2)
        for p in p1:
            self.assertTrue(p["automatic_only"])
            x,y=p["point_coords_xy"][0]
            self.assertTrue(r["geometric_potential_core"][y,x])
            self.assertEqual(p["source_region_id"],int(r["region_ids"][y,x]))
            self.assertEqual(p["point_labels"][0],1)
            self.assertLessEqual(len(p["point_labels"]),2)
            if len(p["point_coords_xy"])>1:
                nx,ny=p["point_coords_xy"][1]
                self.assertNotEqual(r["region_ids"][ny,nx],r["region_ids"][y,x])
                self.assertGreaterEqual(np.hypot(nx-x,ny-y),SOURCE_PROMPT_SEPARATION)

    def test_no_valid_core_abstains_without_prompts(self):
        rgba=sample()
        m=generic_source_maps(rgba)
        r=labels_and_reps(rgba)
        r["geometric_potential_core"]=np.zeros(rgba.shape[:2],bool)
        self.assertEqual(choose_source_prompts(r,m),[])

    def test_no_owner_provenance_fails(self):
        rgba=sample()
        m=generic_source_maps(rgba)
        r=labels_and_reps(rgba)
        mm=dict(m)
        mm["owner_status"]="SOURCE_BOUND"
        with self.assertRaisesRegex(ValueError,"PROMPT_OWNER_PROVENANCE"):
            choose_source_prompts(r,mm)

    def test_empty_masks_are_not_false_success(self):
        rgba=sample()
        m=generic_source_maps(rgba)
        v=mask_metrics(np.zeros((0,32,32),bool),rgba,m)
        self.assertEqual(v["model_proposal_masks"],0)
        self.assertEqual(v["model_union_pixels"],0)
        self.assertIsNone(v["model_boundary_near_original_rgb_edge_ratio"])
        self.assertEqual(v["source_owner_status"],"MISSING")
        self.assertTrue(v["stroke_admission"].startswith("FORBIDDEN"))

    def test_mask_stats_diagnostic_not_ground_truth(self):
        rgba=sample()
        m=generic_source_maps(rgba)
        masks=np.zeros((2,32,32),bool)
        masks[0,:,2:12]=True
        masks[1,3:21,20:28]=True
        v=mask_metrics(masks,rgba,m)
        self.assertEqual(v["nonempty_proposals"],2)
        self.assertGreater(v["model_boundary_pixels"],0)
        self.assertEqual(v["critical_semantic_recall"],"UNKNOWN_NO_INDEPENDENT_GROUND_TRUTH")
        self.assertEqual(v["s4_strict"],"BLOCKED")

    def test_wrong_mask_shape_and_dtype_fail_closed(self):
        rgba=sample()
        m=generic_source_maps(rgba)
        with self.assertRaisesRegex(ValueError,"MODEL_MASK_SHAPE"):
            mask_metrics(np.zeros((1,31,32),bool),rgba,m)
        with self.assertRaisesRegex(ValueError,"MODEL_MASK_SHAPE"):
            mask_metrics(np.zeros((1,32,32),np.uint8),rgba,m)


if __name__=="__main__":
    unittest.main()
