from __future__ import annotations

import unittest
import numpy as np
from PIL import Image, ImageDraw

# Reuse the Stage 14 executor test doubles so every test in this suite talks to the
# same pyautogui instance imported by MouseExecutor. No real desktop input is sent.
from test_execution_hardening import FAKE_PYAUTOGUI, FastEvent, FakeGlobalHotKeys

from palette_detection import create_palette_document
from palette_profiles import create_palette_profile
from color_scanline import build_color_scanline_plan, render_color_scanline_preview
from drawing.color_plan_execution import (
    BrushSliderCalibration,
    BrushSliderController,
    ColorPlanExecutionError,
    ColorPlanExecutionHooks,
    adaptive_brush_plan_to_drawing_plan,
    build_brush_visual_test_plan,
    build_palette_targets,
    normalize_brush_slider_points,
    color_plan_to_drawing_plan,
)
from brush_planner import build_adaptive_brush_plan
from geometry_color_plan import build_geometry_color_plan
from models import Point, Stroke
from drawing.mouse_executor import ExecutorConfig, MouseExecutor


def make_profile_and_plan():
    screen = Image.new("RGB", (160, 100), "#FFFFFF")
    draw = ImageDraw.Draw(screen)
    draw.rectangle((20, 20, 30, 30), fill="#E84E43")
    draw.rectangle((45, 20, 55, 30), fill="#37A85A")
    palette_doc = create_palette_document(
        [
            {"name": "Red", "hex": "#E84E43", "rgb": [232, 78, 67], "screen_x": 25, "screen_y": 25,
             "local_x": 15, "local_y": 15, "source": "manual"},
            {"name": "Green", "hex": "#37A85A", "rgb": [55, 168, 90], "screen_x": 50, "screen_y": 25,
             "local_x": 40, "local_y": 15, "source": "manual"},
        ],
        screen_size=screen.size,
        region={"x": 10, "y": 10, "width": 65, "height": 30},
        metadata={"method": "screenshot-assisted"},
    )
    profile = create_palette_profile(palette_doc, "Test palette", browser_label="Test board", dpi_scale_percent=100)
    for color in profile["colors"]:
        color["status"] = "confirmed"
    palette_for_plan = {"colors": profile["colors"]}
    color_plan = build_color_scanline_plan(
        np.asarray([[0, 1, 1, 0]], dtype=np.int32), palette_for_plan, plan_name="Color test plan"
    )
    return screen, profile, color_plan


class ColorPlanExecutionTests(unittest.TestCase):
    def setUp(self):
        FAKE_PYAUTOGUI.reset()
        FAKE_PYAUTOGUI.down_calls = 0
        FAKE_PYAUTOGUI.up_calls = 0
        FAKE_PYAUTOGUI._size = (160, 100)
        FAKE_PYAUTOGUI.on_move = None
        FakeGlobalHotKeys.trigger_alt_on_start = False
        self.screen, self.profile, self.color_plan = make_profile_and_plan()

    def config(self):
        return ExecutorConfig(
            point_step_px=2.0,
            point_delay_ms=0,
            after_mouse_up_ms=0,
            before_mouse_down_ms=0,
            after_mouse_down_ms=0,
            end_hold_ms=0,
            countdown_seconds=1,
        )

    def hooks(self, **kwargs):
        defaults = {
            "current_screen_size_provider": lambda: (160, 100),
            "screenshot_provider": lambda: self.screen.copy(),
            "dpi_scale_provider": lambda: 100,
        }
        defaults.update(kwargs)
        return ColorPlanExecutionHooks(self.color_plan, self.profile, **defaults)

    def test_color_plan_converts_without_losing_order_or_color_metadata(self):
        converted = color_plan_to_drawing_plan(self.color_plan)
        self.assertEqual((converted.width, converted.height), (4, 1))
        self.assertEqual([s.metadata["palette_index"] for s in converted.strokes], ["0", "1", "0"])
        self.assertEqual([s.metadata["color_hex"] for s in converted.strokes], ["#E84E43", "#37A85A", "#E84E43"])
        self.assertEqual([s.points[0].x for s in converted.strokes], [0.0, 1.0, 3.0])
        # The two single-pixel clicks from Stage 19 become real one-pixel drags.
        self.assertEqual(converted.strokes[0].points[1].x - converted.strokes[0].points[0].x, 1.0)
        self.assertEqual(converted.strokes[2].points[1].x - converted.strokes[2].points[0].x, 1.0)
        self.assertEqual(converted.strokes[0].metadata["single_pixel_expansion"], "horizontal_1px_same_color")
        self.assertEqual(converted.strokes[2].metadata["palette_index"], "0")
        self.assertAlmostEqual(converted.total_drawing_length_px, 3.0)

    def test_single_pixel_at_right_edge_uses_canvas_boundary_not_previous_pixel(self):
        converted = color_plan_to_drawing_plan(self.color_plan)
        last = converted.strokes[-1]
        self.assertEqual(last.points[0].x, 3.0)
        self.assertEqual(last.points[1].x, 4.0)  # DrawingPlan permits the right border.
        self.assertEqual(last.metadata["color_hex"], "#E84E43")
        converted.validate_bounds()

    def test_one_by_one_single_pixel_becomes_a_border_stroke(self):
        from color_scanline import build_color_scanline_plan, render_color_scanline_preview
        import numpy as np
        tiny_plan = build_color_scanline_plan(np.asarray([[0]], dtype=np.int32), self.color_plan["palette"])
        converted = color_plan_to_drawing_plan(tiny_plan)
        self.assertEqual((converted.width, converted.height), (1, 1))
        self.assertEqual(converted.strokes[0].points[0].x, 0.0)
        self.assertEqual(converted.strokes[0].points[1].x, 1.0)
        converted.validate_bounds()

    def test_executor_preview_shows_expanded_single_pixel_stroke(self):
        import numpy as np
        plan = build_color_scanline_plan(
            np.asarray([[-1, 0, -1, -1], [-1, -1, -1, -1]], dtype=np.int32),
            self.color_plan["palette"],
        )
        exact_preview = render_color_scanline_preview(plan)
        execution_preview = render_color_scanline_preview(plan, expand_single_pixel_strokes=True)
        self.assertEqual(exact_preview.getpixel((1, 0)), (232, 78, 67, 255))
        self.assertEqual(exact_preview.getpixel((2, 0))[3], 0)
        self.assertEqual(execution_preview.getpixel((2, 0)), (232, 78, 67, 255))

    def test_adaptive_plan_converts_only_for_matching_source_color_plan(self):
        index_map = np.zeros((5, 50), dtype=np.int32)
        source = build_color_scanline_plan(
            index_map, self.color_plan["palette"], plan_name="adaptive conversion source"
        )
        brush_plan = build_adaptive_brush_plan(
            index_map,
            source,
            brush_scale_x=50 / 460,
            brush_scale_y=5 / 240,
            calibration_confirmed=True,
        )
        converted = adaptive_brush_plan_to_drawing_plan(brush_plan, source)
        self.assertEqual((converted.width, converted.height), (50, 5))
        self.assertTrue(all(stroke.metadata["adaptive_brush_plan"] == "true" for stroke in converted.strokes))
        self.assertTrue(all(stroke.metadata["line_extension_px_override"] == "0" for stroke in converted.strokes))
        self.assertIn("brush_value", converted.strokes[1].metadata)
        self.assertEqual(converted.strokes[1].metadata["brush_value"], "20")

        different_source = build_color_scanline_plan(
            index_map, self.color_plan["palette"], plan_name="different source"
        )
        with self.assertRaisesRegex(ColorPlanExecutionError, "другого цветного плана"):
            adaptive_brush_plan_to_drawing_plan(brush_plan, different_source)

        wrong_scale = build_adaptive_brush_plan(
            index_map, source, calibration_confirmed=True
        )
        with self.assertRaisesRegex(ColorPlanExecutionError, "Масштаб кисти адаптивного плана"):
            adaptive_brush_plan_to_drawing_plan(wrong_scale, source)

    def test_adaptive_plan_cannot_move_stroke_outside_its_source_run(self):
        import copy

        index_map = np.zeros((5, 50), dtype=np.int32)
        source = build_color_scanline_plan(
            index_map, self.color_plan["palette"], plan_name="adaptive geometry source"
        )
        brush_plan = build_adaptive_brush_plan(
            index_map, source, brush_scale_x=50 / 460, brush_scale_y=5 / 240,
            calibration_confirmed=True,
        )
        tampered = copy.deepcopy(brush_plan)
        tampered["strokes"][1]["points"][1]["x"] = 50
        with self.assertRaisesRegex(ColorPlanExecutionError, "выходит за границы"):
            adaptive_brush_plan_to_drawing_plan(tampered, source)

    def test_adaptive_plan_cannot_change_scanline_row_or_reverse_stroke_direction(self):
        import copy

        index_map = np.zeros((5, 50), dtype=np.int32)
        source = build_color_scanline_plan(
            index_map, self.color_plan["palette"], plan_name="adaptive row source"
        )
        brush_plan = build_adaptive_brush_plan(
            index_map, source, brush_scale_x=50 / 460, brush_scale_y=5 / 240,
            calibration_confirmed=True,
        )
        wrong_row = copy.deepcopy(brush_plan)
        wrong_row["strokes"][0]["points"][0]["y"] += 1
        with self.assertRaisesRegex(ColorPlanExecutionError, "горизонтальное направление|исходного участка"):
            adaptive_brush_plan_to_drawing_plan(wrong_row, source)

        reversed_run = copy.deepcopy(brush_plan)
        reversed_run["strokes"][0]["points"] = list(reversed(reversed_run["strokes"][0]["points"]))
        with self.assertRaisesRegex(ColorPlanExecutionError, "горизонтальное направление"):
            adaptive_brush_plan_to_drawing_plan(reversed_run, source)

    def test_brush_slider_calibration_interpolates_and_rejects_stale_screen(self):
        calibration = BrushSliderCalibration(
            x_at_min=100, x_at_max=390, y=200, initial_value=7,
            screen_width=1920, screen_height=1080, confirmed=True,
        )
        self.assertEqual(calibration.coordinate_for_value(1), 100)
        self.assertEqual(calibration.coordinate_for_value(30), 390)
        self.assertEqual(calibration.coordinate_for_value(16), 250)
        calibration.validate((1920, 1080), {"x": 400, "y": 300, "width": 600, "height": 300})
        with self.assertRaisesRegex(ColorPlanExecutionError, "Разрешение экрана изменилось"):
            calibration.validate((1280, 720), {"x": 400, "y": 300, "width": 600, "height": 300})

    def test_brush_slider_mouse_points_produce_track_coordinates(self):
        self.assertEqual(
            normalize_brush_slider_points((100, 200), (390, 202)),
            (100, 390, 201),
        )

    def test_brush_slider_mouse_points_reject_wrong_order_or_short_track(self):
        with self.assertRaisesRegex(ColorPlanExecutionError, "Сначала отметьте позицию"):
            normalize_brush_slider_points((390, 200), (100, 200))
        with self.assertRaisesRegex(ColorPlanExecutionError, "не менее 29 px"):
            normalize_brush_slider_points((100, 200), (120, 200))

    def test_brush_slider_mouse_points_reject_different_heights(self):
        with self.assertRaisesRegex(ColorPlanExecutionError, "разных высотах"):
            normalize_brush_slider_points((100, 200), (390, 220))

    def test_brush_visual_test_plan_contains_separated_strokes_for_sizes(self):
        plan = build_brush_visual_test_plan(260, 180)
        self.assertEqual(plan.name, "Визуальный тест изменения размера кисти")
        self.assertEqual(
            [stroke.metadata["brush_value"] for stroke in plan.strokes],
            ["1", "7", "14", "20"],
        )
        self.assertEqual([stroke.name for stroke in plan.strokes], [
            "Проверка кисти 1", "Проверка кисти 7", "Проверка кисти 14", "Проверка кисти 20"
        ])
        ys = [stroke.points[0].y for stroke in plan.strokes]
        self.assertEqual(ys, sorted(ys))
        self.assertGreaterEqual(min(b - a for a, b in zip(ys, ys[1:])), 30)
        self.assertTrue(all(stroke.metadata["line_extension_px_override"] == "0" for stroke in plan.strokes))
        plan.validate_bounds()

    def test_brush_visual_test_plan_rejects_too_small_region(self):
        with self.assertRaisesRegex(ColorPlanExecutionError, "180 × 160 px"):
            build_brush_visual_test_plan(179, 160)
        with self.assertRaisesRegex(ColorPlanExecutionError, "180 × 160 px"):
            build_brush_visual_test_plan(200, 159)

    def test_brush_slider_calibration_rejects_track_crossing_canvas(self):
        calibration = BrushSliderCalibration(
            x_at_min=100, x_at_max=800, y=200, initial_value=7,
            screen_width=1000, screen_height=800, confirmed=True,
        )
        with self.assertRaisesRegex(ColorPlanExecutionError, "попадает внутрь выделенной области"):
            calibration.validate((1000, 800), {"x": 300, "y": 150, "width": 300, "height": 100})

    def test_brush_slider_controller_can_restore_slider_to_value_30_without_drawing(self):
        calibration = BrushSliderCalibration(
            x_at_min=100, x_at_max=390, y=200, initial_value=7,
            screen_width=1920, screen_height=1080, confirmed=True,
        )
        controller = BrushSliderController(
            calibration,
            {"x": 0, "y": 0, "width": 40, "height": 40},
            current_screen_size_provider=lambda: (1920, 1080),
        )
        executor = MouseExecutor(FastEvent(), self.config())
        detail = controller.select_value(executor, 30)
        self.assertEqual(detail, "Выбрана кисть 30.")
        self.assertEqual(FAKE_PYAUTOGUI.moves, [(160, 200, 0), (390, 200, 0)])
        self.assertEqual(controller.current_value, 30)
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 1)
        self.assertEqual(FAKE_PYAUTOGUI.up_calls, 1)
        with self.assertRaisesRegex(ColorPlanExecutionError, "вне диапазона 1–30"):
            controller.select_value(executor, 31)

    def test_brush_slider_controller_drags_thumb_only_when_value_changes(self):
        from test_execution_hardening import FastEvent
        calibration = BrushSliderCalibration(
            x_at_min=100, x_at_max=390, y=200, initial_value=7,
            screen_width=1920, screen_height=1080, confirmed=True,
        )
        controller = BrushSliderController(
            calibration,
            {"x": 0, "y": 0, "width": 40, "height": 40},
            current_screen_size_provider=lambda: (1920, 1080),
        )
        executor = MouseExecutor(FastEvent(), self.config())
        stroke = Stroke(
            name="adaptive test",
            points=[Point(0, 0), Point(10, 0)],
            metadata={"brush_value": "20"},
        )
        FAKE_PYAUTOGUI.reset()
        detail = controller.before_stroke(executor, 1, stroke)
        self.assertEqual(detail, "Выбрана кисть 20.")
        self.assertEqual(FAKE_PYAUTOGUI.moves, [(160, 200, 0), (290, 200, 0)])
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 1)
        self.assertEqual(FAKE_PYAUTOGUI.up_calls, 1)
        self.assertEqual(controller.selection_order, [20])
        self.assertTrue(executor._release_succeeded)

        FAKE_PYAUTOGUI.reset()
        self.assertEqual(controller.before_stroke(executor, 2, stroke), "Кисть 20 уже выбрана.")
        self.assertEqual(FAKE_PYAUTOGUI.moves, [])

    def test_profile_maps_rgb_to_exact_saved_swatch_coordinates(self):
        targets = build_palette_targets(self.color_plan, self.profile, current_screen_size=(160, 100))
        self.assertEqual((targets[0].screen_x, targets[0].screen_y), (25, 25))
        self.assertEqual((targets[1].screen_x, targets[1].screen_y), (50, 25))

    def test_rejects_screen_resolution_mismatch_before_execution(self):
        with self.assertRaisesRegex(ColorPlanExecutionError, "Разрешение экрана изменилось"):
            build_palette_targets(self.color_plan, self.profile, current_screen_size=(1920, 1080))

    def test_rejects_unconfirmed_used_color(self):
        self.profile["colors"][1]["status"] = "detected"
        with self.assertRaisesRegex(ColorPlanExecutionError, "не подтверждён"):
            build_palette_targets(self.color_plan, self.profile, current_screen_size=(160, 100))

    def test_rejects_profile_missing_used_color(self):
        profile = dict(self.profile)
        profile["colors"] = [self.profile["colors"][0]]
        with self.assertRaisesRegex(ColorPlanExecutionError, "нет цвета"):
            build_palette_targets(self.color_plan, profile, current_screen_size=(160, 100))

    def test_preflight_checks_saved_palette_region_without_manual_reselection(self):
        hooks = self.hooks()
        class ExecutorStub:
            def _check_stop(self):
                return None
        self.assertIn("проверена", hooks.preflight(ExecutorStub()))
        self.assertTrue(hooks.preflight_passed)

    def test_preflight_rejects_changed_swatch_before_any_draw_click(self):
        changed = Image.new("RGB", (160, 100), "#FFFFFF")
        draw = ImageDraw.Draw(changed)
        draw.rectangle((20, 20, 30, 30), fill="#0000FF")
        draw.rectangle((45, 20, 55, 30), fill="#37A85A")
        hooks = self.hooks(screenshot_provider=lambda: changed.copy())
        class ExecutorStub:
            def _check_stop(self):
                return None
        with self.assertRaisesRegex(ColorPlanExecutionError, "Рисование не начато"):
            hooks.preflight(ExecutorStub())
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 0)

    def test_executor_selects_colors_only_when_color_changes_and_keeps_run_order(self):
        hooks = self.hooks()
        plan = color_plan_to_drawing_plan(self.color_plan)
        summary = MouseExecutor(FastEvent(), self.config()).execute(
            plan, 100, 200,
            preflight=hooks.preflight,
            before_stroke=hooks.before_stroke,
        )
        self.assertEqual(summary.status, "completed")
        self.assertEqual(hooks.selection_order, [0, 1, 0])
        self.assertEqual(hooks.selection_count, 3)
        self.assertEqual(FAKE_PYAUTOGUI.moves.count((25, 25, 0)), 2)
        self.assertEqual(FAKE_PYAUTOGUI.moves.count((50, 25, 0)), 1)
        # First palette click occurs before the first drawing coordinate, then changes remain interleaved.
        self.assertLess(FAKE_PYAUTOGUI.moves.index((25, 25, 0)), FAKE_PYAUTOGUI.moves.index((100, 200, 0)))
        self.assertIn((101, 200, 0), FAKE_PYAUTOGUI.moves)  # not a click: the cursor moves 1 px while held
        self.assertGreaterEqual(FAKE_PYAUTOGUI.down_calls, 6)  # three swatch clicks plus three strokes
        self.assertTrue(summary.mouse_release_succeeded)
        self.assertEqual(hooks.to_report()["screenshot_preflight"], "passed")

    def test_stop_after_moving_to_swatch_never_starts_the_color_click(self):
        stop = FastEvent()
        hooks = self.hooks()
        FAKE_PYAUTOGUI.on_move = lambda x, _y, _duration: stop.set() if x == 25 else None
        summary = MouseExecutor(stop, self.config()).execute(
            color_plan_to_drawing_plan(self.color_plan), 100, 200,
            preflight=hooks.preflight,
            before_stroke=hooks.before_stroke,
        )
        self.assertEqual(summary.status, "stopped")
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 0)
        self.assertEqual(hooks.selection_count, 0)
        self.assertTrue(summary.mouse_release_succeeded)

    def test_failed_preflight_does_not_draw_any_stroke(self):
        hooks = self.hooks(screenshot_provider=lambda: Image.new("RGB", (160, 100), "#FFFFFF"))
        summary = MouseExecutor(FastEvent(), self.config()).execute(
            color_plan_to_drawing_plan(self.color_plan), 100, 200,
            preflight=hooks.preflight,
            before_stroke=hooks.before_stroke,
        )
        self.assertEqual(summary.status, "failed")
        self.assertEqual(summary.completed_strokes, 0)
        self.assertEqual(FAKE_PYAUTOGUI.down_calls, 0)
        self.assertTrue(summary.mouse_release_succeeded)


    def test_geometry_plan_executes_through_palette_preflight_and_color_hooks(self):
        index_map = np.asarray([[0, 1, 1, 0]], dtype=np.int32)
        geometry_plan = build_geometry_color_plan(
            index_map,
            self.color_plan["palette"],
            mode="scanline",
            color_grouping=True,
        )
        drawing_plan = color_plan_to_drawing_plan(geometry_plan)
        hooks = ColorPlanExecutionHooks(
            geometry_plan,
            self.profile,
            current_screen_size_provider=lambda: (160, 100),
            screenshot_provider=lambda: self.screen.copy(),
            dpi_scale_provider=lambda: 100,
        )

        summary = MouseExecutor(FastEvent(), self.config()).execute(
            drawing_plan,
            100,
            200,
            preflight=hooks.preflight,
            before_stroke=hooks.before_stroke,
        )

        self.assertEqual(summary.status, "completed")
        self.assertTrue(summary.mouse_release_succeeded)
        self.assertTrue(hooks.preflight_passed)
        self.assertEqual(hooks.selection_order, [0, 1])
        self.assertEqual(hooks.selection_count, 2)
        self.assertEqual(hooks.to_report()["screenshot_preflight"], "passed")


    def test_closed_contour_geometry_executes_without_line_extension(self):
        index_map = np.full((8, 8), -1, dtype=np.int32)
        index_map[1:7, 1:7] = 0
        index_map[3:5, 3:5] = 1
        geometry_plan = build_geometry_color_plan(
            index_map,
            self.color_plan["palette"],
            mode="contour",
            simplify_tolerance_px=0,
            color_grouping=True,
        )
        self.assertTrue(any(stroke["closed"] for stroke in geometry_plan["strokes"]))

        drawing_plan = color_plan_to_drawing_plan(geometry_plan)
        self.assertTrue(any(stroke.closed for stroke in drawing_plan.strokes))
        self.assertTrue(all(
            stroke.metadata["line_extension_px_override"] == "0"
            for stroke in drawing_plan.strokes
        ))
        hooks = ColorPlanExecutionHooks(
            geometry_plan,
            self.profile,
            current_screen_size_provider=lambda: (160, 100),
            screenshot_provider=lambda: self.screen.copy(),
            dpi_scale_provider=lambda: 100,
        )

        summary = MouseExecutor(FastEvent(), self.config()).execute(
            drawing_plan,
            100,
            200,
            preflight=hooks.preflight,
            before_stroke=hooks.before_stroke,
        )

        self.assertEqual(summary.status, "completed")
        self.assertTrue(summary.mouse_release_succeeded)
        self.assertTrue(hooks.preflight_passed)
        self.assertEqual(hooks.selection_order, [0, 1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
