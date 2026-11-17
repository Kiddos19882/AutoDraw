#!/usr/bin/env python3
"""S4 regression: real pretrained model identity guard and explicit feature effect."""
import tempfile
import unittest
from pathlib import Path
import numpy as np

from run_engine001_color32_neural_s4_dinov2 import (
    choose_colors, region_embeddings, real_dino_features, WEIGHTS_SHA,
)


class S4RealNeuralContracts(unittest.TestCase):
    def fixture(self):
        rgb=np.full((240,150,3),255,np.uint8)
        rgb[30:120,20:85]=[165,99,91]
        rgb[30:120,85:115]=[173,103,93]
        palette=np.zeros((32,3),np.uint8)
        palette[30]=[255,255,255]
        palette[3]=[175,108,91]
        palette[4]=[146,98,94]
        regions=np.full((240,150),-1,np.int32)
        regions[30:120,20:85]=0
        regions[30:120,85:115]=1
        ink=np.zeros((240,150),bool)
        return rgb,palette,regions,ink

    def test_wrong_checkpoint_fails_before_neural_import(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"model.safetensors").write_bytes(b"wrong-pretrained-weights")
            rgb=np.full((240,150,3),255,np.uint8)
            with self.assertRaisesRegex(ValueError,"BLOCKED_S4_MODEL_SHA_DRIFT"):
                real_dino_features(rgb,root)

    def test_missing_checkpoint_and_processor_fail_closed(self):
        rgb=np.full((240,150,3),255,np.uint8)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaisesRegex(ValueError,"BLOCKED_S4_MODEL_SHA_DRIFT"):
                real_dino_features(rgb,root)
            (root/"model.safetensors").write_bytes(b"incorrect-weights")
            with self.assertRaisesRegex(ValueError,"BLOCKED_S4_MODEL_SHA_DRIFT"):
                real_dino_features(rgb,root)

    def test_original_background_and_fixed_palette(self):
        rgb,palette,regions,ink=self.fixture()
        out,report=choose_colors(rgb,palette,regions,ink)
        self.assertTrue(np.all(out[regions<0]==30))
        self.assertTrue(np.all(out<32))
        self.assertFalse(report["pretrained_neural_features_used"])

    def test_neural_feature_shape_is_checked(self):
        rgb,palette,regions,ink=self.fixture()
        wrong=np.ones((1,384),float)
        with self.assertRaisesRegex(ValueError,"BLOCKED_S4_NEURAL_REGION_COUNT"):
            choose_colors(rgb,palette,regions,ink,wrong)

    def test_real_feature_region_pooling_shape(self):
        _,_,regions,_=self.fixture()
        features=np.zeros((240,150,4),np.float32)
        features[regions==0]=[1.,0.,0.,0.]
        features[regions==1]=[0.,1.,0.,0.]
        vec=region_embeddings(features,regions)
        self.assertEqual(vec.shape,(2,4))
        self.assertGreater(vec[0]@vec[0],.999)
        self.assertLess(vec[0]@vec[1],.001)

    def test_neural_ablation_is_explicit_not_fake_training(self):
        rgb,palette,regions,ink=self.fixture()
        fake_for_unit_test_only=np.array([[1.,0.],[1.,0.]])
        _,control=choose_colors(rgb,palette,regions,ink)
        _,conditioned=choose_colors(rgb,palette,regions,ink,fake_for_unit_test_only)
        self.assertTrue(conditioned["pretrained_neural_features_used"])
        self.assertFalse(control["pretrained_neural_features_used"])
        self.assertEqual(conditioned["trained_palette_head"],"NOT_TRAINED")
        self.assertEqual(len(WEIGHTS_SHA),64)


if __name__=="__main__":
    unittest.main()
