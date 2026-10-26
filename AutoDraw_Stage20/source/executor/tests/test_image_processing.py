from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from image_processing.pipeline import ProcessingSettings, fit_to_canvas, process_image


class FitToCanvasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = Image.new("RGB", (200, 100), (20, 80, 140))

    def test_contain_keeps_aspect_ratio_and_adds_white_padding(self):
        result = fit_to_canvas(self.image, 100, 100, "contain")
        self.assertEqual(result.size, (100, 100))
        self.assertEqual(result.getpixel((50, 0)), (255, 255, 255))
        self.assertEqual(result.getpixel((50, 50)), (20, 80, 140))

    def test_cover_fills_exact_canvas(self):
        result = fit_to_canvas(self.image, 100, 100, "cover")
        self.assertEqual(result.size, (100, 100))
        self.assertEqual(result.getpixel((50, 50)), (20, 80, 140))

    def test_stretch_uses_exact_dimensions(self):
        self.assertEqual(fit_to_canvas(self.image, 73, 41, "stretch").size, (73, 41))

    def test_unknown_fit_mode_raises(self):
        with self.assertRaises(ValueError):
            fit_to_canvas(self.image, 100, 100, "unknown")  # type: ignore[arg-type]


class ProcessingPipelineTests(unittest.TestCase):
    def test_outputs_match_canvas_size(self):
        image = Image.new("RGB", (80, 60), (180, 100, 30))
        result = process_image(image, 64, 32, "contain")
        self.assertEqual(result.prepared_color.size, (64, 32))
        self.assertEqual(result.grayscale.size, (64, 32))
        self.assertEqual(result.binary_mask.size, (64, 32))
        self.assertEqual(result.grayscale.mode, "L")
        self.assertEqual(result.binary_mask.mode, "L")

    def test_threshold_outputs_only_black_and_white(self):
        image = Image.new("RGB", (20, 10), "white")
        for x in range(10):
            for y in range(10):
                image.putpixel((x, y), (0, 0, 0))
        result = process_image(image, 20, 10, "stretch", settings=ProcessingSettings(threshold_mode="manual", threshold=128))
        values = set(np.unique(np.asarray(result.binary_mask)).tolist())
        self.assertEqual(values, {0, 255})
        self.assertEqual(result.binary_mask.getpixel((2, 2)), 0)
        self.assertEqual(result.binary_mask.getpixel((18, 2)), 255)

    def test_manual_crop_applies_in_source_coordinates(self):
        image = Image.new("RGB", (20, 10), (255, 255, 255))
        for x in range(0, 10):
            for y in range(10):
                image.putpixel((x, y), (0, 0, 0))
        result = process_image(image, 10, 10, "stretch", crop_box=(0, 0, 10, 10),
                               settings=ProcessingSettings(threshold_mode="manual", threshold=128))
        self.assertTrue(np.all(np.asarray(result.binary_mask) == 0))
        self.assertEqual(result.crop_box, (0, 0, 10, 10))

    def test_invalid_crop_raises(self):
        image = Image.new("RGB", (20, 10), "white")
        with self.assertRaises(ValueError):
            process_image(image, 20, 10, crop_box=(5, 0, 25, 10))

    def test_otsu_threshold_is_recorded(self):
        image = Image.new("RGB", (20, 10), "white")
        for x in range(10):
            for y in range(10):
                image.putpixel((x, y), (0, 0, 0))
        result = process_image(image, 20, 10, "stretch", settings=ProcessingSettings(threshold_mode="otsu"))
        self.assertGreaterEqual(result.threshold_used, 0)
        self.assertLessEqual(result.threshold_used, 255)

    def test_settings_validate_ranges(self):
        with self.assertRaises(ValueError):
            ProcessingSettings(brightness=150)
        with self.assertRaises(ValueError):
            ProcessingSettings(contrast=3.5)
        with self.assertRaises(ValueError):
            ProcessingSettings(denoise_level=8)


if __name__ == "__main__":
    unittest.main()
