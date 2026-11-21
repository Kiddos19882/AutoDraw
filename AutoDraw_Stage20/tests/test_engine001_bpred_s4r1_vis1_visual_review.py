#!/usr/bin/env python3
"""VIS1 synthetic display only, protect original source and split boundaries."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from build_engine001_bpred_s4r1_vis1_visual_review import (
    COLORS, AWEAK3_conflict_preview, PANELS, contact_sheet, human_A_preview,
    html_index, overlay, protected_unknown_preview, white_composite,
)
from engine001_bpred_s4r1_semref1_human_review_validation import CODES


class TestVIS1DisplayOnly(unittest.TestCase):
    def setUp(self):
        self.rgba=np.zeros((8,12,4),np.uint8)
        self.rgba[:,:,:3]=(41,90,180)
        self.rgba[:,:,3]=255
        self.base=white_composite(self.rgba)
        self.orig=self.rgba.copy()

    def test_white_original_compositing_keeps_unmodified_opaque_source(self):
        np.testing.assert_array_equal(self.base,self.rgba[:,:,:3])
        np.testing.assert_array_equal(self.orig,self.rgba)

    def test_alpha_white_preview_without_changing_rgba(self):
        rgba=self.rgba.copy()
        rgba[0,0]=(255,0,0,0)
        display=white_composite(rgba)
        self.assertEqual(display[0,0].tolist(),[255,255,255])
        self.assertEqual(rgba[0,0].tolist(),[255,0,0,0])

    def test_overlay_pixels_only_and_keeps_input(self):
        mask=np.zeros((8,12),bool)
        mask[2,3]=True
        result=overlay(self.base,mask,COLORS["source_edges"],1.0)
        self.assertEqual(result[2,3].tolist(),list(COLORS["source_edges"]))
        self.assertEqual(self.base[2,3].tolist(),[41,90,180])
        np.testing.assert_array_equal(result[~mask],self.base[~mask])

    def test_source_unknown_never_colored_as_safe(self):
        protected=np.zeros((8,12),bool)
        protected[:,0]=True
        preview=protected_unknown_preview(self.base,{"protected":protected,"unknown":~protected})
        self.assertFalse(np.array_equal(preview[0,0],preview[0,5]))
        with self.assertRaisesRegex(ValueError,"PROTECTED_UNKNOWN"):
            protected_unknown_preview(self.base,{"protected":protected,"unknown":protected})

    def test_existing_A_semantic_colors_do_not_overwrite_source_or_new_map(self):
        a=np.zeros((8,12,3),dtype=np.uint8)
        a[0,0]=CODES[1]  # critical
        a[0,1]=CODES[2]  # visual boundary
        a[0,2]=CODES[3]  # visual interior
        a[0,3]=CODES[4]  # ambiguous
        original_a=a.copy()
        view=human_A_preview(self.base,a)
        self.assertFalse(np.array_equal(view[0,0],view[0,2]))
        np.testing.assert_array_equal(a,original_a)
        np.testing.assert_array_equal(self.rgba,self.orig)

    def test_new_geometric_core_risk_and_interior_separated(self):
        a=np.zeros((8,12,3),dtype=np.uint8)
        a[0,0]=CODES[1]
        a[0,1]=CODES[3]
        added=np.zeros((8,12),bool)
        added[0,0]=True
        added[0,1]=True
        view=AWEAK3_conflict_preview(self.base,a,added)
        self.assertNotEqual(view[0,0].tolist(),view[0,1].tolist())
        self.assertEqual(view[0,2].tolist(),self.base[0,2].tolist())
        np.testing.assert_array_equal(a[0,0],CODES[1])

    def test_contact_sheet_12_labeled_panels_and_full_resolution_unchanged(self):
        panels={PANELS[0][0]:self.base}
        before=self.base.copy()
        sheet=contact_sheet(panels,"Synthetic DEV / original")
        self.assertEqual(sheet.size,(1440,872))
        np.testing.assert_array_equal(before,self.base)

    def test_offline_index_escapes_filename_and_no_remote_urls(self):
        row={"id":"safe123","original_filename":"<source&test>.png",
             "role":"DEV","AWEAK3_status":"RESEARCH_ONLY","human_A":True}
        h=html_index([row])
        self.assertIn("&lt;source&amp;test&gt;.png",h)
        self.assertIn("safe123/00_contact_sheet.png",h)
        self.assertNotIn("http://",h)
        self.assertNotIn("https://",h)

    def test_no_human_gt_claim_in_model_preview_panels(self):
        self.assertIn("HUMAN A WEAK HINTS",str(PANELS))
        self.assertIn("HYPOTHETICAL CORE",str(PANELS))


if __name__=="__main__":
    unittest.main()
