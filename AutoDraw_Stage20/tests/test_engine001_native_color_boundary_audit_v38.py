#!/usr/bin/env python3
"""ENGINE-001 V38 algorithm-only safety tests; no brush simulation quality."""
import unittest
import numpy as np
from run_engine001_native_color_boundary_audit_v38 import (
    class_metrics,components)

class BoundaryAuditTests(unittest.TestCase):
    def test_boundary_vs_interior_and_foreign(self):
        target=np.zeros((15,15),dtype=bool)
        target[2:13,2:13]=True
        painted=np.zeros_like(target)
        painted[2:13,2:13]=True
        painted[7,7]=False
        painted[2,1]=True
        foreground=target.copy()
        roi=np.zeros_like(target);roi[:,2:13]=True
        result=class_metrics(target,painted,foreground,roi)
        self.assertEqual(result["target_native_pixels"],121)
        self.assertEqual(result["painted_target_native_pixels"],120)
        self.assertEqual(result["missed_target_native_pixels"],1)
        self.assertEqual(result["missed_class_interior_distance_ge_3_native_px"],1)
        self.assertEqual(result["outside_logical_artwork_ROI_native_pixels"],1)
        self.assertEqual(result["missed_components"]["count"],1)

    def test_small_target_all_missing_is_boundary(self):
        target=np.zeros((9,9),dtype=bool)
        target[3:6,3:6]=True
        painted=np.zeros_like(target)
        result=class_metrics(target,painted,target,np.ones_like(target))
        self.assertEqual(result["missed_target_native_pixels"],9)
        self.assertEqual(result["missed_class_interior_distance_ge_3_native_px"],0)
        self.assertEqual(result["native_recall"],0)

    def test_empty_target_rejected(self):
        empty=np.zeros((6,6),dtype=bool)
        with self.assertRaisesRegex(ValueError,"empty required"):
            class_metrics(empty,empty,empty,empty)

    def test_components_size_bins(self):
        mask=np.zeros((20,20),dtype=bool)
        mask[1:4,1:4]=True
        mask[8:14,8:14]=True
        x=components(mask)
        self.assertEqual(x["count"],2)
        self.assertEqual(x["areas_ge_9_native_px"],2)
        self.assertEqual(x["areas_ge_36_native_px"],1)
        self.assertEqual(x["areas_ge_144_native_px"],0)
        self.assertEqual(x["top_largest"][0]["area_native_px"],36)

if __name__=="__main__":
    unittest.main()
