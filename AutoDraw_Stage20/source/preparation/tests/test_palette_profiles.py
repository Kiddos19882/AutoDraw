from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from palette_detection import create_palette_document, load_palette
from palette_profiles import (
    PaletteProfileError,
    check_profile_freshness,
    check_profile_against_screenshot,
    create_palette_profile,
    load_palette_profile,
    palette_document_from_profile,
    sample_profile_colors,
    save_palette_profile,
    validate_palette_profile,
)


def make_palette_document():
    screen = Image.new("RGB", (120, 90), "#FFFFFF")
    draw = ImageDraw.Draw(screen)
    draw.rectangle((15, 25, 34, 44), fill="#E84E43")
    draw.rectangle((40, 25, 59, 44), fill="#37A85A")
    region = {"x": 10, "y": 20, "width": 60, "height": 30}
    region_image = screen.crop((10, 20, 70, 50))
    colors = [
        {
            "name": "Красный",
            "hex": "#E84E43",
            "rgb": [232, 78, 67],
            "screen_x": 25,
            "screen_y": 35,
            "local_x": 15,
            "local_y": 15,
            "source": "auto",
        },
        {
            "name": "Зелёный",
            "hex": "#37A85A",
            "rgb": [55, 168, 90],
            "screen_x": 50,
            "screen_y": 35,
            "local_x": 40,
            "local_y": 15,
            "source": "manual",
        },
    ]
    document = create_palette_document(
        colors,
        screen_size=screen.size,
        region=region,
        metadata={"method": "screenshot-assisted"},
    )
    return document, region_image


class PaletteProfileTests(unittest.TestCase):
    def setUp(self):
        self.palette, self.region_image = make_palette_document()
        self.profile = create_palette_profile(
            self.palette,
            "Farm browser",
            browser_label="Test board",
            dpi_scale_percent=125,
            notes="Main palette",
        )

    def test_profile_has_named_colors_stable_ids_and_statuses(self):
        profile = validate_palette_profile(self.profile)
        self.assertEqual(profile["profile_name"], "Farm browser")
        self.assertEqual(profile["calibration"]["dpi_scale_percent"], 125)
        self.assertEqual(profile["colors"][0]["status"], "detected")
        self.assertEqual(profile["colors"][1]["status"], "detected")
        self.assertTrue(profile["colors"][0]["id"])
        self.assertNotEqual(profile["colors"][0]["id"], profile["colors"][1]["id"])

    def test_explicit_confirmed_and_corrected_statuses_survive(self):
        self.profile["colors"][0]["status"] = "confirmed"
        self.profile["colors"][1]["status"] = "corrected"
        profile = validate_palette_profile(self.profile)
        self.assertEqual([c["status"] for c in profile["colors"]], ["confirmed", "corrected"])

    def test_save_load_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "browser.autodraw-palette.json"
            saved = save_palette_profile(path, self.profile)
            loaded = load_palette_profile(saved)
        self.assertEqual(loaded["profile_name"], "Farm browser")
        self.assertEqual(loaded["colors"], self.profile["colors"])
        self.assertEqual(loaded["region"], self.profile["region"])
        self.assertEqual(loaded["calibration"]["browser_label"], "Test board")

    def test_stage16_palette_json_can_be_imported_as_profile(self):
        imported = validate_palette_profile(self.palette)
        self.assertEqual(imported["profile_schema_version"], 1)
        self.assertEqual(imported["profile_name"], "Импортированный профиль")
        self.assertEqual(len(imported["colors"]), 2)

    def test_profile_can_be_exported_to_stage16_palette_format(self):
        legacy = palette_document_from_profile(self.profile)
        self.assertEqual(legacy["schema_version"], 1)
        self.assertEqual(len(legacy["colors"]), 2)
        self.assertEqual(legacy["colors"][0]["hex"], "#E84E43")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "stage16.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            self.assertEqual(len(load_palette(path)["colors"]), 2)

    def test_current_calibration_is_reported_current(self):
        observations = {c["id"]: c["rgb"] for c in self.profile["colors"]}
        result = check_profile_freshness(
            self.profile,
            current_screen_size=(120, 90),
            current_region={"x": 10, "y": 20, "width": 60, "height": 30},
            current_dpi_scale_percent=125,
            observed_colors=observations,
        )
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["warnings"], [])

    def test_resolution_change_makes_profile_stale(self):
        result = check_profile_freshness(
            self.profile,
            current_screen_size=(1920, 1080),
            current_region=self.profile["region"],
            current_dpi_scale_percent=125,
            observed_colors={c["id"]: c["rgb"] for c in self.profile["colors"]},
        )
        self.assertEqual(result["status"], "stale")
        self.assertIn("разрешение", result["issues"][0].lower())

    def test_region_move_or_resize_makes_profile_stale(self):
        result = check_profile_freshness(
            self.profile,
            current_screen_size=(120, 90),
            current_region={"x": 12, "y": 20, "width": 60, "height": 30},
            current_dpi_scale_percent=125,
            observed_colors={c["id"]: c["rgb"] for c in self.profile["colors"]},
        )
        self.assertEqual(result["status"], "stale")
        self.assertTrue(any("область палитры" in issue.lower() for issue in result["issues"]))

    def test_dpi_change_makes_profile_stale(self):
        result = check_profile_freshness(
            self.profile,
            current_screen_size=(120, 90),
            current_region=self.profile["region"],
            current_dpi_scale_percent=150,
            observed_colors={c["id"]: c["rgb"] for c in self.profile["colors"]},
        )
        self.assertTrue(any("масштаб windows" in issue.lower() for issue in result["issues"]))

    def test_color_change_makes_profile_stale(self):
        observed = {c["id"]: c["rgb"] for c in self.profile["colors"]}
        observed[self.profile["colors"][0]["id"]] = (0, 0, 0)
        result = check_profile_freshness(
            self.profile,
            current_screen_size=(120, 90),
            current_region=self.profile["region"],
            current_dpi_scale_percent=125,
            observed_colors=observed,
        )
        self.assertEqual(result["status"], "stale")
        self.assertTrue(any("цвет образца" in issue.lower() for issue in result["issues"]))

    def test_calibration_uses_saved_region_without_manual_reselection(self):
        screenshot = Image.new("RGB", (120, 90), "#FFFFFF")
        draw = ImageDraw.Draw(screenshot)
        draw.rectangle((15, 25, 34, 44), fill="#E84E43")
        draw.rectangle((40, 25, 59, 44), fill="#37A85A")

        result = check_profile_against_screenshot(
            self.profile,
            screenshot,
            current_dpi_scale_percent=125,
        )
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["warnings"], [])

    def test_saved_region_detects_palette_moved_or_colors_changed(self):
        screenshot = Image.new("RGB", (120, 90), "#FFFFFF")
        draw = ImageDraw.Draw(screenshot)
        draw.rectangle((15, 25, 34, 44), fill="#0000FF")
        draw.rectangle((40, 25, 59, 44), fill="#37A85A")

        result = check_profile_against_screenshot(
            self.profile,
            screenshot,
            current_dpi_scale_percent=125,
        )
        self.assertEqual(result["status"], "stale")
        self.assertTrue(any("цвет образца" in issue.lower() for issue in result["issues"]))

    def test_saved_region_outside_screen_is_reported_without_picker(self):
        screenshot = Image.new("RGB", (60, 45), "#FFFFFF")
        result = check_profile_against_screenshot(
            self.profile,
            screenshot,
            current_dpi_scale_percent=125,
        )
        self.assertEqual(result["status"], "stale")
        self.assertTrue(any("выходит за границы" in issue.lower() for issue in result["issues"]))

    def test_missing_capture_context_is_unverified_not_current(self):
        result = check_profile_freshness(
            self.profile,
            current_screen_size=(120, 90),
            current_region=None,
            current_dpi_scale_percent=125,
            observed_colors=None,
        )
        self.assertEqual(result["status"], "unverified")
        self.assertGreaterEqual(len(result["warnings"]), 2)

    def test_sample_profile_colors_uses_saved_local_positions(self):
        sampled = sample_profile_colors(self.profile, self.region_image)
        self.assertEqual(sampled["unavailable_color_ids"], [])
        self.assertEqual(sampled["mismatched_color_ids"], [])
        self.assertEqual(sampled["observed_colors"][self.profile["colors"][0]["id"]], (232, 78, 67))

    def test_small_region_marks_outside_samples_unavailable(self):
        tiny = Image.new("RGB", (10, 10), "white")
        sampled = sample_profile_colors(self.profile, tiny)
        self.assertEqual(len(sampled["unavailable_color_ids"]), 2)

    def test_invalid_dpi_and_status_are_rejected(self):
        with self.assertRaises(PaletteProfileError):
            create_palette_profile(self.palette, "Bad", dpi_scale_percent=500)
        invalid = json.loads(json.dumps(self.profile))
        invalid["colors"][0]["status"] = "maybe"
        with self.assertRaises(PaletteProfileError):
            validate_palette_profile(invalid)

    def test_duplicate_color_ids_are_rejected(self):
        invalid = json.loads(json.dumps(self.profile))
        invalid["colors"][1]["id"] = invalid["colors"][0]["id"]
        with self.assertRaises(PaletteProfileError):
            validate_palette_profile(invalid)

    def test_profile_requires_name_and_colors(self):
        with self.assertRaises(PaletteProfileError):
            create_palette_profile(self.palette, "  ")
        invalid = json.loads(json.dumps(self.profile))
        invalid["colors"] = []
        with self.assertRaises(PaletteProfileError):
            validate_palette_profile(invalid)


if __name__ == "__main__":
    unittest.main()
