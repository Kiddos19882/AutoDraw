#!/usr/bin/env python3
"""E2 frozen S3v2q native true main-stroke pre/post/repeat and source provenance."""
import base64
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_bpred_s3v2q_incremental_microalpha_owner as q
import run_engine001_bpred_s3v2p_native_canvas_readback_vs_composition as p
import run_engine001_bpred_s3v2o_new_native_low_alpha_readback as o
import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3_native_source_over as s3


class S3v2qFrozenIncrementalNative(unittest.TestCase):
    def test_01_new_first_e0_pinned_before_implementation(self):
        self.assertEqual(q.E0_BLOB,"ac0bd08ee45058e890ef16c75efea58ca27bec47")
        self.assertEqual(q.ROI,(400,220,270,270))
        self.assertEqual(q.SCHEMA,"ENGINE001_BPRED_S3V2Q_TRUE_MAIN_INCREMENTAL_MICROALPHA_V1")
        self.assertEqual(q.STATES,("pre","post","repeat_post"))

    def test_02_80_genuinely_new_source_scene_ids_and_20_controls(self):
        m=q.manifest()
        self.assertEqual(m["experiment"],q.EXPERIMENT)
        self.assertEqual(len(m["scenes"]),80)
        self.assertEqual(len({x["sample_id"] for x in m["scenes"]}),80)
        self.assertEqual(len(m["controls"]),20)
        self.assertEqual(len({x["sample_id"] for x in m["controls"]}),20)
        self.assertEqual({x["width"] for x in m["scenes"]},set(range(1,11)))
        self.assertEqual({x["relation"] for x in m["scenes"]},set(q.RELATIONS))
        self.assertEqual({x["variant"] for x in m["scenes"]},set(q.VARIANTS))
        self.assertFalse(m["S0_BLIND_used"])
        self.assertTrue(m["source_owner_known_only"])

    def test_03_new_angle_palette_and_phase_not_s3v2j_o_p(self):
        self.assertEqual(q.ANGLES,(31,79,127,163,211,257,293,331,359,47))
        self.assertTrue(set(q.ANGLES).isdisjoint(p.ANGLES))
        self.assertTrue(set(q.ANGLES).isdisjoint(o.ANGLES))
        self.assertTrue(set(q.ANGLES).isdisjoint(j.ANGLES))
        self.assertEqual(len(set(q.COLORS)),10)
        self.assertEqual(len({channel for pair in q.COLORS for channel in pair}),20)
        for w in q.WIDTHS:
            self.assertNotEqual(q.COLORS[w-1],p.COLORS[w-1])
            self.assertNotEqual(q.COLORS[w-1],o.COLORS[w-1])
            self.assertNotEqual(q.COLORS[w-1],
                j.ODD_COLORS if w%2 else j.EVEN_COLORS)
            for relation in q.RELATIONS:
                s=q.plans_for(w,relation)["A_ONLY"]
                self.assertNotEqual(s["phase_xy"],p.plans_for(w,relation)["A_ONLY"]["phase_xy"])
                self.assertEqual(s["angle_deg"],q.ANGLES[w-1])

    def test_04_source_rgb_preserved_and_original_runtime_id_only_changes(self):
        for s in q.manifest()["scenes"]:
            self.assertEqual(len(s["source_strokes"]),len(s["runtime_strokes"]))
            for idx,(src,dst) in enumerate(zip(s["source_strokes"],s["runtime_strokes"])):
                self.assertEqual(src["strokeId"],"bpred-"+("A" if src["colorIndex"]==1 else "B"))
                self.assertEqual(dst["strokeId"],f"icon-{idx}")
                self.assertEqual({k:v for k,v in src.items() if k!="strokeId"},
                                 {k:v for k,v in dst.items() if k!="strokeId"})
            self.assertEqual(s["source_plan_sha256"],s3.digest(s3.canonical(s["source_strokes"])))
            self.assertEqual(s["runtime_plan_sha256"],s3.digest(s3.canonical(s["runtime_strokes"])))

    def test_05_all_original_brush_points_and_widths_inside_frozen_roi(self):
        x,y,w,h=q.ROI
        for s in q.manifest()["scenes"]:
            for stroke in s["source_strokes"]:
                self.assertIn(stroke["width"],range(1,11))
                radius=1.5*stroke["width"]+3
                for point in stroke["points"]:
                    self.assertTrue(math.isfinite(point["x"]) and math.isfinite(point["y"]))
                    self.assertTrue(0<point["x"]<460 and 0<point["y"]<240)
                    physx,physy=3*point["x"]+6,3*point["y"]+6
                    self.assertLess(x,physx-radius)
                    self.assertLess(physx+radius,x+w)
                    self.assertLess(y,physy-radius)
                    self.assertLess(physy+radius,y+h)

    def test_06_replay_controls_uninstrumented_original(self):
        for c in q.manifest()["controls"]:
            self.assertEqual(c["parent_sample_id"],
                             q.plans_for(c["width"],c["relation"])["A_THEN_B"]["sample_id"])

    def test_07_frozen_invalid_source_geometry_fails_closed(self):
        for w,r in ((0,"CROSS_ROTATED"),(11,"CROSS_ROTATED"),
                    (True,"CROSS_ROTATED"),(2,"UNKNOWN")):
            with self.assertRaisesRegex(ValueError,"NOT_FROZEN_SOURCE_MATRIX"):
                q.plans_for(w,r)

    def test_08_lossless_raw_base64_pre_post_and_repeated_post(self):
        rgba=bytes([0,11,12,13])*(q.ROI[2]*q.ROI[3])
        event={"pre_rgba_b64":base64.b64encode(rgba).decode(),
               "post_rgba_b64":base64.b64encode(rgba).decode(),
               "repeat_post_rgba_b64":base64.b64encode(rgba).decode()}
        for state in q.STATES:
            raw=q.read_bytes(event,state+"_rgba_b64")
            self.assertEqual(raw,rgba)
            self.assertEqual(q.raw_frame(raw).shape,(270,270,4))
            self.assertEqual(q.raw_frame(raw)[0,0].tolist(),[0,11,12,13])

    def test_09_bad_raw_bytes_fails_closed(self):
        for invalid in [{},{"pre_rgba_b64":"!"},{"pre_rgba_b64":base64.b64encode(b"bad").decode()}]:
            with self.assertRaisesRegex(ValueError,"BLOCKED_BPRED_S3V2Q_"):
                q.read_bytes(invalid,"pre_rgba_b64")
        with self.assertRaisesRegex(ValueError,"RAW_FRAME_SHAPE"):
            q.raw_frame(b"x")

    def test_10_physical_coordinate_maps_original_node_local_to_board(self):
        self.assertEqual(q.coordinate(0,0),
                         {"node_local_xy":[400,220],"aligned_board_xy":[394,214]})
        self.assertEqual(q.coordinate(8,13),
                         {"node_local_xy":[408,233],"aligned_board_xy":[402,227]})

    def test_11_pinned_native_E0_and_original_harness_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):
                q.verify_source(root,root/"engine.js",root/"reference.js",[],root/"q.js")

    def test_12_original_G3_readback_and_foreign_owner_safety_never_retuned(self):
        self.assertNotEqual(q.EXPERIMENT,p.EXPERIMENT)
        self.assertIn("MICROALPHA_NATIVE_SOURCE",q.EXPERIMENT)
        self.assertFalse(q.manifest()["S0_BLIND_used"])
        self.assertEqual(q.ROI,p.ROI)
        self.assertEqual(q.WIDTHS,j.WIDTHS)
        self.assertEqual(q.RELATIONS,("CROSS_ROTATED","NEAR_SKEW"))
        self.assertEqual(q.VARIANTS,("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A"))


if __name__=="__main__":
    unittest.main()
