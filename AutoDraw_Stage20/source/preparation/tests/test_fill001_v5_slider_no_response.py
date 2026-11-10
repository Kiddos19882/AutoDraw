"""Regression: V5 brush control must stop at the first confirmed no-response.

No real PyAutoGUI input, no game, no Stage6 side effects.
"""
from types import SimpleNamespace

import pytest

from drawing.color_plan_execution import (
    BrushSliderCalibration, BrushSliderController, ColorPlanExecutionError,
)
from fill001_v5_stage6_execution import V5BrushSliderController


def _controller(*, initial=30):
    calibration = BrushSliderCalibration(
        x_at_min=100, x_at_max=390, y=100,
        initial_value=initial, screen_width=1920,
        screen_height=1080, confirmed=True,
    )
    roi={"x":483,"y":243,"width":694,"height":363}
    return V5BrushSliderController(
        calibration, roi,
        current_screen_size_provider=lambda:(1920,1080),
        monitor_radius_provider=lambda **kwargs:{
            "radius":initial,
            "observed_at_utc":"2026-11-10T10:15:15.000+00:00",
        },
    )


def test_v5_stops_after_first_unchanged_radius_with_diagnostics(monkeypatch):
    slider=_controller(initial=30)
    movements=[]
    monkeypatch.setattr(
        V5BrushSliderController, "_drag_to",
        lambda self, executor, old_x, target_x: movements.append((old_x,target_x)),
    )
    monkeypatch.setattr(
        BrushSliderController, "_wait_for_stable_radius",
        lambda self, executor, after_utc:{
            "radius":30,"observed_at_utc":"2026-11-10T10:15:15.000+00:00",
        },
    )
    with pytest.raises(ColorPlanExecutionError,match="первый drag.*не изменил радиус"):
        slider.select_value(SimpleNamespace(),10)
    assert len(movements)==1
    assert slider.current_value==30
    assert slider.last_no_response=={
        "requested_radius":10, "radius_before":30,
        "observed_radius":30,
        "observed_at_utc":"2026-11-10T10:15:15.000+00:00",
        "slider_x_at_min":100, "slider_x_at_max":390,
        "slider_y":100,
    }


def test_v5_successful_first_closed_loop_change_retains_normal_behavior(monkeypatch):
    slider=_controller(initial=30)
    movements=[]
    monkeypatch.setattr(
        V5BrushSliderController,"_drag_to",
        lambda self,executor,old_x,target_x:movements.append((old_x,target_x)),
    )
    monkeypatch.setattr(
        BrushSliderController,"_wait_for_stable_radius",
        lambda self,executor,after_utc:{
            "radius":10,"observed_at_utc":"2026-11-10T10:15:15.000+00:00",
        },
    )
    message=slider.select_value(SimpleNamespace(),10)
    assert "Выбрана кисть 10" in message
    assert len(movements)==1
    assert slider.current_value==10
    assert slider.last_no_response is None


def test_production_controller_not_modified_by_v5_watchdog():
    assert V5BrushSliderController is not BrushSliderController
    assert (
        V5BrushSliderController._wait_for_stable_radius
        is not BrushSliderController._wait_for_stable_radius
    )
