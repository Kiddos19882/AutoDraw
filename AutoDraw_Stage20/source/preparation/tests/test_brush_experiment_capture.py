from __future__ import annotations

from PIL import Image
import pytest

from brush_experiment_capture import (
    compare_images, crop_calibrated_regions,
    measure_meter_fill_against_baseline, evaluate_meter_restoration, evaluate_board_clear,
    measure_stroke_visibility,
)


def test_crops_board_and_paint_meter_from_independent_calibrated_regions():
    screen = Image.new("RGB", (100, 80), "white")
    screen.putpixel((10, 10), (255, 0, 0))
    screen.putpixel((70, 50), (0, 0, 255))
    regions = {
        "board_area": {"x": 5, "y": 5, "width": 20, "height": 20},
        "paint_meter_area": {"x": 60, "y": 40, "width": 25, "height": 15},
    }

    crops = crop_calibrated_regions(screen, regions)

    assert crops["board_area"].size == (20, 20)
    assert crops["board_area"].getpixel((5, 5)) == (255, 0, 0)
    assert crops["paint_meter_area"].size == (25, 15)
    assert crops["paint_meter_area"].getpixel((10, 10)) == (0, 0, 255)


def test_crop_rejects_missing_and_out_of_bounds_regions():
    screen = Image.new("RGB", (20, 20), "white")
    with pytest.raises(ValueError, match="не задана"):
        crop_calibrated_regions(screen, {"board_area": {"x": 0, "y": 0, "width": 10, "height": 10}})
    with pytest.raises(ValueError, match="выходит за снимок"):
        crop_calibrated_regions(screen, {
            "board_area": {"x": 15, "y": 0, "width": 10, "height": 10},
            "paint_meter_area": {"x": 0, "y": 0, "width": 10, "height": 10},
        })


def test_compare_images_reports_exact_match_and_pixel_changes():
    before = Image.new("RGB", (4, 4), "black")
    same = before.copy()
    changed = before.copy()
    changed.putpixel((2, 1), (255, 255, 255))

    assert compare_images(before, same)["exact_match"] is True
    result = compare_images(before, changed)
    assert result["changed_pixels"] == 1
    assert result["changed_percent"] == 6.25
    assert result["pixel_similarity_percent"] == 93.75
    assert result["exact_match"] is False


def test_compare_images_rejects_different_dimensions():
    with pytest.raises(ValueError, match="различаются"):
        compare_images(Image.new("RGB", (2, 2)), Image.new("RGB", (3, 2)))


def _meter(width=100, height=12, fill=100):
    image = Image.new("RGB", (width, height), (35, 35, 35))
    for x in range(round(width * fill / 100)):
        for y in range(height):
            image.putpixel((x, y), (40, 190, 80))
    return image


def test_meter_estimates_right_side_consumption_against_full_baseline():
    result = measure_meter_fill_against_baseline(_meter(), _meter(fill=70))
    assert result["status"] == "estimated"
    assert result["filled_width_px"] == 70
    assert result["fill_percent"] == 70.0


def test_identical_meter_is_not_claimed_as_proven_full():
    result = measure_meter_fill_against_baseline(_meter(), _meter())
    assert result["status"] == "unchanged_or_full"
    assert result["confidence"] == "low"


def test_scattered_meter_changes_are_inconclusive():
    current = _meter()
    for x in (10, 30, 50, 70):
        for y in range(2, 10):
            current.putpixel((x, y), (0, 0, 0))
    result = measure_meter_fill_against_baseline(_meter(), current)
    assert result["status"] == "inconclusive"
    assert result["fill_fraction"] is None


def test_exact_baseline_after_clear_is_restored():
    assert evaluate_meter_restoration(_meter(), _meter())["status"] == "restored"


def test_reduced_fill_after_clear_is_not_restored():
    assert evaluate_meter_restoration(_meter(), _meter(fill=75))["status"] == "not_restored"

def test_board_clear_classifies_match_to_explicit_blank_reference():
    blank = Image.new("RGB", (20, 10), (245, 245, 245))
    result = evaluate_board_clear(blank, blank.copy())
    assert result["status"] == "restored"
    assert result["reference_type"] == "explicit_blank_board_roi"
    assert result["changed_percent"] == 0


def test_board_clear_detects_remaining_marks_against_blank_reference():
    blank = Image.new("RGB", (20, 10), (245, 245, 245))
    current = blank.copy()
    for x in range(5, 10):
        current.putpixel((x, 4), (20, 20, 20))
    result = evaluate_board_clear(blank, current, tolerance_percent=0.15)
    assert result["status"] == "not_restored"
    assert result["changed_percent"] > 0.15


def test_board_clear_rejects_different_sizes_and_invalid_tolerance():
    blank = Image.new("RGB", (20, 10), "white")
    with pytest.raises(ValueError, match="различаются"):
        evaluate_board_clear(blank, Image.new("RGB", (19, 10), "white"))
    with pytest.raises(ValueError, match="от 0 до 5"):
        evaluate_board_clear(blank, blank, tolerance_percent=10)


def test_stroke_visibility_detects_change_in_independent_roi():
    blank = Image.new("RGB", (80, 30), (245, 245, 245))
    current = blank.copy()
    for x in range(10, 21):
        current.putpixel((x, 10), (20, 20, 20))
    result = measure_stroke_visibility(
        blank, current,
        [{"name": "horizontal_10", "points": [{"x": 10, "y": 10}, {"x": 20, "y": 10}]}],
        padding_px=2,
    )
    assert result["status"] == "analyzed"
    assert result["visible_change_count"] == 1
    assert result["results"][0]["status"] == "visible_change_detected"
    assert result["results"][0]["changed_pixels_in_roi"] == 11


def test_stroke_visibility_does_not_claim_a_missing_stroke_is_visible():
    blank = Image.new("RGB", (80, 30), (245, 245, 245))
    result = measure_stroke_visibility(
        blank, blank.copy(),
        [{"name": "horizontal_10", "points": [{"x": 10, "y": 10}, {"x": 20, "y": 10}]}],
    )
    assert result["no_change_count"] == 1
    assert result["results"][0]["status"] == "no_change_detected"


def test_stroke_visibility_marks_overlapping_rois_ambiguous():
    blank = Image.new("RGB", (80, 30), (245, 245, 245))
    current = blank.copy()
    current.putpixel((15, 10), (0, 0, 0))
    result = measure_stroke_visibility(
        blank, current,
        [
            {"name": "first", "points": [{"x": 10, "y": 10}, {"x": 20, "y": 10}]},
            {"name": "second", "points": [{"x": 18, "y": 10}, {"x": 28, "y": 10}]},
        ],
        padding_px=4,
    )
    assert result["ambiguous_count"] == 2
    assert all(item["status"] == "ambiguous_overlap" for item in result["results"])
