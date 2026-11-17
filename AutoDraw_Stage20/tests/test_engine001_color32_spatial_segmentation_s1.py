#!/usr/bin/env python3
"""ENGINE-001 COLOR32-S1 fixed geometry/palette E2 regression, not native Egret."""
import unittest
import numpy as np
from PIL import Image
from pathlib import Path

from run_engine001_color32_spatial_segmentation_s1 import (
    CASES, MERGE_MAX_DE00, MERGE_MAX_SHARED_GRADIENT,
    ROI_SIZE, legacy_case, load_game32, merge_adjacent_regions,
    quantize_regions, region_medians, run, source_roi, superpixels,
)

GAME_PALETTE = Path(__file__).resolve().parents[1]/"data"/"palettes"/"browser_palette.json"
SOURCE = Path(__file__).resolve().parents[1]/"testImages"/"wV6VeZI9S1Y.png"


class Color32SpatialTests(unittest.TestCase):
    def test_exact_existing_game_palette_and_real_non_synthetic_rgb(self):
        colors = load_game32(GAME_PALETTE)
        self.assertEqual(len(colors), 32)
        self.assertEqual(len({tuple(c["rgb"]) for c in colors}), 32)
        self.assertIn((255,255,255), {tuple(c["rgb"]) for c in colors})
        self.assertIn((27,27,27), {tuple(c["rgb"]) for c in colors})
        self.assertEqual(len(CASES),4)
        self.assertEqual(MERGE_MAX_DE00,8.0)
        self.assertEqual(MERGE_MAX_SHARED_GRADIENT,0.08)
        centers=np.array([[255,255,255],[252,190,175],[0,0,0]],
                         dtype=np.uint8)
        mapped=quantize_regions(centers,colors)
        self.assertEqual(mapped.shape,(3,))
        self.assertTrue(np.all((mapped>=0)&(mapped<32)))

    def test_slic_preserves_all_source_geometry_and_repeatability(self):
        src=np.asarray(source_roi(SOURCE))
        self.assertEqual(src.shape,(240,150,3))
        a=superpixels(src)
        b=superpixels(src)
        self.assertEqual(a.shape,(240,150))
        self.assertTrue(np.array_equal(a,b))
        self.assertGreaterEqual(int(a.max())+1,10)
        self.assertTrue(np.array_equal(
            np.unique(a),np.arange(int(a.max())+1)))
        med=region_medians(src,a)
        self.assertEqual(med.shape,(int(a.max())+1,3))
        self.assertEqual(med.dtype,np.uint8)
        legacy, rgb, palette=legacy_case(Image.fromarray(src))
        self.assertEqual(legacy.shape,(240,150))
        self.assertEqual(rgb.shape,src.shape)
        self.assertEqual(len(palette),8)

    def test_strong_source_color_edge_prevents_adjacent_merging(self):
        source=np.zeros((240,150,3),dtype=np.uint8)
        source[:,:75,:]=[15,15,15]
        source[:,75:,:]=[245,245,245]
        split=np.zeros((240,150),dtype=np.int32)
        split[:,75:]=1
        result,meta=merge_adjacent_regions(split,source)
        self.assertEqual(meta["accepted_merges"],0)
        self.assertEqual(meta["merged_regions"],2)
        self.assertNotEqual(int(result[120,70]),int(result[120,80]))

    def test_nearly_same_adjoining_regions_merge_but_not_disconnected(self):
        src=np.full((240,150,3),[126,125,122],dtype=np.uint8)
        region=np.zeros((240,150),np.int32)
        region[:,50:100]=1
        region[:,100:]=2
        src[:,50:100,:]=[128,126,124]
        src[:,100:,:]=[127,126,124]
        result,meta=merge_adjacent_regions(region,src)
        self.assertEqual(meta["accepted_merges"],2)
        self.assertEqual(meta["merged_regions"],1)
        self.assertEqual(len(np.unique(result)),1)

    def test_invalid_palette_and_region_geometry_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"source geometry"):
            superpixels(np.zeros((4,4,3),np.uint8))
        with self.assertRaisesRegex(ValueError,"region geometry"):
            region_medians(np.zeros((240,150,3),np.uint8),
                           np.zeros((3,4),np.int32))
        with self.assertRaisesRegex(ValueError,"merge source geometry"):
            merge_adjacent_regions(
                np.zeros((240,149),np.int32),
                np.zeros((240,150,3),np.uint8))


if __name__ == "__main__":
    unittest.main()
