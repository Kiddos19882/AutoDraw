"""Unit-level V5 brush switching guard; no game input in these tests."""
from types import SimpleNamespace

import pytest

from fill001_v5_handoff import (
    CANDIDATES, Fill001V5Error, V5BrushSequenceGuard,
    build_fill001_v5_source_plan,
)


class FakeSlider:
    def __init__(self, initial=10):
        self.calibration = SimpleNamespace(initial_value=initial)
        self.current_value = initial
        self.calls = []
        self.checked = 0

    def validate(self):
        self.checked += 1

    def before_stroke(self, executor, index, stroke):
        width = int(stroke.metadata["brush_value"])
        self.calls.append((index, width))
        self.current_value = width
        return f"Кисть {width} подтверждена"


@pytest.mark.parametrize("candidate,last", [(CANDIDATES[0], 2), (CANDIDATES[1], 3)])
def test_v5_brush_guard_all_29_strokes_through_existing_hook(candidate, last):
    plan = build_fill001_v5_source_plan(candidate)
    slider = FakeSlider()
    guard = V5BrushSequenceGuard(plan)
    guard.preflight(slider)
    for i, raw in enumerate(plan["strokes"], 1):
        stroke = SimpleNamespace(metadata=raw["metadata"])
        guard.before_stroke(slider, object(), i, stroke)
    guard.assert_complete()
    assert guard.verified_widths == [10] * 28 + [last]
    assert slider.calls == [(i, 10 if i < 29 else last) for i in range(1, 30)]


def test_v5_requires_exact_initial_width():
    guard = V5BrushSequenceGuard(build_fill001_v5_source_plan(CANDIDATES[0]))
    with pytest.raises(Fill001V5Error, match="brush width is not 10"):
        guard.preflight(FakeSlider(initial=1))


def test_v5_no_unvalidated_stroke_or_reordered_callback():
    plan = build_fill001_v5_source_plan(CANDIDATES[0])
    guard = V5BrushSequenceGuard(plan)
    slider = FakeSlider()
    stroke = SimpleNamespace(metadata=plan["strokes"][0]["metadata"])
    with pytest.raises(Fill001V5Error, match="preflight"):
        guard.before_stroke(slider, object(), 1, stroke)
    guard.preflight(slider)
    with pytest.raises(Fill001V5Error, match="order"):
        guard.before_stroke(slider, object(), 2, stroke)
    assert slider.calls == []


def test_v5_rejects_metadata_tampering_before_mouse_input():
    plan = build_fill001_v5_source_plan(CANDIDATES[1])
    guard = V5BrushSequenceGuard(plan)
    slider = FakeSlider()
    guard.preflight(slider)
    changed = dict(plan["strokes"][0]["metadata"])
    changed["brush_value"] = "3"
    with pytest.raises(Fill001V5Error, match="identity"):
        guard.before_stroke(slider, object(), 1, SimpleNamespace(metadata=changed))
    assert slider.calls == []


def test_v5_rejects_false_brush_confirmation():
    plan = build_fill001_v5_source_plan(CANDIDATES[0])
    guard = V5BrushSequenceGuard(plan)
    slider = FakeSlider()
    slider.before_stroke = lambda *_args: "claimed success"
    guard.preflight(slider)
    for i in range(1, 29):
        guard.before_stroke(slider, object(), i,
                            SimpleNamespace(metadata=plan["strokes"][i-1]["metadata"]))
    with pytest.raises(Fill001V5Error, match="did not verify"):
        guard.before_stroke(slider, object(), 29,
                            SimpleNamespace(metadata=plan["strokes"][28]["metadata"]))


def test_v5_guard_accepts_slider_calibrated_at_30_after_closed_loop_sets_10():
    plan = build_fill001_v5_source_plan(CANDIDATES[0])
    slider = FakeSlider(initial=30)
    slider.current_value = 10
    guard = V5BrushSequenceGuard(plan)
    guard.preflight(slider)
    assert guard.preflight_done is True
