#!/usr/bin/env python3
"""E2 frozen S3v2p original Egret getImageData vs PNG provenance, geometry and bytes."""
from __future__ import annotations

import hashlib
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3v2p_native_canvas_readback_vs_composition as p
import run_engine001_bpred_s3v2o_new_native_low_alpha_readback as o
import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3_native_source_over as s3


class FrozenNativeReadbackS3v2p(unittest.TestCase):
    def test_01_first_e0_and_expected_original_observer(self):
        self.assertEqual(p.E0_BLOB,"44d6f3d72ed6c62f38054d11f050ee16cab50bc2")
        self.assertEqual(p.E0_FILE,
                         "ENGINE001_BPRED001_S3V2P_NATIVE_CANVAS_READBACK_VS_COMPOSITION_PREREG_2026-11-20.md")
        self.assertEqual(p.ROI,(400,220,270,270))
        self.assertEqual(p.NATIVE_ORIGIN,(-6,-6))
        self.assertEqual(p.JS_FILE,"engine001_bpred_s3v2p_canvas_readback_observer.js")

    def test_02_frozen_80_new_source_scenes_and_20_replays(self):
        m=p.manifest()
        self.assertEqual(m["experiment"],p.EXPERIMENT)
        self.assertFalse(m["S0_BLIND_used"])
        self.assertEqual(len(m["scenes"]),80)
        self.assertEqual(len(m["controls"]),20)
        self.assertEqual(len({x["sample_id"] for x in m["scenes"]}),80)
        self.assertEqual(len({x["sample_id"] for x in m["controls"]}),20)
        self.assertEqual({x["width"] for x in m["scenes"]},set(range(1,11)))
        self.assertEqual({x["relation"] for x in m["scenes"]},set(p.RELATIONS))
        self.assertEqual({x["variant"] for x in m["scenes"]},set(p.VARIANTS))

    def test_03_new_angle_phase_and_colors_do_not_reuse_old_native_family(self):
        self.assertNotEqual(p.ANGLES,o.ANGLES)
        self.assertNotEqual(p.ANGLES,j.ANGLES)
        self.assertEqual(len(set(p.COLORS)),10)
        self.assertEqual(len({x for pair in p.COLORS for x in pair}),20)
        for w in p.WIDTHS:
            self.assertNotEqual(p.COLORS[w-1],o.COLORS[w-1])
            self.assertNotEqual(p.COLORS[w-1],
                j.ODD_COLORS if w%2 else j.EVEN_COLORS)
            scene=p.plans_for(w,"NEAR_SKEW")["A_ONLY"]
            self.assertEqual(scene["angle_deg"],p.ANGLES[w-1])
            self.assertNotEqual(scene["phase_xy"],
                o.plans_for(w,"NEAR_SKEW")["A_ONLY"]["phase_xy"])

    def test_04_original_input_and_transport_only_differ_by_stroke_id(self):
        for scene in p.manifest()["scenes"]:
            source=scene["source_strokes"]
            runtime=scene["runtime_strokes"]
            self.assertEqual([s["width"] for s in source],
                             [s["width"] for s in runtime])
            for a,b in zip(source,runtime):
                self.assertEqual({k:v for k,v in a.items() if k!="strokeId"},
                                 {k:v for k,v in b.items() if k!="strokeId"})
                self.assertIn(a["colorIndex"],(1,2))
            self.assertEqual(scene["source_plan_sha256"],s3.digest(s3.canonical(source)))
            self.assertEqual(scene["runtime_plan_sha256"],s3.digest(s3.canonical(runtime)))

    def test_05_all_original_physical_strokes_within_board_and_readback_roi(self):
        for scene in p.manifest()["scenes"]:
            for stroke in scene["source_strokes"]:
                self.assertIn(stroke["width"],p.WIDTHS)
                for pt in stroke["points"]:
                    self.assertTrue(math.isfinite(pt["x"]) and 0<pt["x"]<460)
                    self.assertTrue(math.isfinite(pt["y"]) and 0<pt["y"]<240)
                    # Physical extent for endpoint plus radius up to w/2
                    physx,physy=(3*pt["x"]+6,3*pt["y"]+6)
                    radius=1.5*stroke["width"]+3
                    self.assertTrue(p.ROI[0]<physx-radius<physx+radius<p.ROI[0]+p.ROI[2])
                    self.assertTrue(p.ROI[1]<physy-radius<physy+radius<p.ROI[1]+p.ROI[3])

    def test_06_replay_is_uninstrumented_original_two_owner_case(self):
        m=p.manifest()
        for c in m["controls"]:
            self.assertEqual(c["parent_sample_id"],
                             p.plans_for(c["width"],c["relation"])["A_THEN_B"]["sample_id"])
            self.assertTrue(c["sample_id"].startswith("BPRED-S3V2P-REPLAY-W"))

    def test_07_invalid_geometry_fails_closed(self):
        for w,rel in [(0,"CROSS_ROTATED"),(11,"CROSS_ROTATED"),
                      (True,"CROSS_ROTATED"),(1,"OTHER")]:
            with self.assertRaisesRegex(ValueError,"UNFROZEN_WIDTH_OR_RELATION"):
                p.plans_for(w,rel)

    def test_08_original_native_canvas_to_board_alignment_exact(self):
        alpha=np.zeros((720,1380,4),dtype=np.uint8)
        y=p.ROI[1]-6+3;x=p.ROI[0]-6+7
        alpha[y,x]=[12,33,44,91]
        got=p.roi_png({"canvas":alpha})
        self.assertEqual(got.shape,(270,270,4))
        self.assertEqual(got[3,7].tolist(),[12,33,44,91])
        self.assertFalse(np.any(got[4,7]))
        with self.assertRaisesRegex(ValueError,"ORIGINAL_ALIGNED_MAIN_SHAPE"):
            p.roi_png({"canvas":np.zeros((2,2,4),dtype=np.uint8)})

    def test_09_sampled_readback_diff_exact_alphazero_is_not_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);sid="BPRED-S3V2P-W01-CROSS_ROTATED-A_ONLY"
            folder=root/"native"/sid
            folder.mkdir(parents=True)
            rgba=np.zeros((270,270,4),np.uint8)
            rgba[5,9]=[12,13,14,0]
            data=rgba.tobytes()
            rawfile=sid+"_REAL_GETIMAGEDATA_STEP_01.rgba"
            (folder/rawfile).write_bytes(data)
            png=np.zeros((732,1392,4),np.uint8)
            pngfile=sid+"_REAL_STROKE_STEP_01.png"
            Image.fromarray(png,mode="RGBA").save(folder/pngfile)
            row={"sample_id":sid,"step":1,"original_main_canvas_png":pngfile,
                 "native_raw_file":rawfile,"native_raw_sha256":hashlib.sha256(data).hexdigest(),
                 "PNG_vs_getImageData_different_RGBA_pixels":1}
            item={"scene":{"sample_id":sid,"width":1,"relation":"CROSS_ROTATED",
                           "variant":"A_ONLY"},"steps":[None],"readback_meta":[row]}
            cases,errors,bins=p.compare_readbacks([item],root)
            self.assertEqual(len(cases),1)
            self.assertEqual(len(errors),1)
            self.assertEqual(errors[0]["node_local_physical_xy"],[409,225])
            self.assertEqual(errors[0]["aligned_board_physical_xy"],[403,219])
            self.assertEqual(errors[0]["PNG_RGBA"],[0,0,0,0])
            self.assertEqual(errors[0]["getImageData_RGBA"],[12,13,14,0])
            self.assertEqual(bins["A0"]["mismatches"],1)

    def test_10_alpha_bins_nonvacuous_include_zero_and_low_alpha(self):
        self.assertEqual([p.bucket_label(x) for x in (0,1,15,16,63,64,127,128,254,255)],
                         ["A0","A01_15","A01_15","A16_63","A16_63",
                          "A64_127","A64_127","A128_254","A128_254","A255"])

    def test_11_missing_frozen_native_provenance_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(ValueError):
                p.check_source(root,root/"engine.js",root/"reference.js",
                               [],root/"new.js")

    def test_12_readback_is_diagnostic_and_no_legacy_planner(self):
        self.assertIn("READBACK_VS_COMPOSITION",p.EXPERIMENT)
        self.assertNotIn("S4_BLIND",p.EXPERIMENT)
        self.assertTrue(p.manifest()["S0_BLIND_used"] is False)
        self.assertEqual(p.RELATIONS,("CROSS_ROTATED","NEAR_SKEW"))
        self.assertEqual(p.VARIANTS,("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A"))


if __name__=="__main__":
    unittest.main()
