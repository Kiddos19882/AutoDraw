#!/usr/bin/env python3
"""E2 S3v2r prospective fixed native repeated source / no relaxed old gates."""
import base64
import math
import unittest
import tempfile
from pathlib import Path

import numpy as np

import run_engine001_bpred_s3v2r_bounded_repeat_contrast_native as r
import run_engine001_bpred_s3v2q_incremental_microalpha_owner as q
import run_engine001_bpred_s3_native_source_over as s3


class FrozenS3v2rNative(unittest.TestCase):
    def test_01_frozen_e0_before_tests_and_original_source(self):
        self.assertEqual(r.E0_BLOB,"e98acc22663beb7f8051e7626c95f696e405f5f3")
        self.assertEqual(r.FIRST_V1_E0_BLOB,"1909565e0a9e4fc7b742e88f2324b848d8f9e017")
        self.assertEqual(r.ROI,(400,220,270,270))
        self.assertEqual(r.SCHEMA,"ENGINE001_BPRED_S3V2R2_ORIGINAL_NATIVE_REPEAT_CONTRAST_V2")

    def test_02_prereg_manifest_exact_42_and_150_real_strokes(self):
        m=r.manifest()
        self.assertEqual(m["experiment"],r.EXPERIMENT)
        self.assertEqual(m["source_native_scenes"],42)
        self.assertEqual(m["original_input_source_strokes"],150)
        self.assertEqual(m["original_main_stroke_events"],192)
        self.assertEqual(m["direct_rgba_expected"],384)
        self.assertEqual(len(m["scenes"]),42)
        self.assertEqual(len({x["sample_id"] for x in m["scenes"]}),42)
        self.assertEqual(len(m["replays"]),6)
        self.assertFalse(m["S0_BLIND_used"])
        self.assertTrue(m["protected_foreign_policy_unchanged"])

    def test_03_new_colors_widths_and_repetitions_are_exact(self):
        self.assertEqual(r.WIDTHS,(3,7,10))
        self.assertEqual(r.BACKGROUNDS,("DARK","LIGHT"))
        self.assertEqual(r.REPEATS,(1,8))
        self.assertEqual(r.TOP,0xD95A83)
        self.assertEqual(r.COLORS["DARK"],0x183A53)
        self.assertEqual(r.COLORS["LIGHT"],0xE9CA9B)
        for x in r.manifest()["scenes"]:
            if x["variant"]=="TOP_ONLY" or x["variant"].endswith("ONLY"):
                self.assertEqual(len(x["source_strokes"]),1)
            else:
                self.assertEqual(len(x["source_strokes"]),1+x["repeat"])
            self.assertEqual(len(x["runtime_strokes"]),len(x["source_strokes"]))
            self.assertEqual(x["source_plan_sha256"],s3.digest(s3.canonical(x["source_strokes"])))
            self.assertEqual(x["runtime_plan_sha256"],s3.digest(s3.canonical(x["runtime_strokes"])))

    def test_04_true_upper_strokes_are_identical_color_geometry_and_new_id(self):
        for width in r.WIDTHS:
            for relation in r.RELATIONS:
                for background in r.BACKGROUNDS:
                    c=r.make_scene(width,relation,background+"_R8")
                    upper=c["source_strokes"][1:]
                    self.assertEqual(len(upper),8)
                    self.assertEqual(len({x["strokeId"] for x in upper}),8)
                    for stroke in upper:
                        self.assertEqual(stroke["colorRgb"],r.TOP)
                        self.assertEqual(stroke["colorIndex"],2)
                        self.assertEqual(stroke["points"],upper[0]["points"])
                        self.assertEqual(stroke["width"],width)
                    self.assertEqual(upper[0]["points"],
                                     r.make_scene(width,relation,"TOP_ONLY")["source_strokes"][0]["points"])
                    self.assertEqual(c["source_strokes"][0]["points"],
                                     r.make_scene(width,relation,background+"_ONLY")["source_strokes"][0]["points"])

    def test_05_finite_original_board_geometry_inside_main_physical_roi(self):
        x,y,w,h=r.ROI
        for s in r.manifest()["scenes"]:
            for original in s["source_strokes"]:
                for point in original["points"]:
                    self.assertTrue(math.isfinite(point["x"]) and math.isfinite(point["y"]))
                    self.assertTrue(0<point["x"]<460 and 0<point["y"]<240)
                    # 3x original pixel scale and generous original 10px width.
                    self.assertLess(x,3*point["x"]+6-18)
                    self.assertLess(3*point["x"]+6+18,x+w)
                    self.assertLess(y,3*point["y"]+6-18)
                    self.assertLess(3*point["y"]+6+18,y+h)

    def test_06_no_borrowing_q_p_or_S0_sample_ids(self):
        ours={s["sample_id"] for s in r.manifest()["scenes"]}
        previous={s["sample_id"] for s in q.manifest()["scenes"]}
        self.assertTrue(ours.isdisjoint(previous))
        self.assertTrue(all(s.startswith("BPRED-S3V2R") for s in ours))

    def test_07_unfrozen_geometry_rejected_instead_of_silent_default(self):
        for width,relation,variant in (
            (1,"CROSS_ROTATED","DARK_R8"),(4,"CROSS_ROTATED","DARK_R1"),
            (True,"NEAR_SKEW","DARK_R1"),(3,"UNKNOWN","DARK_R1"),
            (3,"NEAR_SKEW","R20"),(3,"NEAR_SKEW","PURPLE_ONLY")):
            with self.assertRaisesRegex(ValueError,"BLOCKED_BPRED_S3V2R_"):
                r.make_scene(width,relation,variant)

    def test_08_exact_lossless_direct_rgba_roundtrip(self):
        expected=bytes([2,99,188,0])*(270*270)
        actual=r.decode_rgba64(base64.b64encode(expected).decode("ascii"))
        self.assertEqual(expected,actual)
        self.assertEqual(r.raw_frame(actual).shape,(270,270,4))
        self.assertEqual(r.raw_frame(actual)[0,0].tolist(),[2,99,188,0])

    def test_09_raw_malformed_bytes_rejected(self):
        for value in (None,"?","",base64.b64encode(b"abc").decode("ascii")):
            with self.assertRaisesRegex(ValueError,"BLOCKED_BPRED_S3V2R_"):
                r.decode_rgba64(value)
        with self.assertRaisesRegex(ValueError,"INVALID_RGBA_RAW_FRAME"):
            r.raw_frame(b"abc")

    def test_10_node_local_vs_aligned_coordinates_are_not_conflated(self):
        self.assertEqual(r.xy(0,0),{
            "node_local_physical":[400,220],"aligned_board_physical":[394,214]})
        self.assertEqual(r.xy(10,12),{
            "node_local_physical":[410,232],"aligned_board_physical":[404,226]})

    def test_11_replays_are_six_independent_real_r8_source_plans(self):
        m=r.manifest()
        self.assertEqual(len(m["replays"]),6)
        for c in m["replays"]:
            expected=r.make_scene(c["width"],c["relation"],"DARK_R8")
            self.assertEqual(c["parent_sample_id"],expected["sample_id"])
            self.assertEqual(len(expected["source_strokes"]),9)

    def test_12_missing_first_e0_or_frozen_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(Exception):
                r.verify_source(root,root/"game.js",root/"renderer.js",[],root/"observe.js")


if __name__=="__main__":
    unittest.main()
