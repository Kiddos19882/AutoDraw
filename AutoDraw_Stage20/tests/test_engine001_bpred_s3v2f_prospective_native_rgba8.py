#!/usr/bin/env python3
"""S3v2f prereg immutable new-native matrix, integer RGB and fail-closed tests."""
from __future__ import annotations

import unittest
import numpy as np

import run_engine001_bpred_s3v2f_prospective_native_rgba8 as f
import run_engine001_bpred_s3v2e_rgba8_quantization as q


class BpredS3v2fContracts(unittest.TestCase):
    def test_01_e0_precode_source_pins(self):
        self.assertEqual(f.E0_BLOB,"24259eeeadb9451c43390bdcf5a01fb67c7cf39a")
        self.assertEqual(f.EXPERIMENT,"ENGINE001_BPRED_S3V2F_PROSPECTIVE_ORIGINAL_EGRET_RGBA8_V1")
        self.assertEqual(f.WIDTHS,tuple(range(1,11)))
        self.assertEqual(f.RELATIONS,("CROSS_ROTATED","NEAR_SKEW"))
        self.assertEqual(f.VARIANTS,("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A"))
        self.assertEqual(len(f.JS_BLOBS),3)

    def test_02_80_new_disjoint_native_scene_ids(self):
        m=f.manifest()
        rows=m["scenes"]
        self.assertEqual(len(rows),80)
        self.assertEqual(len({r["sample_id"] for r in rows}),80)
        self.assertEqual(len(m["controls"]),10)
        self.assertEqual(m["final_webgl_PNG"],91)
        self.assertTrue(all(r["sample_id"].startswith("BPRED-S3V2F-") for r in rows))
        self.assertFalse(m["S0_BLIND_used"])

    def test_03_frozen_width_angle_phase_color_groups(self):
        self.assertEqual(len(set(f.ANGLES)),10)
        self.assertEqual(f.PHASES,((3/16,11/16),(13/16,1/16),
                                   (5/16,7/16),(15/16,9/16)))
        for width in f.WIDTHS:
            for relation in f.RELATIONS:
                rows=f.plans_for(width,relation)
                self.assertEqual(rows["A_ONLY"]["phase"],list(f.PHASES[(width-1)%4]))
                pair=f.COLORS_ODD if width%2 else f.COLORS_EVEN
                self.assertEqual(rows["A_ONLY"]["source_strokes"][0]["colorRgb"],pair[0])
                self.assertEqual(rows["B_ONLY"]["source_strokes"][0]["colorRgb"],pair[1])

    def test_04_no_legacy_g32_v44_and_no_coordinate_clipping(self):
        for scene in f.manifest()["scenes"]:
            self.assertNotIn("G32",str(scene))
            self.assertNotIn("V44",str(scene))
            for s in scene["runtime_strokes"]:
                self.assertTrue(1<=s["width"]<=10)
                self.assertEqual(len(s["points"]),2)
                self.assertTrue(all(0<p["x"]<460 and 0<p["y"]<240
                                    for p in s["points"]))

    def test_05_frozen_original_to_runtime_byte_values(self):
        for scene in f.manifest()["scenes"]:
            self.assertEqual(scene["runtime_plan_sha256"],
                             f.s3.digest(f.s3.canonical(scene["runtime_strokes"])))
            self.assertEqual(scene["source_plan_sha256"],
                             f.s3.digest(f.s3.canonical(scene["source_strokes"])))
            for index,(src,dst) in enumerate(zip(scene["source_strokes"],
                                                 scene["runtime_strokes"])):
                self.assertEqual(src["strokeId"],"bpred-A" if (
                    (scene["variant"] in ("A_ONLY","A_THEN_B") and index==0) or
                    (scene["variant"]=="B_THEN_A" and index==1)) else "bpred-B")
                self.assertEqual(dst["strokeId"],f"icon-{index}")
                self.assertEqual({k:v for k,v in src.items() if k!="strokeId"},
                                 {k:v for k,v in dst.items() if k!="strokeId"})

    def test_06_invalid_width_relation_fail_closed(self):
        for width,relation in ((0,"CROSS_ROTATED"),
                               (11,"CROSS_ROTATED"),
                               (1,"SIDEWAYS"),(True,"NEAR_SKEW")):
            with self.assertRaisesRegex(ValueError,"UNFROZEN_INPUT"):
                f.plans_for(width,relation)

    def test_07_qh_precommitted_half_up_tie_changes_even(self):
        a=np.array([[[8,8,8,30]]],np.uint8)
        self.assertEqual(int(q.quantize_stage(a,"QC")[0,0,0]),8)
        self.assertEqual(int(f.quantize_half_up(a)[0,0,0]),9)

    def test_08_qh_alpha0_255_and_input_preserved(self):
        a=np.array([[[13,15,17,0],[22,44,66,255],[8,8,8,30]]],np.uint8)
        old=a.copy()
        v=f.quantize_half_up(a)
        np.testing.assert_array_equal(a,old)
        np.testing.assert_array_equal(v[0,:2],a[0,:2])
        np.testing.assert_array_equal(v[:,:,3],a[:,:,3])
        self.assertFalse(np.shares_memory(v,a))

    def test_09_qh_bad_types_fail_closed(self):
        a=np.zeros((1,1,4),np.uint8)
        for bad in (None,a.astype(np.float32),a[:,:,:3],a[0]):
            with self.assertRaisesRegex(ValueError,"QH_INPUT_RGBA"):
                f.quantize_half_up(bad)

    def test_10_ordered_original_rgb_source_over_not_replaced(self):
        a=np.zeros((2,2,4),np.uint8)
        b=a.copy()
        a[0,0]=[80,61,53,255]
        b[0,0]=[197,65,145,255]
        frames={"A_ONLY":{"canvas":a,"webgl":a},
                "B_ONLY":{"canvas":b,"webgl":b},
                "A_THEN_B":{"canvas":b,"webgl":b},
                "B_THEN_A":{"canvas":a,"webgl":a}}
        r=f.ordered_metrics(1,"CROSS_ROTATED",frames)
        self.assertEqual(set(r["ordered_variants"]),{"A_THEN_B","B_THEN_A"})
        for v in r["ordered_variants"].values():
            self.assertTrue(v["canvas_native_C0"]["frozen_H1_pass"])
            self.assertTrue(v["original_webgl_C0"]["frozen_H1_pass"])
            self.assertTrue(v["canvas_to_webgl_C0"]["QH"]["frozen_H1_pass"])

    def test_11_stage_real_alpha_change_blocks(self):
        a=np.zeros(f.p4d3.NATIVE_SHAPE,np.uint8)
        b=a.copy()
        b[0,0,3]=1
        with self.assertRaisesRegex(ValueError,"STAGE_NATIVE_ALPHA_CHANGED"):
            f.stage_diff(a,b)

    def test_12_replay_controls_source_only(self):
        m=f.manifest()
        self.assertEqual({x["width"] for x in m["controls"]},set(f.WIDTHS))
        for control in m["controls"]:
            self.assertEqual(control["parent_sample_id"],
                             f.plans_for(control["width"],"CROSS_ROTATED")
                             ["A_THEN_B"]["sample_id"])


if __name__=="__main__":
    unittest.main()
