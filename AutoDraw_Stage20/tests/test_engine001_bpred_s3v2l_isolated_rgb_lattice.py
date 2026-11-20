#!/usr/bin/env python3
"""S3v2l E2 fixed premult-byte lattice and original Egret provenance fail-closed."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
import numpy as np

import run_engine001_bpred_s3v2l_isolated_rgb_lattice as l


class S3v2lFrozenRgbLattice(unittest.TestCase):
    def test_01_frozen_E0_and_no_confusion_with_S4(self):
        self.assertEqual(l.E0_BLOB,"85ea039ad6b1683b40297ed307ec750c021b4630")
        self.assertEqual(l.PREV_RUN,"44741517301")
        self.assertEqual(l.PREV_SHA,"88e53c1205e163fd86db9251bb168f2be491fb97")
        self.assertEqual(l.RGB_PADDING,2.)
        self.assertEqual(l.F1_MODES,("floor","nearest_even","ceil"))

    def test_02_F1_roundtrip_exact_opaque_source(self):
        c=[228.,77.,156.]
        alpha=np.array([255.])
        for mode in l.F1_MODES:
            p=l.premul_roundtrip(c,alpha,mode)
            np.testing.assert_array_equal(p,np.array([[228,77,156]],np.uint8))

    def test_03_F1_diverges_under_real_partial_alpha(self):
        c=[228.,77.,156.]
        a=np.array([1.,13.,32.])
        predicted=[l.premul_roundtrip(c,a,mode) for mode in l.F1_MODES]
        self.assertTrue(all(p.shape==(3,3) and p.dtype==np.uint8 for p in predicted))
        self.assertTrue(any(not np.array_equal(predicted[0],p) for p in predicted[1:]))

    def test_04_F2_endpoint_rounding_is_not_a_guaranteed_F1_superset(self):
        # Frozen F2 checks alpha endpoints only. At intermediate A, floor/ceil
        # integer premultiplied p can jump across a discretization threshold.
        # Preserve this negative mathematical counterexample; do NOT widen F2.
        color=[228,77,156]
        a=np.array([1.,2.,13.,32.,63.,127.,254.])
        lo,hi=l.f2_lattice_interval(color,a)
        self.assertEqual(lo.shape,(7,3))
        self.assertTrue(np.all(lo>=0) and np.all(hi<=255))
        nearest=l.premul_roundtrip(color,a,"nearest_even")
        self.assertTrue(np.all((nearest>=lo-1e-9)&(nearest<=hi+1e-9)))
        floor=l.premul_roundtrip(color,a,"floor")
        self.assertEqual(int(floor[1,0]),128)
        self.assertGreater(float(lo[1,0]),128)
        self.assertTrue(np.any((floor<lo-1e-9)|(floor>hi+1e-9)))
        ceil=l.premul_roundtrip(color,a,"ceil")
        self.assertTrue(np.any((ceil<lo-1e-9)|(ceil>hi+1e-9)))

    def test_05_F2_uses_fixed_plus_minus_two_RGB_not_new_quality_threshold(self):
        self.assertEqual(l.RGB_PADDING,2.)
        lo,hi=l.f2_lattice_interval([150,210,40],np.array([254.]))
        self.assertTrue(np.all(lo<=hi))
        self.assertTrue(np.all(lo>=0.))

    def test_06_F2_rejects_zero_or_opaque_denominator(self):
        for a in (np.array([0.]),np.array([255.]),np.array([-1.])):
            with self.assertRaisesRegex(ValueError,"F2_PARTIAL_ALPHA_ONLY"):
                l.f2_lattice_interval([10,20,30],a)

    def test_07_F1_rejects_undefined_or_unfrozen_mode(self):
        with self.assertRaisesRegex(ValueError,"F1_ALPHA_SHAPE_OR_ZERO"):
            l.premul_roundtrip([10,20,30],np.array([0.]),"floor")
        with self.assertRaisesRegex(ValueError,"F1_UNFROZEN_ROUNDING"):
            l.premul_roundtrip([10,20,30],np.array([22.]),"round_half_up")

    def test_08_F1_rejects_out_of_range_owner_RGB(self):
        with self.assertRaisesRegex(ValueError,"INVALID_SOURCE_OWNER_COLOR"):
            l.premul_roundtrip([256,20,30],np.array([20.]),"ceil")

    def test_09_original_alpha_bins_fixed(self):
        self.assertEqual(l.ALPHA_BINS,((0,0),(1,15),(16,63),(64,127),(128,254),(255,255)))

    def test_10_source_negative_archive_missing_must_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"broken.zip"
            with ZipFile(p,"w") as z:
                z.writestr("report.json",json.dumps({}))
            with ZipFile(p) as z:
                with self.assertRaisesRegex(ValueError,"PRIOR_NEGATIVE_ARCHIVE_CRC_OR_SET"):
                    l.check_negative_archive(z)

    def test_11_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"already"
            output.mkdir()
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                l.run(Path(tmp)/"none.zip",Path(tmp)/"neg.zip",output)

    def test_12_partial_owner_reproducible_palette_roundtrip_is_not_assumed(self):
        c=np.array([228,77,156])
        a=np.array([32.])
        pred=l.premul_roundtrip(c,a,"nearest_even")
        self.assertFalse(np.array_equal(pred[0],c))
        lo,hi=l.f2_lattice_interval(c,a)
        self.assertTrue(np.all(lo[0]<=pred[0]) and np.all(pred[0]<=hi[0]))


if __name__=="__main__":
    unittest.main()
