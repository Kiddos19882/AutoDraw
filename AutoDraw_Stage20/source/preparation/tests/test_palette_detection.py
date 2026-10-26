from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from palette_detection_ui import map_display_rect_to_image

from palette_detection import (
    PaletteFormatError,
    build_palette_entry,
    create_palette_document,
    detect_color_candidates,
    load_palette,
    merge_palette_entries,
    parse_hex_color,
    rgb_to_hex,
    sample_color_at,
    save_palette,
    validate_palette_document,
)


class PaletteColorTests(unittest.TestCase):
    def test_rgb_hex_round_trip(self):
        self.assertEqual(rgb_to_hex((232, 78, 67)), "#E84E43")
        self.assertEqual(parse_hex_color("e84e43"), (232, 78, 67))

    def test_invalid_hex_is_rejected(self):
        for value in ("#FFF", "GGGGGG", "12345678"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_hex_color(value)

    def test_sample_uses_median_patch(self):
        image = Image.new("RGB", (9, 9), (232, 78, 67))
        image.putpixel((4, 4), (0, 0, 0))
        self.assertEqual(sample_color_at(image, 4, 4, radius=2), (232, 78, 67))

    def test_sample_rejects_outside_coordinate(self):
        with self.assertRaises(ValueError):
            sample_color_at(Image.new("RGB", (4, 4), "white"), 4, 0)

    def test_manual_entry_keeps_global_and_local_coordinates(self):
        image = Image.new("RGB", (20, 15), (50, 100, 150))
        entry = build_palette_entry(image, 7, 8, origin_x=300, origin_y=120, source="manual")
        self.assertEqual(entry["hex"], "#326496")
        self.assertEqual((entry["local_x"], entry["local_y"]), (7, 8))
        self.assertEqual((entry["screen_x"], entry["screen_y"]), (307, 128))

    def test_autodetection_finds_separate_color_swatches_in_scan_order(self):
        image = Image.new("RGB", (130, 65), (230, 230, 230))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, 25, 25), fill=(240, 20, 30))
        draw.rectangle((34, 8, 51, 25), fill=(20, 200, 45))
        draw.rectangle((8, 36, 25, 53), fill=(30, 70, 230))
        candidates = detect_color_candidates(image, origin_x=100, origin_y=200)
        hexes = [item["hex"] for item in candidates]
        self.assertIn("#F0141E", hexes)
        self.assertIn("#14C82D", hexes)
        self.assertIn("#1E46E6", hexes)
        self.assertEqual(candidates, sorted(candidates, key=lambda item: (item["local_y"], item["local_x"])))
        red = next(item for item in candidates if item["hex"] == "#F0141E")
        self.assertEqual(red["screen_x"], 100 + red["local_x"])
        self.assertEqual(red["screen_y"], 200 + red["local_y"])


    def test_autodetection_includes_maximum_brightness_swatch(self):
        image = Image.new("RGB", (70, 35), (220, 220, 220))
        ImageDraw.Draw(image).rectangle((10, 8, 30, 28), fill=(255, 255, 0))
        candidates = detect_color_candidates(image)
        self.assertIn("#FFFF00", [item["hex"] for item in candidates])

    def test_duplicate_colors_are_not_added_twice(self):
        color = {"hex": "#010203", "rgb": [1, 2, 3], "screen_x": 1, "screen_y": 1,
                 "local_x": 1, "local_y": 1, "source": "manual"}
        merged, added = merge_palette_entries([color], [dict(color), {**color, "hex": "#040506", "rgb": [4, 5, 6]}])
        self.assertEqual(added, 1)
        self.assertEqual(len(merged), 2)


class PalettePersistenceTests(unittest.TestCase):
    def _document(self):
        image = Image.new("RGB", (80, 40), (90, 110, 130))
        colors = [build_palette_entry(image, 20, 20, origin_x=500, origin_y=100)]
        return create_palette_document(
            colors,
            screen_size=(1920, 1080),
            region={"x": 500, "y": 100, "width": 80, "height": 40},
            metadata={"source": "test"},
        )

    def test_round_trip_palette_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "palette.json"
            save_palette(path, self._document())
            loaded = load_palette(path)
            self.assertEqual(loaded["screen"], {"width": 1920, "height": 1080})
            self.assertEqual(loaded["region"], {"x": 500, "y": 100, "width": 80, "height": 40})
            self.assertEqual(loaded["colors"][0]["hex"], "#5A6E82")

    def test_save_is_atomic_and_does_not_replace_target_for_invalid_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "palette.json"
            path.write_text("previous", encoding="utf-8")
            with self.assertRaises(PaletteFormatError):
                save_palette(path, {"schema_version": 999})
            self.assertEqual(path.read_text(encoding="utf-8"), "previous")
            self.assertEqual(list(Path(temp).glob("*.tmp")), [])


    def test_region_outside_screen_bounds_is_rejected(self):
        document = self._document()
        document["region"]["x"] = 1900
        with self.assertRaises(PaletteFormatError):
            validate_palette_document(document)

    def test_mismatched_hex_and_rgb_are_rejected(self):
        document = self._document()
        document["colors"][0]["rgb"] = [1, 2, 3]
        with self.assertRaises(PaletteFormatError):
            validate_palette_document(document)

    def test_out_of_region_coordinates_are_rejected(self):
        document = self._document()
        document["colors"][0]["local_x"] = 500
        with self.assertRaises(PaletteFormatError):
            validate_palette_document(document)

    def test_duplicate_colors_are_rejected_in_saved_document(self):
        document = self._document()
        document["colors"].append(dict(document["colors"][0]))
        with self.assertRaises(PaletteFormatError):
            validate_palette_document(document)

    def test_invalid_json_is_reported_as_palette_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(PaletteFormatError):
                load_palette(path)



class ScreenSelectionMappingTests(unittest.TestCase):
    def test_mapping_accounts_for_centering_offset_and_scale(self):
        mapped = map_display_rect_to_image(
            (120, 70, 219, 119),
            source_size=(1920, 1080),
            display_size=(960, 540),
            offset=(20, 10),
        )
        self.assertEqual(mapped, (200, 120, 200, 100))

    def test_mapping_clamps_to_image_bounds(self):
        mapped = map_display_rect_to_image(
            (-100, -100, 500, 500),
            source_size=(100, 100),
            display_size=(50, 50),
            offset=(0, 0),
        )
        self.assertEqual(mapped, (0, 0, 100, 100))

if __name__ == "__main__":
    unittest.main(verbosity=2)
