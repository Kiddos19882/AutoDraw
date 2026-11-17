#!/usr/bin/env python3
"""COLOR32-V1 source-only regression: no native brush/CHALK claims."""
import json
import unittest
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from run_engine001_color32_region_opt_v1 import (
    BASE, SOURCE_SHA, EXP, baseline_a, load_game_palette, load_original,
    nearest_game32, slic_game32, merge_small_regions, metrics, render, sha,
)

PALETTE = BASE/"data"/"palettes"/"browser_palette.json"
SOURCE = BASE/"testImages"/"wV6VeZI9S1Y.png"


class Color32RegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette,cls.palette_sha=load_game_palette(PALETTE)

    def test_real_palette_and_frozen_source_provenance(self):
        self.assertEqual(len(self.palette),32)
        self.assertEqual(len(set(x["hex"] for x in self.palette)),32)
        self.assertIn("#FFFFFF",{x["hex"] for x in self.palette})
        self.assertNotIn("#000000",{x["hex"] for x in self.palette})
        self.assertEqual(sha(SOURCE),SOURCE_SHA)
        roi=load_original(SOURCE)
        self.assertEqual(roi.size,(150,240))
        self.assertEqual(roi.mode,"RGB")

    def test_a_is_exactly_original_roi_medincut8_no_dithering(self):
        roi=load_original(SOURCE)
        a,p=baseline_a(roi)
        self.assertEqual(len(p),8)
        expected=roi.quantize(colors=8,method=Image.Quantize.MEDIANCUT,
                              dither=Image.Dither.NONE)
        self.assertTrue(np.array_equal(render(a,p),
                                       np.asarray(expected.convert("RGB"))))

    def test_b_and_c_only_use_actual_32_game_swatches(self):
        roi=load_original(SOURCE)
        arr=np.asarray(roi)
        colors=np.asarray([x["rgb"] for x in self.palette],dtype=np.uint8)
        b=nearest_game32(roi,self.palette)
        c,details=slic_game32(roi,self.palette)
        self.assertTrue(np.all(b>=0)&np.all(b<32))
        self.assertTrue(np.all(c>=0)&np.all(c<32))
        self.assertTrue(details["superpixels"]>1)
        self.assertEqual(c.shape,(240,150))
        self.assertEqual(b.shape,(240,150))
        self.assertEqual(nearest_game32(roi,self.palette).tolist(),b.tolist())
        self.assertTrue(np.array_equal(slic_game32(roi,self.palette)[0],c))
        for labels in (b,c):
            actual=np.unique(render(labels,colors).reshape(-1,3),axis=0)
            allowed={tuple(x) for x in colors.tolist()}
            self.assertTrue(set(map(tuple,actual.tolist()))<=allowed)

    def test_d_edge_guard_and_no_new_colors(self):
        # A tiny color4 island on a strongly contrasting original backdrop
        # is deliberately NOT mergeable across source-edge RGB >30.
        colors=np.asarray([x["rgb"] for x in self.palette],np.uint8)
        ids=np.zeros((240,150),np.int32)
        ids[100:102,40:42]=1
        source=np.full((240,150,3),0,dtype=np.uint8)
        source[100:102,40:42]=255
        after,runs=merge_small_regions(ids,source,self.palette)
        self.assertTrue(np.array_equal(ids,after))
        self.assertLessEqual(len(runs),3)
        # D cannot assign labels outside the immutable game32 index domain.
        self.assertTrue(np.all(after>=0)&np.all(after<len(colors)))
        # Determinism is required for frozen source evidence.
        self.assertTrue(np.array_equal(
            merge_small_regions(ids,source,self.palette)[0],after))

    def test_metrics_finite_and_source_edge_recall_bounded(self):
        roi=load_original(SOURCE)
        labels,colors=baseline_a(roi)
        source=np.asarray(roi,np.uint8)
        edges=cv2.Canny(cv2.cvtColor(source,cv2.COLOR_RGB2GRAY),60,120)>0
        x=metrics(render(labels,colors),labels,source,colors,edges)
        for key in ("mean_delta_E00","p95_delta_E00","max_delta_E00","RGB_MAE"):
            self.assertTrue(np.isfinite(x[key]))
            self.assertGreaterEqual(x[key],0)
        self.assertTrue(0<=x["source_canny_edge_recall_within_1px"]<=1)
        self.assertTrue(x["connected_regions_8"]>0)
        self.assertTrue(x["boundary_contours_including_holes"]>0)


if __name__=="__main__":
    unittest.main()
