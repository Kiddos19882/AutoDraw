#!/usr/bin/env python3
"""E2 frozen S3v2n: all byte colors, fractional alpha transitions and source fail closed."""
from __future__ import annotations
from fractions import Fraction
import tempfile
import unittest
from pathlib import Path

import numpy as np
import run_engine001_bpred_s3v2n_correlated_alpha_premult as n


class S3v2nCorrelatedNativeSource(unittest.TestCase):
    def test_01_first_original_e0_before_code(self):
        self.assertEqual(n.E0_BLOB,"81f1a18ed5b04265123c337a3cbd63985a835307")
        self.assertEqual(n.M_RUN,"44751330819")
        self.assertEqual(n.EXPERIMENT,"ENGINE001_BPRED_S3V2N_CORRELATED_ALPHA_PREMULT_TRANSITIONS_V1")

    def test_02_all_color_bytes_all_alpha_bytes_five_phases_all_round_modes(self):
        # 256*254*5*3 = 975360 exact rational candidate comparisons.
        # Synthetic data only: proves bounds conditional on arithmetic, not Firefox.
        phases=[Fraction(-1,2),Fraction(-1,4),Fraction(0),Fraction(1,4),Fraction(1,2)]
        for c in range(256):
            for A in range(1,255):
                low,high=n.channel_bounds(c,A)
                for d in phases:
                    a=Fraction(A)+d
                    x=Fraction(c,255)*a
                    modes={n.floor_fraction(x),n.nearest_even_fraction(x),n.ceil_fraction(x)}
                    for p in modes:
                        r=n.readback(p,a)
                        self.assertLessEqual(low,r,(c,A,d,p))
                        self.assertGreaterEqual(high,r,(c,A,d,p))

    def test_03_all_interior_integer_and_half_integer_transitions(self):
        # Check before/after each rational transition, including ultra-small epsilon.
        eps=Fraction(1,1<<30)
        for c in (1,2,5,19,31,77,128,156,228,253,254,255):
            for A in range(1,255):
                lo,hi=n.channel_bounds(c,A)
                L=Fraction(2*A-1,2);U=Fraction(2*A+1,2)
                tlo=Fraction(c,255)*L;thi=Fraction(c,255)*U
                left=max(0,n.floor_fraction(tlo)-2)
                right=min(255,n.ceil_fraction(thi)+2)
                for k in range(left,right+1):
                    for a0 in (Fraction(255*k,c),Fraction(255*(2*k+1),2*c)):
                        if L<a0<U:
                            for a in (a0-eps,a0,a0+eps):
                                x=Fraction(c,255)*a
                                for p in {n.floor_fraction(x),n.nearest_even_fraction(x),n.ceil_fraction(x)}:
                                    result=n.readback(p,a)
                                    self.assertTrue(lo<=result<=hi,(c,A,a,p,lo,result,hi))

    def test_04_old_floor_discontinuity_c228_a2_is_contained(self):
        low,high=n.channel_bounds(228,2)
        self.assertLessEqual(low,128)
        self.assertGreaterEqual(high,128)
        self.assertLessEqual(low,255)
        self.assertGreaterEqual(high,255)

    def test_05_channel_zero_no_div_by_zero(self):
        self.assertEqual(n.channel_bounds(0,1),(0,2))
        self.assertEqual(n.channel_bounds(0,254),(0,2))
        lo,hi=n.g3([0,0,0],np.array([1.,16.,254.]))
        self.assertTrue(np.all(lo==0))
        self.assertTrue(np.all(hi==2))

    def test_06_invalid_byte_or_alpha_fails_closed(self):
        for c,A in ((-1,30),(256,1),(10,0),(10,255),(10,-1)):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                n.channel_bounds(c,A)
        for alpha in (0,255,-1,300):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                n.g3([12,19,31],np.array([alpha]))

    def test_07_invalid_source_vector_not_a_3channel_color(self):
        for c in ([1,2],[1,2,3,4],[-1,2,3],[2,256,5],[2,float("nan"),5]):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                n.g3(c,np.array([100]))

    def test_08_invalid_native_alpha_shape_or_fraction(self):
        for a in (np.array(50),np.array([[50.]]),np.array([1.5]),np.array([float("nan")])):
            with self.assertRaisesRegex(ValueError,"INVALID_COLOR_OR_PARTIAL_ALPHA"):
                n.g3([1,2,3],a)

    def test_09_existing_output_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"exists"
            p.mkdir()
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                n.run(Path(tmp)/"src.zip",Path(tmp)/"k.zip",Path(tmp)/"l.zip",
                      Path(tmp)/"m.zip",p)

    def test_10_original_e0_pin_missing_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"E0_MISSING"):
                n.verify_e0(Path(tmp))

    def test_11_all_quantizers_are_source_math_not_owner_policy(self):
        self.assertEqual(n.nearest_even_fraction(Fraction(3,2)),2)
        self.assertEqual(n.nearest_even_fraction(Fraction(5,2)),2)
        self.assertEqual(n.nearest_even_fraction(Fraction(7,2)),4)
        self.assertEqual(n.nearest_even_fraction(Fraction(9,2)),4)
        self.assertEqual(n.readback(0,Fraction(1,2)),0)
        self.assertEqual(n.readback(255,Fraction(1,2)),255)


if __name__=="__main__":
    unittest.main()
