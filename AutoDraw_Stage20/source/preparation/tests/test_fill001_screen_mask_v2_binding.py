from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from chalk_fill_matrix import FillMatrixError
from fill001_screen_mask_v2_binding import bind_from_monitor_run


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()


class TestV2Binding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_path = Path(self.tmp.name) / "run.json"
        self.evidence_path = Path(self.tmp.name) / "e4.json"
        corners = {
            "topLeft": {"x": 497.96, "y": 104.86},
            "topRight": {"x": 1170.1, "y": 104.86},
            "bottomRight": {"x": 1170.1, "y": 456.06},
            "bottomLeft": {"x": 497.96, "y": 456.06},
        }
        self.geom = {
            "boardLogicalSize": {"width": 460, "height": 240},
            "renderMode": "webgl",
            "players": [{
                "boardClientMappingMethod": "validated_axis_aligned_rect",
                "boardClientCorners": corners,
            }],
        }
        self.run = {
            "run_id": "run-a", "session_id": "session-a",
            "renderer_geometry_at_start": self.geom,
            "renderer_geometry_at_end": self.geom,
            "renderer_geometry_updates": [],
            "events": [{
                "type": "MOUSE_MOVE_SAMPLE",
                "source": "window-bubble-after-egret-canvas",
                "clientX": 510 + i, "clientY": 300 + i,
                "screenX": 510 + i, "screenY": 463 + i,
            } for i in range(30)],
        }
        self.evidence = {
            "run_id": "run-a", "session_id": "session-a",
            "status": "PASS_E4_RAW_CAPTURE",
            "monitor_version": "0.2.4",
            "geometry_at_start_sha256": digest(self.geom),
            "mouse_move_count": 30,
            "screen_roi": {"x": 496, "y": 265, "width": 674, "height": 355},
        }

    def write(self):
        self.run_path.write_text(json.dumps(self.run), encoding="utf-8")
        self.evidence["raw_run_sha256"] = hashlib.sha256(
            self.run_path.read_bytes()).hexdigest()
        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")

    def bind(self):
        self.write()
        return bind_from_monitor_run(self.run_path, self.evidence_path)

    def test_exact_mouse_offset_builds_run_bound_geometry(self):
        binding = self.bind()
        p = binding["provenance"]
        self.assertEqual(p["mouse_sample_count"], 30)
        self.assertEqual(p["client_screen_offset_y"], 163.0)
        self.assertEqual(p["max_offset_residual_px"], 0.0)
        self.assertAlmostEqual(binding["geometry"]["board_screen_corners"]["top"], 267.86)
        self.assertTrue(binding["geometry"]["independent_screen_mapping"])

    def test_reject_changed_geometry_even_if_e4_audit_is_rehashed(self):
        self.run["renderer_geometry_at_end"] = dict(self.geom, renderMode="canvas")
        with self.assertRaises(FillMatrixError):
            self.bind()

    def test_reject_inconsistent_screen_offset(self):
        self.run["events"][7]["screenY"] += 2
        with self.assertRaises(FillMatrixError):
            self.bind()

    def test_reject_missing_mouse_samples(self):
        self.run["events"] = self.run["events"][:10]
        self.evidence["mouse_move_count"] = 10
        with self.assertRaises(FillMatrixError):
            self.bind()

    def test_reject_untrusted_status_or_session(self):
        self.evidence["status"] = "PARTIAL"
        with self.assertRaises(FillMatrixError):
            self.bind()
        self.evidence["status"] = "PASS_E4_RAW_CAPTURE"
        self.evidence["session_id"] = "foreign"
        with self.assertRaises(FillMatrixError):
            self.bind()

    def test_reject_missing_source_and_bad_client_corners(self):
        self.run["events"][0]["source"] = "unknown"
        with self.assertRaises(FillMatrixError):
            self.bind()
        self.run["events"][0]["source"] = "window-bubble-after-egret-canvas"
        self.geom["players"][0]["boardClientCorners"]["bottomLeft"]["x"] = 590
        with self.assertRaises(FillMatrixError):
            self.bind()

    def test_exact_original_crlf_reconstruction_is_accepted(self):
        self.write()
        checked_out = self.run_path.read_bytes()
        reconstructed = checked_out.replace(b"\\n", b"\\r\\n")
        self.evidence["raw_run_sha256"] = hashlib.sha256(reconstructed).hexdigest()
        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")
        binding = bind_from_monitor_run(self.run_path, self.evidence_path)
        self.assertEqual(binding["provenance"]["raw_run_sha256"],
                         self.evidence["raw_run_sha256"])
        self.assertEqual(binding["provenance"]["byte_reconstruction"],
                         "git_normalized_LF_to_original_CRLF")

    def test_wrong_original_hash_still_fails(self):
        self.write()
        self.evidence["raw_run_sha256"] = "f" * 64
        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")
        with self.assertRaises(FillMatrixError):
            bind_from_monitor_run(self.run_path, self.evidence_path)

    def test_reject_tampered_raw_file(self):
        self.write()
        self.run_path.write_bytes(self.run_path.read_bytes() + b" ")
        with self.assertRaises(FillMatrixError):
            bind_from_monitor_run(self.run_path, self.evidence_path)


if __name__ == "__main__":
    unittest.main()
