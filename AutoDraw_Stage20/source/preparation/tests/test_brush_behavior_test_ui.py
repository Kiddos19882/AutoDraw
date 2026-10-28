from __future__ import annotations

import pytest

from brush_behavior_test_ui import TEST_CASES, build_brush_test_record


def test_brush_test_record_contains_reproducible_stroke_template() -> None:
    record = build_brush_test_record(
        brush_value=7,
        test_case="Горизонтальные линии",
        canvas_area={"x": 100, "y": 200, "width": 646, "height": 323},
        screen_area={"x": 500, "y": 300, "width": 646, "height": 323},
        screenshot_path="capture.png",
        execution_report_path="execution.json",
        execution_report={"status": "completed", "stroke_count": 5},
        notes="Проверка кисти 7",
        outcome="partial",
    )

    assert record["schema_version"] == 1
    assert record["record_type"] == "autodraw_brush_behavior_observation"
    assert record["brush_value"] == 7
    assert record["test_case"]["id"] == "horizontal_lengths"
    assert len(record["planned_strokes"]) == 5
    assert record["planned_strokes"][2]["points"] == [[20, 70], [70, 70]]
    assert record["screen_area"]["width"] == 646
    assert record["screenshot_path"] == "capture.png"
    assert record["execution_report_path"] == "execution.json"
    assert record["execution_report"]["stroke_count"] == 5
    assert record["outcome"] == "partial"
    assert record["measurement_fields"]["paint_points_before"] is None
    assert record["interpretation"]["automatic_execution_allowed"] is False


@pytest.mark.parametrize("brush_value", [0, 31, -1, True, 7.5])
def test_brush_test_record_rejects_invalid_brush_value(brush_value) -> None:
    with pytest.raises(ValueError):
        build_brush_test_record(brush_value=brush_value, test_case="Диагонали")


def test_all_test_cases_have_named_strokes_with_two_endpoints() -> None:
    assert len(TEST_CASES) >= 5
    for scenario in TEST_CASES.values():
        assert scenario["strokes"]
        for stroke in scenario["strokes"]:
            assert stroke["name"]
            assert len(stroke["points"]) == 2
            assert len(stroke["points"][0]) == 2
            assert len(stroke["points"][1]) == 2


def test_brush_test_record_rejects_unknown_case() -> None:
    with pytest.raises(ValueError, match="Неизвестный тест"):
        build_brush_test_record(brush_value=7, test_case="не существует")
