"""S5-R6 source-owner Boustrophedon topology and footprint invariants E2."""
import unittest
import numpy as np
import engine001_bpred_s5r6_boustrophedon_cells as r6
from engine001_bpred_s5r2_region_candidates import swept_capsule_pixel_masks, BlockedS5R2


def scene(game, regions=None, dots=()):
    game = np.asarray(game, np.int16)
    h, w = game.shape
    if regions is None:
        regions = np.where(game >= 0, 1, 0).astype(np.int32)
    regions = np.asarray(regions, np.int32)
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[game >= 0, 3] = 255
    protected = np.zeros(game.shape, bool)
    for y, x in dots:
        protected[y, x] = True
    edge = np.zeros(game.shape, bool)
    edge[:, 1:] |= regions[:, 1:] != regions[:, :-1]
    edge[1:, :] |= regions[1:, :] != regions[:-1, :]
    return dict(game_index=game, paintable_id=regions, original_rgba=rgba,
                protected_original_dot=protected, source_edge=edge)


class S5R6CellsTests(unittest.TestCase):
    def check_partition(self, a):
        ids = a['paintable_id']
        opaque = a['original_rgba'][:, :, 3] == 255
        t = r6.decompose(ids, opaque)
        owner = np.zeros_like(ids)
        counts = np.zeros_like(ids, dtype=np.int16)
        for c in t['cells']:
            for y, left, right in c['spans']:
                owner[y, left:right+1] = c['region']
                counts[y, left:right+1] += 1
        self.assertTrue(np.array_equal(owner, ids))
        self.assertTrue(np.all(counts[opaque] == 1))
        self.assertTrue(np.all(counts[~opaque] == 0))
        self.assertEqual(t, r6.decompose(ids, opaque))
        return t

    def check_brush(self, a):
        result = r6.build_candidates(a)
        self.assertFalse(result['smooth'])
        self.assertFalse(result['safe_to_execute'])
        self.assertFalse(result['admissible_for_gameplay'])
        self.assertLessEqual(result['phase_trials']['broad'], 1400)
        self.assertLessEqual(result['phase_trials']['detail'], 600)
        self.assertLessEqual(result['phase_strokes']['broad'], 80)
        self.assertLessEqual(result['phase_strokes']['detail'], 120)
        h, w = a['game_index'].shape
        union = set()
        for s in result['proposals']:
            f = swept_capsule_pixel_masks(s['points'], s['brush_value'], 1., 1., w, h)
            for x, y in f['potential_cells']:
                self.assertEqual(int(a['paintable_id'][y, x]), s['paintable_id'])
                self.assertEqual(int(a['game_index'][y, x]), s['color_index'])
                self.assertEqual(int(a['original_rgba'][y, x, 3]), 255)
            union.update(f['potential_cells'])
        self.assertEqual(len(union), result['potential_covered_pixel_count'])
        self.assertEqual(result, r6.build_candidates(a))
        return result

    def test_rectangle_long_multilane(self):
        a = scene(np.full((44, 140), 5, np.int16), dots=((4, 5),))
        t = self.check_partition(a)
        self.assertEqual(len(t['cells']), 1)
        self.assertEqual(t['split_events'], 0)
        r = self.check_brush(a)
        self.assertGreater(r['topology']['cells_multiple_broad_lanes'], 0)

    def test_donut_has_real_split_and_merge(self):
        m = np.full((50, 85), 5, np.int16)
        m[12:38, 24:61] = -1
        a = scene(m)
        t = self.check_partition(a)
        self.assertGreater(t['split_events'], 0)
        self.assertGreater(t['merge_events'], 0)
        self.check_brush(a)

    def test_branch_neck_alpha_wall(self):
        m = np.full((63, 90), -1, np.int16)
        m[4:57, 39:51] = 5
        m[9:25, 8:82] = 5
        m[34:47, 8:82] = 5
        m[19:22, 44:46] = -1
        a = scene(m)
        t = self.check_partition(a)
        self.assertGreater(t['split_events']+t['merge_events'], 0)
        self.check_brush(a)

    def test_adjacent_same_swatch_different_owner(self):
        m = np.full((35, 70), 6, np.int16)
        ids = np.ones((35, 70), np.int32)
        ids[:, 35:] = 2
        a = scene(m, ids)
        t = self.check_partition(a)
        self.assertEqual(len(t['cells']), 2)
        self.check_brush(a)

    def test_white_details_and_two_other_swatch_regions(self):
        a = scene(np.full((56, 100), 6, np.int16))
        a['game_index'][10:34, 12:39] = 28
        a['paintable_id'][10:34, 12:39] = 2
        a['game_index'][12:34, 56:88] = 36
        a['paintable_id'][12:34, 56:88] = 3
        a['game_index'][18:26, 20:30] = 6
        a['paintable_id'][18:26, 20:30] = 4
        self.check_partition(a)
        self.check_brush(a)

    def test_failclosed_invalid_topology_and_budgets(self):
        a = scene(np.ones((10, 10), np.int16))
        for kw in ({'max_trials': 0}, {'max_trials': True},
                   {'max_strokes': 201}, {'max_strokes': 0}):
            with self.assertRaises(BlockedS5R2):
                r6.build_candidates(a, **kw)
        for bad in (np.zeros((2, 2), bool), None):
            a['source_edge'] = bad
            with self.assertRaises(BlockedS5R2):
                r6.build_candidates(a)
        ids = np.ones((10, 10), np.int32)
        ids[1, 1] = 0
        with self.assertRaises(BlockedS5R2):
            r6.decompose(ids, np.ones((10, 10), bool))


if __name__ == '__main__':
    unittest.main()
