#!/usr/bin/env python3
"""B1-R-P3 original-derived P2D vs real 32 game swatches regression tests."""
import ast
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p3_source_game32 as p3


class P3Game32SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palpath = Path(__file__).resolve().parents[1] / "data" / "palettes" / "browser_palette.json"
        cls.game, cls.entries, cls.palette_sha = p3.load_game_swatches(cls.palpath)

    def test_01_protocol_32_swatches_pinned(self):
        self.assertEqual(p3.EXPERIMENT,
                         "ENGINE001_B1R_P3_ORIGINAL_SOURCE_32_GAME_SWATCH_V1")
        self.assertEqual(p3.MAPPING_METHODS, ("N_NEAREST", "S_GUARDED"))
        self.assertEqual(p3.PALETTE_BLOB_SHA1,
                         "461b5f3725b9b79888ad36e807b3cf4c9e445e98")
        self.assertEqual(p3.WHITE_INDEX, 30)
        self.assertEqual(p3.unique_rgb(self.game), 32)
        self.assertEqual(self.game[30].tolist(), [255,255,255])

    def test_02_real_game_palette_only_and_sha(self):
        blob=self.palpath.read_bytes()
        self.assertEqual(p3.git_blob_sha(blob),p3.PALETTE_BLOB_SHA1)
        self.assertEqual(p3.unique_rgb(self.game),32)
        self.assertEqual(
            [e["hex"] for e in self.entries],
            ["#"+"".join(f"{v:02X}" for v in c) for c in self.game])

    def test_03_palette_drift_refused_without_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fake.json"
            data=json.loads(self.palpath.read_text(encoding="utf8"))
            data["colors"][0]["rgb"]=[0,255,0]
            p.write_text(json.dumps(data),encoding="utf8")
            with self.assertRaisesRegex(ValueError,"GAME_SWATCH_GIT_BLOB"):
                p3.load_game_swatches(p)

    def test_04_nearest_only_exact_game_rgb_and_no_unresolved(self):
        target=np.array([[[242,240,236],[75,47,48],[242,190,153]],
                         [[255,255,255],[55,43,50],[200,100,78]]],dtype=np.uint8)
        original=target.copy()
        indices,rgba,preview,info=p3.assign_game32(
            target,original,self.game,"N_NEAREST")
        self.assertEqual(info["unresolved_pixels"],0)
        self.assertTrue(np.all(indices>=0))
        self.assertTrue(np.array_equal(preview,self.game[indices]))
        self.assertTrue(np.all(rgba[...,3]==255))
        self.assertEqual(int(indices[1,0]),30)

    def test_05_near_white_forces_genuine_game_white(self):
        original=np.array([[[254,252,252],[245,246,247]],
                           [[245,244,255],[30,30,30]]],dtype=np.uint8)
        target=np.array([[[240,225,220],[243,224,222]],
                         [[250,252,246],[30,30,30]]],dtype=np.uint8)
        for mode in p3.MAPPING_METHODS:
            ix,rgba,preview,r=p3.assign_game32(
                target,original,self.game,mode)
            self.assertEqual(int(ix[0,0]),30)
            self.assertEqual(int(ix[0,1]),30)
            self.assertEqual(preview[0,0].tolist(),[255,255,255])
            self.assertEqual(r["near_white_forced_game_white"],2)

    def test_06_source_grounding_abstains_bad_pink(self):
        original=np.full((3,4,3),[180,180,180],dtype=np.uint8)
        target=np.full((3,4,3),[255,0,255],dtype=np.uint8)
        ix,rgba,preview,info=p3.assign_game32(
            target,original,self.game,"S_GUARDED")
        self.assertEqual(info["unresolved_pixels"],12)
        self.assertTrue(np.all(ix==-1))
        self.assertTrue(np.all(rgba[...,3]==0))
        self.assertTrue(np.all(preview==255))
        self.assertTrue(info["unresolved_is_not_drawable"])

    def test_07_original_neutral_does_not_gain_saturated_chroma(self):
        original=np.full((3,4,3),[70,68,69],dtype=np.uint8)
        target=np.full((3,4,3),[60,44,47],dtype=np.uint8)
        ix,_,_,_=p3.assign_game32(target,original,self.game,"S_GUARDED")
        sourceLab=p3.rgb_lab(original)
        sourceCh=np.linalg.norm(sourceLab[...,1:],axis=2)
        paletteLab=p3.rgb_lab(self.game.reshape(1,32,3))[0]
        paletteCh=np.linalg.norm(paletteLab[:,1:],axis=1)
        self.assertTrue(all(paletteCh[i]<=sourceCh.flat[k]+12
                            for k,i in enumerate(ix.ravel()) if i>=0))

    def test_08_bad_mapping_name_and_shape_refused(self):
        src=np.full((2,2,3),[32,32,32],dtype=np.uint8)
        with self.assertRaisesRegex(ValueError,"UNREGISTERED_METHOD"):
            p3.assign_game32(src,src,self.game,"G32_OLD")
        with self.assertRaisesRegex(ValueError,"GAME32_DIMENSIONS"):
            p3.assign_game32(src,src[:1],self.game,"S_GUARDED")
        with self.assertRaisesRegex(ValueError,"GAME32_DIMENSIONS"):
            p3.assign_game32(src,src,self.game[:30],"N_NEAREST")

    def test_09_p2d_two_guards_and_two_source_palettes_reused(self):
        self.assertEqual(p3.SOURCE_INK_BUDGETS,
                         {"C_096":96,"C_192":192})
        self.assertEqual(p3.GUARD_VARIANTS,
                         ("D_BORDER","D_COMPONENT24"))
        self.assertEqual(p3.MAX_ABSTAIN,720)
        self.assertEqual(p3.MAX_HUE_DISTANCE,45)

    def test_10_no_history_G32_or_V44_or_game_modules_imported(self):
        tree=ast.parse(Path(p3.__file__).read_text(encoding="utf8"))
        actual={n.module for n in ast.walk(tree)
                if isinstance(n,ast.ImportFrom) and n.module and
                n.module.startswith("run_engine001")}
        self.assertEqual(actual,{
            "run_engine001_b1r_p1_fullrgb_edge_aware",
            "run_engine001_b1r_p2_joint_region_outline",
            "run_engine001_b1r_p2b_residual_ink",
            "run_engine001_b1r_p2c_source_ink_palette",
            "run_engine001_b1r_p2d_background_halo_guard",
        })

    def test_11_source_pin_original(self):
        self.assertEqual(
            p3.SOURCE_SHA256,
            "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")

    def test_12_output_must_not_overwrite_frozen(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                p3.run(Path(temp)/"not-source.png",
                       Path(temp)/"not-game.json",Path(temp))

    def test_13_palette_unresolved_is_not_game_raster(self):
        src=np.full((1,1,3),[180,180,180],dtype=np.uint8)
        tgt=np.full((1,1,3),[255,0,255],dtype=np.uint8)
        ix,rgba,preview,info=p3.assign_game32(tgt,src,self.game,"S_GUARDED")
        self.assertEqual(int(ix[0,0]),-1)
        self.assertEqual(int(rgba[0,0,3]),0)
        self.assertEqual(int(preview[0,0,0]),255)
        self.assertEqual(info["assigned_pixels"],0)

if __name__=="__main__":
    unittest.main()
