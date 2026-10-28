from __future__ import annotations

import json

import pytest

from brush_calibration import (
    BrushCalibrationError,
    adapt_profile_to_screen,
    create_default_profile,
    load_profile,
    missing_required_fields,
    normalize_point,
    normalize_region,
    save_profile,
    validate_profile,
)


def _set_point(profile, key, x, y, status="set"):
    profile["points"][key] = {"x": x, "y": y}
    profile["status"]["points"][key] = status


def _set_region(profile, key, x, y, width, height, status="set"):
    profile["regions"][key] = {"x": x, "y": y, "width": width, "height": height}
    profile["status"]["regions"][key] = status


def test_default_profile_is_partial_and_valid():
    profile = create_default_profile((1920, 1080))
    assert validate_profile(profile) == profile
    assert profile["environment"]["screen_width"] == 1920
    assert profile["points"]["clear_board"] is None
    assert profile["regions"]["paint_meter_area"] is None
    assert missing_required_fields(profile) == ["clear_board", "board_area", "paint_meter_area"]


def test_normalize_point_rejects_out_of_screen_coordinates():
    assert normalize_point(10, 20, (1920, 1080)) == {"x": 10, "y": 20}
    with pytest.raises(BrushCalibrationError, match="за пределами"):
        normalize_point(1920, 20, (1920, 1080))
    with pytest.raises(BrushCalibrationError):
        normalize_point(True, 20, (1920, 1080))


def test_normalize_region_orders_corners_and_checks_screen():
    assert normalize_region(80, 60, 10, 20, (1920, 1080)) == {
        "x": 10, "y": 20, "width": 70, "height": 40
    }
    with pytest.raises(BrushCalibrationError, match="слишком мала"):
        normalize_region(10, 10, 11, 30, (1920, 1080))
    with pytest.raises(BrushCalibrationError, match="за пределы"):
        normalize_region(10, 10, 2000, 30, (1920, 1080))


def test_validate_rejects_point_without_matching_status():
    profile = create_default_profile((1920, 1080))
    profile["points"]["clear_board"] = {"x": 20, "y": 30}
    with pytest.raises(BrushCalibrationError, match="not_set"):
        validate_profile(profile)

def test_validate_rejects_point_missing_coordinate_without_leaking_key_error():
    profile = create_default_profile((1920, 1080))
    profile["points"]["clear_board"] = {"x": 20}
    profile["status"]["points"]["clear_board"] = "set"
    with pytest.raises(BrushCalibrationError, match="X и Y"):
        validate_profile(profile)


def test_missing_fields_require_the_correct_brush_control():
    profile = create_default_profile((1920, 1080))
    _set_point(profile, "clear_board", 10, 10)
    _set_region(profile, "board_area", 100, 100, 646, 323)
    _set_region(profile, "paint_meter_area", 100, 80, 120, 8)
    assert missing_required_fields(profile, 7) == ["brush_control_mode"]
    profile["brush_control_mode"] = "presets"
    assert missing_required_fields(profile, 7) == ["brush_7"]
    _set_point(profile, "brush_7", 15, 15)
    assert missing_required_fields(profile, 7) == []
    assert missing_required_fields(profile, 1) == ["brush_control_mode"]
    profile["brush_control_mode"] = "slider"
    assert missing_required_fields(profile, 1) == ["brush_slider_value_1", "brush_slider_value_30"]


def test_screen_change_marks_existing_coordinates_for_review_and_drops_outside_values():
    profile = create_default_profile((1920, 1080))
    _set_point(profile, "clear_board", 1900, 100)
    _set_region(profile, "board_area", 100, 100, 646, 323)
    adapted, changed = adapt_profile_to_screen(profile, (1280, 720))
    assert changed is True
    assert adapted["points"]["clear_board"] is None
    assert adapted["status"]["points"]["clear_board"] == "not_set"
    assert adapted["regions"]["board_area"] == {"x": 100, "y": 100, "width": 646, "height": 323}
    assert adapted["status"]["regions"]["board_area"] == "needs_review"
    assert adapted["environment"]["screen_width"] == 1280
    validate_profile(adapted)


def test_save_load_profile_round_trip_is_atomic_and_valid(tmp_path):
    path = tmp_path / "calibration.json"
    profile = create_default_profile((1920, 1080))
    _set_point(profile, "clear_board", 12, 34)
    save_profile(path, profile)
    assert json.loads(path.read_text(encoding="utf-8"))["points"]["clear_board"] == {"x": 12, "y": 34}
    assert load_profile(path) == profile
    assert not list(tmp_path.glob("*.tmp"))
