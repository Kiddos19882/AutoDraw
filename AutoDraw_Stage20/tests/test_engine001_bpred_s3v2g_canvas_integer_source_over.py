#!/usr/bin/env python3
"""Frozen S3v2g integer premul source-over arithmetic and fail-closed unit tests."""
from __future__ import annotations

import unittest
import numpy as np

import run_engine001_bpred_s3v2g_canvas_integer_source_over as c
import run_engine001_bpred_s3_native_source_over as s3


class BpredS3v2gContracts(unittest.TestCase):
    def test_01_frozen_candidate_set_and_original_E0(self):
        self.assertEqual(c.E0_BLOB,"9dd47155d284f63c81cbb525ad757b137c287f11")
        self.assertEqual(c.NAMES,("P0","P1","P2","P3"))
        self.assertEqual(c.PARENT_SHA,"819b7fd20272e5ac87ead72ce0610687fa51cbf4")
        self.assertEqual(c.PARENT_RUN,"44710870514")
        self.assertEqual(c.BINS,((0,0),(1,15),(16,63),(64,127),(128,254),(255,255)))

    def test_02_each_integer_blend_preserves_opaque_top(self):
        b=np.array([[[20,30,40,255]]],np.uint8)
        t=np.array([[[197,65,145,255]]],np.uint8)
        for mode in ("P1","P2","P3"):
            np.testing.assert_array_equal(c.byte_blend(b,t,mode),t)

    def test_03_opaque_bottom_with_transparent_top(self):
        b=np.array([[[80,61,53,255]]],np.uint8)
        t=np.array([[[0,0,0,0]]],np.uint8)
        for mode in ("P1","P2","P3"):
            np.testing.assert_array_equal(c.byte_blend(b,t,mode),b)

    def test_04_empty_both_remain_empty(self):
        b=np.zeros((2,3,4),np.uint8)
        t=b.copy()
        for mode in ("P1","P2","P3"):
            np.testing.assert_array_equal(c.byte_blend(b,t,mode),b)

    def test_05_non_opaque_alpha_integer_model_is_bounded(self):
        a=np.array([[[80,61,53,32],[197,65,145,64]]],np.uint8)
        b=np.array([[[197,65,145,30],[80,61,53,128]]],np.uint8)
        for mode in ("P1","P2","P3"):
            r=c.byte_blend(a,b,mode)
            self.assertEqual(r.dtype,np.uint8)
            self.assertEqual(r.shape,a.shape)
            self.assertTrue(np.all(r[:,:,3]>=np.maximum(a[:,:,3],b[:,:,3])))

    def test_06_reject_unfrozen_mode_and_bad_rgba(self):
        a=np.zeros((1,1,4),np.uint8)
        for bottom,top,mode in ((a,a,"P0"),(a,a,"P4"),
                                 (a.astype(float),a,"P2"),
                                 (a,a[:,:,:3],"P3"),
                                 (a,a[0],"P2")):
            with self.assertRaisesRegex(ValueError,"UNFROZEN_BLEND_MODE_RGBA"):
                c.byte_blend(bottom,top,mode)

    def test_07_half_up_inverse_is_not_any_color_at_low_alpha(self):
        lut=c.feasible_lookup()
        self.assertEqual(int(lut[64,80]),1)
        self.assertEqual(int(lut[1,80]),0)
        self.assertEqual(int(lut[1,255]),1)
        self.assertEqual(int(lut[255,80]),0)

    def test_08_unknown_sources_are_recorded_not_silenced(self):
        a=np.array([[[80,61,53,64],[80,70,60,1],[0,0,0,0]]],np.uint8)
        d=c.unknown_pixels(a,c.feasible_lookup())
        self.assertEqual(d["fractional_alpha_pixels"],2)
        self.assertGreaterEqual(d["unknown_fractional_rgba_pixels"],1)
        self.assertGreaterEqual(d["zero_feasible_channels"],1)
        self.assertEqual(d["multiple_feasible_channels"],0)

    def test_09_original_float_C0_still_reference(self):
        a=np.array([[[80,61,53,255]]],np.uint8)
        b=np.array([[[197,65,145,255]]],np.uint8)
        model, _ = c.metric("P0",a,b,b,np.array([[True]]))
        self.assertTrue(model["frozen_H1_pass"])
        np.testing.assert_array_equal(s3.source_over(a,b),b)

    def test_10_errors_do_not_raise_thresholds(self):
        a=np.array([[[80,61,53,255]]],np.uint8)
        b=np.array([[[197,65,145,255]]],np.uint8)
        changed=b.copy()
        changed[0,0,0]=201
        metric,_=c.metric("P0",a,b,changed,np.array([[True]]))
        self.assertFalse(metric["frozen_H1_pass"])
        self.assertEqual(metric["max_channel_byte"],4)


if __name__=="__main__":
    unittest.main()
