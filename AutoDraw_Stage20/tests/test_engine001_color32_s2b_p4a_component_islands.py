#!/usr/bin/env python3
"""ENGINE-001 P4a frozen source component isolation, source-only E2 regressions."""
import hashlib
import unittest
from pathlib import Path

import numpy as np

from run_engine001_color32_s2b_p4a_component_islands import (
    component_aware_h, components_for, _png_bytes,
    source_checks, ORIGINAL_SOURCE_SHA256, FROZEN_G_INDEX_PNG_SHA256,
    WHITE_OWNER,
)
from run_engine001_palette32_region_study import (
    read_source,read_palette,nearest32,sha,
)
from run_engine001_color32_s2_edge_protection import strong_edges,protected_merge

ROOT=Path(__file__).resolve().parents[1]


class P4aSourceOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette=read_palette(ROOT/"data/palettes/browser_palette.json")

    def fixture(self):
        labels=np.full((240,150),29,dtype=np.uint8)
        labels[0:10,:]=WHITE_OWNER
        labels[33:35,70:72]=31
        source=self.palette[labels].copy()
        # Original source makes tiny isolated owner31 expensive and owner29
        # visually plausible; do not rely on native Egret for source rules.
        source[33:35,70:72]=self.palette[29]
        protected=np.zeros(labels.shape,dtype=np.bool_)
        return source,labels,protected

    def test_unprotected_whole_component_merges_to_existing_neighbor(self):
        source,g,protected=self.fixture()
        h,diag=component_aware_h(source,g,self.palette,protected)
        self.assertEqual(diag["accepted_component_count"],1)
        self.assertEqual(diag["changed_pixel_count"],4)
        self.assertTrue(np.all(h[33:35,70:72]==29))
        self.assertTrue(np.all(h[g==WHITE_OWNER]==WHITE_OWNER))
        self.assertLess(components_for(h)["all_components"],
                        components_for(g)["all_components"])
        self.assertEqual(source_checks(source,g,h,self.palette,protected)
                         ["checks"]["protected_pixels_unchanged"],True)

    def test_protected_pixel_rejects_entire_connected_island(self):
        source,g,protected=self.fixture()
        protected[33,70]=True
        h,diag=component_aware_h(source,g,self.palette,protected)
        self.assertTrue(np.array_equal(h,g))
        self.assertEqual(diag["accepted_component_count"],0)
        self.assertGreaterEqual(diag["blocked_if_any_protected_pixel"],1)

    def test_white_and_invalid_inputs_fail_closed(self):
        source,g,protected=self.fixture()
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4A_SOURCE_GEOMETRY_OR_PALETTE"):
            component_aware_h(source,g[:10],self.palette,protected)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4A_SOURCE_GEOMETRY_OR_PALETTE"):
            component_aware_h(source,g,self.palette[:10],protected)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4A_SOURCE_GEOMETRY_OR_PALETTE"):
            component_aware_h(source,g,self.palette,protected.astype(np.uint8))
        h,diag=component_aware_h(source,g,self.palette,protected)
        h2,diag2=component_aware_h(source,g,self.palette,protected)
        self.assertTrue(np.array_equal(h,h2))
        self.assertEqual(diag,diag2)

    def test_real_frozen_G_source_png_is_identical_to_S2b_CI(self):
        source_path=ROOT/"testImages/wV6VeZI9S1Y.png"
        self.assertEqual(sha(source_path),ORIGINAL_SOURCE_SHA256)
        _,source=read_source(source_path)
        b=nearest32(source,self.palette)
        protected,_=strong_edges(source)
        g,_=protected_merge(source,b,self.palette,protected)
        digest=hashlib.sha256(_png_bytes(g)).hexdigest()
        self.assertEqual(digest,FROZEN_G_INDEX_PNG_SHA256)
        h,diag=component_aware_h(source,g,self.palette,protected)
        gates=source_checks(source,g,h,self.palette,protected)
        self.assertTrue(gates["checks"]["protected_pixels_unchanged"])
        self.assertTrue(gates["checks"]["white_pixel_unmodified"])
        self.assertTrue(gates["checks"]["only_original_game32_swatch_indices"])
        self.assertEqual(gates["changed_pixels"],diag["changed_pixel_count"])
        # No claim about native coverage, game CHALK or eventual visual quality.
        self.assertEqual(gates["native_BoardPane"],"NOT_RUN")
        self.assertIsNone(gates["CHALK"])


if __name__=="__main__":
    unittest.main()
