#!/usr/bin/env python3
"""CTR1 E2 source crack evidence tests: original 4neighbor, alpha, detail."""
import unittest

import numpy as np
from skimage import color

from engine001_bpred_s4r1_ctr1_source_contour import (
    _source_crack_segments, build_ctr1,
    REGION_STRONG_DIFFERENT_SWATCH as COLOR,
    REGION_STRONG_SAME_SWATCH_DETAIL as DETAIL,
    TRUE_ALPHA_SILHOUETTE as SILHOUETTE,
    SEGMENT_FIELDS,
)


def palette():
    p=np.array([(i*37%256,i*61%256,i*103%256) for i in range(128)],np.uint8)
    p[0]=[100,100,100]
    p[1]=[245,245,245]
    assert len(np.unique(p,axis=0)) == 128
    return p


def rgba(h=55,w=70):
    a=np.full((h,w,4),255,np.uint8)
    a[...,:3] = [100,100,100]
    return a


def pieces(image, atoms, swatches, protected=None):
    lab=color.rgb2lab(image[...,:3].astype(np.float64)/255.)
    opaque=image[...,3]==255
    if protected is None:protected=np.zeros(opaque.shape,bool)
    return _source_crack_segments(lab,opaque,atoms,swatches,protected)


class SourceContourCTR1Tests(unittest.TestCase):
    def test_single_highcontrast_source_pixel_four_true_unit_cracks(self):
        a=rgba(9,9);a[4,4,:3]=[245,245,245]
        reg=np.ones((9,9),np.int32);reg[4,4]=2
        colors=np.zeros((9,9),np.int16);colors[4,4]=1
        dots=np.zeros((9,9),bool);dots[4,4]=True
        rows,delta,info=pieces(a,reg,colors,dots)
        self.assertEqual(rows.shape,(4,len(SEGMENT_FIELDS)))
        self.assertTrue(np.all(rows[:,8]==COLOR))
        self.assertTrue(np.all(rows[:,9]==1))
        self.assertEqual(info["protected_dot_true_strong_crack_edges"],4)
        self.assertEqual(info["represented_original_strong_4neighbor_pairs"],4)
        self.assertEqual(info["unrepresented_within_atom_original_strong_pairs"],0)
        self.assertTrue(np.all(delta>=12))
        corners={(int(x),int(y),int(x2),int(y2)) for x,y,x2,y2,*_ in rows}
        self.assertEqual(corners,{(4,4,5,4),(4,5,5,5),(4,4,4,5),(5,4,5,5)})

    def test_vertical_highcontrast_one_pixel_line_two_supported_sides(self):
        a=rgba(17,19);a[2:15,9,:3]=[245,245,245]
        reg=np.ones((17,19),np.int32);reg[2:15,9]=2
        sw=np.zeros((17,19),np.int16);sw[2:15,9]=1
        r,_,s=pieces(a,reg,sw)
        self.assertEqual(s["represented_original_strong_4neighbor_pairs"],28)
        self.assertEqual(s["contour_strong_different_swatch"],28)
        self.assertTrue(np.all(r[:,8]==COLOR))

    def test_strong_real_source_neighbor_same_game_swatch_is_detail_not_black(self):
        a=rgba(12,12)
        a[:,6:,:3]=[245,245,245]
        reg=np.ones((12,12),np.int32);reg[:,6:]=2
        game=np.zeros((12,12),np.int16)
        r,_,s=pieces(a,reg,game)
        self.assertEqual(s["contour_strong_same_swatch_detail"],12)
        self.assertEqual(s["contour_strong_different_swatch"],0)
        self.assertTrue(np.all(r[:,8]==DETAIL))
        self.assertEqual(int(r[:,6].max()),0)
        self.assertEqual(int(r[:,7].max()),0)

    def test_quantization_only_original_weak_boundary_never_outlined(self):
        a=rgba(16,18)
        reg=np.ones((16,18),np.int32);reg[:,9:]=2
        game=np.zeros((16,18),np.int16);game[:,9:]=1
        r,_,s=pieces(a,reg,game)
        self.assertEqual(r.shape[0],0)
        self.assertEqual(s["excluded_weak_quantization_only_pairs"],16)
        self.assertEqual(s["source_original_strong_4neighbor_pairs"],0)

    def test_internal_alpha_walls_both_full_transparency_and_partial(self):
        a=rgba(20,24);a[4:9,5:12,3]=0
        a[12:15,15:21,3]=128
        opaque=a[...,3]==255
        reg=opaque.astype(np.int32)
        game=np.where(opaque,0,-1).astype(np.int16)
        r,delta,s=pieces(a,reg,game)
        self.assertEqual(s["contour_alpha_silhouette"],2*(5+7)+2*(3+6))
        self.assertTrue(np.all(r[:,8]==SILHOUETTE))
        self.assertTrue(np.all((r[:,4]>0) != (r[:,5]>0)))
        self.assertTrue(np.all((r[:,6]>=0) != (r[:,7]>=0)))
        self.assertTrue(np.all(delta==0))

    def test_no_false_crop_image_border_for_opaque_original(self):
        a=rgba(7,9)
        r,_,s=pieces(a,np.ones((7,9),np.int32),
                     np.zeros((7,9),np.int16))
        self.assertEqual(len(r),0)
        self.assertEqual(s["original_alpha_wall_pairs"],0)

    def test_unrepresented_original_strong_within_atom_is_explicit_unknown(self):
        a=rgba(8,10);a[:,5:,:3]=[245,245,245]
        r,_,s=pieces(a,np.ones((8,10),np.int32),
                     np.zeros((8,10),np.int16))
        self.assertEqual(len(r),0)
        self.assertEqual(s["source_original_strong_4neighbor_pairs"],8)
        self.assertEqual(s["unrepresented_within_atom_original_strong_pairs"],8)
        self.assertEqual(s["represented_original_strong_4neighbor_pairs"],0)

    def test_every_unit_segment_maps_to_source_grid_not_css(self):
        a=rgba(15,12);a[3:11,4:8,:3]=[245,245,245]
        reg=np.ones((15,12),np.int32);reg[3:11,4:8]=2
        sw=np.zeros((15,12),np.int16);sw[3:11,4:8]=1
        r,_,_=pieces(a,reg,sw)
        self.assertGreater(len(r),0)
        self.assertTrue(np.all(r[:,0]>=0))
        self.assertTrue(np.all(r[:,2]<=12))
        self.assertTrue(np.all(r[:,1]>=0))
        self.assertTrue(np.all(r[:,3]<=15))
        self.assertTrue(np.all(np.abs(r[:,0]-r[:,2])+np.abs(r[:,1]-r[:,3])==1))
        self.assertTrue(np.all((r[:,0]==r[:,2]) | (r[:,1]==r[:,3])))

    def test_end_to_end_original_only_dot_and_line_regenerated_no_overlay(self):
        a=rgba(67,79)
        a[12,10,:3]=[245,245,245]
        a[5:59,42,:3]=[245,245,245]
        source=a.copy()
        r=build_ctr1(a,palette())
        self.assertTrue(np.array_equal(a,source))
        self.assertTrue(bool(r["protected_original_dot"][12,10]))
        self.assertGreaterEqual(r["contour_summary"]["protected_dot_true_strong_crack_edges"],4)
        self.assertGreater(r["contour_summary"]["contour_strong_different_swatch"],0)
        self.assertEqual(r["source_owner_status"],"MISSING")
        self.assertEqual(r["stroke_admission"],
                         "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE")
        self.assertEqual(r["provisional_source_quality"],
                         "DG1_COLOR_ART125_FAIL_NOT_PROMOTED")
        self.assertEqual(r["native_renderer"],"NOT_RUN")
        self.assertEqual(r["game_chalk"],"NOT_RUN")

    def test_end_to_end_alpha_wall_from_current_original_only(self):
        a=rgba(57,65)
        a[12:23,8:19,3]=0
        a[27:38,31:40,3]=127
        r=build_ctr1(a,palette())
        self.assertGreater(r["contour_summary"]["contour_alpha_silhouette"],0)
        self.assertTrue(np.all(r["game_index"][a[...,3]!=255]==-1))
        self.assertTrue(np.all(r["source_atom_id"][a[...,3]!=255]==0))
        self.assertTrue(np.array_equal(r["source_original_alpha"],a[...,3]))

    def test_4neighbor_cracks_repeat_byte_identical_source_outputs(self):
        a=rgba()
        a[16:42,22:48,:3]=[245,245,245]
        a[12,14,:3]=[245,245,245]
        p=palette()
        first=build_ctr1(a,p);second=build_ctr1(a,p)
        for key in ("source_atom_id","surface_id","protected_original_dot",
                    "game_index","paintable_id","contour_segments",
                    "contour_source_lab","preview_rgba"):
            self.assertTrue(np.array_equal(first[key],second[key]),key)
        self.assertEqual(first["contour_summary"],second["contour_summary"])

    def test_reject_invalid_source_palette_and_nonopaque_region(self):
        a=rgba()
        for image, pal in ((a[...,:3],palette()),
                           (a,palette()[:127]),
                           (a,np.zeros((128,3),np.uint8))):
            with self.assertRaises(ValueError):
                build_ctr1(image,pal)
        lab=np.zeros((*a.shape[:2],3))
        atoms=np.ones(a.shape[:2],np.int32)
        game=np.full(a.shape[:2],-1,np.int16)
        with self.assertRaises(ValueError):
            _source_crack_segments(lab,np.ones(a.shape[:2],bool),
                                   atoms,game,np.zeros(a.shape[:2],bool))

    def test_all_transparent_source_no_unit_segments(self):
        a=rgba();a[...,3]=0
        r=build_ctr1(a,palette())
        self.assertEqual(len(r["contour_segments"]),0)
        self.assertEqual(r["contour_summary"]["original_alpha_wall_pairs"],0)
        self.assertTrue(np.all(r["game_index"]==-1))
        self.assertTrue(np.all(r["source_atom_id"]==0))


if __name__=="__main__":
    unittest.main()
