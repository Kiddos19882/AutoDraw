#!/usr/bin/env python3
"""S3v2m E2: exact precommitted interval bounds and fail-closed source contracts."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
import numpy as np
import run_engine001_bpred_s3v2m_full_fractional_alpha_lattice as m

class S3v2mFullFractionalAlpha(unittest.TestCase):
    def test_01_frozen_precode_e0(self):
        self.assertEqual(m.E0_BLOB,"33d40233c271bb8086d1d9c01d45eef3b401679e")
        self.assertEqual(m.EXPERIMENT,"ENGINE001_BPRED_S3V2M_FULL_FRACTIONAL_ALPHA_INTEGER_LATTICE_V1")

    def test_02_full_alpha_lattice_includes_all_five_samples_and_three_modes(self):
        for color in range(256):
            c=np.array([color,color,color],np.float64)
            a=np.arange(1,255,dtype=np.float64)
            lo,hi=m.g1(c,a)
            for phase in (-.5,-.25,0.,.25,.5):
                physical=a+phase
                for fn in (np.floor,np.rint,np.ceil):
                    p=fn(c[None,:]*physical[:,None]/255.)
                    read=np.clip(np.floor(255.*p/physical[:,None]+.5),0,255)
                    self.assertTrue(np.all(read>=lo) and np.all(read<=hi),
                                    (color,phase,fn.__name__))

    def test_03_old_F2_endpoint_interior_discontinuity_now_contained(self):
        lo,hi=m.g1([228,77,156],np.array([2.]))
        self.assertLessEqual(int(lo[0,0]),128)
        self.assertGreaterEqual(int(hi[0,0]),128)
        self.assertLessEqual(int(lo[0,0]),255)
        self.assertGreaterEqual(int(hi[0,0]),255)

    def test_04_opaque_and_zero_not_silent_partial(self):
        for a in (0,255,-1,256):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                m.g1([200,30,50],np.array([a]))

    def test_05_color_shape_or_range_fails_closed(self):
        for color in ([1,2],[1,2,256],[-1,2,3],[1,2,float("nan")]):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                m.g1(color,np.array([30.]))

    def test_06_alpha_shape_fails_closed(self):
        for a in (np.array(20.),np.array([[20.]])):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                m.g1([10,20,30],a)

    def test_07_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"exists";p.mkdir()
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                m.run(Path(t)/"missing1",Path(t)/"missing2",Path(t)/"missing3",p)

    def test_08_frozen_e0_missing_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,"E0_MISSING"):
                m.verify_e0(Path(t))

    def test_09_width_bounded_not_fabricated_rgb_safety(self):
        lo,hi=m.g1([228,77,156],np.array([1.,2.,16.,63.,254.]))
        self.assertTrue(np.all(lo<=hi))
        self.assertTrue(np.all(hi<=255))
        self.assertTrue(np.any(hi-lo>16))
        self.assertEqual(m.SOURCE_RUN,"44721915503")
        self.assertEqual(m.L_RUN,"44743578450")

if __name__=="__main__":
    unittest.main()
