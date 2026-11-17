#!/usr/bin/env python3
"""Preflight actual Egret-P1 selection and metrics, not a game rendering claim."""
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from run_engine001_color32_s2b_egret_p1 import (
    ALPHAS, BACKING_SHAPE, EXP, WIDTHS, native_metrics, select_interior_loops,
)
from run_engine001_palette32_region_study import (
    nearest32, read_palette, read_source,
)
from run_engine001_color32_s2_edge_protection import strong_edges, protected_merge

ROOT = Path(__file__).resolve().parents[1]


class EgretP1Preflight(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / "testImages/wV6VeZI9S1Y.png"
        cls.palette = read_palette(ROOT / "data/palettes/browser_palette.json")

    def test_synthetic_safe_areas_choose_genuine_game_rgb(self):
        g = np.full((240, 150), 30, dtype=np.uint8)
        cv2.circle(g, (40, 60), 28, 31, -1)
        cv2.circle(g, (109, 168), 26, 28, -1)
        probes, info = select_interior_loops(g, self.palette)
        self.assertEqual(info["selected_count"], 2)
        self.assertEqual(set(info["selected_colors"]), {31, 28})
        self.assertEqual(len({s["strokeId"] for s in probes}), len(probes))
        for s in probes:
            own = g == s["colorIndex"]
            self.assertEqual(s["colorRgb"], int(
                (int(self.palette[s["colorIndex"], 0]) << 16)
                | (int(self.palette[s["colorIndex"], 1]) << 8)
                | int(self.palette[s["colorIndex"], 2])))
            self.assertEqual(s["width"], 2)
            self.assertTrue(4 <= len(s["points"]) <= 128)
            self.assertEqual(s["points"][0], s["points"][-1])
            self.assertTrue(all(155 <= p["x"] < 305 and 0 <= p["y"] < 240
                                and own[int(p["y"]), int(p["x"] - 155)]
                                for p in s["points"]))

    def test_real_source_G_is_deterministic_and_bounded(self):
        _, rgb = read_source(self.source)
        b = nearest32(rgb, self.palette)
        protected, _ = strong_edges(rgb)
        g, _ = protected_merge(rgb, b, self.palette, protected)
        p, stats = select_interior_loops(g, self.palette)
        self.assertEqual((p, stats), select_interior_loops(g, self.palette))
        self.assertLessEqual(len(p), 4)
        self.assertGreaterEqual(len(p), 1)
        self.assertLessEqual(len(p) * len(WIDTHS), 16)
        self.assertLessEqual(sum(len(s["points"]) for s in p) * len(WIDTHS), 5900)
        self.assertEqual(WIDTHS, (2, 4, 6, 10))

    def test_no_safe_area_is_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "BLOCKED_NOT_ENOUGH_SAFE_PROBES"):
            select_interior_loops(np.full((240,150),30,np.uint8),self.palette)
        with self.assertRaisesRegex(ValueError, "BLOCKED_S2B_G_GEOMETRY"):
            select_interior_loops(np.zeros((20,20),np.uint8),self.palette)

    def test_native_RGBA_must_be_original_backing_geometry(self):
        g = np.full((240,150),30,np.uint8)
        cv2.circle(g,(70,110),27,31,-1)
        p,_ = select_interior_loops(g,self.palette)
        wrong = {f"color-{p[0]['colorIndex']}": np.zeros((24,24,4),np.uint8),
                 "composite": np.zeros(BACKING_SHAPE,np.uint8)}
        with self.assertRaisesRegex(ValueError,"BLOCKED_NATIVE_BACKING_GEOMETRY"):
            native_metrics(wrong,g,p)
        with self.assertRaisesRegex(ValueError,"BLOCKED_NATIVE_SCENE_SET"):
            native_metrics({"composite":np.zeros(BACKING_SHAPE,np.uint8)},g,p)


if __name__ == "__main__":
    unittest.main()
