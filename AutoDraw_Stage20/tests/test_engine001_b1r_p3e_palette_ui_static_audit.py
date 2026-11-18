#!/usr/bin/env python3
"""P3E synthetic original-only static palette UI contract tests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p3e_palette_ui_static_audit as p3e


def fixture_engine():
    rgb = np.asarray([[(n * 3) % 256, (n * 5) % 256, (n * 7) % 256]
                      for n in range(128)], dtype=np.uint8)
    rgb[6] = [255, 255, 255]
    return rgb


def fixture_json(game):
    colors = []
    for i in range(32):
        v = [int(x) for x in game[i]]
        colors.append({"rgb": v,
                       "hex": "#%02X%02X%02X" % tuple(v),
                       "screen_x": i*3, "screen_y": 77})
    return {"colors": colors}


class P3EStaticPaletteContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = fixture_engine()
        cls.sample = fixture_json(cls.game)

    def test_01_id_and_pins(self):
        self.assertEqual(p3e.EXPERIMENT,"ENGINE001_B1R_P3E_ENGINE128_COLOR_UI_AUDIT_V1")
        self.assertEqual(p3e.SCREENSHOT_PALETTE_BLOB,
                         "461b5f3725b9b79888ad36e807b3cf4c9e445e98")
        self.assertEqual(p3e.MAX_MATCHES_PER_TOKEN,3)

    def test_02_synthetic_32_exact_true_engine_indices(self):
        entries = p3e.validate_palette_object(self.sample, self.game)
        self.assertEqual(len(entries),32)
        self.assertEqual([x["engine128_index"] for x in entries],list(range(32)))
        self.assertFalse(any(x["screen_position_executor_validated"] for x in entries))

    def test_03_duplicate_color_rejected(self):
        data = fixture_json(self.game)
        data["colors"][1] = dict(data["colors"][0])
        with self.assertRaisesRegex(ValueError, "INVALID_OR_OUTSIDE_ENGINE"):
            p3e.validate_palette_object(data,self.game)

    def test_04_unsourced_color_rejected(self):
        data = fixture_json(self.game)
        data["colors"][1]["rgb"] = [254,254,252]
        data["colors"][1]["hex"] = "#FEFEFC"
        with self.assertRaisesRegex(ValueError, "INVALID_OR_OUTSIDE_ENGINE"):
            p3e.validate_palette_object(data,self.game)

    def test_05_rgb_and_hex_must_agree(self):
        data = fixture_json(self.game)
        data["colors"][1]["hex"] = "#123456"
        with self.assertRaisesRegex(ValueError, "INVALID_OR_OUTSIDE_ENGINE"):
            p3e.validate_palette_object(data,self.game)

    def test_06_synthetic_31_colors_fails(self):
        data = fixture_json(self.game)
        data["colors"].pop()
        with self.assertRaisesRegex(ValueError, "SHAPE"):
            p3e.validate_palette_object(data,self.game)

    def test_07_invalid_dtype_and_shape_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "SHAPE"):
            p3e.validate_palette_object(self.sample,self.game[:127])
        with self.assertRaisesRegex(ValueError, "SHAPE"):
            p3e.validate_palette_object(self.sample,self.game.astype(np.float32))

    def test_08_git_blob_drift_rejected_before_json(self):
        with self.assertRaisesRegex(ValueError, "BLOB_DRIFT"):
            p3e.validate_screenshot_palette(b'{"colors":[]}', self.game)

    def test_09_contexts_bounded_and_stable(self):
        a="xxx eggColorChangedHandler xx .setColor( x createElaborateEasterEggs"
        result=p3e.token_contexts(a)
        self.assertEqual(result["egg_color_event_handler"]["occurrence_count"],1)
        self.assertEqual(result["board_set_color"]["occurrence_count"],1)
        self.assertEqual(result["extended_palette_gate"]["occurrence_count"],0)
        self.assertLessEqual(len(result["egg_color_event_handler"]["bounded_examples"]),3)

    def test_10_handler_definition_diagnostic_not_E4(self):
        text="q.prototype.eggColorChangedHandler=function(e){this.board.setColor(e)}"
        r=p3e.event_handler_evidence(text)
        self.assertEqual(r["definition_count"],1)
        self.assertTrue(r["setColor_within_handler_E1_possible"])
        self.assertFalse(r["runtime_callback_invocation_observed"])

    def test_11_swatch_sheet_128_grid_stays_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"swatches.png"
            p3e.palette_sheet(self.game,{"#FFFFFF"},path)
            from PIL import Image
            self.assertEqual(Image.open(path).size,(16*82,8*67+32))

    def test_12_fail_closed_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"OUTPUT_EXISTS"):
                p3e.run(Path(directory)/"absent.js",
                        Path(directory)/"absent.json",Path(directory))

if __name__ == "__main__":
    unittest.main()
