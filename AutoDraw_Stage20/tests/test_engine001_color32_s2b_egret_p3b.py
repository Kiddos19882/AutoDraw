#!/usr/bin/env python3
"""P3b E2: exact immutable P3 route identity, only native brush width changes."""
import unittest

from run_engine001_color32_s2b_egret_p3b import (
    make_width4_replay, canonical_path_sha, FROZEN_ADDITIONAL_PATH_COUNT,
    FROZEN_ADDITIONS_CANONICAL_SHA256, ORIGINAL_WIDTH, REPLAY_WIDTH,
)


def synthetic_routes():
    base=[{
        "strokeId":"icon-0","colorIndex":31,"colorRgb":0x1b1b1b,
        "width":10,"points":[{"x":200.0,"y":70.0},{"x":202.0,"y":73.0}],
    }]
    later=[]
    for i in range(FROZEN_ADDITIONAL_PATH_COUNT):
        later.append({
            "strokeId":f"icon-{i+1}",
            "colorIndex":31 if i%2 else 29,
            "colorRgb":0x1b1b1b if i%2 else 0xfec0af,
            "width":ORIGINAL_WIDTH,
            "points":[{"x":200.0+i%15,"y":40.0+i%13},
                      {"x":204.0+i%15,"y":43.0+i%13}],
        })
    return base,later


class FrozenP3bOnlyWidthTests(unittest.TestCase):
    def test_only_width_change_preserves_original_points_and_color(self):
        p2,extra=synthetic_routes()
        sha=canonical_path_sha(extra)
        combined,info=make_width4_replay(p2,extra,expected_sha=sha)
        self.assertEqual(len(combined),len(p2)+FROZEN_ADDITIONAL_PATH_COUNT)
        self.assertEqual(combined[0],p2[0])
        self.assertEqual(info["only_brush_width_changed_from"],6)
        self.assertEqual(info["only_brush_width_changed_to"],4)
        self.assertTrue(all(s["width"]==REPLAY_WIDTH for s in combined[1:]))
        self.assertEqual([(s["points"],s["colorRgb"],s["colorIndex"],s["strokeId"])
                          for s in combined[1:]],
                         [(s["points"],s["colorRgb"],s["colorIndex"],s["strokeId"])
                          for s in extra])
        self.assertTrue(all(s["width"]==ORIGINAL_WIDTH for s in extra))
        self.assertLessEqual(info["total_strokes_with_original410_V44B_LAST"],3000)
        self.assertLessEqual(info["total_vertices_with_original1792_V44B_LAST_NOT_CHALK"],5900)
        self.assertIsNone(info["exact_game_CHALK"])

    def test_source_replay_sha_and_width_are_fail_closed(self):
        base,extra=synthetic_routes()
        self.assertEqual(len(FROZEN_ADDITIONS_CANONICAL_SHA256),64)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3B_FROZEN_P3_PATH_DRIFT"):
            make_width4_replay(base,extra)
        sha=canonical_path_sha(extra)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3B_FROZEN_ROUTE_CONTRACT"):
            make_width4_replay(base,extra[:-1],
                               expected_sha=canonical_path_sha(extra[:-1]))
        changed=[dict(s) for s in extra]
        changed[0]["width"]=4
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3B_FROZEN_ROUTE_CONTRACT"):
            make_width4_replay(base,changed,
                               expected_sha=canonical_path_sha(changed))
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3B_RESOURCES_OR_DUPLICATE_ID"):
            make_width4_replay([dict(base[0],strokeId="icon-1")],extra,
                               expected_sha=sha)

    def test_no_paths_is_blocked(self):
        base,_=synthetic_routes()
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3B_REPLAY_INPUT"):
            make_width4_replay(base,[])
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3B_REPLAY_INPUT"):
            make_width4_replay([],base)


if __name__=="__main__":
    unittest.main()
