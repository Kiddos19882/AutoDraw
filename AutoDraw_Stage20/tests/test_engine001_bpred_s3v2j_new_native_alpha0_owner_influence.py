#!/usr/bin/env python3
"""S3v2j E2 frozen new-Egret matrix and conservative source-owner contracts."""
from __future__ import annotations
import math
import tempfile
import unittest
from pathlib import Path

import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3_native_source_over as s3


class S3v2jFrozenNativeContracts(unittest.TestCase):
    def test_01_e0_precedes_runner(self):
        self.assertEqual(j.E0_BLOB,"6801292e01a650a2b014ffe09256313ebe10562b")
        self.assertEqual(j.ANGLES,(9,43,83,137,175,203,241,277,321,353))
        self.assertEqual(j.WIDTHS,tuple(range(1,11)))
        self.assertEqual(j.RELATIONS,("CROSS_ROTATED","NEAR_SKEW"))
        self.assertEqual(j.VARIANTS,("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A"))

    def test_02_80_new_source_native_cases_exact(self):
        m=j.manifest()
        self.assertEqual(m["experiment"],j.EXPERIMENT)
        self.assertFalse(m["S0_BLIND_used"])
        self.assertTrue(m["new_true_native_80"])
        self.assertEqual((len(m["scenes"]),len(m["controls"])),(80,10))
        self.assertEqual(len({s["sample_id"] for s in m["scenes"]}),80)

    def test_03_precommitted_phases_are_not_old_16ths(self):
        for w in j.WIDTHS:
            scene=j.plans_for(w,"CROSS_ROTATED")["A_ONLY"]
            phase=scene["phase_xy"]
            self.assertEqual(len(phase),2)
            for x in phase:
                self.assertTrue(0<x<1)
                self.assertNotEqual(x*16,round(x*16))

    def test_04_new_source_colors_not_legacy_palette_seeds(self):
        for w in j.WIDTHS:
            scene=j.plans_for(w,"NEAR_SKEW")["A_THEN_B"]
            self.assertEqual(tuple(scene["source_colors"]),
                             j.ODD_COLORS if w%2 else j.EVEN_COLORS)
            self.assertEqual([x["colorRgb"] for x in scene["runtime_strokes"]],
                             list(reversed(scene["source_colors"])))
            self.assertEqual([x["colorIndex"] for x in scene["runtime_strokes"]],[1,2])

    def test_05_transport_mutates_only_stroke_id(self):
        for relation in j.RELATIONS:
            scene=j.plans_for(5,relation)["B_THEN_A"]
            self.assertEqual([x["strokeId"] for x in scene["runtime_strokes"]],
                             ["icon-0","icon-1"])
            for original,actual in zip(scene["source_strokes"],
                                       scene["runtime_strokes"]):
                self.assertEqual({k:v for k,v in original.items() if k!="strokeId"},
                                 {k:v for k,v in actual.items() if k!="strokeId"})
            self.assertEqual(s3.digest(s3.canonical(scene["runtime_strokes"])),
                             scene["runtime_plan_sha256"])

    def test_06_points_are_finite_and_inside_true_native_board(self):
        for scene in j.manifest()["scenes"]:
            for stroke in scene["runtime_strokes"]:
                self.assertTrue(stroke["width"] in j.WIDTHS)
                self.assertEqual(len(stroke["points"]),2)
                for p in stroke["points"]:
                    self.assertTrue(math.isfinite(p["x"]) and 0<p["x"]<460)
                    self.assertTrue(math.isfinite(p["y"]) and 0<p["y"]<240)

    def test_07_malformed_width_relation_fail_closed(self):
        for w,r in ((0,"CROSS_ROTATED"),(11,"CROSS_ROTATED"),
                    (1,"UNKNOWN"),(True,"CROSS_ROTATED")):
            with self.assertRaisesRegex(ValueError,"NOT_FROZEN_NEW_GEOMETRY"):
                j.plans_for(w,r)

    def test_08_missing_frozen_e0_and_scripts_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):
                j.check_source(root,root/"game.js",root/"renderer.js",[])

    def test_09_replay_is_original_named_A_THEN_B(self):
        m=j.manifest()
        self.assertEqual(len({r["width"] for r in m["controls"]}),10)
        for control in m["controls"]:
            s=j.plans_for(control["width"],"CROSS_ROTATED")["A_THEN_B"]
            self.assertEqual(control["parent_sample_id"],s["sample_id"])

    def test_10_never_implicitly_suppress_alpha0_risk(self):
        self.assertIn("ALPHA0",j.EXPERIMENT)
        self.assertNotIn("S4_BLIND",j.EXPERIMENT)
        self.assertEqual(j.ODD_COLORS,(0x218C6F,0xE44D9C))
        self.assertEqual(j.EVEN_COLORS,(0xA5D742,0x2C49F0))


if __name__=="__main__":
    unittest.main()
