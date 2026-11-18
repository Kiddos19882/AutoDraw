"""R2-P1 N1 contracts; synthetic feature tensors are explicitly unit-test only."""
import unittest
from pathlib import Path
import numpy as np
from run_engine001_color_island_r2_p1_m0 import merge_one_pass, SHAPE
from run_engine001_color_island_r2_p1_n1 import (
    pooled_vectors, source_rgb_unsupported_chroma, load_real_s4_features,
    load_pinned_m0,
)


class R2P1NeuralHelperContracts(unittest.TestCase):
    def setup_fixture(self):
        im = np.full((*SHAPE, 3), 255, np.uint8)
        ids = np.full(SHAPE, -1, np.int32)
        im[120:132, 48:60] = [75, 71, 69]
        ids[120:132, 48:60] = 0
        im[120:132, 62:74] = [75, 71, 69]
        ids[120:132, 62:74] = 1
        im[123:125, 60:62] = [75, 71, 69]
        ids[123:125, 60:62] = 2
        coarse = np.zeros(SHAPE, np.int32)
        protected = np.zeros(SHAPE, bool)
        return im, ids, coarse, protected

    def test_zero_bonus_matches_exact_math_control(self):
        rgb, ids, coarse, prot = self.setup_fixture()
        m0, r0 = merge_one_pass(rgb, ids, coarse, prot)
        no_bonus, r1 = merge_one_pass(rgb, ids, coarse, prot,
                                       score_adjustment=lambda *args: 0)
        np.testing.assert_array_equal(m0, no_bonus)
        self.assertEqual(r0['accepted'], r1['accepted'])

    def test_neural_bonus_can_only_reorder_eligible_neighbor(self):
        rgb, ids, coarse, prot = self.setup_fixture()
        base, info_base = merge_one_pass(rgb, ids, coarse, prot)
        calls = []
        def neural(src, dst, de, contacts, extra):
            calls.append((src['id'],dst['id']))
            return -4 if dst['id'] == 1 else 0
        result, info = merge_one_pass(rgb, ids, coarse, prot, score_adjustment=neural)
        self.assertEqual(int(base[123, 60]), 0)
        self.assertEqual(int(result[123, 60]), 1)
        self.assertEqual(info_base['changed_pixels'], info['changed_pixels'])
        self.assertEqual(info['merged_regions'], 1)
        self.assertEqual(set(calls), {(2,0), (2,1)})

    def test_forbidden_pink_does_not_become_merge_candidate(self):
        rgb, ids, coarse, prot = self.setup_fixture()
        rgb[123:125, 60:62] = [235, 35, 130]
        called=[]
        out, info = merge_one_pass(rgb, ids, coarse, prot,
              score_adjustment=lambda *args: called.append(1) or -1000)
        np.testing.assert_array_equal(out, ids)
        self.assertEqual(called, [], 'neural score must not run on disallowed joins')
        self.assertEqual(info['merged_regions'], 0)

    def test_protected_eye_blocks_neural_override(self):
        rgb, ids, coarse, prot = self.setup_fixture()
        prot[123, 60] = True
        out, info = merge_one_pass(rgb, ids, coarse, prot,
              score_adjustment=lambda *args: -100000)
        np.testing.assert_array_equal(out, ids)
        self.assertEqual(info['merged_regions'], 0)

    def test_neural_nan_score_fails_closed(self):
        rgb, ids, coarse, prot = self.setup_fixture()
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1_INVALID_NEURAL_SCORE'):
            merge_one_pass(rgb, ids, coarse, prot, score_adjustment=lambda *args: np.nan)

    def test_repool_uses_new_r2_ids_not_s4_468(self):
        rgb, ids, coarse, prot = self.setup_fixture()
        vec = np.zeros(384,np.float32); vec[10] = 1.0
        field = np.broadcast_to(vec,(*SHAPE,384))
        result = pooled_vectors(field, ids)
        self.assertEqual(result.shape, (3,384))
        np.testing.assert_allclose(result[:,10], [1,1,1],atol=1e-8)
        self.assertTrue(np.allclose(np.linalg.norm(result,axis=1),1))

    def test_feature_bad_shape_or_wrong_dtype_fails_closed(self):
        _, ids, _, _ = self.setup_fixture()
        for wrong in (np.zeros((240,150,383),np.float32),
                      np.zeros((240,150,384),np.float64)):
            with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1_DINO_R2'):
                pooled_vectors(wrong, ids)

    def test_failing_frozen_archive_is_not_synthetic_fallback(self):
        for fn in (load_pinned_m0,load_real_s4_features):
            with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1'):
                fn(Path('/path/that/does/not/exist.zip'))

    def test_true_pink_is_not_an_unsupported_chroma_pixel(self):
        a = np.full((*SHAPE,3),70,np.uint8)
        a[100:103,60:63] = [235,40,140]
        self.assertEqual(source_rgb_unsupported_chroma(a,a),0)
        changed=a.copy()
        changed[105:107,60:62] = [255,0,255]
        self.assertGreater(source_rgb_unsupported_chroma(a,changed),0)

    def test_color_diagnostic_invalid_input_fails_closed(self):
        source=np.zeros((*SHAPE,3),np.uint8)
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1'):
            source_rgb_unsupported_chroma(source,source[:200])


if __name__=='__main__':
    unittest.main()