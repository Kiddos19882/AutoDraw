from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build_windows import copy_existing_user_data, copy_source_user_data, create_data_layout, replace_release


class BuildHelperTests(unittest.TestCase):
    def test_existing_user_data_is_copied_to_new_staging_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root / "old"
            new = root / "new"
            marker = old / "data" / "profiles" / "profiles.json"
            marker.parent.mkdir(parents=True)
            marker.write_text('{"profiles":["keep"]}', encoding="utf-8")
            copy_existing_user_data(old, new)
            self.assertEqual((new / "data" / "profiles" / "profiles.json").read_text(encoding="utf-8"), '{"profiles":["keep"]}')

    def test_data_layout_creates_missing_folders_without_overwriting_existing_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            profile = root / "data" / "profiles" / "profiles.json"
            profile.parent.mkdir(parents=True)
            profile.write_text("user profile data", encoding="utf-8")
            create_data_layout(root)
            self.assertEqual(profile.read_text(encoding="utf-8"), "user profile data")
            for name in ("profiles", "palettes", "projects", "results", "logs", "runtime"):
                self.assertTrue((root / "data" / name).is_dir())
            self.assertTrue((root / "data" / "results" / "paint_limit_tests").is_dir())
            self.assertTrue((root / "data" / "palettes" / "profiles").is_dir())
            self.assertTrue((root / "data" / "results" / "color_scanline_plans").is_dir())

    def test_replace_release_swaps_new_build_and_removes_previous_after_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            final = root / "AutoDrawPortable"
            staging = root / ".staging"
            backup = root / ".backup"
            (final / "data" / "profiles").mkdir(parents=True)
            (final / "data" / "profiles" / "profiles.json").write_text("user data", encoding="utf-8")
            (staging / "apps").mkdir(parents=True)
            (staging / "AutoDraw.exe").write_text("new binary placeholder", encoding="utf-8")
            replace_release(staging, final, backup)
            self.assertTrue((final / "AutoDraw.exe").is_file())
            self.assertFalse(staging.exists())
            self.assertFalse(backup.exists())

    def test_replace_release_works_for_first_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            final = root / "AutoDrawPortable"
            staging = root / ".staging"
            backup = root / ".backup"
            staging.mkdir()
            (staging / "AutoDraw.exe").write_text("binary", encoding="utf-8")
            replace_release(staging, final, backup)
            self.assertTrue((final / "AutoDraw.exe").exists())


    def test_source_data_is_seeded_into_first_build(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_profile = root / "source" / "data" / "palettes" / "profiles" / "palette.json"
            source_profile.parent.mkdir(parents=True)
            source_profile.write_text('{"colors":[]}', encoding="utf-8")
            staging = root / "staging"
            copy_source_user_data(source_profile.parents[2].parents[0], staging)
            copied = staging / "data" / "palettes" / "profiles" / "palette.json"
            self.assertTrue(copied.is_file())
            self.assertEqual(copied.read_text(encoding="utf-8"), '{"colors":[]}')

    def test_existing_release_data_overrides_source_seed_data(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            staging = root / "staging"
            old = root / "old_release"
            seed = source / "data" / "profiles" / "settings.json"
            seed.parent.mkdir(parents=True)
            seed.write_text("source version", encoding="utf-8")
            copy_source_user_data(source, staging)
            previous = old / "data" / "profiles" / "settings.json"
            previous.parent.mkdir(parents=True)
            previous.write_text("existing user version", encoding="utf-8")
            copy_existing_user_data(old, staging)
            self.assertEqual((staging / "data" / "profiles" / "settings.json").read_text(encoding="utf-8"), "existing user version")


if __name__ == "__main__":
    unittest.main(verbosity=2)
