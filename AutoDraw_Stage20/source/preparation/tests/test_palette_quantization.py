from __future__ import annotations

import unittest

import numpy as np
from PIL import Image

from palette_quantization import (
    PaletteQuantizationError,
    delta_e_ciede2000,
    normalize_palette,
    quantize_image_to_palette,
    merge_rare_palette_colors,
    remove_edge_connected_background,
    remove_white_palette_pixels,
    optimize_short_scanline_runs,
    rgb_to_lab,
)


RED = {"name": "Красный", "hex": "#FF0000", "rgb": [255, 0, 0], "id": "red"}
GREEN = {"name": "Зелёный", "hex": "#00FF00", "rgb": [0, 255, 0], "id": "green"}
BLUE = {"name": "Синий", "hex": "#0000FF", "rgb": [0, 0, 255], "id": "blue"}
WHITE = {"name": "Белый", "hex": "#FFFFFF", "rgb": [255, 255, 255], "id": "white"}
BLACK = {"name": "Чёрный", "hex": "#000000", "rgb": [0, 0, 0], "id": "black"}


class CIEDE2000Tests(unittest.TestCase):
    def test_known_reference_pairs_from_ciede2000_reference_data(self):
        pairs = [
            ((50, 2.6772, -79.7751), (50, 0, -82.7485), 2.0425),
            ((50, 3.1571, -77.2803), (50, 0, -82.7485), 2.8615),
            ((50, 2.8361, -74.0200), (50, 0, -82.7485), 3.4412),
            ((50, -1.3802, -84.2814), (50, 0, -82.7485), 1.0000),
            ((50, 0, 0), (50, -1, 2), 2.3669),
        ]
        for first, second, expected in pairs:
            with self.subTest(first=first, second=second):
                actual = float(delta_e_ciede2000(np.array(first), np.array(second)))
                self.assertAlmostEqual(actual, expected, delta=0.0006)

    def test_exact_lab_match_has_zero_distance(self):
        lab = rgb_to_lab(np.array([42, 123, 210]))
        self.assertAlmostEqual(float(delta_e_ciede2000(lab, lab)), 0.0, places=8)

    def test_broadcasting_returns_pixel_by_color_matrix(self):
        pixels = rgb_to_lab(np.array([[255, 0, 0], [0, 255, 0]], dtype=np.uint8))[:, None, :]
        palette = rgb_to_lab(np.array([[255, 0, 0], [0, 255, 0]], dtype=np.uint8))[None, :, :]
        distances = delta_e_ciede2000(pixels, palette)
        self.assertEqual(distances.shape, (2, 2))
        self.assertLess(distances[0, 0], distances[0, 1])
        self.assertLess(distances[1, 1], distances[1, 0])


class BackgroundRemovalTests(unittest.TestCase):
    def test_removes_white_background_connected_to_edges_but_keeps_enclosed_white_detail(self):
        image = Image.new("RGB", (7, 7), "white")
        # Dark ring encloses a white detail. The outer white field should become transparent,
        # while the enclosed white center remains a visible foreground detail.
        for y in range(2, 5):
            for x in range(2, 5):
                image.putpixel((x, y), (0, 0, 0))
        image.putpixel((3, 3), (255, 255, 255))

        result = remove_edge_connected_background(image, tolerance=0)

        self.assertEqual(result.image.mode, "RGBA")
        self.assertEqual(result.image.getpixel((0, 0)), (255, 255, 255, 0))
        self.assertEqual(result.image.getpixel((2, 2)), (0, 0, 0, 255))
        self.assertEqual(result.image.getpixel((3, 3)), (255, 255, 255, 255))
        self.assertEqual(result.report["removed_pixel_count"], 40)
        self.assertEqual(result.report["background_rgb"], [255, 255, 255])
        # The caller's image is not modified.
        self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_tolerance_removes_near_white_antialiased_edge_background(self):
        image = Image.new("RGB", (4, 2), (255, 255, 255))
        image.putpixel((0, 0), (238, 244, 250))
        image.putpixel((1, 0), (240, 240, 250))
        image.putpixel((2, 0), (220, 240, 250))
        result = remove_edge_connected_background(image, tolerance=20)
        self.assertEqual(result.image.getpixel((0, 0))[3], 0)
        self.assertEqual(result.image.getpixel((1, 0))[3], 0)
        self.assertEqual(result.image.getpixel((2, 0))[3], 255)
        self.assertEqual(result.report["removed_pixel_count"], 7)

    def test_color_not_matching_background_survives_even_when_touching_edge(self):
        image = Image.new("RGB", (3, 2), (255, 255, 255))
        image.putpixel((0, 0), (255, 0, 0))
        result = remove_edge_connected_background(image, tolerance=24)
        self.assertEqual(result.image.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(result.image.getpixel((2, 1))[3], 0)

    def test_preserves_original_transparency_and_counts_only_newly_removed_pixels(self):
        image = Image.new("RGBA", (3, 2), (255, 255, 255, 255))
        image.putpixel((1, 1), (10, 20, 30, 0))
        result = remove_edge_connected_background(image, tolerance=0)
        self.assertEqual(result.image.getpixel((1, 1)), (10, 20, 30, 0))
        self.assertEqual(result.report["removed_pixel_count"], 5)
        self.assertEqual(int(np.count_nonzero(result.removed_mask)), 5)

    def test_empty_match_does_not_remove_anything(self):
        image = Image.new("RGB", (3, 2), (20, 30, 40))
        result = remove_edge_connected_background(image, tolerance=5)
        self.assertEqual(result.report["removed_pixel_count"], 0)
        self.assertTrue(np.all(np.asarray(result.image)[..., 3] == 255))

    def test_invalid_tolerance_and_background_color_are_rejected(self):
        image = Image.new("RGB", (1, 1), "white")
        for tolerance in (-1, 256, True, 1.5):
            with self.subTest(tolerance=tolerance), self.assertRaises(PaletteQuantizationError):
                remove_edge_connected_background(image, tolerance=tolerance)
        for color in ((255, 255), (255, 256, 255), "#FFFFFF", (True, 255, 255)):
            with self.subTest(color=color), self.assertRaises(PaletteQuantizationError):
                remove_edge_connected_background(image, background_rgb=color)

    def test_removed_background_becomes_transparent_in_quantization_index_map(self):
        image = Image.new("RGB", (5, 3), "white")
        image.putpixel((2, 1), (255, 0, 0))
        transparent_source = remove_edge_connected_background(image, tolerance=0).image
        converted = quantize_image_to_palette(transparent_source, [RED, WHITE])
        self.assertTrue(np.all(converted.index_map[:, :2] == -1))
        self.assertTrue(np.all(converted.index_map[:, 3:] == -1))
        self.assertEqual(int(converted.index_map[1, 2]), 0)
        self.assertEqual(converted.report["transparent_pixel_count"], 14)
        self.assertEqual(converted.report["visible_pixel_count"], 1)


class WhitePaletteRemovalTests(unittest.TestCase):
    def test_remove_all_white_palette_pixels_including_enclosed_details(self):
        image = Image.new("RGB", (5, 2), "black")
        image.putdata([
            (255, 255, 255), (0, 0, 0), (0, 0, 0), (255, 255, 255), (0, 0, 0),
            (0, 0, 0), (255, 255, 255), (0, 0, 0), (0, 0, 0), (0, 0, 0),
        ])
        palette = [BLACK, WHITE]
        result = quantize_image_to_palette(image, palette)
        converted, report = remove_white_palette_pixels(result, palette, image, tolerance=0)

        self.assertEqual(report["removed_pixel_count"], 3)
        self.assertTrue(report["applied"])
        self.assertEqual(converted.image.mode, "RGBA")
        self.assertEqual(converted.image.getpixel((0, 0))[3], 0)
        self.assertEqual(converted.image.getpixel((3, 0))[3], 0)
        self.assertEqual(converted.image.getpixel((1, 0)), (0, 0, 0, 255))
        self.assertEqual(int(converted.index_map[0, 0]), -1)
        self.assertEqual(converted.report["visible_pixel_count"], 7)
        self.assertEqual(converted.report["transparent_pixel_count"], 3)
        self.assertEqual(converted.report["used_palette_color_count"], 1)
        self.assertEqual(converted.report["used_colors"][0]["hex"], "#000000")

    def test_automatic_mode_removes_white_when_share_is_strictly_above_30_percent(self):
        image = Image.new("RGB", (10, 1), "black")
        for x in range(4):
            image.putpixel((x, 0), (255, 255, 255))
        palette = [BLACK, WHITE]
        result = quantize_image_to_palette(image, palette)
        converted, report = remove_white_palette_pixels(
            result, palette, image, tolerance=0, threshold_percentage=30.0
        )
        self.assertEqual(report["white_percentage_of_visible_pixels"], 40.0)
        self.assertEqual(report["removed_pixel_count"], 4)
        self.assertEqual(report["decision"], "white_percentage_exceeded_threshold")
        self.assertTrue(np.all(converted.index_map[0, :4] == -1))
        self.assertEqual(converted.report["visible_pixel_count"], 6)

    def test_automatic_mode_keeps_white_at_exactly_30_percent(self):
        image = Image.new("RGB", (10, 1), "black")
        for x in range(3):
            image.putpixel((x, 0), (255, 255, 255))
        palette = [BLACK, WHITE]
        result = quantize_image_to_palette(image, palette)
        converted, report = remove_white_palette_pixels(
            result, palette, image, tolerance=0, threshold_percentage=30.0
        )
        self.assertEqual(report["white_percentage_of_visible_pixels"], 30.0)
        self.assertEqual(report["removed_pixel_count"], 0)
        self.assertFalse(report["applied"])
        self.assertTrue(np.all(converted.index_map[0, :3] == 1))
        self.assertEqual(converted.image.mode, "RGB")

    def test_automatic_mode_keeps_white_below_30_percent(self):
        image = Image.new("RGB", (10, 1), "black")
        image.putpixel((0, 0), (255, 255, 255))
        palette = [BLACK, WHITE]
        result = quantize_image_to_palette(image, palette)
        converted, report = remove_white_palette_pixels(
            result, palette, image, tolerance=0, threshold_percentage=30.0
        )
        self.assertEqual(report["white_percentage_of_visible_pixels"], 10.0)
        self.assertEqual(report["removed_pixel_count"], 0)
        self.assertEqual(converted.index_map[0, 0], 1)

    def test_white_detection_uses_palette_colors_and_rgb_tolerance(self):
        image = Image.new("RGB", (4, 1), "#F0F0F0")
        palette = [BLACK, {"name": "Off white", "hex": "#F0F0F0", "rgb": [240, 240, 240], "id": "off-white"}]
        result = quantize_image_to_palette(image, palette)
        converted, report = remove_white_palette_pixels(result, palette, image, tolerance=16)
        self.assertEqual(report["removed_pixel_count"], 4)
        self.assertEqual(report["white_palette_colors"][0]["hex"], "#F0F0F0")
        self.assertTrue(np.all(converted.index_map == -1))

    def test_removal_preserves_preexisting_transparency_and_denominator_uses_visible_pixels(self):
        image = Image.new("RGBA", (10, 1), (0, 0, 0, 255))
        for x in range(4):
            image.putpixel((x, 0), (255, 255, 255, 255))
        for x in range(6, 10):
            image.putpixel((x, 0), (255, 255, 255, 0))
        palette = [BLACK, WHITE]
        result = quantize_image_to_palette(image, palette)
        converted, report = remove_white_palette_pixels(
            result, palette, image, tolerance=0, threshold_percentage=30.0
        )
        self.assertAlmostEqual(report["white_percentage_of_visible_pixels"], 66.6667, places=3)
        self.assertEqual(report["removed_pixel_count"], 4)
        self.assertEqual(converted.report["transparent_pixel_count"], 8)
        self.assertEqual(converted.report["visible_pixel_count"], 2)

    def test_rejects_invalid_tolerance_threshold_and_image_size(self):
        image = Image.new("RGB", (1, 1), "white")
        palette = [WHITE]
        result = quantize_image_to_palette(image, palette)
        for tolerance in (-1, 256, True, 1.5):
            with self.subTest(tolerance=tolerance), self.assertRaises(PaletteQuantizationError):
                remove_white_palette_pixels(result, palette, image, tolerance=tolerance)
        for threshold in (-1, 100.1, True, float("nan")):
            with self.subTest(threshold=threshold), self.assertRaises(PaletteQuantizationError):
                remove_white_palette_pixels(result, palette, image, threshold_percentage=threshold)
        with self.assertRaises(PaletteQuantizationError):
            remove_white_palette_pixels(result, palette, Image.new("RGB", (2, 2)), tolerance=0)


class PaletteQuantizationTests(unittest.TestCase):
    def test_exact_palette_colors_remain_unchanged(self):
        image = Image.new("RGB", (3, 1))
        image.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255)])
        result = quantize_image_to_palette(image, [RED, GREEN, BLUE])
        self.assertEqual([tuple(pixel) for pixel in np.asarray(result.image).reshape(-1, 3)], [(255, 0, 0), (0, 255, 0), (0, 0, 255)])
        self.assertEqual(result.report["changed_pixel_count"], 0)
        self.assertEqual(result.report["exact_color_pixel_count"], 3)
        self.assertEqual(result.report["mean_delta_e_2000"], 0)

    def test_every_visible_output_pixel_is_a_palette_color(self):
        image = Image.new("RGB", (7, 3))
        pixels = [((x * 31) % 256, (y * 97) % 256, ((x + y) * 53) % 256) for y in range(3) for x in range(7)]
        image.putdata(pixels)
        palette = [RED, GREEN, BLUE, WHITE, BLACK]
        result = quantize_image_to_palette(image, palette)
        allowed = {tuple(item["rgb"]) for item in palette}
        self.assertTrue(all(tuple(pixel) in allowed for pixel in np.asarray(result.image).reshape(-1, 3)))

    def test_dimensions_and_single_pixel_details_are_preserved_without_dithering(self):
        image = Image.new("RGB", (9, 7), "#FFFFFF")
        image.putpixel((4, 3), (245, 20, 25))
        result = quantize_image_to_palette(image, [WHITE, RED, BLACK])
        self.assertEqual(result.image.size, image.size)
        self.assertEqual(tuple(result.image.getpixel((4, 3))), (255, 0, 0))
        self.assertEqual(int(np.count_nonzero(result.index_map == 1)), 1)
        self.assertFalse(result.report["dithering"])

    def test_index_map_matches_palette_indices_and_counts(self):
        image = Image.new("RGB", (4, 1))
        image.putdata([(255, 0, 0), (240, 10, 10), (0, 255, 0), (5, 245, 5)])
        result = quantize_image_to_palette(image, [RED, GREEN])
        self.assertEqual(result.index_map.tolist(), [[0, 0, 1, 1]])
        self.assertEqual(result.report["used_palette_color_count"], 2)
        self.assertEqual(sum(item["pixel_count"] for item in result.report["used_colors"]), 4)
        self.assertAlmostEqual(sum(item["percentage_visible"] for item in result.report["used_colors"]), 100.0, places=3)

    def test_nearest_color_is_selected_by_ciede2000(self):
        target = (130, 75, 70)
        image = Image.new("RGB", (1, 1), target)
        palette = [
            {"name": "Candidate A", "rgb": [180, 30, 30], "hex": "#B41E1E"},
            {"name": "Candidate B", "rgb": [120, 82, 70], "hex": "#785246"},
            {"name": "Candidate C", "rgb": [20, 100, 200], "hex": "#1464C8"},
        ]
        target_lab = rgb_to_lab(np.array(target))
        distances = [float(delta_e_ciede2000(target_lab, rgb_to_lab(np.array(item["rgb"])))) for item in palette]
        expected = tuple(palette[int(np.argmin(distances))]["rgb"])
        result = quantize_image_to_palette(image, palette)
        self.assertEqual(result.image.getpixel((0, 0)), expected)
        self.assertEqual(result.index_map[0, 0], int(np.argmin(distances)))

    def test_transparent_pixels_and_alpha_are_preserved(self):
        image = Image.new("RGBA", (3, 1))
        image.putdata([(255, 0, 0, 255), (255, 255, 255, 0), (10, 240, 10, 128)])
        result = quantize_image_to_palette(image, [RED, GREEN, WHITE])
        self.assertEqual(result.image.mode, "RGBA")
        self.assertEqual([p[3] for p in np.asarray(result.image).reshape(-1, 4)], [255, 0, 128])
        self.assertEqual(result.report["transparent_pixel_count"], 1)
        self.assertEqual(result.report["visible_pixel_count"], 2)
        self.assertEqual(result.index_map[0, 1], -1)

    def test_all_transparent_image_is_valid(self):
        image = Image.new("RGBA", (2, 2), (100, 200, 10, 0))
        result = quantize_image_to_palette(image, [RED, GREEN])
        self.assertEqual(result.report["visible_pixel_count"], 0)
        self.assertEqual(result.report["transparent_pixel_count"], 4)
        self.assertTrue(np.all(result.index_map == -1))
        self.assertTrue(np.array_equal(np.asarray(result.image), np.asarray(image)))

    def test_chunk_size_does_not_change_result(self):
        image = Image.new("RGB", (29, 17))
        image.putdata([((x * 7) % 256, (x * 13) % 256, (x * 29) % 256) for x in range(image.width * image.height)])
        a = quantize_image_to_palette(image, [RED, GREEN, BLUE, WHITE, BLACK], chunk_pixels=7)
        b = quantize_image_to_palette(image, [RED, GREEN, BLUE, WHITE, BLACK], chunk_pixels=4096)
        self.assertTrue(np.array_equal(np.asarray(a.image), np.asarray(b.image)))
        self.assertTrue(np.array_equal(a.index_map, b.index_map))

    def test_profile_document_can_be_passed_directly(self):
        profile = {"profile_name": "Test", "profile_schema_version": 1, "colors": [RED, GREEN]}
        result = quantize_image_to_palette(Image.new("RGB", (1, 1), "#00FF00"), profile)
        self.assertEqual(result.report["palette_color_count"], 2)
        self.assertEqual(result.image.getpixel((0, 0)), (0, 255, 0))

    def test_empty_palette_rejected(self):
        with self.assertRaisesRegex(PaletteQuantizationError, "пуста"):
            quantize_image_to_palette(Image.new("RGB", (1, 1)), [])

    def test_duplicate_rgb_colors_rejected(self):
        with self.assertRaisesRegex(PaletteQuantizationError, "повторяется"):
            normalize_palette([RED, {"hex": "#FF0000", "rgb": [255, 0, 0]}])

    def test_mismatched_rgb_and_hex_rejected(self):
        with self.assertRaisesRegex(PaletteQuantizationError, "не совпадают"):
            normalize_palette([{"hex": "#FF0000", "rgb": [0, 255, 0]}])

    def test_invalid_palette_rgb_rejected(self):
        with self.assertRaises(PaletteQuantizationError):
            normalize_palette([{"rgb": [256, 0, 0]}])

    def test_limit_on_palette_size_is_enforced(self):
        colors = [{"rgb": [index % 256, (index // 256) % 256, (index // (256 * 256)) % 256]} for index in range(513)]
        with self.assertRaisesRegex(PaletteQuantizationError, "максимум 512"):
            normalize_palette(colors)

    def test_rare_color_merges_to_similar_frequent_color_and_reduces_scanline_strokes(self):
        common = {"name": "Частый синий", "hex": "#3472C0", "rgb": [52, 114, 192], "id": "common-blue"}
        rare = {"name": "Редкий синий", "hex": "#3977C5", "rgb": [57, 119, 197], "id": "rare-blue"}
        image = Image.new("RGB", (10, 10), tuple(common["rgb"]))
        image.putpixel((5, 0), tuple(rare["rgb"]))
        result = quantize_image_to_palette(image, [common, rare])
        before_indexes = result.index_map.copy()
        before_strokes = 12  # the rare pixel splits the top scanline into three runs

        optimized, report = merge_rare_palette_colors(
            result,
            [common, rare],
            min_pixel_count=20,
            min_percentage=0.05,
            max_delta_e=8.0,
        )

        self.assertEqual(report["rare_color_count_merged"], 1)
        self.assertEqual(report["remapped_pixel_count"], 1)
        self.assertEqual(report["estimated_scanline_strokes_before"], before_strokes)
        self.assertEqual(report["estimated_scanline_strokes_after"], 10)
        self.assertEqual(report["estimated_scanline_strokes_reduced"], 2)
        self.assertNotEqual(before_indexes[0, 5], optimized.index_map[0, 5])
        self.assertTrue(np.all(optimized.index_map == 0))
        self.assertEqual(optimized.image.getpixel((5, 0)), tuple(common["rgb"]))
        self.assertEqual(optimized.report["used_palette_color_count"], 1)
        self.assertEqual(optimized.report["used_colors"][0]["id"], "common-blue")
        self.assertEqual(optimized.report["rare_color_merge"]["mappings"][0]["source_hex"], "#3977C5")

    def test_rare_color_is_preserved_when_nearest_frequent_color_is_too_different(self):
        common = {"name": "Синий", "hex": "#0000FF", "rgb": [0, 0, 255], "id": "blue"}
        rare = {"name": "Красный", "hex": "#FF0000", "rgb": [255, 0, 0], "id": "red"}
        image = Image.new("RGB", (10, 10), tuple(common["rgb"]))
        image.putpixel((5, 0), tuple(rare["rgb"]))
        result = quantize_image_to_palette(image, [common, rare])

        optimized, report = merge_rare_palette_colors(result, [common, rare], max_delta_e=8.0)

        self.assertEqual(report["rare_color_count_detected"], 1)
        self.assertEqual(report["rare_color_count_merged"], 0)
        self.assertEqual(report["remapped_pixel_count"], 0)
        self.assertEqual(optimized.index_map[0, 5], 1)
        self.assertEqual(optimized.image.getpixel((5, 0)), tuple(rare["rgb"]))

    def test_transparency_is_never_reassigned_during_rare_color_merge(self):
        common = {"name": "Синий", "hex": "#3472C0", "rgb": [52, 114, 192], "id": "blue"}
        rare = {"name": "Синий редкий", "hex": "#3977C5", "rgb": [57, 119, 197], "id": "rare"}
        image = Image.new("RGBA", (10, 10), (*common["rgb"], 255))
        image.putpixel((5, 0), (*rare["rgb"], 255))
        image.putpixel((0, 0), (255, 0, 0, 0))
        result = quantize_image_to_palette(image, [common, rare])

        optimized, report = merge_rare_palette_colors(result, [common, rare])

        self.assertEqual(int(optimized.index_map[0, 0]), -1)
        self.assertEqual(optimized.image.getpixel((0, 0))[3], 0)
        self.assertEqual(optimized.image.getpixel((5, 0))[3], 255)
        self.assertEqual(report["visible_pixel_count"], 99)

    def test_rare_color_merge_preserves_original_palette_order_and_dimensions(self):
        common = {"name": "Частый", "hex": "#3472C0", "rgb": [52, 114, 192], "id": "common"}
        rare = {"name": "Редкий", "hex": "#3977C5", "rgb": [57, 119, 197], "id": "rare"}
        image = Image.new("RGB", (10, 10), tuple(common["rgb"]))
        image.putpixel((3, 3), tuple(rare["rgb"]))
        result = quantize_image_to_palette(image, [common, rare])

        optimized, _ = merge_rare_palette_colors(result, [common, rare])

        self.assertEqual(optimized.image.size, image.size)
        self.assertEqual(optimized.report["palette"][0]["id"], "common")
        self.assertEqual(optimized.report["palette"][1]["id"], "rare")
        self.assertEqual(optimized.report["palette"][1]["pixel_count"], 0)

    def test_invalid_rare_color_merge_parameters_are_rejected(self):
        image = Image.new("RGB", (2, 2), "blue")
        result = quantize_image_to_palette(image, [BLUE])
        for kwargs in (
            {"min_pixel_count": -1},
            {"min_pixel_count": True},
            {"min_percentage": -0.1},
            {"min_percentage": float("nan")},
            {"max_delta_e": 101},
            {"min_frequency_ratio": 0.5},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(PaletteQuantizationError):
                merge_rare_palette_colors(result, [BLUE], **kwargs)

    def test_no_merge_when_there_is_no_non_rare_target(self):
        first = {"name": "First", "hex": "#3472C0", "rgb": [52, 114, 192], "id": "first"}
        second = {"name": "Second", "hex": "#3977C5", "rgb": [57, 119, 197], "id": "second"}
        image = Image.new("RGB", (2, 1))
        image.putdata([tuple(first["rgb"]), tuple(second["rgb"])])
        result = quantize_image_to_palette(image, [first, second])
        optimized, report = merge_rare_palette_colors(result, [first, second])
        self.assertEqual(report["rare_color_count_merged"], 0)
        self.assertEqual(optimized.index_map.tolist(), [[0, 1]])

    def test_workload_guard_rejects_extreme_pixel_palette_product(self):
        colors = []
        for index in range(512):
            rgb = [index % 256, (index // 256) % 256, 100]
            colors.append({"rgb": rgb, "hex": "#%02X%02X%02X" % tuple(rgb)})
        image = Image.new("RGB", (800, 800), "#112233")
        with self.assertRaisesRegex(PaletteQuantizationError, "Слишком много сравнений"):
            quantize_image_to_palette(image, colors)




class ShortScanlineOptimizationTests(unittest.TestCase):
    def setUp(self):
        self.common = {
            "name": "Частый синий", "hex": "#3472C0",
            "rgb": [52, 114, 192], "id": "common-blue",
        }
        self.near = {
            "name": "Похожий синий", "hex": "#3977C5",
            "rgb": [57, 119, 197], "id": "near-blue",
        }

    def test_merges_similar_short_run_between_same_color_and_reduces_strokes(self):
        image = Image.new("RGB", (10, 1), tuple(self.common["rgb"]))
        image.putpixel((4, 0), tuple(self.near["rgb"]))
        image.putpixel((5, 0), tuple(self.near["rgb"]))
        result = quantize_image_to_palette(image, [self.common, self.near])

        optimized, report = optimize_short_scanline_runs(result, [self.common, self.near])

        self.assertTrue(np.all(optimized.index_map == 0))
        self.assertEqual(report["short_run_count_before"], 1)
        self.assertEqual(report["short_run_count_after"], 0)
        self.assertEqual(report["remapped_pixel_count"], 2)
        self.assertEqual(report["estimated_scanline_strokes_before"], 3)
        self.assertEqual(report["estimated_scanline_strokes_after"], 1)
        self.assertEqual(optimized.report["used_palette_color_count"], 1)
        self.assertEqual(optimized.image.getpixel((4, 0)), tuple(self.common["rgb"]))

    def test_preserves_high_contrast_short_detail(self):
        image = Image.new("RGB", (10, 1), tuple(self.common["rgb"]))
        image.putpixel((4, 0), (255, 0, 0))
        image.putpixel((5, 0), (255, 0, 0))
        result = quantize_image_to_palette(image, [self.common, RED])

        optimized, report = optimize_short_scanline_runs(result, [self.common, RED], max_delta_e=8.0)

        self.assertEqual(int(optimized.index_map[0, 4]), 1)
        self.assertEqual(report["remapped_pixel_count"], 0)

    def test_edge_run_is_merged_only_to_a_similar_more_frequent_color(self):
        image = Image.new("RGB", (10, 1), tuple(self.common["rgb"]))
        image.putpixel((0, 0), tuple(self.near["rgb"]))
        result = quantize_image_to_palette(image, [self.common, self.near])

        optimized, report = optimize_short_scanline_runs(result, [self.common, self.near])

        self.assertEqual(int(optimized.index_map[0, 0]), 0)
        self.assertEqual(report["estimated_scanline_strokes_reduced"], 1)

    def test_does_not_change_runs_at_or_above_minimum_length(self):
        image = Image.new("RGB", (10, 1), tuple(self.common["rgb"]))
        for x in range(4, 7):
            image.putpixel((x, 0), tuple(self.near["rgb"]))
        result = quantize_image_to_palette(image, [self.common, self.near])

        optimized, report = optimize_short_scanline_runs(result, [self.common, self.near], min_run_length=3)

        self.assertTrue(np.array_equal(optimized.index_map, result.index_map))
        self.assertEqual(report["remapped_pixel_count"], 0)

    def test_transparent_pixels_are_not_reassigned(self):
        image = Image.new("RGBA", (10, 1), (*self.common["rgb"], 255))
        image.putpixel((4, 0), (*self.near["rgb"], 0))
        image.putpixel((5, 0), (*self.near["rgb"], 0))
        result = quantize_image_to_palette(image, [self.common, self.near])

        optimized, report = optimize_short_scanline_runs(result, [self.common, self.near])

        self.assertTrue(np.all(optimized.index_map[0, 4:6] == -1))
        self.assertTrue(np.all(np.asarray(optimized.image)[0, 4:6, 3] == 0))
        self.assertEqual(report["remapped_pixel_count"], 0)

    def test_invalid_options_are_rejected(self):
        image = Image.new("RGB", (2, 1), tuple(self.common["rgb"]))
        result = quantize_image_to_palette(image, [self.common])
        invalid_options = (
            {"min_run_length": 1},
            {"min_run_length": True},
            {"max_delta_e": float("nan")},
            {"max_delta_e": 101},
            {"min_frequency_ratio": 0.5},
            {"max_passes": 6},
        )
        for options in invalid_options:
            with self.subTest(options=options), self.assertRaises(PaletteQuantizationError):
                optimize_short_scanline_runs(result, [self.common], **options)


if __name__ == "__main__":
    unittest.main(verbosity=2)
