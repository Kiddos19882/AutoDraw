import unittest

import numpy as np

from engine001_s5_palette import SIZES, paintable_regions, select_swatches


class ReducedPaletteTests(unittest.TestCase):
    def test_limits_are_local_to_each_picture(self):
        palette = np.arange(96, dtype=np.uint8).reshape(32, 3)
        for offset in (0, 16):
            game = np.arange(offset, offset + 16, dtype=np.int16).reshape(4,4)
            game[0,0] = -1
            variants = select_swatches(game, palette)
            for size in SIZES:
                reduced = variants[size]
                actual = set(reduced[reduced >= 0])
                self.assertEqual(len(actual), size)
                self.assertTrue(actual.issubset(set(game.ravel())))
                np.testing.assert_array_equal(game < 0, reduced < 0)

    def test_small_and_empty_palettes_preserve_pixels(self):
        palette = np.eye(3, dtype=np.uint8)
        for game in (np.array([[1,2,-1]], np.int16), np.array([[-1]], np.int16)):
            for reduced in select_swatches(game, palette).values():
                np.testing.assert_array_equal(reduced, game)

    def test_shared_swatch_keeps_source_surface_and_alpha_boundaries(self):
        game = np.array([[5,5,5,-1,5]],np.int16)
        surfaces = np.array([[1,1,2,0,2]],np.int32)
        np.testing.assert_array_equal(paintable_regions(surfaces, game), [[1,1,2,0,3]])
