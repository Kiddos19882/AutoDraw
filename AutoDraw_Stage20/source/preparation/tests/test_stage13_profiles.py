from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from profile_manager import (
    CalibrationSettings,
    ProfileStore,
    ProfileValidationError,
    ScreenArea,
    WorkspaceProfile,
)


class WorkspaceProfileTests(unittest.TestCase):
    def test_default_profile_uses_calibrated_stage6_values(self):
        profile = WorkspaceProfile.create_default()
        self.assertEqual((profile.canvas_width, profile.canvas_height), (646, 323))
        self.assertEqual(profile.fit_mode, "contain")
        self.assertEqual(
            profile.calibration.to_stage6_settings(),
            {
                "point_step_px": 2.0,
                "point_delay_ms": 10,
                "after_mouse_up_ms": 20,
                "before_mouse_down_ms": 20,
                "after_mouse_down_ms": 40,
                "end_hold_ms": 50,
                "countdown_seconds": 5,
            },
        )

    def test_profile_serialization_round_trip(self):
        profile = replace(
            WorkspaceProfile.create_default("Second monitor"),
            canvas_width=800,
            canvas_height=600,
            fit_mode="cover",
            brightness=10,
            contrast=1.25,
            denoise_level=1,
            threshold_mode="manual",
            threshold=143,
            row_step_px=3,
            screen_area=ScreenArea(120, 80, 800, 600, 1920, 1080),
            calibration=CalibrationSettings(2.0, 10, 20, 20, 40, 50, 5),
        )
        loaded = WorkspaceProfile.from_dict(profile.to_dict())
        self.assertEqual(loaded, profile)

    def test_stage6_target_profile_shape_is_compatible(self):
        profile = replace(
            WorkspaceProfile.create_default(),
            screen_area=ScreenArea(40, 60, 646, 323),
        )
        self.assertEqual(
            profile.to_stage6_target_profile(),
            {"area": {"x": 40, "y": 60, "width": 646, "height": 323}},
        )

    def test_stage6_target_export_requires_screen_area(self):
        with self.assertRaises(ProfileValidationError):
            WorkspaceProfile.create_default().to_stage6_target_profile()

    def test_stage6_execution_settings_have_expected_keys(self):
        profile = WorkspaceProfile.create_default()
        payload = profile.to_stage6_settings()
        self.assertEqual(
            set(payload),
            {"point_step_px", "point_delay_ms", "after_mouse_up_ms", "before_mouse_down_ms",
             "after_mouse_down_ms", "end_hold_ms", "countdown_seconds"},
        )

    def test_import_stage6_target_profile(self):
        imported = WorkspaceProfile.from_external_dict(
            {"area": {"x": 15, "y": 25, "width": 700, "height": 400}},
            name="Imported target",
        )
        self.assertEqual((imported.canvas_width, imported.canvas_height), (700, 400))
        self.assertEqual(imported.screen_area, ScreenArea(15, 25, 700, 400))

    def test_import_stage12_canvas_profile(self):
        imported = WorkspaceProfile.from_external_dict({"width": 900, "height": 500})
        self.assertEqual((imported.canvas_width, imported.canvas_height), (900, 500))
        self.assertIsNone(imported.screen_area)

    def test_import_stage6_execution_settings(self):
        imported = WorkspaceProfile.from_external_dict(
            {
                "point_step_px": 3.0,
                "point_delay_ms": 12,
                "after_mouse_up_ms": 25,
                "before_mouse_down_ms": 30,
                "after_mouse_down_ms": 45,
                "end_hold_ms": 55,
                "countdown_seconds": 7,
            }
        )
        self.assertEqual(imported.calibration.point_step_px, 3.0)
        self.assertEqual(imported.calibration.point_delay_ms, 12)
        self.assertEqual(imported.calibration.countdown_seconds, 7)

    def test_profile_rejects_canvas_over_pixel_limit(self):
        profile = replace(WorkspaceProfile.create_default(), canvas_width=10000, canvas_height=5000)
        with self.assertRaises(ProfileValidationError):
            profile.validate()

    def test_profile_rejects_invalid_calibration(self):
        with self.assertRaises(ProfileValidationError):
            CalibrationSettings(point_step_px=0.1).validate()
        with self.assertRaises(ProfileValidationError):
            CalibrationSettings(point_delay_ms=101).validate()

    def test_screen_area_cannot_exceed_known_display_size(self):
        with self.assertRaises(ProfileValidationError):
            ScreenArea(1900, 0, 200, 400, 1920, 1080).validate()

    def test_profile_store_creates_default_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProfileStore(Path(temp_dir) / "profiles" / "profiles.json")
            profiles = store.load()
            self.assertEqual(len(profiles), 1)
            self.assertTrue(store.path.exists())
            second = replace(WorkspaceProfile.create_default("Canvas B"), canvas_width=800)
            profiles = store.upsert(second)
            self.assertEqual(len(profiles), 2)
            reloaded = store.load()
            found = next(item for item in reloaded if item.profile_id == second.profile_id)
            self.assertEqual(found.canvas_width, 800)

    def test_profile_store_updates_existing_profile_without_duplicate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProfileStore(Path(temp_dir) / "profiles.json")
            initial = store.load()[0]
            changed = replace(initial, name="Renamed", canvas_width=777)
            profiles = store.upsert(changed)
            self.assertEqual(len(profiles), 1)
            self.assertEqual(profiles[0].name, "Renamed")
            self.assertEqual(profiles[0].canvas_width, 777)

    def test_profile_store_deletes_profile_but_preserves_last_profile_rule(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProfileStore(Path(temp_dir) / "profiles.json")
            first = store.load()[0]
            with self.assertRaises(ProfileValidationError):
                store.delete(first.profile_id)
            second = replace(WorkspaceProfile.create_default("Second"), profile_id="second-id")
            store.upsert(second)
            remaining = store.delete(first.profile_id)
            self.assertEqual([profile.profile_id for profile in remaining], ["second-id"])

    def test_duplicate_profile_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "profiles.json"
            one = WorkspaceProfile.create_default()
            path.write_text(json.dumps({"schema_version": 1, "profiles": [one.to_dict(), one.to_dict()]}), encoding="utf-8")
            with self.assertRaises(ProfileValidationError):
                ProfileStore(path).load()

    def test_invalid_external_values_are_rejected(self):
        with self.assertRaises(ProfileValidationError):
            WorkspaceProfile.from_external_dict({"width": 0, "height": 10})
        with self.assertRaises(ProfileValidationError):
            WorkspaceProfile.from_external_dict({"point_step_px": 99})

    def test_profile_export_json_is_readable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile = WorkspaceProfile.create_default("Export me")
            output = Path(temp_dir) / "profile.json"
            ProfileStore.export_json(output, profile.to_dict())
            doc = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(doc["name"], "Export me")
            self.assertEqual(doc["workspace"]["canvas_width"], 646)


if __name__ == "__main__":
    unittest.main(verbosity=2)
