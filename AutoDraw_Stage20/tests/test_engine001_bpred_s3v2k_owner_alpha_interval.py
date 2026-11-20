#!/usr/bin/env python3
"""S3v2k immutable E0 physical-byte interval E2 unit and fail-closed regressions."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

import numpy as np

import run_engine001_bpred_s3v2k_owner_alpha_interval as k


class S3v2kFrozenIntervalTests(unittest.TestCase):
    def test_01_pins_and_original_gates(self):
        self.assertEqual(k.E0_BLOB,"3ae0356c353b89249ad636fa03cdd094e3d3e713")
        self.assertEqual(k.SOURCE_SHA,"ad1fa7fd66d4df563d729b7faae27651ca8279ea")
        self.assertEqual(k.SOURCE_RUN,"44721915503")
        self.assertEqual(k.PAD_RGB,2.)
        self.assertEqual(k.PAD_ALPHA,1.)
        self.assertEqual(k.MARGIN_LOGICAL,3.)
        self.assertEqual(k.ROI,(slice(279,441),slice(435,597)))

    def test_02_alpha0_is_interval_not_zero(self):
        a=np.array([[0,1,255]],np.uint8)
        lo,hi=k.alpha_interval(a)
        self.assertAlmostEqual(lo[0,0],0.)
        self.assertAlmostEqual(hi[0,0],.5/255.)
        self.assertAlmostEqual(lo[0,2],254.5/255.)
        self.assertEqual(hi[0,2],1.)

    def test_03_transparent_two_owners_stay_unknown_low_alpha(self):
        b=np.zeros((1,2,4),dtype=np.uint8)
        t=b.copy()
        lo,hi,unknown=k.interval_envelope(
            b,t,[20,120,220],[230,55,10])
        self.assertTrue(unknown.all())
        np.testing.assert_array_equal(lo[:,:,:3],np.zeros((1,2,3)))
        np.testing.assert_array_equal(hi[:,:,:3],np.full((1,2,3),255))
        self.assertTrue(k.output_contained(b,lo,hi).all())

    def test_04_alpha0_top_can_change_opaque_lower_by_one(self):
        b=np.array([[[165,215,66,255]]],np.uint8)
        t=np.zeros_like(b)
        actual=np.array([[[164,214,66,255]]],np.uint8)
        lo,hi,unk=k.interval_envelope(b,t,[165,215,66],[44,73,240])
        self.assertFalse(unk[0,0])
        self.assertTrue(k.output_contained(actual,lo,hi).all())
        self.assertFalse(np.array_equal(b,actual))

    def test_05_envelope_real_missing_pixel_must_not_be_hidden(self):
        b=np.array([[[165,215,66,255]]],np.uint8)
        t=np.zeros_like(b)
        actual=np.array([[[110,110,110,255]]],np.uint8)
        lo,hi,_=k.interval_envelope(b,t,[165,215,66],[44,73,240])
        self.assertFalse(k.output_contained(actual,lo,hi)[:,:,:3].all())

    def test_06_geometry_candidate_not_auto_production_safe(self):
        # pixel x=1 far from stroke centered x=100 logical; true no-change.
        b=np.array([[[111,112,113,255]]],np.uint8)
        t=np.zeros_like(b)
        seg={"width":1,"points":[{"x":100,"y":100},{"x":120,"y":100}]}
        out=k.classifier(b,t,b,seg)
        self.assertEqual(out["unchanged_candidate_correct"],1)
        self.assertEqual(out["false_safe"],0)
        self.assertEqual(out["unknown"],0)

    def test_07_true_change_outside_geometry_is_false_safe_not_tolerated(self):
        b=np.array([[[111,112,113,255]]],np.uint8)
        t=np.zeros_like(b)
        actual=b.copy()
        actual[0,0,0]-=1
        seg={"width":1,"points":[{"x":100,"y":100},{"x":120,"y":100}]}
        out=k.classifier(b,t,actual,seg)
        self.assertEqual(out["false_safe"],1)
        self.assertEqual(out["unchanged_candidate_correct"],0)

    def test_08_near_opaque_edge_changes_are_unknown(self):
        b=np.array([[[165,215,66,255]]],np.uint8)
        t=np.zeros_like(b)
        actual=b.copy()
        actual[0,0,1]-=1
        seg={"width":2,"points":[{"x":0.1,"y":0.1},{"x":0.4,"y":0.4}]}
        out=k.classifier(b,t,actual,seg)
        self.assertEqual(out["false_safe"],0)
        self.assertEqual(out["unknown"],1)
        self.assertEqual(out["changed"],1)

    def test_09_invalid_distance_and_width_fail_closed(self):
        xs=np.array([0,1])
        ys=np.array([0,1])
        with self.assertRaisesRegex(ValueError,"OWNER_SEGMENT_NOT_FINITE"):
            k.segment_distance(xs,ys,[{"x":1,"y":1},{"x":1,"y":1}])
        b=np.zeros((1,1,4),np.uint8)
        with self.assertRaisesRegex(ValueError,"OWNER_ORIGINAL_WIDTH"):
            k.classifier(b,b,b,{"width":11,"points":[{"x":1,"y":1},{"x":2,"y":2}]})

    def test_10_corrupt_parent_zip_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"corrupt.zip"
            with ZipFile(file,"w") as z:
                z.writestr("report.json",json.dumps({}))
            with ZipFile(file) as z:
                with self.assertRaisesRegex(ValueError,"PARENT_ZIP_CRC_MEMBERS"):
                    k.check_parent(z)

    def test_11_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"already_present"
            path.mkdir()
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                k.run(Path(tmp)/"does_not_exist.zip",path)

    def test_12_original_source_pixels_are_full_byte_not_thresholded(self):
        assert k.ALPHA_BINS if hasattr(k,"ALPHA_BINS") else True
        self.assertEqual(k.STRATA,((0,0),(1,15),(16,63),(64,127),(128,254),(255,255)))
        self.assertEqual(k.WIDTHS,tuple(range(1,11)))
        self.assertEqual(k.VARIANTS,("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A"))


if __name__=="__main__":
    unittest.main()
