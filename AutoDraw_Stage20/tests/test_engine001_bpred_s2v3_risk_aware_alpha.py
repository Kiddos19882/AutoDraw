#!/usr/bin/env python3
"""BPRED-S2v3 E2 synthetic contracts; no synthetic sample is true native evidence."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np

import run_engine001_bpred_s2v3_risk_aware_alpha as v3


def blank(value=0):
    return np.full((162,162),value,dtype=np.uint8)


def made_cell(m2tp=100,m2fp=4,m4tp=95,m4fp=0):
    return {
        "M2_AREA8":{"TP":m2tp,"FP":m2fp,
            "FN":10,"positive_predicted":m2tp+m2fp},
        "M4_EMPIRICAL_ALPHA_GUARD":{"TP":m4tp,"FP":m4fp,
            "FN":10+m2tp-m4tp,"positive_predicted":m4tp+m4fp},
        "UNKNOWN_physical_pixels":162*162-m4tp-m4fp,
        "UNKNOWN_native_positive_pixels":10+m2tp-m4tp
    }


def synthetic_rows(**kw):
    return [{
        "sample_id":f"w{w}-a{a}-z{z}", "width":w,"angle_deg":a,
        "cells":[made_cell(**kw) for _ in range(3)]
    } for w in range(1,11) for a in v3.ANGLES for z in range(4)]


def baseline_for(rows):
    sums=v3.sum_counters(rows)["M2"]
    return {"alpha24":{"TP":sums["TP"],"FP":sums["FP"],"FN":sums["FN"]}}


class BpredS2v3Contracts(unittest.TestCase):
    def test_01_integer_higher_quantile(self):
        h=np.zeros(256,np.int64)
        for a in (0,1,1,3,21,255):
            h[a]+=1
        q,n=v3.quantile_higher_from_hist(h)
        want=int(np.quantile(np.array([0,1,1,3,21,255]),.995,method="higher"))
        self.assertEqual((q,n),(want,6))

    def test_02_reject_negative_histogram(self):
        h=np.zeros(256,np.int64);h[1]=-1;h[2]=3
        with self.assertRaisesRegex(ValueError,"NEGATIVE_QUANTILE_COUNTS"):
            v3.quantile_higher_from_hist(h)

    def test_03_reject_empty_histogram(self):
        with self.assertRaisesRegex(ValueError,"EMPTY_TRAINING_UNION"):
            v3.quantile_higher_from_hist(np.zeros(256,np.int64))

    def test_04_training_width_eight_scenes_three_copies(self):
        p=blank(100);t=blank(90)
        training=[{"pixel_pairs":[(p,t)]*3} for _ in range(8)]
        q,details=v3.fit_guard(training)
        self.assertEqual(q,10)
        self.assertEqual(details["train_scenes"],8)
        self.assertEqual(details["train_ROIs"],24)
        self.assertEqual(details["trust_alpha24_threshold_uint16"],34)

    def test_05_training_never_uses_both_zero(self):
        p=blank();t=blank()
        with self.assertRaisesRegex(ValueError,"EMPTY_TRAINING_UNION"):
            v3.fit_guard([{"pixel_pairs":[(p,t)]*3} for _ in range(8)])

    def test_06_high_guard_never_wraps_uint8(self):
        p=blank(255);t=blank(0)
        x=v3.classify_pair(p,t,255)
        self.assertEqual(x["M2_AREA8"]["FP"],162*162)
        self.assertEqual(x["M4_EMPIRICAL_ALPHA_GUARD"]["FP"],0)
        self.assertEqual(x["M4_EMPIRICAL_ALPHA_GUARD"]["TP"],0)
        self.assertEqual(x["UNKNOWN_physical_pixels"],162*162)
        self.assertEqual(x["guard_threshold_uint16"],279)

    def test_07_unknown_must_not_claim_confident_negative(self):
        p=blank();t=blank()
        t[10,10]=200
        x=v3.classify_pair(p,t,0)
        self.assertFalse(x["confident_negative_claim"])
        self.assertEqual(x["M4_EMPIRICAL_ALPHA_GUARD"]["FN"],1)
        self.assertEqual(x["UNKNOWN_native_positive_pixels"],1)

    def test_08_guard_subset_m2_and_false_safe(self):
        p=blank();t=blank()
        p[0,0]=24;t[0,0]=0
        p[1,1]=150;t[1,1]=255
        p[2,2]=250;t[2,2]=0
        o=v3.classify_pair(p,t,50)
        self.assertEqual(o["M2_AREA8"]["FP"],2)
        self.assertEqual(o["M2_AREA8"]["TP"],1)
        self.assertEqual(o["M4_EMPIRICAL_ALPHA_GUARD"]["FP"],1)
        self.assertEqual(o["M4_EMPIRICAL_ALPHA_GUARD"]["TP"],1)
        self.assertEqual(o["M4_EMPIRICAL_ALPHA_GUARD"]["positive_predicted"],2)

    def test_09_exact_bands_cover_physical_roi(self):
        p=np.tile(np.array([0,1,23,24,63,64,127,128,191,192,254,255],np.uint8),
                  (162*162+11)//12)[:162*162].reshape(162,162)
        t=blank()
        res=v3.classify_pair(p,t,100)
        self.assertEqual(len(res["predicted_alpha_error_bins"]),7)
        self.assertEqual(sum(x["count"] for x in res["predicted_alpha_error_bins"]),162*162)
        self.assertEqual(res["M2_AREA8"]["FP"],
                         int(np.count_nonzero(p>=24)))

    def test_10_synthetic_hypotheses_distinguish_science(self):
        rows=synthetic_rows()
        s=v3.hypothesis_scores(rows,baseline_for(rows))
        self.assertEqual(s["H1_total_FP_90pct_reduction"],"PASS")
        self.assertEqual(s["H2_total_TP_90pct_retention"],"PASS")
        self.assertEqual(s["H3_each_angle_FP_and_TP"],"PASS")
        self.assertEqual(s["independent_safety_gate_zero_FP"],"PASS")
        self.assertFalse(s["M4_pixel_exact_safe"])

    def test_11_all_unknown_cannot_pass_h2_h3(self):
        rows=synthetic_rows(m4tp=0)
        s=v3.hypothesis_scores(rows,baseline_for(rows))
        self.assertEqual(s["H2_total_TP_90pct_retention"],"FAIL")
        self.assertEqual(s["H3_each_angle_FP_and_TP"],"FAIL")

    def test_12_false_safe_gate_fails_even_if_average_ok(self):
        rows=synthetic_rows(m4fp=1)
        s=v3.hypothesis_scores(rows,baseline_for(rows))
        self.assertEqual(s["independent_safety_gate_zero_FP"],"FAIL")
        self.assertFalse(s["M4_pixel_exact_safe"])

    def test_13_baseline_drift_is_blocked(self):
        rows=synthetic_rows()
        base=baseline_for(rows)
        base["alpha24"]["FP"]+=1
        with self.assertRaisesRegex(ValueError,"S2V1_BASELINE_DRIFT"):
            v3.hypothesis_scores(rows,base)

    def test_14_synthetic_roi_wrong_shape_blocked(self):
        with self.assertRaisesRegex(ValueError,"PIXEL_PAIR_SHAPE_OR_DTYPE"):
            v3.classify_pair(blank()[:4],blank()[:4],0)

    def test_15_guard_negative_and_nan_blocked(self):
        for q in (-1,256,1.5,float("nan")):
            with self.assertRaisesRegex(ValueError,"INVALID_GUARD_Q"):
                v3.classify_pair(blank(90),blank(),q)

    def test_16_output_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"report.json"
            v3.save(p,{"x":1})
            with self.assertRaises(FileExistsError):
                v3.save(p,{"x":2})


if __name__=="__main__":
    unittest.main()
