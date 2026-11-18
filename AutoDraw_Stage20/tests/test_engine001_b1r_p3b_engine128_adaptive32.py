#!/usr/bin/env python3
"""ENGINE-001 P3B: source-only deterministic engine128 adaptive32 contracts."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p3b_engine128_adaptive32 as p3b


def fake_engine():
    # 128 valid 24-bit integers; index6 white. Real engine blob checked in CI run.
    numbers = list(range(128))
    numbers[6] = 16777215
    rgb = p3b.parse_engine_palette(
        "o.prototype.createElaborateEasterEggs=function(){"
        "if(0==this._isPainterExtend)return void this.oldCreateElaborateEasterEggs();"
        "var e=[" + ",".join(map(str, numbers)) + "]"
        "};o.prototype.oldCreateElaborateEasterEggs=function(){var e=[" +
        ",".join(map(str, numbers)) + "]"
    )
    return rgb


def synthetic_engine():
    rgb = np.array([
        [i * 2, (i * 7) % 256, (i * 13) % 256]
        for i in range(128)
    ], dtype=np.uint8)
    rgb[p3b.ENGINE_WHITE_INDEX] = [255, 255, 255]
    assert p3b.unique_rgb(rgb) == 128
    return rgb


def synthetic_picture():
    source = np.full(p3b.LOGICAL_SHAPE, 255, dtype=np.uint8)
    source[50:160, 10:125] = (85, 62, 65)
    source[62:100, 30:62] = (245, 204, 191)
    source[86:126, 80:105] = (246, 203, 175)
    source[120:142, 30:115] = (215, 170, 141)
    source[156:220, 12:120] = (244, 235, 227)
    source[40:45, 10:125] = (65, 43, 50)
    target = source.copy()
    target[50:160, 10:125] = [75, 51, 56]
    target[60:100, 30:62] = [239, 203, 183]
    return source, target


class P3BEngine128UnitContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.target = synthetic_picture()
        cls.game = synthetic_engine()

    def test_01_experiment_and_absolute_pins(self):
        self.assertEqual(p3b.EXPERIMENT,
                         "ENGINE001_B1R_P3B_ENGINE128_ADAPTIVE32_V1")
        self.assertEqual(p3b.SOURCE_SHA,
                         "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")
        self.assertEqual(p3b.ENGINE_GIT_BLOB_SHA1,
                         "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388")
        self.assertEqual(p3b.ENGINE_WHITE_INDEX, 6)
        self.assertEqual(p3b.ENGINE_COLOR_COUNT, 128)
        self.assertEqual(p3b.GAME_COLOR_BUDGET, 32)
        self.assertEqual(p3b.METHODS, ("A_BALANCED", "B_FACE_DETAIL"))

    def test_02_parse_exact_engine_method_not_any_color_array(self):
        rgb = fake_engine()
        self.assertEqual(rgb.shape, (128, 3))
        self.assertTrue(np.array_equal(rgb[6], [255, 255, 255]))
        self.assertEqual(p3b.unique_rgb(rgb), 128)
        with self.assertRaisesRegex(ValueError, "CONTEXT_NOT_UNIQUE"):
            p3b.parse_engine_palette("GameConstants.COLORS=[1,2,3]")

    def test_03_wrong_or_duplicate_engine_color_fail_closed(self):
        prefix = ("o.prototype.createElaborateEasterEggs=function(){"
                  "if(0==this._isPainterExtend)return void this.oldCreateElaborateEasterEggs();var e=[")
        old = "o.prototype.oldCreateElaborateEasterEggs=function(){var e=["
        numbers = list(range(128))
        numbers[6] = 16777215
        numbers[7] = numbers[6]
        bad = ",".join(map(str, numbers))
        with self.assertRaisesRegex(ValueError, "SWATCH_DRIFT"):
            p3b.parse_engine_palette(prefix + bad + "];" + old + bad + "]")
        numbers[7] = 7
        numbers[6] = 8
        numbers[8] = 6
        wrong_white = ",".join(map(str, numbers))
        with self.assertRaisesRegex(ValueError, "WHITE_INDEX"):
            p3b.parse_engine_palette(
                prefix + wrong_white + "];" + old + wrong_white + "]"
            )

    def test_04_read_rejects_non_pinned_js_before_parsing(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)/"fake_engine.js"
            tmp.write_text("GameConstants.COLORS=[];", encoding="utf8")
            with self.assertRaisesRegex(ValueError, "ENGINE_BLOB_SHA_OR_SIZE"):
                p3b.read_engine_palette(tmp)

    def test_05_weights_source_edges_faces_and_hands(self):
        a = p3b.selection_weights(self.original, "A_BALANCED")
        b = p3b.selection_weights(self.original, "B_FACE_DETAIL")
        self.assertEqual(a.shape, (240, 150))
        self.assertGreater(float(b.max()), float(a.max()))
        self.assertGreater(float(b.sum()), float(a.sum()))
        with self.assertRaisesRegex(ValueError, "UNKNOWN_SELECTION"):
            p3b.selection_weights(self.original, "G32")

    def test_06_balanced_greedy_32_exact_and_deterministic(self):
        a, ledger, info = p3b.greedy_source_palette(
            self.target, self.original, self.game, "A_BALANCED")
        b, ledger2, info2 = p3b.greedy_source_palette(
            self.target, self.original, self.game, "A_BALANCED")
        self.assertEqual(len(a), 32)
        self.assertEqual(len(set(a.tolist())), 32)
        self.assertEqual(int(a[0]), p3b.ENGINE_WHITE_INDEX)
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(ledger, ledger2)
        self.assertEqual(info, info2)

    def test_07_detail_greedy_32_game_only(self):
        indices, ledger, info = p3b.greedy_source_palette(
            self.target, self.original, self.game, "B_FACE_DETAIL")
        self.assertEqual(indices.dtype, np.int16)
        self.assertTrue(np.all((indices>=0)&(indices<128)))
        self.assertEqual(len(ledger), 32)
        self.assertEqual(info["method"], "B_FACE_DETAIL")

    def test_08_assignment_rgb_exact_palette_and_background_white(self):
        selected, _, _ = p3b.greedy_source_palette(
            self.target, self.original, self.game, "A_BALANCED")
        index, mapped = p3b.assign_engine32(
            self.target, self.original, self.game, selected)
        self.assertEqual(index.shape, (240, 150))
        self.assertEqual(mapped.shape, (240, 150, 3))
        self.assertTrue(np.array_equal(mapped, self.game[index]))
        self.assertTrue(set(np.unique(index)).issubset(set(selected.tolist())))
        white = np.min(self.original, axis=2) >= 245
        self.assertTrue(np.all(index[white] == p3b.ENGINE_WHITE_INDEX))

    def test_09_engine128_diagnostic_not_a_budget32_candidate(self):
        index, mapped = p3b.full_engine128_diagnostic(
            self.target, self.original, self.game)
        self.assertTrue(np.array_equal(mapped, self.game[index]))
        self.assertTrue(np.all(index[np.min(self.original, axis=2)>=245]==6))

    def test_10_unknown_duplicate_out_of_range_selection_rejected(self):
        idx = np.arange(32, dtype=np.int16)
        idx[0] = p3b.ENGINE_WHITE_INDEX
        idx[6] = 0
        a = idx.copy()
        a[1] = a[2]
        with self.assertRaisesRegex(ValueError, "ASSIGNMENT_SHAPE_OR_PALETTE"):
            p3b.assign_engine32(self.target, self.original, self.game, a)
        b = idx.copy()
        b[1] = 129
        with self.assertRaisesRegex(ValueError, "ASSIGNMENT_SHAPE_OR_PALETTE"):
            p3b.assign_engine32(self.target, self.original, self.game, b)

    def test_11_islands_and_metric_evidence_only(self):
        index = np.full((240, 150), 6, dtype=np.uint8)
        index[2, 2] = 42
        island = p3b.connected_color_islands(index)
        self.assertEqual(island["single_pixel_components"], 1)
        self.assertGreaterEqual(island["components4"], 2)
        selected, _, _ = p3b.greedy_source_palette(
            self.target, self.original, self.game, "A_BALANCED")
        ids, rgb = p3b.assign_engine32(
            self.target, self.original, self.game, selected)
        result = p3b.source_quality(self.original, rgb, ids, selected)
        self.assertIn("gates", result)
        self.assertIn("male_face_eye_deltaE00_at_most11", result["gates"])
        self.assertIn(result["status"], {
            "SOURCE_GATE_FAIL",
            "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED",
        })

    def test_12_no_archived_G32_or_V44_input_imports(self):
        tree = ast.parse(Path(p3b.__file__).read_text(encoding="utf8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("run_engine001"):
                    modules.add(node.module)
        self.assertEqual(modules, {
            "run_engine001_b1r_p1_fullrgb_edge_aware",
            "run_engine001_b1r_p2_joint_region_outline",
            "run_engine001_b1r_p2b_residual_ink",
            "run_engine001_b1r_p2c_source_ink_palette",
            "run_engine001_b1r_p2d_background_halo_guard",
        })

    def test_13_output_overwrite_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                p3b.run(Path(t)/"missing_orig.png",
                        Path(t)/"missing_engine.js", Path(t))


if __name__ == "__main__":
    unittest.main()
