from __future__ import annotations

import json
import os
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import numpy as np
import pyautogui
import integrated_app
from stage8_optimizer import build_scanline_plan, save_plan
from models import DrawingPlan
from stage6_execute_plan import TargetArea
from paint_limit_test import build_paint_limit_test_plan
from color_scanline import save_color_scanline_plan
from palette_detection import create_palette_document
from palette_profiles import create_palette_profile


class UnifiedAppCoreTests(unittest.TestCase):
    def test_environment_routes_both_workflows_to_shared_data(self):
        old_values = {key: os.environ.get(key) for key in (
            "AUTODRAW_ROOT", "AUTODRAW_APP_DIR", "AUTODRAW_DATA_DIR",
            "AUTODRAW_PROFILE_STORE_PATH", "AUTODRAW_PALETTES_DIR", "AUTODRAW_TARGET_PROFILE_PATH",
            "AUTODRAW_EXECUTION_SETTINGS_PATH", "AUTODRAW_PROJECTS_DIR",
            "AUTODRAW_RESULTS_DIR", "AUTODRAW_LOGS_DIR", "AUTODRAW_PALETTE_CONVERSIONS_DIR", "AUTODRAW_COLOR_PLANS_DIR",
            "AUTODRAW_PAINT_LIMIT_TESTS_DIR", "AUTODRAW_BRUSH_CALIBRATION_PATH",
        )}
        try:
            with tempfile.TemporaryDirectory(prefix="AutoDraw unified данные ") as temp:
                root = Path(temp)
                paths = integrated_app.configure_environment(root)
                self.assertEqual(Path(os.environ["AUTODRAW_APP_DIR"]), root.resolve())
                self.assertEqual(Path(os.environ["AUTODRAW_DATA_DIR"]), paths["root"])
                self.assertEqual(Path(os.environ["AUTODRAW_PROFILE_STORE_PATH"]), paths["profiles"] / "profiles.json")
                self.assertEqual(Path(os.environ["AUTODRAW_PALETTES_DIR"]), paths["palettes"])
                self.assertTrue(paths["palettes"].is_dir())
                self.assertEqual(Path(os.environ["AUTODRAW_RESULTS_DIR"]), paths["results"])
                self.assertTrue(paths["runtime"].is_dir())
                self.assertTrue(paths["palette_conversions"].is_dir())
                self.assertEqual(Path(os.environ["AUTODRAW_PALETTE_CONVERSIONS_DIR"]), paths["palette_conversions"])
                self.assertEqual(Path(os.environ["AUTODRAW_COLOR_PLANS_DIR"]), paths["color_plans"])
                self.assertTrue(paths["color_plans"].is_dir())
                self.assertEqual(Path(os.environ["AUTODRAW_PAINT_LIMIT_TESTS_DIR"]), paths["paint_limit_tests"])
                self.assertTrue(paths["paint_limit_tests"].is_dir())
                self.assertEqual(Path(os.environ["AUTODRAW_BRUSH_CALIBRATION_PATH"]), paths["brush_calibration"])
                self.assertEqual(paths["brush_calibration"], paths["profiles"] / "brush_paint_calibration.json")
                self.assertTrue(paths["profiles"].is_dir())
        finally:
            for key, value in old_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_preparation_plan_is_written_and_loadable_by_stage6_model(self):
        with tempfile.TemporaryDirectory(prefix="AutoDraw unified plan ") as temp:
            mask = Image.new("L", (8, 5), 255)
            ImageDraw.Draw(mask).rectangle((1, 2, 6, 2), fill=0)
            plan = build_scanline_plan(mask, row_step_px=1)
            destination = Path(temp) / "runtime" / "current_plan.json"
            actual = integrated_app.write_validated_execution_plan(plan, destination, save_plan, DrawingPlan)
            loaded = DrawingPlan.load(actual)
            self.assertEqual((loaded.width, loaded.height), (8, 5))
            self.assertEqual(loaded.stroke_count, 1)
            self.assertTrue(actual.is_file())
            self.assertFalse(list(actual.parent.glob("*.tmp.json")))

    def test_invalid_plan_does_not_replace_previous_execution_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "current_plan.json"
            destination.write_text("user-owned previous plan", encoding="utf-8")
            with self.assertRaises(ValueError):
                integrated_app.write_validated_execution_plan({"strokes": []}, destination, save_plan, DrawingPlan)
            self.assertEqual(destination.read_text(encoding="utf-8"), "user-owned previous plan")

    def test_out_of_bounds_plan_does_not_replace_previous_execution_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "current_plan.json"
            destination.write_text("keep this", encoding="utf-8")
            invalid = {
                "schema_version": 1,
                "name": "invalid bounds",
                "canvas": {"width": 3, "height": 3},
                "strokes": [{"name": "bad", "points": [{"x": -1, "y": 0}, {"x": 1, "y": 0}], "closed": False}],
            }
            with self.assertRaises(ValueError):
                integrated_app.write_validated_execution_plan(invalid, destination, save_plan, DrawingPlan)
            self.assertEqual(destination.read_text(encoding="utf-8"), "keep this")


    def test_transfer_button_loads_current_plan_into_executor_tab(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            previous_runtime = app.data_paths["runtime"]
            try:
                with tempfile.TemporaryDirectory(prefix="AutoDraw handoff ") as temp:
                    app.data_paths["runtime"] = Path(temp) / "runtime"
                    mask = Image.new("L", (10, 5), 255)
                    ImageDraw.Draw(mask).line((1, 2, 8, 2), fill=0, width=1)
                    app.workbench.plan = build_scanline_plan(mask, row_step_px=1)
                    app.workbench.quality_result = object()
                    app._transfer_plan_to_executor()
                    self.assertIsNotNone(app.executor.source_plan)
                    self.assertEqual((app.executor.source_plan.width, app.executor.source_plan.height), (10, 5))
                    self.assertEqual(app.notebook.select(), str(app.execution_tab))
                    self.assertTrue(app.executor.plan_path.is_file())
            finally:
                app.data_paths["runtime"] = previous_runtime
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_brush_test_plan_transfers_to_existing_executor(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            app.executor.area = TargetArea(x=100, y=80, width=646, height=323)
            from brush_behavior_test_ui import build_brush_test_drawing_plan
            plan = build_brush_test_drawing_plan("Горизонтальные линии", (646, 323))
            with tempfile.TemporaryDirectory(prefix="AutoDraw brush test ") as temp:
                app.data_paths["runtime"] = Path(temp) / "runtime"
                source_path = Path(temp) / "brush-source.json"
                save_plan(source_path, plan)
                with patch.object(app.executor, "load_plan_from_path") as load_plan:
                    result = app._transfer_brush_test_plan(plan, source_path)
                    self.assertTrue(result)
                    load_plan.assert_called_once()
                    self.assertTrue(Path(load_plan.call_args.args[0]).is_file())
                    self.assertEqual(app.notebook.select(), str(app.execution_tab))
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_paint_limit_test_plan_transfers_into_color_executor(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            palette_doc = create_palette_document(
                [{"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0], "screen_x": 110, "screen_y": 110,
                  "local_x": 10, "local_y": 10, "source": "manual"}],
                screen_size=(1920, 1080), region={"x": 100, "y": 100, "width": 40, "height": 40},
            )
            profile = create_palette_profile(palette_doc, "Paint-test profile")
            profile["colors"][0]["status"] = "confirmed"
            plan = build_paint_limit_test_plan(
                profile, canvas_width=512, canvas_height=288, color_hex="#FF0000", scenario_id="few_long",
                experiment_id="PAIR01",
            )
            with tempfile.TemporaryDirectory(prefix="AutoDraw paint limit ") as temp:
                app.data_paths["paint_limit_tests"] = Path(temp) / "tests"
                source_path = save_color_scanline_plan(Path(temp) / "source-test-plan.json", plan)
                app.executor.area = TargetArea(x=30, y=40, width=512, height=288)
                with patch.object(app.executor, "load_color_palette_profile_document") as load_profile, \
                     patch.object(app.executor, "load_color_plan_from_path") as load_plan:
                    result = app._transfer_paint_limit_plan(plan, profile, source_path)
                    self.assertTrue(result)
                    load_profile.assert_called_once_with(profile)
                    load_plan.assert_called_once()
                    self.assertTrue(Path(load_plan.call_args.args[0]).is_file())
                    self.assertEqual(app.notebook.select(), str(app.execution_tab))
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_workflow_executor_start_uses_standard_validation_path(self):
        executor = object.__new__(integrated_app.Stage6App)
        executor.running = False
        executor.execution_plan = object()
        executor.area = object()
        executor.plan_path = Path("brush-plan.json")

        def start_validated(*, confirmed=False):
            self.assertTrue(confirmed)
            executor.running = True

        with patch.object(executor, "_start_execution", side_effect=start_validated) as start:
            self.assertTrue(executor.start_execution_from_workflow())
            start.assert_called_once_with(confirmed=True)

    def test_workflow_executor_start_rejects_missing_plan_or_area(self):
        executor = object.__new__(integrated_app.Stage6App)
        executor.running = False
        executor.execution_plan = None
        executor.area = object()
        executor.plan_path = Path("brush-plan.json")
        with patch.object(executor, "_start_execution") as start:
            self.assertFalse(executor.start_execution_from_workflow())
            start.assert_not_called()

    def test_unified_window_has_preparation_and_execution_tabs(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            labels = [app.notebook.tab(tab, "text") for tab in app.notebook.tabs()]
            self.assertEqual(labels, ["1. Подготовка изображения", "2. Исполнение рисунка", "3. Палитра браузера", "4. Преобразование в палитру", "5. Цветной scanline-план", "6. Тест лимита краски", "7. Тест кистей", "8. Калибровка теста"])
            self.assertIsNotNone(app.workbench.on_select_canvas_area)
            self.assertIs(app.executor.area_change_callback.__self__, app)
            self.assertIs(app.executor.execution_finished_callback.__self__, app)
            self.assertEqual(app.executor.execution_finished_callback.__func__.__name__, "_on_executor_finished")
            self.assertEqual(app.executor.area_change_callback.__func__.__name__, "_synchronize_area_with_preparation")
            self.assertIsNotNone(app.workbench)
            self.assertIsNotNone(app.executor)
            self.assertIsNotNone(app.palette_detector)
            self.assertIsNotNone(app.palette_quantizer)
            self.assertIsNotNone(app.color_scanline_tab)
            self.assertIsNotNone(app.paint_limit_tab)
            self.assertIsNotNone(app.brush_behavior_tab)
            self.assertTrue((app.data_paths["paint_limit_tests"]).is_dir())
            self.assertTrue((app.data_paths["brush_tests"]).is_dir())
            self.assertEqual(app.notebook.tab(app.paint_limit_tab_frame, "text"), "6. Тест лимита краски")
            self.assertEqual(app.notebook.tab(app.brush_test_tab_frame, "text"), "7. Тест кистей")
            self.assertEqual(app.color_scanline_tab.row_step_var.get(), "1")
            self.assertEqual(tuple(app.color_scanline_tab.row_step_combo.cget("values")), ("1", "2", "3", "4", "5", "8", "10"))
            self.assertEqual(tuple(app.paint_limit_tab.scenario_combo.cget("values")), (
                "650 px — длинные", "200 px — средние", "50 px — короткие", "10 px — очень короткие"
            ))
            self.assertEqual(app.paint_limit_tab.total_length_var.get(), "26000")
            self.assertEqual(app.paint_limit_tab._get_scenario_id(), "length_650")
            self.assertIsNotNone(app.paint_limit_tab.scrollbar)
            self.assertIsNotNone(app.paint_limit_tab.scroll_canvas)
            self.assertEqual(app.paint_limit_tab.generate_button.winfo_manager(), "pack")
            self.assertTrue(hasattr(app.palette_quantizer, "profile_combo"))
            self.assertTrue(hasattr(app.palette_quantizer, "merge_rare_colors_var"))
            self.assertTrue(hasattr(app.palette_quantizer, "rare_color_max_delta_spinbox"))
            self.assertTrue((app.data_paths["palette_conversions"]).is_dir())
            self.assertTrue((app.data_paths["color_plans"]).is_dir())
            self.assertTrue(hasattr(app.palette_detector, "saved_profile_combo"))
            self.assertTrue(hasattr(app.palette_detector, "check_calibration"))
            self.assertTrue((app.data_paths["palettes"] / "profiles").is_dir())
            def collect_text(widget):
                values = []
                try:
                    text = widget.cget("text")
                    if text:
                        values.append(str(text))
                except tk.TclError:
                    pass
                for child in widget.winfo_children():
                    values.extend(collect_text(child))
                return values
            preparation_texts = collect_text(app.workbench.image_tab)
            self.assertIn("Выбрать область рисования…", preparation_texts)
            self.assertNotIn("Загрузить профиль холста…", preparation_texts)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_executor_area_syncs_preparation_canvas_dimensions(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            with patch.object(app.workbench, "_process_now") as process_now:
                app.workbench.source_image = Image.new("RGB", (16, 8), "white")
                app.palette_quantizer.result = object()
                app.palette_quantizer.source_image = Image.new("RGB", (512, 288), "white")
                app.color_scanline_tab.plan = {"plan_type": "old-plan"}
                app.color_scanline_tab.quantization_result = object()
                area = {"x": 120, "y": 75, "width": 512, "height": 288}
                app._synchronize_area_with_preparation(area, (1920, 1080))
                self.assertEqual(app.workbench.width_var.get(), "512")
                self.assertEqual(app.workbench.height_var.get(), "288")
                self.assertEqual(app.workbench.profile_canvas_width_var.get(), "512")
                self.assertEqual(app.workbench.profile_canvas_height_var.get(), "288")
                self.assertEqual(app.workbench.profile_area_x_var.get(), "120")
                self.assertEqual(app.workbench.profile_area_y_var.get(), "75")
                self.assertEqual(app.workbench.profile_area_width_var.get(), "512")
                self.assertEqual(app.workbench.profile_area_height_var.get(), "288")
                self.assertEqual(app.workbench.profile_screen_width_var.get(), "1920")
                self.assertEqual(app.workbench.profile_screen_height_var.get(), "1080")
                self.assertIn("512 × 288", app.workbench.target_area_info_var.get())
                self.assertEqual(app.palette_quantizer.expected_canvas_size, (512, 288))
                self.assertIsNone(app.palette_quantizer.result)
                self.assertIsNone(app.color_scanline_tab.plan)
                self.assertIsNone(app.color_scanline_tab.quantization_result)
                process_now.assert_called_once()
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_each_main_tab_has_vertical_scroll_support(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.geometry("1350x820+0+0")
            app = integrated_app.AutoDrawUnifiedApp(root)

            for scrollable in (
                app.preparation_scroll,
                app.palette_scroll,
                app.color_scanline_scroll,
            ):
                self.assertIsInstance(scrollable.canvas, tk.Canvas)
                self.assertIsInstance(scrollable.scrollbar, ttk.Scrollbar)
                self.assertEqual(str(scrollable.scrollbar.cget("orient")), "vertical")
                self.assertTrue(callable(scrollable._on_mousewheel))

            # Section 2 owns its scroll container inside Stage6App; do not add
            # a second, outer scroll container around it.
            self.assertFalse(hasattr(app, "execution_scroll"))
            self.assertIsInstance(app.executor.scroll_canvas, tk.Canvas)
            self.assertIsInstance(app.executor.scrollbar, ttk.Scrollbar)
            self.assertEqual(str(app.executor.scrollbar.cget("orient")), "vertical")

            # Sections 4 and 6 already had their own scrollable content areas.
            self.assertIsInstance(app.palette_quantizer.scroll_canvas, tk.Canvas)
            self.assertIsInstance(app.palette_quantizer.scrollbar, ttk.Scrollbar)
            self.assertIsInstance(app.paint_limit_tab.scroll_canvas, tk.Canvas)
            self.assertIsInstance(app.paint_limit_tab.scrollbar, ttk.Scrollbar)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_execution_tab_scroll_reaches_lower_controls(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.geometry("1350x820+0+0")
            app = integrated_app.AutoDrawUnifiedApp(root)
            app.notebook.select(app.execution_tab)
            root.update_idletasks()
            root.update()

            executor = app.executor
            self.assertIsInstance(executor.scroll_canvas, tk.Canvas)
            self.assertIsInstance(executor.scrollbar, ttk.Scrollbar)
            bounds = executor.scroll_canvas.bbox("all")
            self.assertIsNotNone(bounds)
            self.assertGreater(
                bounds[3],
                executor.scroll_canvas.winfo_height(),
                "Execution controls must extend below the visible viewport",
            )

            before = executor.scroll_canvas.yview()[0]
            # Use a real widget with the wheel binding, rather than calling the
            # handler directly, to catch accidental binding/scroll-container regressions.
            executor.preview.canvas.event_generate("<MouseWheel>", delta=-120)
            root.update_idletasks()
            root.update()
            self.assertGreater(executor.scroll_canvas.yview()[0], before)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_color_scanline_tab_scroll_reaches_lower_controls(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.geometry("1350x820+0+0")
            app = integrated_app.AutoDrawUnifiedApp(root)
            app.notebook.select(app.color_scanline_tab_frame)
            root.update_idletasks()
            root.update()

            scroll = app.color_scanline_scroll
            self.assertIsInstance(scroll.canvas, tk.Canvas)
            self.assertIsInstance(scroll.scrollbar, ttk.Scrollbar)
            bounds = scroll.canvas.bbox("all")
            self.assertIsNotNone(bounds)
            self.assertGreater(bounds[3], scroll.canvas.winfo_height())

            before = scroll.canvas.yview()[0]
            event = type("MouseWheelEvent", (), {})()
            event.widget = scroll.canvas
            event.delta = -120
            event.num = None
            self.assertEqual(scroll._on_mousewheel(event), "break")
            root.update_idletasks()
            self.assertGreater(scroll.canvas.yview()[0], before)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_quantization_tab_has_vertical_scroll_support(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.geometry("1350x820+0+0")
            app = integrated_app.AutoDrawUnifiedApp(root)
            app.notebook.select(app.quantization_tab)
            root.update_idletasks()
            root.update()
            tab = app.palette_quantizer
            self.assertIsInstance(tab.scroll_canvas, tk.Canvas)
            self.assertIsInstance(tab.scrollbar, ttk.Scrollbar)
            self.assertEqual(str(tab.scrollbar.cget("orient")), "vertical")
            self.assertTrue(hasattr(tab, "_on_mousewheel"))
            self.assertTrue(hasattr(tab, "_update_scroll_region"))
            bbox = tab.scroll_canvas.bbox("all")
            self.assertIsNotNone(bbox)
            self.assertGreater(bbox[3], tab.scroll_canvas.winfo_height())
            before = tab.scroll_canvas.yview()[0]
            event = type("MouseWheelEvent", (), {})()
            event.widget = tab.colors_table
            event.delta = -120
            tab._on_mousewheel(event)
            root.update_idletasks()
            self.assertGreater(tab.scroll_canvas.yview()[0], before)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_calibration_check_reuses_saved_region_without_opening_picker(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.palette_detector
            tab.screen_size = (120, 90)
            tab.region = {"x": 10, "y": 20, "width": 60, "height": 30}
            tab.colors = [
                {"name": "Red", "hex": "#E84E43", "rgb": [232, 78, 67], "screen_x": 25, "screen_y": 35,
                 "local_x": 15, "local_y": 15, "source": "manual", "status": "confirmed"},
                {"name": "Green", "hex": "#37A85A", "rgb": [55, 168, 90], "screen_x": 50, "screen_y": 35,
                 "local_x": 40, "local_y": 15, "source": "manual", "status": "confirmed"},
            ]
            tab.profile_name_var.set("Calibration test")
            tab.browser_label_var.set("Test board")
            tab.dpi_scale_var.set("100")
            tab._calibration_profile_snapshot = tab._make_current_profile()
            tab._calibration_check_active = True

            screenshot = Image.new("RGB", (120, 90), "#FFFFFF")
            draw = ImageDraw.Draw(screenshot)
            draw.rectangle((15, 25, 34, 44), fill="#E84E43")
            draw.rectangle((40, 25, 59, 44), fill="#37A85A")
            with patch("pyautogui.screenshot", return_value=screenshot), \
                 patch("palette_detection_ui.ScreenRegionPicker") as picker, \
                 patch("palette_detection_ui.messagebox.showinfo") as showinfo:
                tab._capture_calibration_screenshot()

            picker.assert_not_called()
            showinfo.assert_called_once()
            self.assertIn("повторное выделение не потребовалось", tab.status_var.get())
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_palette_profile_can_be_saved_selected_loaded_and_deleted_from_ui(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.palette_detector
            with tempfile.TemporaryDirectory(prefix="AutoDraw palette profiles ") as temp:
                tab.profile_dir = Path(temp) / "profiles"
                tab.profile_dir.mkdir(parents=True)
                tab.screen_size = (120, 90)
                tab.region = {"x": 10, "y": 10, "width": 40, "height": 30}
                tab.colors = [{
                    "name": "Orange",
                    "hex": "#C86432",
                    "rgb": [200, 100, 50],
                    "screen_x": 20,
                    "screen_y": 20,
                    "local_x": 10,
                    "local_y": 10,
                    "source": "manual",
                    "status": "confirmed",
                }]
                tab.profile_name_var.set("Test palette")
                tab.browser_label_var.set("Test board")
                tab.dpi_scale_var.set("100")
                profile_path = tab.profile_dir / "test-palette.autodraw-palette.json"
                with patch("palette_detection_ui.filedialog.asksaveasfilename", return_value=str(profile_path)):
                    tab.save_profile_dialog()
                self.assertTrue(profile_path.is_file())
                self.assertIn(profile_path.name, tuple(tab.saved_profile_combo["values"]))
                tab.saved_profile_var.set(profile_path.name)
                with patch("palette_detection_ui.messagebox.showwarning"):
                    tab.load_selected_profile()
                self.assertEqual(tab.active_profile["profile_name"], "Test palette")
                self.assertEqual(tab.colors[0]["status"], "confirmed")
                with patch("palette_detection_ui.messagebox.askyesno", return_value=True):
                    tab.delete_selected_profile()
                self.assertFalse(profile_path.exists())
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass


    def test_palette_quantization_tab_converts_image_using_active_profile(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.palette_quantizer
            source = Image.new("RGB", (3, 1))
            source.putdata([(250, 8, 8), (5, 240, 5), (128, 128, 128)])
            tab._set_source_image(source, None, "unit test image")
            tab.palette_profile = {
                "profile_name": "Unit test",
                "profile_schema_version": 1,
                "colors": [
                    {"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0], "id": "red"},
                    {"name": "Green", "hex": "#00FF00", "rgb": [0, 255, 0], "id": "green"},
                ],
            }
            tab.quantize()
            self.assertIsNotNone(tab.result)
            self.assertEqual(tab.result.image.size, (3, 1))
            self.assertEqual(tab.result.image.getpixel((0, 0)), (255, 0, 0))
            self.assertEqual(tab.result.image.getpixel((1, 0)), (0, 255, 0))
            self.assertEqual(tab.result.report["palette_profile"]["name"], "Unit test")
            self.assertFalse(tab.result.report["background_removal"]["enabled"])
            self.assertEqual(tab.result.report["background_removal"]["removed_pixel_count"], 0)
            self.assertTrue(tab.colors_table.get_children())
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_palette_quantization_can_remove_white_background_and_keep_transparent_index_map(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.palette_quantizer
            source = Image.new("RGB", (5, 3), "white")
            source.putpixel((2, 1), (255, 0, 0))
            tab._set_source_image(source, None, "white background test")
            tab.palette_profile = {
                "profile_name": "Transparent test",
                "profile_schema_version": 1,
                "colors": [
                    {"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0], "id": "red"},
                    {"name": "White", "hex": "#FFFFFF", "rgb": [255, 255, 255], "id": "white"},
                ],
            }
            # With the checkbox off, the existing behavior is preserved exactly:
            # white is still a regular opaque palette color.
            tab.quantize()
            self.assertIsNotNone(tab.result)
            self.assertEqual(tab.result.image.mode, "RGB")
            self.assertEqual(tab.result.image.getpixel((0, 0)), (255, 255, 255))
            self.assertFalse(tab.result.report["background_removal"]["enabled"])

            tab.remove_white_background_var.set(True)
            tab.background_tolerance_var.set(0)
            tab._toggle_background_tolerance()
            tab.quantize()
            self.assertIsNotNone(tab.result)
            self.assertEqual(tab.result.image.mode, "RGBA")
            self.assertEqual(tab.result.image.getpixel((0, 0)), (255, 255, 255, 0))
            self.assertEqual(tab.result.image.getpixel((2, 1)), (255, 0, 0, 255))
            self.assertEqual(int(tab.result.index_map[0, 0]), -1)
            self.assertEqual(int(tab.result.index_map[1, 2]), 0)
            self.assertTrue(tab.result.report["background_removal"]["enabled"])
            self.assertEqual(tab.result.report["background_removal"]["removed_pixel_count"], 14)
            self.assertEqual(tab.difference_preview.image.getpixel((0, 0)), (255, 0, 255))

            from color_scanline import build_color_scanline_plan
            plan = build_color_scanline_plan(
                tab.result.index_map,
                tab.palette_profile,
                source_report=tab.result.report,
            )
            self.assertEqual(plan["summary"]["visible_pixel_count"], 1)
            self.assertEqual(plan["summary"]["transparent_pixel_count"], 14)
            self.assertEqual(plan["summary"]["stroke_count"], 1)
            with tempfile.TemporaryDirectory(prefix="AutoDraw transparent export ") as temp:
                png_path = Path(temp) / "cutout.png"
                tab.result.image.save(png_path, format="PNG")
                with Image.open(png_path) as saved:
                    self.assertEqual(saved.size, (5, 3))
                    self.assertEqual(saved.convert("RGBA").getpixel((0, 0))[3], 0)
                    self.assertEqual(saved.convert("RGBA").getpixel((2, 1))[3], 255)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_palette_quantization_supports_global_white_removal_and_auto_30_percent_mode(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.palette_quantizer
            tab.palette_profile = {
                "profile_name": "White removal modes",
                "profile_schema_version": 1,
                "colors": [
                    {"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0], "id": "red"},
                    {"name": "White", "hex": "#FFFFFF", "rgb": [255, 255, 255], "id": "white"},
                    {"name": "Black", "hex": "#000000", "rgb": [0, 0, 0], "id": "black"},
                ],
            }
            tab.background_tolerance_var.set(0)
            # Global mode removes white even when it is an enclosed/isolated detail.
            source = Image.new("RGB", (10, 1), "black")
            for x in range(4):
                source.putpixel((x, 0), (255, 255, 255))
            tab._set_source_image(source, None, "global white test")
            tab._set_background_mode("all_white")
            tab.quantize()
            self.assertIsNotNone(tab.result)
            self.assertEqual(tab.result.report["background_removal"]["mode"], "remove_all_white_palette_pixels")
            self.assertEqual(tab.result.report["background_removal"]["removed_pixel_count"], 4)
            self.assertTrue(np.all(tab.result.index_map[0, :4] == -1))
            self.assertEqual(tab.result.image.getpixel((0, 0))[3], 0)

            # Exact 30% is not enough: the option is explicitly for MORE than 30%.
            source = Image.new("RGB", (10, 1), "black")
            for x in range(3):
                source.putpixel((x, 0), (255, 255, 255))
            tab._set_source_image(source, None, "threshold white test")
            tab._set_background_mode("auto_white_30")
            tab.quantize()
            self.assertIsNotNone(tab.result)
            report = tab.result.report["background_removal"]
            self.assertEqual(report["white_percentage_of_visible_pixels"], 30.0)
            self.assertEqual(report["removed_pixel_count"], 0)
            self.assertEqual(tab.result.image.mode, "RGB")
            self.assertEqual(tab.result.index_map[0, 0], 1)

            # Above 30%, all matching white palette pixels become transparent.
            source.putpixel((3, 0), (255, 255, 255))
            tab._set_source_image(source, None, "threshold white above 30 test")
            tab.quantize()
            self.assertEqual(tab.result.report["background_removal"]["white_percentage_of_visible_pixels"], 40.0)
            self.assertEqual(tab.result.report["background_removal"]["removed_pixel_count"], 4)
            self.assertTrue(np.all(tab.result.index_map[0, :4] == -1))
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_palette_quantization_can_use_prepared_image_from_workbench(self):
        from types import SimpleNamespace

        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            prepared = Image.new("RGB", (11, 7), "#3579B4")
            app.workbench.result = SimpleNamespace(prepared_color=prepared)
            app.palette_quantizer.use_prepared_image()
            self.assertIsNotNone(app.palette_quantizer.source_image)
            self.assertEqual(app.palette_quantizer.source_image.size, (11, 7))
            self.assertEqual(app.palette_quantizer.source_image.getpixel((0, 0)), (53, 121, 180))
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass



    def test_palette_quantization_loads_saved_stage17_profile_and_converts(self):
        from palette_detection import create_palette_document
        from palette_profiles import create_palette_profile, save_palette_profile

        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.palette_quantizer
            with tempfile.TemporaryDirectory(prefix="AutoDraw stage18 saved palette ") as temp:
                tab.profile_dir = Path(temp) / "profiles"
                tab.profile_dir.mkdir(parents=True)
                raw_palette = create_palette_document(
                    [
                        {"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0], "screen_x": 15, "screen_y": 15,
                         "local_x": 10, "local_y": 10, "source": "manual"},
                        {"name": "Green", "hex": "#00FF00", "rgb": [0, 255, 0], "screen_x": 25, "screen_y": 15,
                         "local_x": 20, "local_y": 10, "source": "manual"},
                    ],
                    screen_size=(120, 80),
                    region={"x": 5, "y": 5, "width": 40, "height": 30},
                )
                profile = create_palette_profile(raw_palette, "Saved test profile", dpi_scale_percent=100)
                saved_path = save_palette_profile(tab.profile_dir / "saved.autodraw-palette.json", profile)
                tab.refresh_profiles()
                tab.profile_choice_var.set(saved_path.name)
                self.assertTrue(tab.load_selected_profile())
                tab._set_source_image(Image.new("RGB", (2, 1), "#F90808"), None, "saved profile test")
                tab.quantize()
                self.assertIsNotNone(tab.result)
                self.assertEqual(tab.result.image.getpixel((0, 0)), (255, 0, 0))
                self.assertEqual(tab.result.report["palette_profile"]["name"], "Saved test profile")
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass


    def test_stage19_rejects_quantization_result_if_active_palette_changed(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            quantizer = app.palette_quantizer
            quantizer._set_source_image(Image.new("RGB", (2, 1), "#FF0000"), None, "stale palette test")
            quantizer.palette_profile = {
                "profile_name": "Original palette",
                "profile_schema_version": 1,
                "colors": [{"id": "red", "name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0]}],
            }
            quantizer.quantize()
            self.assertIsNotNone(quantizer.result)
            quantizer.palette_profile = {
                "profile_name": "Changed palette",
                "profile_schema_version": 1,
                "colors": [{"id": "blue", "name": "Blue", "hex": "#0000FF", "rgb": [0, 0, 255]}],
            }
            with patch("color_scanline_ui.messagebox.showwarning") as warning:
                app.color_scanline_tab.use_latest_quantization()
            warning.assert_called_once()
            self.assertIsNone(app.color_scanline_tab.quantization_result)
            self.assertIsNone(app.color_scanline_tab.plan)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass


    def test_stage19_builds_color_plan_from_stage18_quantization_without_sending_it_to_stage6(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            quantizer = app.palette_quantizer
            source = Image.new("RGB", (5, 2))
            source.putdata([
                (250, 10, 10), (250, 10, 10), (10, 245, 10), (10, 245, 10), (250, 10, 10),
                (10, 10, 245), (10, 10, 245), (10, 245, 10), (10, 245, 10), (10, 10, 245),
            ])
            quantizer._set_source_image(source, None, "stage 19 integration image")
            quantizer.palette_profile = {
                "profile_name": "Stage 19 test palette",
                "profile_schema_version": 1,
                "colors": [
                    {"id": "red", "name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0]},
                    {"id": "green", "name": "Green", "hex": "#00FF00", "rgb": [0, 255, 0]},
                    {"id": "blue", "name": "Blue", "hex": "#0000FF", "rgb": [0, 0, 255]},
                ],
            }
            quantizer.quantize()
            self.assertIsNotNone(quantizer.result)

            tab = app.color_scanline_tab
            tab.use_latest_quantization()
            self.assertIsNotNone(tab.quantization_result)
            tab.build_plan()
            self.assertIsNotNone(tab.plan)
            plan = tab.plan
            self.assertEqual(plan["plan_type"], "autodraw_color_scanline_plan")
            self.assertEqual(plan["canvas"], {"width": 5, "height": 2})
            self.assertEqual([s["points"][0]["y"] for s in plan["strokes"]], sorted(s["points"][0]["y"] for s in plan["strokes"]))
            self.assertIsNone(app.executor.source_plan, "Stage 19 color plan must not be loaded by the stage 6 one-color executor")
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass


    def test_color_plan_handoff_loads_stage19_plan_and_same_palette_profile_into_executor(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            previous_runtime = app.data_paths["runtime"]
            previous_area = app.executor.area
            try:
                with tempfile.TemporaryDirectory(prefix="AutoDraw color handoff ") as temp:
                    app.data_paths["runtime"] = Path(temp) / "runtime"
                    app.executor.area = None  # exercise handoff without touching persistent target-area settings

                    screen_width, screen_height = pyautogui.size()
                    palette_doc = create_palette_document(
                        [
                            {"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0],
                             "screen_x": 15, "screen_y": 15, "local_x": 10, "local_y": 10, "source": "manual"},
                            {"name": "Green", "hex": "#00FF00", "rgb": [0, 255, 0],
                             "screen_x": 35, "screen_y": 15, "local_x": 30, "local_y": 10, "source": "manual"},
                        ],
                        screen_size=(screen_width, screen_height),
                        region={"x": 5, "y": 5, "width": 45, "height": 30},
                    )
                    profile = create_palette_profile(palette_doc, "Handoff palette", dpi_scale_percent=100)
                    for color in profile["colors"]:
                        color["status"] = "confirmed"

                    quantizer = app.palette_quantizer
                    source = Image.new("RGB", (4, 2))
                    source.putdata([
                        (255, 0, 0), (0, 255, 0), (0, 255, 0), (255, 0, 0),
                        (255, 0, 0), (0, 255, 0), (0, 255, 0), (255, 0, 0),
                    ])
                    quantizer._set_source_image(source, None, "handoff integration test")
                    quantizer.palette_profile = profile
                    quantizer.quantize()

                    tab = app.color_scanline_tab
                    tab.use_latest_quantization()
                    tab.build_plan()
                    expected_plan = tab.plan
                    expected_profile = tab.palette_profile
                    self.assertIsNotNone(expected_plan)

                    app._transfer_color_plan_to_executor()

                    self.assertEqual(app.executor.color_plan_data["plan_type"], "autodraw_color_scanline_plan")
                    self.assertEqual(app.executor.color_plan_data["strokes"], expected_plan["strokes"])
                    self.assertEqual(app.executor.color_palette_profile["profile_name"], "Handoff palette")
                    self.assertEqual(
                        [tuple(color["rgb"]) for color in app.executor.color_palette_profile["colors"]],
                        [tuple(color["rgb"]) for color in expected_profile["colors"]],
                    )
                    self.assertEqual(app.notebook.select(), str(app.execution_tab))
                    self.assertTrue(app.executor.plan_path.is_file())
                    self.assertEqual(app.executor.plan_path.parent, Path(temp).resolve() / "runtime")
                    self.assertIsNotNone(app.executor.source_plan)
                    self.assertEqual(
                        [stroke.metadata["palette_index"] for stroke in app.executor.source_plan.strokes],
                        [str(stroke["color"]["palette_index"]) for stroke in expected_plan["strokes"]],
                    )
            finally:
                app.data_paths["runtime"] = previous_runtime
                app.executor.area = previous_area
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass



    def test_geometry_plan_handoff_uses_geometry_serializer_and_loads_into_executor(self):
        from geometry_color_plan import build_geometry_color_plan

        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            previous_runtime = app.data_paths["runtime"]
            previous_area = app.executor.area
            try:
                with tempfile.TemporaryDirectory(prefix="AutoDraw geometry handoff ") as temp:
                    app.data_paths["runtime"] = Path(temp) / "runtime"
                    app.executor.area = None

                    screen_width, screen_height = pyautogui.size()
                    palette_doc = create_palette_document(
                        [
                            {"name": "Red", "hex": "#FF0000", "rgb": [255, 0, 0],
                             "screen_x": 15, "screen_y": 15, "local_x": 10, "local_y": 10, "source": "manual"},
                            {"name": "Green", "hex": "#00FF00", "rgb": [0, 255, 0],
                             "screen_x": 35, "screen_y": 15, "local_x": 30, "local_y": 10, "source": "manual"},
                        ],
                        screen_size=(screen_width, screen_height),
                        region={"x": 5, "y": 5, "width": 45, "height": 30},
                    )
                    profile = create_palette_profile(
                        palette_doc, "Geometry handoff palette", dpi_scale_percent=100
                    )
                    for color in profile["colors"]:
                        color["status"] = "confirmed"

                    geometry_plan = build_geometry_color_plan(
                        np.array([[0, 0, 1, 1], [0, 0, 1, 1]], dtype=np.int32),
                        profile,
                        mode="scanline",
                        source_name="geometry handoff integration test",
                    )
                    self.assertEqual(geometry_plan["plan_type"], "autodraw_geometry_color_plan")
                    tab = app.color_scanline_tab
                    tab.plan = geometry_plan
                    tab.palette_profile = profile

                    with patch("integrated_app.messagebox.showerror") as showerror:
                        app._transfer_color_plan_to_executor()

                    showerror.assert_not_called()
                    self.assertEqual(
                        app.executor.color_plan_data["plan_type"],
                        "autodraw_geometry_color_plan",
                    )
                    self.assertEqual(
                        app.executor.color_plan_data["strokes"],
                        geometry_plan["strokes"],
                    )
                    self.assertEqual(
                        app.executor.color_palette_profile["profile_name"],
                        "Geometry handoff palette",
                    )
                    self.assertIsNotNone(app.executor.source_plan)
                    self.assertTrue(app.executor.plan_path.is_file())
                    self.assertEqual(
                        app.executor.plan_path.name,
                        "current_geometry_color_plan_for_execution.json",
                    )
                    saved_document = json.loads(
                        app.executor.plan_path.read_text(encoding="utf-8")
                    )
                    self.assertEqual(
                        saved_document["plan_type"],
                        "autodraw_geometry_color_plan",
                    )
                    self.assertEqual(app.notebook.select(), str(app.execution_tab))
            finally:
                app.data_paths["runtime"] = previous_runtime
                app.executor.area = previous_area
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_paint_model_explanation_uses_its_own_wrapped_row(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            tab = app.color_scanline_tab
            self.assertIs(tab.paint_model_controls.master, tab.paint_model_frame)
            self.assertIs(tab.paint_model_explanation.master, tab.paint_model_frame)
            self.assertEqual(tab.paint_model_controls.winfo_manager(), "pack")
            self.assertEqual(tab.paint_model_explanation.winfo_manager(), "pack")
            self.assertEqual(int(tab.paint_model_explanation.cget("wraplength")), 1120)
            self.assertIn("25 650", tab.paint_model_explanation.cget("text"))
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass

    def test_color_plan_status_describes_existing_execution_not_future_stage(self):
        root = None
        app = None
        try:
            root = tk.Tk()
            root.withdraw()
            app = integrated_app.AutoDrawUnifiedApp(root)
            status = app.color_scanline_tab.status_var.get()
            self.assertIn("экспериментальная", status)
            self.assertNotIn("будет добавлено на этапе 20", status)
        except tk.TclError as exc:
            self.skipTest(f"Tk desktop session unavailable: {exc}")
        finally:
            if app is not None:
                app.workbench.cleanup()
            if root is not None:
                try:
                    root.destroy()
                except tk.TclError:
                    pass



if __name__ == "__main__":
    unittest.main(verbosity=2)
