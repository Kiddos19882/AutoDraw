#!/usr/bin/env python3
"""BPRED-S0 synthetic E2 only; NEVER equate synthetic zip with native Egret."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import run_engine001_bpred_s0_corpus_audit as b


class BpredS0Unit(unittest.TestCase):
    def test_01_future_exact_counts_and_unique(self):
        v = b.future_manifest()
        self.assertEqual((len(v["calibration"]), len(v["blind_holdout"]), len(v["controls"])),
                         (120, 120, 11))
        self.assertEqual(len({s["sample_id"] for x in
                              ("calibration", "blind_holdout", "controls")
                              for s in v[x]}), 251)

    def test_02_family_split_no_leakage(self):
        v = b.future_manifest()
        self.assertFalse({s["family_id"] for s in v["calibration"]} &
                         {s["family_id"] for s in v["blind_holdout"]})
        self.assertEqual({s["angle_deg"] % 180 for s in v["blind_holdout"]},
                         {38, 121, 97})

    def test_03_replays_byte_exact_plan(self):
        v = b.future_manifest()
        blind = {s["sample_id"]: s for s in v["blind_holdout"]}
        for s in v["controls"][:-1]:
            parent = blind[s["parent_sample_id"]]
            self.assertEqual(s["plan_sha256"], parent["plan_sha256"])
            self.assertEqual(s["strokes"], parent["strokes"])

    def test_04_blank_and_no_fake_native(self):
        v = b.future_manifest()
        self.assertEqual(v["controls"][-1]["strokes"], [])
        for s in v["calibration"] + v["blind_holdout"] + v["controls"]:
            self.assertIsNone(s["native_png_sha256"])
            self.assertEqual(s["capture_status"], "NOT_RUN")

    def test_05_all_strokes_real_width_owner_coords(self):
        v = b.future_manifest()
        for s in v["calibration"] + v["blind_holdout"]:
            self.assertEqual(len(s["strokes"]), 3)
            for st in s["strokes"]:
                self.assertIn(st["width"], range(1, 11))
                self.assertEqual(st["colorRgb"], 0x503D35)
                self.assertEqual(st["colorIndex"], 1)
                for p in st["points"]:
                    self.assertGreater(p["x"], 0)
                    self.assertLess(p["x"], 460)
                    self.assertGreater(p["y"], 0)
                    self.assertLess(p["y"], 240)

    def test_06_xy_phases_are_not_equal(self):
        v = b.future_manifest()
        for s in v["calibration"]:
            self.assertNotEqual(s["phase_x"], s["phase_y"])

    def test_07_repeatability_sha_deterministic(self):
        a = b.future_manifest()
        self.assertEqual(b.sha256(b.canonical_json(a)),
                         b.sha256(b.canonical_json(b.future_manifest())))

    def test_08_mutated_plan_blocked(self):
        x = b.future_manifest()
        x["calibration"][0]["strokes"][0]["points"][0]["x"] += 0.1
        with self.assertRaisesRegex(ValueError, "BLOCKED_BPRED_S0_MUTATED_PLAN"):
            b.validate_future_manifest(x)

    def test_09_family_leakage_blocked(self):
        x = b.future_manifest()
        x["blind_holdout"][0]["family_id"] = x["calibration"][0]["family_id"]
        with self.assertRaisesRegex(ValueError, "BLOCKED_BPRED_S0_FAMILY_LEAKAGE"):
            b.validate_future_manifest(x)

    def test_10_replay_drift_blocked(self):
        x = b.future_manifest()
        x["controls"][0]["plan_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "BLOCKED_BPRED_S0_REPLAY_DRIFT"):
            b.validate_future_manifest(x)

    def test_11_bad_members_blocked(self):
        for name in ("../escape.json", "/root/file", "a\\b.png", "./foo"):
            with self.assertRaisesRegex(ValueError, "BLOCKED_BPRED_S0"):
                b.clean_member(name)

    def make_fixture(self, directory, *, mismatch=False, extra=False, bad_provenance=False):
        source = ("P4D3", 1, 2, "fixture", "c" * 40, 1,
                  "pinned_engine_git_blob", "pinned_renderer_git_blob")
        plan = b"x"
        raw = b"\x89PNG\r\n\x1a\nSYNTHETIC_NOT_NATIVE"
        report = {
            "experiment": "ENGINE001_B1R_P4D3_FIXTURE",
            "github_sha": "0" * 40 if bad_provenance else "c" * 40,
            "github_run_id": "1",
            "pinned_engine_git_blob": b.GAME_BLOB,
            "pinned_renderer_git_blob": b.RENDERER_BLOB,
            "members_sha256": {
                "A_REAL_NATIVE.png": b.sha256(b"other" if mismatch else raw),
                "A_PLAN.json": b.sha256(plan)
            }
        }
        path = directory / "fixture.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("A_REAL_NATIVE.png", raw)
            z.writestr("A_PLAN.json", plan)
            z.writestr("report.json", json.dumps(report))
            if extra:
                z.writestr("unexpected.txt", "bad")
        return path, source

    def test_12_fixture_zip_sha_crc_honest(self):
        with tempfile.TemporaryDirectory() as d:
            path, src = self.make_fixture(Path(d))
            got = b.audit_zip(path, src)
            self.assertEqual(got["members_verified"], 2)
            self.assertEqual(got["png_files_verified"], 1)
            self.assertEqual(got["crc"], "PASS")

    def test_13_member_sha_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path, src = self.make_fixture(Path(d), mismatch=True)
            with self.assertRaisesRegex(ValueError, "MEMBER_SHA_MISMATCH"):
                b.audit_zip(path, src)

    def test_14_unindexed_member_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path, src = self.make_fixture(Path(d), extra=True)
            with self.assertRaisesRegex(ValueError, "MANIFEST_INCOMPLETE"):
                b.audit_zip(path, src)

    def test_15_wrong_source_commit_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path, src = self.make_fixture(Path(d), bad_provenance=True)
            with self.assertRaisesRegex(ValueError, "REPORT_PROVENANCE"):
                b.audit_zip(path, src)

    def test_16_corrupt_crc_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            path, src = self.make_fixture(Path(d))
            raw = path.read_bytes()
            # Flip a compressed byte in the first file data, leaving the central directory.
            with zipfile.ZipFile(path) as z:
                info = z.infolist()[0]
                ix = info.header_offset + 30 + len(info.filename) + len(info.extra)
            arr = bytearray(raw)
            arr[ix + 4] ^= 0x20
            path.write_bytes(arr)
            with self.assertRaises((ValueError, zipfile.BadZipFile, RuntimeError, OSError)):
                b.audit_zip(path, src)

    def test_17_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            b.save_json_exclusive(p, {"x": 1})
            with self.assertRaises(FileExistsError):
                b.save_json_exclusive(p, {"x": 2})


if __name__ == "__main__":
    unittest.main()
