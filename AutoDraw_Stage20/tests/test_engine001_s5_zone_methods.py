"""Synthetic E2 only, not evidence of Egret visual quality."""
import itertools
import unittest
import numpy as np
from skimage.color import deltaE_ciede2000
import engine001_s5_zone_methods as m

def rgba(rgb):
    return np.concatenate((rgb,np.full((*rgb.shape[:2],1),255,np.uint8)),axis=2)

class Methods(unittest.TestCase):
    def test_neutral_peach_and_hue_guard(self):
        colors=np.array([[238,238,238],[252,210,188],[159,159,159],[255,0,0],[0,255,0],[255,255,255]],np.uint8)
        compat,neutral,_=m.palette_compatibility(colors)
        self.assertTrue(neutral[0] and not neutral[1])
        self.assertFalse(compat[0,1] or compat[1,0])
        self.assertTrue(compat[0,2])
        self.assertFalse(compat[3,4])
        self.assertFalse(compat[0,5])
        np.testing.assert_array_equal(compat,compat.T)

    def test_cn_lookup_and_probability_overlap(self):
        table=np.zeros((32768,11))
        table[:,3]=1
        ix=31+32*26+1024*23
        table[ix]=0;table[ix,5]=1
        table=m.validate_table(table)
        q=m.cn_probabilities(np.array([[252,210,188],[238,238,238]],np.uint8),table)
        self.assertEqual(q.argmax(axis=1).tolist(),[5,3])
        with self.assertRaises(ValueError):
            m.validate_table(np.ones((32768,11)))

    def test_ciede2000_reference(self):
        a=np.array([50,2.6772,-79.7751]);b=np.array([50,0,-82.7485])
        self.assertAlmostEqual(float(deltaE_ciede2000(a,b)),2.0425,places=4)

    def test_rtv_constant_and_mask(self):
        lab=np.full((9,11,3),40.,float)
        mask=np.ones(lab.shape[:2],bool);mask[:,5]=False
        lab[:,5]=999
        out=m.rtv(lab,mask)
        np.testing.assert_allclose(out[mask],lab[mask],atol=1e-5)
        np.testing.assert_allclose(out[~mask],lab[~mask],atol=1e-8)
        np.testing.assert_array_equal(out,m.rtv(lab,mask))

    def test_exact_binary_expansion_against_bruteforce(self):
        labels=np.array([0,1,2],np.int32);alpha=2
        unary=np.array([[2.,6.,1.],[8.,2.,3.],[4.,5.,1.]])
        pair=np.array([[0,1],[1,2],[0,2]],np.int32)
        weight=np.array([4.,3.,2.])
        allowed=np.ones_like(unary,bool);allowed[0,2]=False
        proposal=m.expansion(labels,alpha,unary,allowed,pair,weight)
        candidates=[]
        for moves in itertools.product([False,True],repeat=3):
            q=np.where(moves,alpha,labels)
            if np.all(allowed[np.arange(3),q]):
                candidates.append(m.energy(q,unary,pair,weight))
        self.assertAlmostEqual(m.energy(proposal,unary,pair,weight),min(candidates))

    def test_all_methods_preserve_baseline_compatibility_and_foreground(self):
        target=np.full((15,19,3),[238,238,238],np.uint8)
        target[:,10:]=[252,210,188]
        target[4:9,3]=[205,205,205]
        target[5:8,13]=[247,200,172]
        target[0,:]=255
        original=rgba(target.copy());original[0,:,3]=0
        # Synthetic valid probability table tests method plumbing, not learned model performance.
        table=np.zeros((32768,11));table[:,3]=1
        frozen=target.copy()
        for variant in m.FLAGS:
            with self.subTest(variant=variant):
                one=m.run_variant(original,target,variant,table)
                out=one[0];report=one[4]
                np.testing.assert_array_equal(np.any(out!=255,axis=2),np.any(target!=255,axis=2))
                self.assertEqual(report["neutral_to_chromatic"],0)
                self.assertEqual(report["chromatic_to_neutral"],0)
                np.testing.assert_array_equal(out[one[3]],target[one[3]])
                np.testing.assert_array_equal(target,frozen)
                np.testing.assert_array_equal(out,m.run_variant(original,target,variant,table)[0])
                for name in ("spatial","graph"):
                    if name in one[5]:
                        tr=one[5][name]["energy"]
                        self.assertTrue(all(b<=a+1e-6 for a,b in zip(tr,tr[1:])))

    def test_close_gray_regions_merge_and_white_stays(self):
        target=np.full((13,16,3),[128,128,128],np.uint8)
        target[2:10,4]=[136,136,136]
        target[10,4:10]=[136,136,136]
        target[0,:]=255
        src=rgba(np.full_like(target,132));src[0,:,3]=0
        out,_,_,_,report,_=m.run_variant(src,target,"chroma")
        self.assertEqual(report["after"]["zones"],1)
        self.assertTrue(np.all(out[0]==255))

if __name__=="__main__":
    unittest.main()
