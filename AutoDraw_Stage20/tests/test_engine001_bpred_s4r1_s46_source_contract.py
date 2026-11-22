#!/usr/bin/env python3
"""S4.6 source contract E2: deterministic source-only and fail-closed tests."""
import json
import unittest

import numpy as np

import engine001_bpred_s4r1_s46_source_contract as contract


def fixture():
    rgba = np.zeros((1, 3, 4), np.uint8)
    rgba[0, :2, 3] = 255
    rgba[0, 0, :3] = [0, 0, 0]
    rgba[0, 1, :3] = [128, 128, 128]
    game128 = np.zeros((128, 3), np.uint8)
    game128[4, :] = [0, 0, 0]
    game128[5, :] = [128, 128, 128]
    data = dict(
        version=contract.CTR1_VERSION,
        e0_git_blob_sha1="5d0da0694ce0333e9d477fb2fb964329a06763eb",
        source_owner_status="MISSING",
        stroke_admission="FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        provisional_source_quality="DG1_COLOR_ART125_FAIL_NOT_PROMOTED",
        native_renderer="NOT_RUN", game_chalk="NOT_RUN",
        source_to_logical={
            "source_wh": [3, 1], "target_wh": [3, 1],
            "coordinate_system": "image-pixel-edges; NOT desktop/client/Egret calibration",
            "source_to_target_xy": [[1., 0., 0.], [0., 1., 0.]],
            "target_to_source_xy": [[1., 0., 0.], [0., 1., 0.]],
        },
        source_original_alpha=rgba[..., 3].copy(),
        source_atom_id=np.array([[1,2,0]], np.int32),
        surface_id=np.array([[1,2,0]], np.int32),
        paintable_id=np.array([[1,2,0]], np.int32),
        game_index=np.array([[4,5,-1]], np.int16),
        source_edge=np.array([[True, True, False]], bool),
        protected_original_dot=np.array([[False, False, False]], bool),
        preview_rgba=rgba.copy(),
        contour_segments=np.array([
            [1,0,1,1,1,2,4,5,1,0],
            [2,0,2,1,2,0,5,-1,3,0]],np.int32),
        contour_source_lab=np.array([25,0],np.float32),
        adjacency=np.array([[1,2]],np.int32),
        counts={"source_atoms":2, "paintable_components":2},
    )
    return rgba,game128,data


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.rgba, self.game128, self.data = fixture()
        self.args = (b"genuine-original-file-bytes", self.rgba,
                     self.game128, self.data, "testImages/current.png",
                     "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388")

    def test_double_export_bitwise_and_verify(self):
        meta, raw = contract.export_quarantined(*self.args)
        meta2, raw2 = contract.export_quarantined(*self.args)
        self.assertEqual(meta, meta2)
        self.assertEqual(raw, raw2)
        obj = contract.verify_quarantined(meta, raw, self.args[0])
        self.assertFalse(obj["admissible_for_gameplay"])
        self.assertEqual(obj["next_stage_S5"], "BLOCKED")
        self.assertIn("adjacency", obj["array_contract"])

    def test_alpha_silhouette_and_same_swatch_source_detail(self):
        self.data["game_index"][0,1] = 4
        self.data["preview_rgba"][0,1,:3] = self.game128[4]
        self.data["contour_segments"][0,7] = 4
        self.data["contour_segments"][1,6] = 4
        self.data["contour_segments"][0,8] = 2
        self.assertTrue(contract.validate_original_ctr1(
            self.rgba,self.game128,self.data))

    def test_reject_source_owner_promotion(self):
        self.data["source_owner_status"] = "ACCEPTED"
        with self.assertRaisesRegex(ValueError, "NOT_RESEARCH_ONLY"):
            contract.export_quarantined(*self.args)

    def test_reject_false_native_calibration(self):
        self.data["source_to_logical"]["target_wh"] = [100,100]
        with self.assertRaisesRegex(ValueError, "COORDINATE"):
            contract.export_quarantined(*self.args)

    def test_reject_broken_segment_adjacency(self):
        self.data["contour_segments"][0,5] = 100
        with self.assertRaisesRegex(ValueError, "SEGMENT_ATOM"):
            contract.export_quarantined(*self.args)

    def test_reject_weak_fake_line(self):
        self.data["contour_source_lab"][0] = 1.
        with self.assertRaisesRegex(ValueError, "FALSE_SOURCE_BORDER"):
            contract.export_quarantined(*self.args)

    def test_reject_opaque_foreign_swatches(self):
        self.data["game_index"][0,0] = 200
        with self.assertRaises(ValueError):
            contract.export_quarantined(*self.args)

    def test_reject_altered_alpha(self):
        self.data["source_original_alpha"][0,2] = 255
        with self.assertRaisesRegex(ValueError, "ALPHA"):
            contract.export_quarantined(*self.args)

    def test_reject_legacy_candidate_input(self):
        args=list(self.args);args[4]="output/G32_legacy.png"
        with self.assertRaisesRegex(ValueError, "LEGACY"):
            contract.export_quarantined(*args)

    def test_reject_changed_original_or_packet(self):
        meta,raw=contract.export_quarantined(*self.args)
        with self.assertRaisesRegex(ValueError, "PACKET_INPUT_SHA"):
            contract.verify_quarantined(meta,raw,b"other")
        with self.assertRaisesRegex(ValueError, "PACKET_RAW_SHA"):
            contract.verify_quarantined(meta,raw+b"x",self.args[0])

    def test_reject_modified_manifest_admission(self):
        meta,raw=contract.export_quarantined(*self.args)
        m=json.loads(meta);m["admissible_for_gameplay"]=True
        with self.assertRaisesRegex(ValueError, "PACKET_PROMOTION"):
            contract.verify_quarantined(json.dumps(m).encode(),raw,self.args[0])


if __name__ == "__main__":
    unittest.main()
