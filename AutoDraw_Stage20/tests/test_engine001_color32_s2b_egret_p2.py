#!/usr/bin/env python3
"""ENGINE-001 P2 isolated real Egret preflight; geometry tests are MODEL_ONLY."""
import unittest

import cv2
import numpy as np

from run_engine001_color32_s2b_egret_p2 import (
    OWNERS, WIDTHS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES,
    MAX_P2_STROKES, MAX_P2_VERTICES, MIN_NATIVE_RELATIVE_GAIN,
    plan_p2, compare_native,
)
from run_engine001_palette32_region_study import read_palette
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def native_cell(own, foreign=0, far=0, outside=0, target=9000):
    return {
        "native_correct_owner_pixels":own,
        "non_owner_native_pixels_any_distance":foreign,
        "non_owner_beyond_3logical_px":far,
        "ink_outside_image_ROI":outside,
        "isolated_fraction_of_full_owner_NOT_full_fill_coverage":own/target,
    }


class EgretP2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette=read_palette(ROOT/"data/palettes/browser_palette.json")
        cls.g=np.full((240,150),30,np.uint8)
        cv2.circle(cls.g,(41,65),30,31,-1)
        cv2.circle(cls.g,(112,169),26,29,-1)

    def test_synthetic_concentric_paths_reuse_original_game_RGB(self):
        paths,info=plan_p2(self.g,self.palette)
        self.assertEqual(info["status"],"SOURCE_MODEL_READY_FOR_E3")
        self.assertEqual(set(p["colorIndex"] for p in paths),set(OWNERS))
        self.assertEqual(info["same_color_revisit_penalty"],0)
        self.assertEqual(len({p["strokeId"] for p in paths}),len(paths))
        self.assertEqual(info["paint_paths"],len(paths))
        self.assertLessEqual(len(paths),MAX_P2_STROKES)
        self.assertLessEqual(info["paint_vertices_NOT_CHALK"],MAX_P2_VERTICES)
        self.assertLessEqual(len(paths)+FROZEN_DETAILS,3000)
        self.assertLessEqual(info["paint_vertices_NOT_CHALK"]+
                             FROZEN_DETAIL_VERTICES,5900)
        for p in paths:
            self.assertIn(p["width"],WIDTHS)
            self.assertTrue(2<=len(p["points"])<=128)
            self.assertTrue(all(155<=v["x"]<305 and 0<=v["y"]<240
                                for v in p["points"]))
            rgb=self.palette[p["colorIndex"]]
            self.assertEqual(p["colorRgb"],int(rgb[0])*65536+
                             int(rgb[1])*256+int(rgb[2]))

    def test_original_mask_and_palette_shape_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_P2_SOURCE_GEOMETRY"):
            plan_p2(np.zeros((10,10),np.uint8),self.palette)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P2_SOURCE_GEOMETRY"):
            plan_p2(self.g,self.palette[:10])
        with self.assertRaisesRegex(ValueError,"BLOCKED_P2_SOURCE_GEOMETRY"):
            plan_p2(np.full((240,150),30,np.uint8),self.palette)
        paths1,info1=plan_p2(self.g,self.palette)
        paths2,info2=plan_p2(self.g,self.palette)
        self.assertEqual((paths1,info1),(paths2,info2))

    def test_native_gate_uses_real_rgba_numbers_not_model_proxy(self):
        p1={str(a):{str(o):native_cell(100) for o in OWNERS}
            for a in (24,128)}
        p2={str(a):{str(o):native_cell(130) for o in OWNERS}
            for a in (24,128)}
        passed=compare_native(p1,p2)
        self.assertTrue(passed["native_P2_source_gate_pass"])
        self.assertEqual(len(passed["checks"]),4)
        self.assertAlmostEqual(passed["measurements"]["alpha24_owner31"]["relative_gain"],0.3)
        p2["24"]["31"]["non_owner_beyond_3logical_px"]=1
        self.assertFalse(compare_native(p1,p2)["native_P2_source_gate_pass"])
        p2["24"]["31"]["non_owner_beyond_3logical_px"]=0
        p2["128"]["29"]["native_correct_owner_pixels"]=119
        self.assertFalse(compare_native(p1,p2)["native_P2_source_gate_pass"])
        p1["24"]["31"]["native_correct_owner_pixels"]=0
        with self.assertRaisesRegex(ValueError,"BLOCKED_P1_NATIVE_ZERO_BASELINE"):
            compare_native(p1,p2)


if __name__=="__main__":
    unittest.main()
