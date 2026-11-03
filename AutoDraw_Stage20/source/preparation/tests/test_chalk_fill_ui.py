from __future__ import annotations

from PIL import Image

import chalk_fill_ui


class _BrushTab:
    def __init__(self, region):
        self.region = region

    def get_calibration_profile(self):
        return {
            "screen_size": {"width": 1000, "height": 800},
            "regions": {"board_area": dict(self.region)},
        }

    def get_canvas_area(self):
        return dict(self.region)


def test_fill_ui_captures_actual_calibrated_roi_without_460x240_requirement(
    tmp_path, monkeypatch
):
    region = {"x": 120, "y": 80, "width": 581, "height": 304}
    screen = Image.new("RGB", (1000, 800), (240, 240, 240))
    tab = chalk_fill_ui.Fill001Tab.__new__(chalk_fill_ui.Fill001Tab)
    tab.output_dir = tmp_path
    tab.brush_tab = _BrushTab(region)
    tab.capture_region = dict(region)

    monkeypatch.setattr(chalk_fill_ui.ImageGrab, "grab", lambda: screen.copy())
    monkeypatch.setattr(chalk_fill_ui.pyautogui, "mouseUp", lambda: None)
    monkeypatch.setattr(chalk_fill_ui.pyautogui, "moveTo", lambda *_args: None)
    monkeypatch.setattr(chalk_fill_ui.time, "sleep", lambda *_args: None)
    monkeypatch.setattr(
        chalk_fill_ui,
        "_cursor_safe_point_outside_region",
        lambda *_args, **_kwargs: (10, 10),
    )

    path = tab._capture_board_png({"task_id": "roi-581x304"}, phase="after")

    with Image.open(path) as captured:
        assert captured.size == (581, 304)
        assert captured.getpixel((0, 0)) == (240, 240, 240)
