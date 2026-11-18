"""R2-P2-P1 M1 numerical and safety contracts (synthetic MODEL_ONLY fixtures)."""
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
import numpy as np
from PIL import Image
from skimage import color
from run_engine001_color_island_r2_p2_p1_m1 import (
    SHAPE, MEDOID_TIE_EPSILON_SQUARED_LAB, stable_region_stats,
    render_stable_source_medoids, source_sobel_fixed_threshold,
    fixed_edge_overlap, merge_one_pass_m1, load_pinned_p1_m0,
    source_chroma_excess,
)


class StableM1SourceContracts(unittest.TestCase):
    def blank(self):
        return np.full((*SHAPE, 3), 255, np.uint8), np.full(SHAPE, -1, np.int32)

    def test_stable_tie_selects_first_row_major_original_pixel(self):
        rgb, labels = self.blank()
        labels[100, 65:67] = 0
        rgb[100, 65] = [70, 71, 69]
        rgb[100, 66] = [72, 73, 71]
        result = stable_region_stats(rgb, labels)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['original_medoid_linear_index'], 100*150+65)
        self.assertTrue(np.array_equal(result[0]['rgb_medoid'], rgb[100, 65]))
        self.assertEqual(result[0]['tie_candidates'], 2)
        self.assertEqual(MEDOID_TIE_EPSILON_SQUARED_LAB, 1e-9)

    def test_original_member_medoid_not_artificial_average(self):
        rgb, ids = self.blank()
        rgb[120,40:43]=[[25,25,25],[45,45,45],[50,50,50]]
        ids[120,40:43]=0
        member_rgb={tuple(x) for x in rgb[120,40:43]}
        medoid=stable_region_stats(rgb,ids)[0]['rgb_medoid']
        self.assertIn(tuple(medoid),member_rgb)
        self.assertNotEqual(tuple(medoid),(40,40,40))

    def test_identical_bytes_and_row_major_perturbation_reproducible(self):
        rgb, labels=self.blank()
        rgb[102:109,71:77]=[45,80,119]
        labels[102:109,71:77]=0
        rgb[103,72]=[55,90,129]
        bg=labels==-1
        a=render_stable_source_medoids(rgb,labels,bg)
        b=render_stable_source_medoids(np.array(rgb,order='C',copy=True),
             np.array(labels,order='C',copy=True),bg.copy())
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(a[bg],rgb[bg])

    def test_existing_true_small_pink_is_not_replaced_with_dark(self):
        rgb, labels=self.blank()
        rgb[110:112,61:63]=[226,37,125]
        labels[110:112,61:63]=0
        image=render_stable_source_medoids(rgb,labels,labels==-1)
        np.testing.assert_array_equal(image[110:112,61:63],rgb[110:112,61:63])

    def test_fake_pink_cannot_be_created_from_dark_source(self):
        rgb,labels=self.blank()
        rgb[123:129,55:64]=[69,58,53]
        labels[123:129,55:64]=0
        image=render_stable_source_medoids(rgb,labels,labels==-1)
        self.assertEqual(int(np.count_nonzero((image[:,:,0]>150)&(image[:,:,2]>100)&(image[:,:,1]<90))),0)

    def test_protected_eye_prevents_merge(self):
        rgb,ids=self.blank()
        rgb[110:121,45:55]=[75,72,70]
        ids[110:121,45:55]=0
        rgb[114:116,55:57]=[75,72,70]
        ids[114:116,55:57]=1
        coarse=np.zeros(SHAPE,np.int32)
        protected=np.zeros(SHAPE,bool)
        protected[114,55]=True
        new,metadata=merge_one_pass_m1(rgb,ids,coarse,protected)
        np.testing.assert_array_equal(new,ids)
        self.assertTrue(metadata['protected_unchanged'])

    def test_reject_background_and_preserve_narrow_lines(self):
        rgb,ids=self.blank()
        for i in range(6):
            rgb[110+i,40+i]=[45,43,41]
            ids[110+i,40+i]=i
        coarse=np.zeros(SHAPE,np.int32)
        protected=np.zeros(SHAPE,bool)
        protected[ids>=0]=True
        res,_=merge_one_pass_m1(rgb,ids,coarse,protected)
        np.testing.assert_array_equal(res,ids)

    def test_invalid_source_or_labels_fail_closed(self):
        rgb,ids=self.blank()
        with self.assertRaisesRegex(ValueError, 'BLOCKED_R2_P2'):
            stable_region_stats(rgb[:200],ids)
        with self.assertRaisesRegex(ValueError, 'BLOCKED_R2_P2'):
            stable_region_stats(rgb,ids.astype(np.uint8))
        with self.assertRaisesRegex(ValueError, 'BLOCKED_R2_P2'):
            render_stable_source_medoids(rgb,ids,np.zeros(SHAPE,bool))

    def test_fixed_edge_threshold_comes_only_from_source(self):
        rgb,_=self.blank()
        rgb[50:150,30:100]=[10,15,20]
        edges,threshold=source_sobel_fixed_threshold(rgb)
        before,a=fixed_edge_overlap(edges,threshold,rgb)
        # Same scale threshold is used for both versions, independent of their distribution.
        modified=rgb.copy()
        modified[170:190,10:40]=[190,190,190]
        after,b=fixed_edge_overlap(edges,threshold,modified)
        self.assertAlmostEqual(before['fixed_source_sobel90_threshold'],threshold)
        self.assertAlmostEqual(after['fixed_source_sobel90_threshold'],threshold)
        self.assertGreater(int(edges.sum()),0)
        self.assertGreaterEqual(int(a.sum()),int((edges&a).sum()))

    def test_fixed_edge_bad_input_fails_closed(self):
        rgb,_=self.blank()
        edges=np.zeros(SHAPE,bool)
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P2'):
            fixed_edge_overlap(edges,float('nan'),rgb)
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P2'):
            source_sobel_fixed_threshold(np.zeros((*SHAPE,3),np.uint8))

    def test_chroma_identity_never_false_flags_real_small_pink(self):
        rgb,_=self.blank()
        rgb[50:53,20:23]=[244,25,129]
        self.assertEqual(source_chroma_excess(rgb,rgb.copy()),0)

    def test_missing_pinned_M0_archive_blocks_instead_of_fallback(self):
        with self.assertRaisesRegex(ValueError,'BLOCKED_R2_P2'):
            load_pinned_p1_m0(Path('/no/such/frozen-m0.zip'))


if __name__=='__main__':
    unittest.main()
