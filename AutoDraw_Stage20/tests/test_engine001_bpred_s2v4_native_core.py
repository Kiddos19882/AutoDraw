#!/usr/bin/env python3
"""BPRED-S2v4 research E2: matrix, source geometry, masks and scientific gates.

All synthetic; actual Egret proof is the separately pinned Windows E3 job.
"""
from __future__ import annotations
import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np

import run_engine001_bpred_s2v4_native_core as s4
import run_engine001_bpred_s2v3_risk_aware_alpha as s3


def fake_cell(m2tp=100,m2fp=3,m5tp=95,m5fp=0):
    return {
        "M2_AREA8":{"TP":m2tp,"FP":m2fp,"FN":10,
                   "positive_predicted":m2tp+m2fp},
        "M5_HIGH_ALPHA_CORE":{"TP":m5tp,"FP":m5fp,
                              "FN":10+m2tp-m5tp,
                              "positive_predicted":m5tp+m5fp},
        "M4_PREVIOUS_MAX_Q_DIAGNOSTIC":{"TP":m5tp,
                                       "FP":m5fp,"FN":10+m2tp-m5tp,
                                       "positive_predicted":m5tp+m5fp}
    }


def rows(**kwargs):
    return [{"width":w,"angle_deg":angle,
             "cells":[fake_cell(**kwargs) for _ in range(3)]}
            for w in s4.WIDTHS for angle in s4.ANGLES for _ in range(4)]


class BpredS2v4Contracts(unittest.TestCase):
    def test_01_frozen_scene_matrix_and_replay_count(self):
        m=s4.manifest()
        self.assertEqual((len(m["scenes"]),len(m["repeat_controls"]),m["blank_count"]),
                         (120,10,1))
        self.assertEqual(len({s["sample_id"] for s in m["scenes"]}),120)
        self.assertEqual({s["angle_deg"] for s in m["scenes"]},{22,111,241})
        self.assertEqual({s["width"] for s in m["scenes"]},set(range(1,11)))
        self.assertEqual({s["length_logical"] for s in m["scenes"]},{9,23})
        self.assertEqual({(s["phase_x"],s["phase_y"]) for s in m["scenes"]},
                         {(1/32,11/32),(13/32,7/32)})

    def test_02_families_never_overlap_blind_or_calibration(self):
        angles={a%180 for a in s4.ANGLES}
        self.assertEqual(angles,{22,111,61})
        self.assertFalse(angles & {7,73,166,38,121,97})

    def test_03_transport_only_changes_native_stroke_ids(self):
        source=s4.prepare_scene(7,22,9,(1,11))
        self.assertEqual([s["strokeId"] for s in source["runtime"]],
                         ["icon-0","icon-1","icon-2"])
        for old,new in zip(source["strokes"],source["runtime"]):
            self.assertEqual({k:v for k,v in old.items() if k!="strokeId"},
                             {k:v for k,v in new.items() if k!="strokeId"})
        self.assertNotEqual(source["source_plan_sha256"],
                            source["runtime_plan_sha256"])

    def test_04_reverse_direction_241(self):
        v=s4.source_points(58,40,241,9,(1,11))
        self.assertGreater(v[0]["x"],v[1]["x"])
        self.assertGreater(v[0]["y"],v[1]["y"])

    def test_05_all_strokes_within_logical_board(self):
        for c in s4.manifest()["scenes"]:
            self.assertEqual(len(c["strokes"]),3)
            for st in c["strokes"]:
                self.assertEqual(st["colorIndex"],1)
                self.assertEqual(st["colorRgb"],s4.s0.OWNER_COLOR)
                for p in st["points"]:
                    self.assertTrue(0<p["x"]<460)
                    self.assertTrue(0<p["y"]<240)

    def test_06_replay_source_matching(self):
        m=s4.manifest()
        original={s["sample_id"]:s for s in m["scenes"]}
        for repeat in m["repeat_controls"]:
            parent=original[repeat["parent_sample_id"]]
            self.assertEqual(repeat["width"],parent["width"])
            self.assertEqual(repeat["runtime_plan_sha256"],
                             parent["runtime_plan_sha256"])
            self.assertEqual(parent["angle_deg"],22)
            self.assertEqual(parent["length_logical"],9)

    def test_07_m5_threshold_from_m2_guard_math(self):
        pred=np.zeros((162,162),dtype=np.uint8)
        native=np.zeros_like(pred)
        pred[0,0]=127;pred[0,1]=128
        native[0,0]=0;native[0,1]=255
        measured=s3.classify_pair(pred,native,s4.M5_ALPHA_THRESHOLD-s4.ALPHA_GATE)
        core=measured["M4_EMPIRICAL_ALPHA_GUARD"]
        self.assertEqual(core["TP"],1)
        self.assertEqual(core["FP"],0)
        self.assertEqual(core["FN"],0)

    def test_08_scientific_pass_does_not_mean_safe(self):
        m=s4.evaluate(rows())
        self.assertEqual((m["H1_zero_FP"],m["H2_90pct_TP_retention"],
                          m["H3_each_width_and_angle_retention"]),("PASS","PASS","PASS"))
        self.assertFalse(m["M5_pixel_exact_safe"])
        self.assertEqual(m["M5_model_status"],"MODEL_ONLY_NEW_NATIVE_STRESS_ONLY")

    def test_09_single_false_safe_causes_h1_fail(self):
        m=s4.evaluate(rows(m5fp=1))
        self.assertEqual(m["H1_zero_FP"],"FAIL")
        self.assertEqual(m["safety_gate_zero_FP"],"FAIL")

    def test_10_all_unknown_not_success(self):
        m=s4.evaluate(rows(m5tp=0))
        self.assertEqual(m["H2_90pct_TP_retention"],"FAIL")
        self.assertEqual(m["H3_each_width_and_angle_retention"],"FAIL")

    def test_11_bad_per_width_coverage_fails_h3(self):
        r=rows()
        for scene in r:
            if scene["width"]==1:
                scene["cells"]=[fake_cell(m5tp=75) for _ in range(3)]
        m=s4.evaluate(r)
        self.assertEqual(m["H3_each_width_and_angle_retention"],"FAIL")

    def test_12_malformed_size_and_angle_fail_closed(self):
        for args in ((0,22,9,(1,11)),(11,22,9,(1,11)),
                     (1,38,9,(1,11)),(1,22,7,(1,11)),
                     (1,22,9,(1,7))):
            with self.assertRaisesRegex(ValueError,"BLOCKED_BPRED_S2V4"):
                s4.prepare_scene(*args)

    def test_13_no_unverified_output_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"immutable.json"
            s4.save_json(path,{"x":1})
            with self.assertRaises(FileExistsError):
                s4.save_json(path,{"x":2})

    def test_14_scoring_empty_blocked(self):
        with self.assertRaisesRegex(ValueError,"RESULT_SCENES"):
            s4.evaluate([])


if __name__=="__main__":
    unittest.main()
