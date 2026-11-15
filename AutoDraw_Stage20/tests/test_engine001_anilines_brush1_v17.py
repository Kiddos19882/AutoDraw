"""ENGINE001 V17 fixed protocol synthetic graph and source guards."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

from run_engine001_anilines_brush1_v17 import (
    trace_graph, simplify, length, run, SOURCE_SHA, ANI_SHA,
)


class AniLinesBrush1V17Tests(unittest.TestCase):
    def test_line_trace_covers_all_edges_once(self):
        sk = np.zeros((320, 200), dtype=bool)
        sk[20, 10:18] = True
        chains, degree, edges = trace_graph(sk)
        self.assertEqual(edges, 7)
        self.assertEqual(len(chains), 1)
        self.assertEqual(len(chains[0]), 8)
        self.assertEqual(sorted(degree.values()).count(1), 2)

    def test_isolated_pixel_no_stroke_edges(self):
        sk = np.zeros((320, 200), dtype=bool)
        sk[10, 10] = True
        chains, degree, edges = trace_graph(sk)
        self.assertEqual(edges, 0)
        self.assertEqual(chains, [])
        self.assertEqual(degree[(10, 10)], 0)

    def test_branch_graph_preserves_edges(self):
        sk = np.zeros((320, 200), dtype=bool)
        sk[20, 10:19] = True
        sk[19, 14] = True
        chains, degrees, edges = trace_graph(sk)
        self.assertGreater(edges, 9)
        self.assertTrue(any(d >= 3 for d in degrees.values()))
        self.assertGreaterEqual(len(chains), 3)

    def test_short_length_and_rdp_simplification(self):
        self.assertEqual(length([(0, 0), (3, 4)]), 5.0)
        self.assertEqual(simplify([(0, 0), (1, 0), (2, 0), (3, 0)]),
                         [(0, 0), (3, 0)])
        sharp = [(0, 0), (2, 2), (4, 0)]
        self.assertEqual(simplify(sharp), sharp)

    def test_wrong_source_or_line_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            fake = p / "original.png"
            output = p / "edge.png"
            Image.fromarray(np.zeros((320, 200, 3), dtype=np.uint8)).save(fake)
            Image.fromarray(np.zeros((320, 200), dtype=np.uint8)).save(output)
            with self.assertRaises(ValueError):
                run(fake, output, p / "results")

    def test_repository_image_is_exact_pinned_original(self):
        import hashlib
        path = Path(__file__).resolve().parents[1]/"testImages"/"wV6VeZI9S1Y.png"
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), SOURCE_SHA)
        self.assertEqual(path.stat().st_size, 97308)
        self.assertEqual(ANI_SHA,
                         "2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b")


if __name__ == "__main__":
    unittest.main()
