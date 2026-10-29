from stage7_validator_rules import skeleton_transparency_error


def _result(pixel_count: int) -> dict:
    return {
        "painted_transparent_pixel_count": pixel_count,
        "transparent_stroke_samples": [
            {"stroke_id": f"skeleton-{index}", "transparent_pixels": [[index, 0]]}
            for index in range(pixel_count)
        ],
    }


def test_skeleton_validator_accepts_exactly_three_isolated_pixels() -> None:
    assert skeleton_transparency_error(_result(3), "boundary-report.json") is None


def test_skeleton_validator_rejects_four_transparent_pixels() -> None:
    error = skeleton_transparency_error(_result(4), "over-limit-report.json")
    assert error is not None
    assert "allowed maximum is 3" in error


def test_skeleton_validator_rejects_duplicate_pixel_coordinates() -> None:
    result = _result(2)
    result["transparent_stroke_samples"][1]["transparent_pixels"] = [[0, 0]]
    error = skeleton_transparency_error(result, "duplicate-report.json")
    assert error is not None
    assert "diagnostics do not match" in error


def test_skeleton_validator_rejects_multiple_pixels_from_one_stroke() -> None:
    result = {
        "painted_transparent_pixel_count": 2,
        "transparent_stroke_samples": [
            {"stroke_id": "skeleton-0", "transparent_pixels": [[0, 0], [1, 0]]}
        ],
    }
    error = skeleton_transparency_error(result, "multi-hit-report.json")
    assert error is not None
    assert "only isolated one-pixel hits per stroke" in error
