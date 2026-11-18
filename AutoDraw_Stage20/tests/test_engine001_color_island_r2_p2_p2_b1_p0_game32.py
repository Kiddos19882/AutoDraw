#!/usr/bin/env python3
"""B1 source-only synthetic tests; no brush, cost or live quality assertion."""
import unittest
import numpy as np
from skimage import color
from run_engine001_color_island_r2_p2_p2_b1_p0_game32 import (
    CANDIDATES, get_de_table, palette_guard, choose_by_support, spatial_smooth,
    screen, topology)

def palette_fixture():
    p=np.full((32,3),50,dtype=np.uint8)
    p[3]=[255,0,255]
    p[10]=[226,0,133]
    p[15]=[165,1,91]
    p[23]=[80,0,71]
    p[29]=[254,192,175]
    p[30]=[255,255,255]
    p[31]=[27,27,27]
    return p

class TestB1SourceSupport(unittest.TestCase):
    def test_palette_chroma_caps_prevent_invented_magenta_for_neutral(self):
        source=np.full((240,150,3),[60,55,53],dtype=np.uint8)
        p=palette_fixture()
        lab,plab,de=get_de_table(source,p)
        allowed=palette_guard(lab,plab,12)
        out=choose_by_support(de,allowed)
        self.assertTrue(np.all(allowed[np.arange(240)[:,None],np.arange(150)[None,:],out]))
        self.assertFalse(np.any(out==10))
        self.assertFalse(np.any(out==15))
    def test_real_original_magenta_is_not_globally_banned(self):
        p=palette_fixture()
        source=np.full((240,150,3),p[10],dtype=np.uint8)
        lab,plab,de=get_de_table(source,p)
        ids=choose_by_support(de,palette_guard(lab,plab,12))
        self.assertTrue(np.all(ids==10))
    def test_chroma20_is_superset_of_chroma12(self):
        src=np.full((240,150,3),[150,110,85],np.uint8)
        p=palette_fixture()
        lab,plab,_=get_de_table(src,p)
        a=palette_guard(lab,plab,12)
        b=palette_guard(lab,plab,20)
        self.assertTrue(np.all(~a|b))
        with self.assertRaisesRegex(ValueError,"BLOCKED_UNREGISTERED_GUARD"):
            palette_guard(lab,plab,13)
    def test_spatial_is_deterministic_and_protected_labels_immutable(self):
        src=np.full((240,150,3),[60,55,53],np.uint8)
        src[:,75:,:]=[215,196,175]
        lab,_,_=get_de_table(src,palette_fixture())
        de=np.full((240,150,32),12.0,np.float32)
        de[:,:,15]=5.
        de[:,:,31]=4.
        a=np.zeros((240,150,32),bool);a[:,:,15]=True;a[:,:,31]=True
        labels=np.full((240,150),15,np.uint8)
        labels[:,75:]=31
        protected=np.zeros((240,150),bool)
        protected[50:72,30:80]=True
        x=spatial_smooth(labels,de,a,lab,protected)
        y=spatial_smooth(labels,de,a,lab,protected)
        self.assertTrue(np.array_equal(x,y))
        self.assertTrue(np.array_equal(x[protected],labels[protected]))
        self.assertTrue(np.all(a[np.arange(240)[:,None],np.arange(150)[None,:],x]))
    def test_invalid_candidates_fail_closed(self):
        d=np.full((240,150,32),1.,np.float32)
        a=np.zeros(d.shape,bool)
        with self.assertRaisesRegex(ValueError,"BLOCKED_EMPTY_VALID_CHOICES"):
            choose_by_support(d,a)
    def test_game32_quality_gate_cannot_fake_pass_when_color_regresses(self):
        base=dict(mean_deltaE00=5.,p95_deltaE00=18.,
                  excess_chroma_pixels=100,original_fixed_edge_fraction=.7,
                  nonwhite_components4=200,nonwhite_singletons=80,
                  female_face_eyes_mean_deltaE00=8.,male_face_eyes_mean_deltaE00=9.,
                  hands_orange_mean_deltaE00=7.)
        c=dict(base)
        c["excess_chroma_pixels"]=20
        c["female_face_eyes_mean_deltaE00"]=15.
        gates=screen(c,base)
        self.assertTrue(gates["chroma_suspect"])
        self.assertFalse(gates["female_face"])
        self.assertFalse(all(gates.values()))
    def test_topology_counts_disconnected_singletons(self):
        x=np.full((240,150),30,np.uint8)
        x[1,1]=15;x[2,2]=15;x[4:8,5:10]=31
        t=topology(x)
        self.assertEqual(t["nonwhite_components4"],3)
        self.assertEqual(t["nonwhite_singletons"],2)
        self.assertEqual(t["nonwhite_pixels"],22)

if __name__=="__main__":unittest.main()
