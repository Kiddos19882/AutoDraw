#!/usr/bin/env python3
"""E2 contracts for the separately frozen NEW original Egret S3v2o E0."""
from __future__ import annotations
from fractions import Fraction
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_bpred_s3v2o_new_native_low_alpha_readback as o
import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3v2n_correlated_alpha_premult as n
import run_engine001_bpred_s3_native_source_over as s3


class S3v2oFrozenContracts(unittest.TestCase):
    def test_01_first_preregistered_e0_is_pinned(self):
        self.assertEqual(o.E0_BLOB, "72343545d1f8645625085afb36e5fddeda2f91c8")
        self.assertEqual(o.WIDTHS, tuple(range(1, 11)))
        self.assertEqual(o.RELATIONS, j.RELATIONS)
        self.assertEqual(o.VARIANTS, j.VARIANTS)
        self.assertEqual(o.ANGLES, (17,59,101,149,187,229,269,307,337,379))
        self.assertEqual(len(o.COLORS), 10)
        self.assertEqual(o.MODES, ("floor","nearest_even","ceil"))

    def test_02_all_80_independent_source_ids(self):
        m = o.manifest()
        self.assertEqual(m["experiment"], o.EXPERIMENT)
        self.assertFalse(m["S0_BLIND_used"])
        self.assertEqual((len(m["scenes"]),len(m["controls"])),(80,10))
        self.assertEqual(len({x["sample_id"] for x in m["scenes"]}),80)
        self.assertTrue(all(x["sample_id"].startswith("BPRED-S3V2O-") for x in m["scenes"]))
        self.assertEqual({x["width"] for x in m["scenes"]}, set(range(1,11)))
        self.assertEqual({x["relation"] for x in m["scenes"]},set(o.RELATIONS))
        self.assertEqual({x["variant"] for x in m["scenes"]},set(o.VARIANTS))

    def test_03_new_colors_and_angles_are_not_prior_source_family(self):
        self.assertNotEqual(o.ANGLES,j.ANGLES)
        self.assertEqual(len(set(o.COLORS)), 10)
        self.assertEqual(len({x for pair in o.COLORS for x in pair}),20)
        for width in o.WIDTHS:
            self.assertNotEqual(o.COLORS[width-1],j.ODD_COLORS if width % 2 else j.EVEN_COLORS)
            scene=o.plans_for(width,"CROSS_ROTATED")["A_ONLY"]
            self.assertEqual(scene["angle_deg"],o.ANGLES[width-1])
            self.assertNotEqual(scene["phase_xy"],j.plans_for(width,"CROSS_ROTATED")["A_ONLY"]["phase_xy"])

    def test_04_source_to_native_transport_only_changes_id(self):
        for scene in o.manifest()["scenes"]:
            for original,runtime in zip(scene["source_strokes"],scene["runtime_strokes"]):
                self.assertEqual({k:v for k,v in original.items() if k!="strokeId"},
                                 {k:v for k,v in runtime.items() if k!="strokeId"})
                self.assertEqual(runtime["width"],scene["width"])
            self.assertEqual(s3.digest(s3.canonical(scene["source_strokes"])),scene["source_plan_sha256"])
            self.assertEqual(s3.digest(s3.canonical(scene["runtime_strokes"])),scene["runtime_plan_sha256"])

    def test_05_original_logical_board_and_finite_points(self):
        for scene in o.manifest()["scenes"]:
            for stroke in scene["runtime_strokes"]:
                self.assertEqual(len(stroke["points"]),2)
                for p in stroke["points"]:
                    self.assertTrue(math.isfinite(p["x"]) and 0<p["x"]<460)
                    self.assertTrue(math.isfinite(p["y"]) and 0<p["y"]<240)

    def test_06_replays_have_exact_parent_source(self):
        for c in o.manifest()["controls"]:
            parent=o.plans_for(c["width"],"CROSS_ROTATED")["A_THEN_B"]
            self.assertEqual(c["parent_sample_id"],parent["sample_id"])

    def test_07_invalid_frozen_geometry_fails_closed(self):
        for w,r in ((0,"CROSS_ROTATED"),(11,"CROSS_ROTATED"),
                    (True,"CROSS_ROTATED"),(1,"OTHER")):
            with self.assertRaisesRegex(ValueError,"NOT_FROZEN_GEOMETRY"):
                o.plans_for(w,r)

    def test_08_color_decoding_exact_and_invalid_fails(self):
        for pair in o.COLORS:
            for color in pair:
                self.assertEqual(o.source_rgb(color).tolist(),
                    [(color>>16)&255,(color>>8)&255,color&255])
        for bad in (-1,0x1000000,1.5,True):
            with self.assertRaises(ValueError):
                o.source_rgb(bad)

    def test_09_rational_half_even_ties_distinct(self):
        self.assertEqual(o.quantize_mode(Fraction(3,2),"floor"),1)
        self.assertEqual(o.quantize_mode(Fraction(3,2),"nearest_even"),2)
        self.assertEqual(o.quantize_mode(Fraction(3,2),"ceil"),2)
        self.assertEqual(o.quantize_mode(Fraction(5,2),"nearest_even"),2)
        with self.assertRaisesRegex(ValueError,"INVALID_READBACK_MODE"):
            o.quantize_mode(Fraction(1,2),"unknown")

    def test_10_single_mode_intervals_are_contained_in_original_g3(self):
        for color in [0,1,7,63,127,228,255]:
            for a in [1,2,15,16,32,63,64,128,254]:
                union=n.channel_bounds(color,a)
                for mode in o.MODES:
                    lo,hi=o.single_mode_channel_bounds(color,a,mode)
                    self.assertTrue(union[0]<=lo<=hi<=union[1],
                                    (color,a,mode,union,(lo,hi)))

    def test_11_rgb_bounds_vector_and_invalid_fails(self):
        color=o.source_rgb(o.COLORS[0][0])
        alpha=np.array([1,2,16,63,128,254],dtype=np.int16)
        union_low,union_high=n.g3(color,alpha)
        for mode in o.MODES:
            lo,hi=o.mode_rgb_bounds(color,alpha,mode)
            self.assertEqual(lo.shape,(6,3))
            self.assertTrue(np.all(lo>=union_low) and np.all(hi<=union_high))
        for bad in [np.array([0]),np.array([255]),np.array([-1])]:
            with self.assertRaisesRegex(ValueError,"INVALID_PARTIAL_ALPHA_VECTOR"):
                o.mode_rgb_bounds(color,bad,"floor")

    def test_12_missing_e0_and_provenance_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):
                o.verify_source(root,root/"game.js",root/"renderer.js",[])

    def test_13_no_model_and_production_promotion_in_experiment_contract(self):
        self.assertIn("NEW_NATIVE_LOW_ALPHA_READBACK",o.EXPERIMENT)
        self.assertNotIn("S4_BLIND",o.EXPERIMENT)
        self.assertTrue(o.manifest()["new_original_native_E3"])
        self.assertFalse(o.manifest()["S0_BLIND_used"])


if __name__=="__main__":
    unittest.main()
