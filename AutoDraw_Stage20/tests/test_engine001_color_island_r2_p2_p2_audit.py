"""R2-P2-P2-A diagnostic-only contracts; synthetic pixels are not game evidence."""
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from run_engine001_color_island_r2_p2_p2_audit import (
    mismatch_masks, component_audit, exact_swatch_ids, singleton_audit,
    small_region_audit, original_and_archive, sha256, blob_sha,
    SOURCE_SHA, STRUCT4,
)


class SourceRegionVersusG32DiagnosticContracts(unittest.TestCase):
    def pair(self,original,swatch):
        a=np.array([[original]],dtype=np.uint8)
        b=np.array([[swatch]],dtype=np.uint8)
        return mismatch_masks(a,b)

    def fixture(self):
        src=np.full((5,5,3),[70,70,70],dtype=np.uint8)
        ids=np.full((5,5),-1,dtype=np.int32)
        coarse=np.zeros((5,5),dtype=np.int32)
        prot=np.zeros((5,5),dtype=bool)
        game=np.full((5,5),30,dtype=np.int16)
        scores={'chroma':np.zeros((5,5),bool),'union':np.zeros((5,5),bool)}
        return src,ids,coarse,prot,game,scores

    def test_real_pink_source_identical_swatch_has_no_suspect(self):
        result=self.pair([226,0,133],[226,0,133])
        self.assertFalse(result['union'][0,0])
        self.assertFalse(result['chroma'][0,0])

    def test_dark_source_magenta_game_is_source_unsupported(self):
        result=self.pair([68,58,60],[226,0,133])
        self.assertTrue(result['chroma'][0,0])
        self.assertTrue(result['union'][0,0])

    def test_neutral_original_has_no_hue_guard_but_still_chroma_guard(self):
        result=self.pair([95,95,95],[226,0,133])
        self.assertFalse(result['hue'][0,0])
        self.assertFalse(result['hue_guard_active'][0,0])
        self.assertTrue(result['chroma'][0,0])

    def test_identical_white_is_not_automatically_false_background(self):
        result=self.pair([255,255,255],[255,255,255])
        self.assertFalse(result['union'][0,0])

    def test_diagonal_pixels_are_separate_four_connected_components(self):
        mask=np.zeros((5,5),bool)
        mask[1,1]=True;mask[2,2]=True
        audit=component_audit(mask)
        self.assertEqual(audit['components4']['count'],2)
        self.assertEqual(audit['components4']['area_le1'],2)
        self.assertEqual(audit['pixels'],2)
        self.assertEqual(STRUCT4[0,0],0)

    def test_diagnostic_diagonal_only_singleton_never_auto_merge(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0;ids[3,3]=1
        rows,single=singleton_audit(src,ids,coarse,prot,game,scores)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(x['diagonal_only'] for x in rows))
        self.assertTrue(all(not x['safe_merge_upper_bound'] for x in rows))
        self.assertEqual(int(single.sum()),2)

    def test_fully_isolated_source_singleton_has_no_target(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0
        rows,_=singleton_audit(src,ids,coarse,prot,game,scores)
        self.assertTrue(rows[0]['fully_8_isolated'])
        self.assertFalse(rows[0]['safe_merge_upper_bound'])

    def test_unprotected_four_neighbor_with_same_source_color_is_candidate_only(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0;ids[2,3]=1
        rows,_=singleton_audit(src,ids,coarse,prot,game,scores)
        a=next(r for r in rows if r['id']==0)
        self.assertTrue(a['safe_merge_upper_bound'])
        self.assertEqual(a['safe_target_original_region_id'],1)
        self.assertEqual(ids[2,2],0) # No destructive merge

    def test_source_protection_prevents_candidate(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0;ids[2,3]=1;prot[2,2]=True
        rows,_=singleton_audit(src,ids,coarse,prot,game,scores)
        self.assertFalse(next(r for r in rows if r['id']==0)['safe_merge_upper_bound'])
        prot[2,2]=False;prot[2,3]=True
        rows,_=singleton_audit(src,ids,coarse,prot,game,scores)
        self.assertFalse(next(r for r in rows if r['id']==0)['safe_merge_upper_bound'])

    def test_coarse_partition_blocks_neighbor_ceiling(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0;ids[2,3]=1;coarse[2,3]=7
        rows,_=singleton_audit(src,ids,coarse,prot,game,scores)
        self.assertFalse(next(r for r in rows if r['id']==0)['safe_merge_upper_bound'])

    def test_four_neighbor_different_color_blocks_ceiling(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0;ids[2,3]=1;src[2,2]=[40,40,40];src[2,3]=[220,0,170]
        rows,_=singleton_audit(src,ids,coarse,prot,game,scores)
        self.assertFalse(next(r for r in rows if r['id']==0)['safe_merge_upper_bound'])

    def test_small_region_ledger_medoid_is_original_member_and_input_unchanged(self):
        src,ids,coarse,prot,game,scores=self.fixture()
        ids[2,2]=0;ids[2,3]=0;src[2,3]=[71,71,71];prot[2,2]=True
        baseline=src.copy(); rows=small_region_audit(src,ids,prot,coarse)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['area'],2)
        self.assertEqual(rows[0]['protected_source_pixels'],1)
        self.assertIn(tuple(rows[0]['original_member_medoid_rgb']),[(70,70,70),(71,71,71)])
        self.assertTrue(np.array_equal(src,baseline))

    def test_exact_palette_mapping_refuses_unknown_rgb(self):
        p=np.stack((np.arange(32),np.arange(32),np.arange(32)),axis=1).astype(np.uint8)
        pixels=np.array([[[1,1,1],[2,2,2]]],dtype=np.uint8)
        self.assertTrue(np.array_equal(exact_swatch_ids(pixels,p),[[1,2]]))
        pixels[0,1]=[8,3,1]
        with self.assertRaisesRegex(ValueError,'BLOCKED_UNRECOGNIZED_G32_SWATCH'):
            exact_swatch_ids(pixels,p)

    def test_frozen_archive_sha_mismatch_fails_closed(self):
        with patch('run_engine001_color_island_r2_p2_p2_audit.file_sha',side_effect=[SOURCE_SHA,'tampered']):
            with self.assertRaisesRegex(ValueError,'BLOCKED_FROZEN_M1_ZIP_SHA'):
                original_and_archive(Path('source.png'),Path('broken.zip'))

    def test_git_blob_hash_function_correct(self):
        raw=b'example blob'
        import hashlib
        expected=hashlib.sha1(b'blob 12\0'+raw).hexdigest()
        self.assertEqual(blob_sha(raw),expected)
        self.assertEqual(sha256(raw),hashlib.sha256(raw).hexdigest())


if __name__=='__main__':
    unittest.main()
