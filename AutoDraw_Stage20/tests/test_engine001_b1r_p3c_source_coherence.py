#!/usr/bin/env python3
"""P3C synthetic source-protected deterministic island coherence regression."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p3c_source_coherence as p3c
from run_engine001_b1r_p3b_engine128_adaptive32 import ENGINE_WHITE_INDEX

def fixture():
    game = np.asarray([[(i * 3) % 256, (i * 5) % 256, (i * 7) % 256]
                       for i in range(128)], dtype=np.uint8)
    game[6] = (255, 255, 255)
    game[7] = (80, 60, 70)
    game[8] = (215, 180, 160)
    game[9] = (0, 255, 0)
    selected = np.asarray([6, 7, 8, 9] + list(range(10, 38)), dtype=np.int16)
    original = np.tile(game[7].reshape(1, 1, 3), (240, 150, 1))
    idx = np.full((240, 150), 7, np.uint8)
    core = np.zeros(idx.shape, dtype=bool)
    return idx, original, game, selected, core

class P3CContracts(unittest.TestCase):
    def test_01_preregistered_experiment_methods_budget(self):
        self.assertEqual(p3c.EXPERIMENT, "ENGINE001_B1R_P3C_SOURCE_COHERENCE_V1")
        self.assertEqual(set(p3c.METHODS), {"S_STRICT", "T_LOCAL"})
        self.assertEqual(p3c.MAX_CHANGED_PIXELS, 360)
        self.assertEqual(p3c.MAX_COMPONENT_AREA, 3)
        self.assertEqual(p3c.MIN_TINY_REDUCTION, .05)

    def test_02_merge_singleton_only_to_4_neighbor(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25] = 8
        out, ledger = p3c.coherence_pass(
            idx, original, game, selected, core, "S_STRICT")
        self.assertEqual(int(out[15, 25]), 7)
        self.assertEqual(ledger["changed_pixels"], 1)
        self.assertEqual(ledger["accepted_components"], 1)
        self.assertEqual(int(idx[15, 25]), 8)

    def test_03_no_source_unsupported_donor(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25] = 8
        original[15, 25] = game[8]
        out, ledger = p3c.coherence_pass(
            idx, original, game, selected, core, "T_LOCAL")
        self.assertEqual(int(out[15, 25]), 8)
        self.assertEqual(ledger["accepted_components"], 0)

    def test_04_protection_never_recolored(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25] = 8
        core[15, 25] = True
        for method in p3c.METHODS:
            out, ledger = p3c.coherence_pass(
                idx, original, game, selected, core, method)
            self.assertTrue(np.array_equal(idx, out))
            self.assertEqual(ledger["changed_pixels"], 0)

    def test_05_strict_dilates_source_edges_local_does_not(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25] = 8
        core[15, 24] = True
        s, _ = p3c.coherence_pass(idx, original, game, selected, core,
                                   "S_STRICT")
        t, _ = p3c.coherence_pass(idx, original, game, selected, core,
                                   "T_LOCAL")
        self.assertEqual(int(s[15, 25]), 8)
        self.assertEqual(int(t[15, 25]), 7)

    def test_06_bright_white_lock(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25] = ENGINE_WHITE_INDEX
        original[15, 25] = (255, 255, 255)
        for method in p3c.METHODS:
            out, _ = p3c.coherence_pass(idx, original, game,
                                         selected, core, method)
            self.assertEqual(int(out[15, 25]), ENGINE_WHITE_INDEX)
        idx[15, 25] = 7
        with self.assertRaisesRegex(ValueError, "WHITE_LOCK"):
            p3c.coherence_pass(idx, original, game, selected, core, "T_LOCAL")

    def test_07_four_pixel_component_not_targeted(self):
        idx, original, game, selected, core = fixture()
        idx[15:17, 25:27] = 8
        for method in p3c.METHODS:
            out, _ = p3c.coherence_pass(idx, original, game, selected, core,
                                         method)
            self.assertTrue(np.array_equal(out, idx))

    def test_08_three_pixel_component_is_complete(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25:28] = 8
        out, led = p3c.coherence_pass(idx, original, game, selected, core,
                                      "T_LOCAL")
        self.assertTrue(np.all(out[15, 25:28] == 7))
        self.assertEqual(led["changed_pixels"], 3)
        self.assertEqual(led["accepted_components"], 1)

    def test_09_cap_without_partial_components(self):
        idx, original, game, selected, core = fixture()
        for y in range(10, 210, 3):
            for x in range(10, 130, 4):
                idx[y, x] = 8
        out, ledger = p3c.coherence_pass(idx, original, game, selected,
                                          core, "T_LOCAL")
        self.assertEqual(ledger["changed_pixels"], 360)
        self.assertEqual(int(np.count_nonzero(out != idx)), 360)

    def test_10_palette_strict_input_fail_closed(self):
        idx, original, game, selected, core = fixture()
        invalid = selected.copy()
        invalid[5] = 129
        for bad in (invalid, selected[:-1]):
            with self.assertRaisesRegex(ValueError, "INPUT_OR_PALETTE"):
                p3c.coherence_pass(idx, original, game, bad, core, "T_LOCAL")
        with self.assertRaisesRegex(ValueError, "INPUT_OR_PALETTE"):
            p3c.coherence_pass(idx, original, game, selected, core,
                                "UNKNOWN_METHOD")
        with self.assertRaisesRegex(ValueError, "INPUT_OR_PALETTE"):
            p3c.coherence_pass(idx[:-1], original, game, selected, core,
                                "T_LOCAL")

    def test_11_deterministic_no_mutation(self):
        idx, original, game, selected, core = fixture()
        idx[15, 25] = 8
        frozen = idx.copy()
        a, la = p3c.coherence_pass(idx, original, game, selected, core,
                                    "T_LOCAL")
        b, lb = p3c.coherence_pass(idx, original, game, selected, core,
                                    "T_LOCAL")
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(la, lb)
        self.assertTrue(np.array_equal(idx, frozen))

    def test_12_provenance_no_legacy_source_import(self):
        tree = ast.parse(Path(p3c.__file__).read_text(encoding="utf8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertFalse(any("v44" in s.lower() or "g32" in s.lower()
                             for s in imported))
        direct = {name for n in ast.walk(tree) if isinstance(n, ast.Import)
                  for name in (x.name for x in n.names)}
        self.assertIn("run_engine001_b1r_p3b_engine128_adaptive32", direct)
        self.assertIn("run_engine001_b1r_p1_fullrgb_edge_aware", imported)

    def test_13_output_overwrite_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                p3c.run(Path(directory)/"missing.png",
                        Path(directory)/"missing.js", Path(directory))

if __name__ == "__main__":
    unittest.main()
