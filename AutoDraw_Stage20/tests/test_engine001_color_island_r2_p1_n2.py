"""R2-P1 N2 source-only contract tests; synthetic arrays are unit fixtures, NOT real inference."""
import unittest
from pathlib import Path
import numpy as np
from run_engine001_color_island_r2_p1_m0 import SHAPE, merge_one_pass
from run_engine001_color_island_r2_p1_n2 import (
    load_pinned_biref_alpha, region_alpha_means, pair_ranking_adjustment,
    ALPHA_PENALTY_MAX,
)


class N2BiRefNetMathHelperContracts(unittest.TestCase):
    def fixture(self):
        rgb = np.full((*SHAPE,3),255,np.uint8)
        labels = np.full(SHAPE,-1,np.int32)
        rgb[120:132,48:60] = [75,71,69]; labels[120:132,48:60] = 0
        rgb[120:132,62:74] = [75,71,69]; labels[120:132,62:74] = 1
        rgb[123:125,60:62] = [75,71,69]; labels[123:125,60:62] = 2
        coarse = np.zeros(SHAPE,np.int32)
        protected = np.zeros(SHAPE,bool)
        return rgb,labels,coarse,protected

    def test_frozen_genuine_alpha_has_no_synthetic_fallback(self):
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1_N2_BIREFNET_ZIP_SHA'):
            load_pinned_biref_alpha(Path('/definitely/no/file.zip'))

    def test_alpha_region_means_are_correct(self):
        _, ids, _, _ = self.fixture()
        alpha=np.full(SHAPE,128,np.uint8)
        alpha[ids==0]=0
        alpha[ids==1]=255
        alpha[ids==2]=64
        means=region_alpha_means(alpha,ids)
        np.testing.assert_allclose(means,[0,255,64],atol=1e-12)

    def test_alpha_mismatch_rejected_before_ranking(self):
        _, ids, _, _ = self.fixture()
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1_N2_ALPHA_REGION_ALIGNMENT'):
            region_alpha_means(np.ones((150,240),np.uint8),ids)
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1_N2_ALPHA_REGION_ALIGNMENT'):
            region_alpha_means(np.ones(SHAPE,np.float32),ids)

    def test_pure_dino_control_and_zero_alpha_penalty_agree(self):
        vec=np.zeros((3,384),np.float64); vec[:,0]=1
        a=pair_ranking_adjustment(vec,0,2,None)
        b=pair_ranking_adjustment(vec,0,2,np.array([160.,160.,160.]))
        self.assertAlmostEqual(a[0],b[0])
        self.assertAlmostEqual(b[3],0)
        self.assertAlmostEqual(a[2],4)

    def test_birefnet_disagreement_can_only_penalize_not_enable(self):
        vec=np.zeros((3,384),np.float64);vec[:,0]=1
        b=pair_ranking_adjustment(vec,0,2,np.array([0.,255.,255.]))
        self.assertAlmostEqual(b[3],ALPHA_PENALTY_MAX)
        self.assertAlmostEqual(b[0],-2.)
        no_alpha=pair_ranking_adjustment(vec,0,2,None)
        self.assertAlmostEqual(no_alpha[0],-4.)

    def test_neural_hint_never_bypasses_original_protected_pixel(self):
        rgb,ids,coarse,protected=self.fixture()
        protected[123,60]=True
        calls=[]
        def helper(*x):
            calls.append(x)
            return -1000.
        merged,stats=merge_one_pass(rgb,ids,coarse,protected,score_adjustment=helper)
        np.testing.assert_array_equal(merged,ids)
        self.assertEqual(calls,[])
        self.assertEqual(stats['merged_regions'],0)

    def test_false_pink_source_cannot_be_merged_by_alpha_or_dino(self):
        rgb,ids,coarse,protected=self.fixture()
        rgb[123:125,60:62]=[235,35,130]
        out,stats=merge_one_pass(rgb,ids,coarse,protected,score_adjustment=lambda *x:-1000.)
        np.testing.assert_array_equal(out,ids)
        self.assertEqual(stats['merged_regions'],0)

    def test_birefnet_alpha_can_switch_between_source_eligible_neighbors(self):
        rgb,ids,coarse,protected=self.fixture()
        alpha=np.full(SHAPE,128,np.uint8)
        alpha[ids==0]=0
        alpha[ids==1]=255
        alpha[ids==2]=255
        means=region_alpha_means(alpha,ids)
        vectors=np.zeros((3,384),np.float64)
        vectors[:,0]=1
        m1,_=merge_one_pass(rgb,ids,coarse,protected,
               score_adjustment=lambda src,dst,*rest:pair_ranking_adjustment(vectors,src['id'],dst['id'])[0])
        m2,_=merge_one_pass(rgb,ids,coarse,protected,
               score_adjustment=lambda src,dst,*rest:pair_ranking_adjustment(vectors,src['id'],dst['id'],means)[0])
        self.assertEqual(int(m1[123,60]),0)
        self.assertEqual(int(m2[123,60]),1)

    def test_corrupt_neural_alpha_means_fail_closed(self):
        v=np.zeros((3,384),np.float64);v[:,0]=1
        for invalid in (np.array([1.,2.]),np.array([0.,float('nan'),2.]),np.array([0.,-1.,255.])):
            with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P1_N2_ALPHA_MEANS_INVALID'):
                pair_ranking_adjustment(v,0,1,invalid)


if __name__=='__main__':
    unittest.main()
