from __future__ import annotations

from PIL import Image
import pytest

from brush_experiment_capture import compare_images, crop_calibrated_regions


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
