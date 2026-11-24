"""Source-only A6-Z1 contracts. Native Egret validation is a separate job."""
import unittest
import numpy as np
import engine001_s5_zone_merge as z

DARK = (128,128,128)
LIGHT = (136,136,136)
WHITE = (255,255,255)

def rgba(rgb):
    return np.concatenate((rgb, np.full((*rgb.shape[:2],1),255,np.uint8)),axis=2)

class Zones(unittest.TestCase):
    def test_speckles_and_winding_band_merge_without_shape_template(self):
        original=np.full((21,31,3),132,np.uint8)
        target=np.full_like(original,128)
        target[2:19,5]=LIGHT
        target[18,5:25]=LIGHT
        target[3,18]=LIGHT
        target[8,22]=LIGHT
        before=z.region_counts(target)[0]
        out,_,ids,_,report,ledger=z.consolidate(rgba(original),target,"balanced")
        self.assertGreaterEqual(before["zones"],4)
        self.assertEqual(report["after"]["zones"],1)
        self.assertEqual(int(ids.max()),1)
        self.assertTrue(np.all(out==out[0,0]))
        for s in ledger:
            self.assertLessEqual(s["after"],s["before"]-len(s["merges"]))

    def test_high_contrast_winding_outline_retained(self):
        target=np.full((23,30,3),200,np.uint8)
        target[3:19,5]=25
        target[18,5:24]=25
        target[5:19,23]=25
        for preset in z.PRESETS:
            out,_,_,_,report,_=z.consolidate(rgba(target),target,preset)
            np.testing.assert_array_equal(out,target)
            self.assertEqual(report["after"]["zones"],2)

    def test_diagonal_and_white_do_not_connect(self):
        target=np.full((5,5,3),255,np.uint8)
        target[1,1]=DARK
        target[2,2]=DARK
        target[2,3]=LIGHT
        original=rgba(target)
        original[0,0,3]=0
        out,_,_,_,report,_=z.consolidate(original,target,"strong")
        np.testing.assert_array_equal(np.any(out!=255,axis=2),np.any(target!=255,axis=2))
        self.assertGreaterEqual(report["after"]["zones"],2)
        self.assertEqual(z.region_counts(target)[0]["zones"],3)

    def test_original_contrast_dot_is_protected(self):
        src=np.full((11,11,3),150,np.uint8)
        src[5,5]=0
        target=np.full_like(src,136)
        target[5,5]=128
        out,_,_,protected,_,_=z.consolidate(rgba(src),target,"strong")
        self.assertTrue(protected[5,5])
        np.testing.assert_array_equal(out[5,5],target[5,5])

    def test_deterministic_and_palette_unchanged(self):
        target=np.full((15,15,3),128,np.uint8)
        target[::2,::2]=136
        original=rgba(np.full_like(target,132))
        frozen=target.copy()
        one=z.consolidate(original,target,"strong")
        two=z.consolidate(original,target,"strong")
        np.testing.assert_array_equal(target,frozen)
        np.testing.assert_array_equal(one[0],two[0])
        np.testing.assert_array_equal(one[2],two[2])
        self.assertEqual(one[4:],two[4:])
        colors={tuple(c) for c in target.reshape(-1,3)}
        self.assertTrue(all(tuple(c) in colors for c in one[0].reshape(-1,3)))

    def test_no_size_based_erasure_and_invalid_alpha(self):
        target=np.full((7,7,3),255,np.uint8)
        target[3,3]=DARK
        original=rgba(target)
        out,_,_,_,report,_=z.consolidate(original,target,"strong")
        np.testing.assert_array_equal(out,target)
        self.assertEqual(report["after"]["singleton"],1)
        original[3,3,3]=0
        with self.assertRaises(ValueError):
            z.consolidate(original,target,"balanced")

    def test_empty_foreground(self):
        target=np.full((4,5,3),255,np.uint8)
        out,_,_,_,report,_=z.consolidate(rgba(target),target,"balanced")
        np.testing.assert_array_equal(out,target)
        self.assertEqual(report["after"]["zones"],0)

if __name__ == "__main__":
    unittest.main()
