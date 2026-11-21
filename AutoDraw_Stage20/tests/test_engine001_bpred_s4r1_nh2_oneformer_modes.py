#!/usr/bin/env python3
"""Synthetic NH2 OneFormer postprocessor provenance tests; never fake model inference."""
import unittest
import numpy as np

from engine001_bpred_s4r1_generic_source_maps import generic_source_maps
from run_engine001_bpred_s4r1_nh2_oneformer_modes import (
    MODEL_ID, MODEL_REVISION, TASKS, THRESHOLDS, safe_segments,
    validate_prediction, preview,
)


def source():
    a=np.zeros((12,14,4),np.uint8)
    a[:,:,:3]=[180,115,75]
    a[:,:,3]=255
    a[0,0,3]=0
    return a


class NH2ModeContracts(unittest.TestCase):
    def test_pinned_model_and_modes(self):
        self.assertEqual(MODEL_ID,"shi-labs/oneformer_ade20k_swin_tiny")
        self.assertEqual(MODEL_REVISION,"05f2812b1eccf9909b3897777450f8d68148cafc")
        self.assertEqual(TASKS,("semantic","instance","panoptic"))
        self.assertEqual(THRESHOLDS,(.5,.3))

    def test_semantic_labels_not_game_owner(self):
        a=source();m=generic_source_maps(a)
        labels=np.zeros(a.shape[:2],np.int32)
        labels[:,7:]=22
        v=validate_prediction("semantic",labels,[],a,m)
        self.assertEqual(v["distinct_ids"],2)
        self.assertEqual(v["semantic_reference"],"PSEUDOLABEL_NOT_INDEPENDENT_GT")
        self.assertEqual(v["source_owner_status"],"MISSING")
        self.assertEqual(v["selected_pixels"],a.shape[0]*a.shape[1])
        self.assertEqual(v["selected_invalid_original_alpha_pixels"],1)
        self.assertTrue(v["stroke_admission"].startswith("FORBIDDEN"))
        self.assertEqual(preview(labels).shape,(12,14,3))

    def test_instance_selected_segments_and_alpha_are_diagnostic(self):
        a=source();m=generic_source_maps(a)
        labels=np.full(a.shape[:2],-1,np.int32)
        labels[:4,:4]=5
        v=validate_prediction(
            "instance",labels,[{"id":5,"label_id":12,"score":0.95}],a,m)
        self.assertEqual(v["distinct_ids"],1)
        self.assertEqual(v["selected_pixels"],16)
        self.assertEqual(v["selected_invalid_original_alpha_pixels"],1)
        self.assertEqual(v["label_or_segment_counts"],{"5":16})
        self.assertEqual(v["exact_CHALK"],None)

    def test_panoptic_negative_background_and_zero_id_supported(self):
        a=source();m=generic_source_maps(a)
        labels=np.full(a.shape[:2],-1,np.int32)
        labels[0:2,0:3]=0
        v=validate_prediction("panoptic",labels,[{"id":0,"label_id":0}],a,m)
        self.assertEqual(v["label_or_segment_counts"],{"0":6})
        self.assertEqual(v["status"],"REAL_INSTANCE_PANOPTIC_PSEUDOLABELS_ONLY")

    def test_no_segments_must_abstain(self):
        a=source();m=generic_source_maps(a)
        v=validate_prediction("instance",None,[],a,m)
        self.assertEqual(v["distinct_ids"],0)
        self.assertEqual(v["selected_pixels"],0)
        self.assertEqual(v["status"],"NO_SEGMENTS_NOT_MODEL_QUALITY_PASS")

    def test_unknown_unbound_instance_id_fails(self):
        a=source();m=generic_source_maps(a)
        x=np.zeros(a.shape[:2],np.int32)
        with self.assertRaisesRegex(ValueError,"UNBOUND_INSTANCE_SEGMENT_ID"):
            validate_prediction("instance",x,[],a,m)

    def test_bad_semantic_range_and_shapes_fail(self):
        a=source();m=generic_source_maps(a)
        with self.assertRaisesRegex(ValueError,"SEMANTIC_CLASS_RANGE"):
            validate_prediction("semantic",np.full(a.shape[:2],150,np.int32),[],a,m)
        with self.assertRaisesRegex(ValueError,"SEGMENTATION_SHAPE_OR_IDS"):
            validate_prediction("semantic",np.zeros((12,13),np.int32),[],a,m)
        with self.assertRaisesRegex(ValueError,"UNKNOWN_TASK"):
            validate_prediction("unverified",np.zeros(a.shape[:2],np.int32),[],a,m)

    def test_duplicate_and_bad_source_provenance_fail(self):
        a=source();m=generic_source_maps(a)
        with self.assertRaisesRegex(ValueError,"DUPLICATE_SEGMENT_ID"):
            safe_segments([{"id":2},{"id":2}])
        v=dict(m);v["owner_status"]="SOURCE_BOUND"
        with self.assertRaisesRegex(ValueError,"SOURCE_OR_OWNER_PROVENANCE"):
            validate_prediction("semantic",np.zeros(a.shape[:2],np.int32),[],a,v)


if __name__=="__main__":
    unittest.main()
