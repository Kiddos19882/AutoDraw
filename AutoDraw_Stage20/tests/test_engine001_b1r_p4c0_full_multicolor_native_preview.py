"""Static E2 contracts for original-sourced, diagnostic full-color native pilot."""
import unittest
from pathlib import Path
import numpy as np

import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0


class P4C0Contracts(unittest.TestCase):
    def test_01_identity_not_legacy(self):
        self.assertEqual(p4c0.EXPERIMENT,
                         "ENGINE001_B1R_P4C0_FULL_MULTICOLOR_EGRET_PREVIEW_V1")
        self.assertEqual(p4c0.METHODS, ("E_SOBEL90", "F_SOBEL90_LAB12"))
        self.assertEqual(p4c0.SOURCE, "C_192_D_COMPONENT24")
        self.assertEqual(p4c0.WHITE, 6)
        text=Path(p4c0.__file__).read_text("utf8")
        self.assertNotIn("import run_engine001_color32_p4c1",text)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",text)
        self.assertIn("source_joint_outline(source_index, original, game)",text)

    def test_02_frozen_renderer_caps(self):
        self.assertEqual((p4c0.MAX_STROKES,p4c0.MAX_VERTICES),(3000,5900))
        self.assertLess(p4c0.PAINT_STROKES_CAP,p4c0.MAX_STROKES)
        self.assertLess(p4c0.PAINT_VERTICES_CAP,p4c0.MAX_VERTICES)
        self.assertEqual(p4c0.ALPHA,24)
        self.assertEqual(p4c0.RENDERER_BLOB,
                         "76d950e0a8911888a9df3b675b866519ecf7bba4")

    def test_03_original_palette_source_fail_closed(self):
        game=np.zeros((128,3),np.uint8)
        index=np.full((240,150),6,np.uint8)
        chosen=[6]+[i for i in range(33) if i != 6][:31]
        p4c0.validate_source(index,game,chosen)
        index[100,100]=115
        with self.assertRaisesRegex(ValueError,"PALETTE"):
            p4c0.validate_source(index,game,chosen)
        with self.assertRaisesRegex(ValueError,"PALETTE"):
            p4c0.validate_source(index.astype(np.int16),game,chosen)

    def test_04_deterministic_fair_cap(self):
        source={115:1800,12:2,33:44,71:600}
        a=p4c0.allocate_limits(source,60)
        b=p4c0.allocate_limits(source,60)
        self.assertEqual(a,b)
        self.assertEqual(sum(a.values()),60)
        self.assertTrue(all(a[k]>=1 for k in source))
        self.assertLessEqual(max(a.values()),250)
        with self.assertRaisesRegex(ValueError,"BUDGET"):
            p4c0.allocate_limits(source,3)

    def test_05_global_renumber_preserves_source(self):
        a={"strokeId":"icon-8","width":3,"colorIndex":22,
           "colorRgb":0x323232,"points":[{"x":155.5,"y":10.},
                                          {"x":156.5,"y":10.}]}
        result=p4c0.renumber([a,a])
        self.assertEqual([s["strokeId"] for s in result],["icon-0","icon-1"])
        self.assertEqual(result[0]["points"],a["points"])

    def test_06_source_micro_correct_board_coordinates(self):
        game=np.zeros((128,3),np.uint8)
        game[22]=[1,2,3]
        x=p4c0.source_micro(22,game,(200,40))
        self.assertEqual(x["width"],1)
        self.assertEqual(x["colorRgb"],0x010203)
        self.assertEqual(x["points"],[{"x":195.125,"y":200.},
                                     {"x":195.375,"y":200.}])

    def test_07_joint_outline_is_new_original_source(self):
        index=np.full((240,150),6,np.uint8)
        index[:,10:80]=115
        rgb=np.full((240,150,3),255,np.uint8)
        rgb[:,10:80]=[35,40,50]
        game=np.zeros((128,3),np.uint8)
        game[115]=[35,40,50]
        paths,mask,color=p4c0.source_joint_outline(index,rgb,game)
        self.assertTrue(mask.any())
        self.assertEqual(color,115)
        self.assertGreater(len(paths),0)
        self.assertTrue(all(s["width"]==1 and s["colorIndex"]==115 for s in paths))
        self.assertTrue(all(155<=pt["x"]<305 and 0<=pt["y"]<240
                        for s in paths for pt in s["points"]))

    def test_08_native_preview_shape_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"NATIVE_RGBA"):
            p4c0.preview_native(np.zeros((240,150,4),np.uint8))
        img=p4c0.preview_native(np.zeros((720,1380,4),np.uint8))
        self.assertEqual(img.size,(450,720))

    def test_09_true_native_mask_scoring_not_color_proxy(self):
        index=np.full((240,150),6,np.uint8)
        index[10:12,20:22]=115
        rgba=np.zeros((720,1380,4),np.uint8)
        rgba[30:36, (155+20)*3:(155+22)*3,3]=255
        missing,foreign,scores=p4c0.native_mask_metrics({115:rgba},index)
        self.assertEqual(missing.sum(),0)
        self.assertEqual(foreign.sum(),0)
        self.assertEqual(scores["115"]["owner_coverage_alpha24"],1.)
        self.assertTrue(scores["115"]["quality_frozen_gates"])
        rgba[:,:,:]=0
        missing,foreign,scores=p4c0.native_mask_metrics({115:rgba},index)
        self.assertEqual(scores["115"]["owner_coverage_alpha24"],0.)
        self.assertFalse(scores["115"]["quality_frozen_gates"])

    def test_10_no_e4_or_chalk_fabrication(self):
        text=Path(p4c0.__file__).read_text("utf8")
        self.assertIn('"game_E4":"NOT_RUN"',text)
        self.assertIn('"exact_CHALK":None',text)
        self.assertIn('native_batch(',text)
        self.assertIn('renderP4A2BrushWidths1to10Probe(arguments[0])',text)
        self.assertIn('"production_promotion":False',text)


if __name__=="__main__":
    unittest.main()
