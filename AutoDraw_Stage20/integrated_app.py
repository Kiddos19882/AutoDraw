from __future__ import annotations

import json
import os
import shutil
import sys
import tkinter as tk
import uuid
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

APP_VERSION = "1.8.3"
IS_FROZEN = bool(getattr(sys, "frozen", False))
APP_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
DATA_ROOT = APP_ROOT / "data"


def configure_environment(root: str | Path, *, create_directories: bool = True) -> dict[str, Path]:
    """Point both formerly separate applications to one persistent data location."""
    root_path = Path(root).resolve()
    data = root_path / "data"
    paths = {
        "root": data,
        "profiles": data / "profiles",
        "palettes": data / "palettes",
        "projects": data / "projects",
        "results": data / "results",
        "logs": data / "logs",
        "runtime": data / "runtime",
        "palette_conversions": data / "results" / "palette_conversions",
        "color_plans": data / "results" / "color_scanline_plans",
        "paint_limit_tests": data / "results" / "paint_limit_tests",
    }
    if create_directories:
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)

    environment = {
        "AUTODRAW_ROOT": str(root_path),
        "AUTODRAW_APP_DIR": str(root_path),
        "AUTODRAW_DATA_DIR": str(data),
        "AUTODRAW_PROFILE_STORE_PATH": str(paths["profiles"] / "profiles.json"),
        "AUTODRAW_PALETTES_DIR": str(paths["palettes"]),
        "AUTODRAW_TARGET_PROFILE_PATH": str(paths["profiles"] / "target_profile.json"),
        "AUTODRAW_EXECUTION_SETTINGS_PATH": str(paths["profiles"] / "execution_settings.json"),
        "AUTODRAW_PROJECTS_DIR": str(paths["projects"]),
        "AUTODRAW_RESULTS_DIR": str(paths["results"]),
        "AUTODRAW_LOGS_DIR": str(paths["logs"]),
        "AUTODRAW_PALETTE_CONVERSIONS_DIR": str(paths["palette_conversions"]),
        "AUTODRAW_COLOR_PLANS_DIR": str(paths["color_plans"]),
        "AUTODRAW_PAINT_LIMIT_TESTS_DIR": str(paths["paint_limit_tests"]),
    }
    os.environ.update(environment)
    return paths


def ensure_import_paths(root: str | Path) -> tuple[Path, Path]:
    """Expose preparation/executor modules while avoiding separate process launches."""
    root_path = Path(root).resolve()
    preparation = root_path / "source" / "preparation"
    executor = root_path / "source" / "executor"
    missing = [path for path in (preparation, executor) if not path.is_dir()]
    if missing and not IS_FROZEN:
        raise FileNotFoundError("Не найдены компоненты AutoDraw: " + ", ".join(map(str, missing)))
    for path in reversed((preparation, executor)):
        value = str(path)
        if path.is_dir() and value not in sys.path:
            sys.path.insert(0, value)
    return preparation, executor


def write_validated_execution_plan(plan: dict[str, Any], target: str | Path, save_plan_fn, drawing_plan_cls) -> Path:
    """Write a stage-6-compatible plan, validate it, then atomically publish it."""
    if not isinstance(plan, dict) or not plan.get("strokes"):
        raise ValueError("Нет готового DrawingPlan. Сначала постройте растровый план.")
    target_path = Path(target).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target_path.with_name(f".{target_path.stem}.{uuid.uuid4().hex}.tmp.json")
    try:
        save_plan_fn(temporary_path, plan)
        loaded = drawing_plan_cls.load(temporary_path)
        loaded.validate_bounds()
        temporary_path.replace(target_path)
    except Exception:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target_path


ensure_import_paths(APP_ROOT)
# Environment must be configured before importing either former application: both
# modules read profile/project/result paths during import.
DATA_PATHS = configure_environment(APP_ROOT, create_directories=False)

try:
    from stage13_workbench import AutoDrawWorkbench
    from stage8_optimizer import save_plan
    from models import DrawingPlan
    from stage6_execute_plan import Stage6App
    from palette_detection_ui import PaletteDetectionTab
    from palette_quantization_ui import PaletteQuantizationTab
    from color_scanline_ui import ColorScanlineTab
    from color_scanline import save_color_scanline_plan
    from geometry_color_plan import save_geometry_color_plan
    from paint_limit_test_ui import PaintLimitTestTab
except ImportError as exc:  # pragma: no cover - exercised by packaging smoke test
    raise SystemExit(
        "Не удалось загрузить компоненты AutoDraw. Проверьте комплект поставки и зависимости.\n"
        f"Подробности: {exc}"
    ) from exc


class ScrollableTabContent:
    """Vertical scrolling container for a main notebook tab.

    The content frame keeps its natural requested height inside a Canvas, so
    lower controls remain reachable when a tab contains more widgets than the
    visible window. Widgets with their own vertical scrolling keep priority
    while they can still scroll; at their boundary the tab itself scrolls.
    """

    def __init__(self, parent: tk.Widget):
        self.host = ttk.Frame(parent)
        self.host.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.host, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(
            self.host, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )
        self.content.bind("<Configure>", self._update_scroll_region, add="+")
        self.canvas.bind("<Configure>", self._resize_content, add="+")

    def _update_scroll_region(self, _event: tk.Event | None = None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_content(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.window_id, width=max(1, event.width))
        self._update_scroll_region()

    @staticmethod
    def _wheel_units(event: tk.Event) -> int:
        number = getattr(event, "num", None)
        if number == 4:
            return -1
        if number == 5:
            return 1
        delta = int(-getattr(event, "delta", 0) / 120)
        if delta == 0:
            delta = -1 if getattr(event, "delta", 0) > 0 else 1
        return delta

    def _on_mousewheel(self, event: tk.Event) -> str:
        units = self._wheel_units(event)
        widget = getattr(event, "widget", None)

        # Preserve native wheel behavior for an overflowing Text, Treeview,
        # Listbox or other child widget with its own yview.
        if widget is not None and widget not in (self.canvas, self.content):
            yview = getattr(widget, "yview", None)
            scroll = getattr(widget, "yview_scroll", None)
            if callable(yview) and callable(scroll):
                try:
                    first, last = yview()
                    if (units < 0 and first > 0.0) or (units > 0 and last < 1.0):
                        scroll(units, "units")
                        return "break"
                except (tk.TclError, TypeError, ValueError):
                    pass

        self.canvas.yview_scroll(units, "units")
        return "break"

    def bind_mousewheel_events(self) -> None:
        """Bind wheel support after the tab's widgets have been constructed."""
        def bind_descendants(widget: tk.Widget) -> None:
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")
            for child in widget.winfo_children():
                bind_descendants(child)

        bind_descendants(self.canvas)


class AutoDrawUnifiedApp:
    """Single Tk window containing both preparation and execution interfaces."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title(f"AutoDraw — подготовка и исполнение {APP_VERSION}")
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        window_width = min(1500, max(1180, screen_width - 48))
        window_height = min(960, max(760, screen_height - 64))
        position_x = max(0, (screen_width - window_width) // 2)
        position_y = max(0, (screen_height - window_height) // 2)
        root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        root.minsize(1050, 720)
        try:
            ttk.Style(root).theme_use("vista")
        except tk.TclError:
            pass

        self.data_paths = DATA_PATHS
        outer = ttk.Frame(root, padding=10)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 8))
        title_block = ttk.Frame(header)
        title_block.pack(side="left", fill="x", expand=True)
        ttk.Label(title_block, text="AutoDraw", font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(
            title_block,
            text="Подготовка → палитра → цветной план → тест лимита краски → исполнение",
        ).pack(anchor="w", pady=(2, 0))
        transfer_buttons = ttk.Frame(header)
        transfer_buttons.pack(side="right", padx=(12, 0))
        ttk.Button(
            transfer_buttons,
            text="Передать цветной план в исполнение →",
            command=self._transfer_color_plan_to_executor,
        ).pack(anchor="e", pady=(0, 3))
        ttk.Button(
            transfer_buttons,
            text="Передать одноцветный план в исполнение →",
            command=self._transfer_plan_to_executor,
        ).pack(anchor="e")

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.preparation_tab = ttk.Frame(self.notebook)
        self.execution_tab = ttk.Frame(self.notebook)
        self.palette_tab = ttk.Frame(self.notebook)
        self.quantization_tab = ttk.Frame(self.notebook)
        self.color_scanline_tab_frame = ttk.Frame(self.notebook)
        self.paint_limit_tab_frame = ttk.Frame(self.notebook)
        # The executor (tab 2), quantizer (tab 4), and paint-limit test (tab 6)
        # already own scrollable content areas. Wrap only tabs that need scrolling.
        self.preparation_scroll = ScrollableTabContent(self.preparation_tab)
        self.palette_scroll = ScrollableTabContent(self.palette_tab)
        self.color_scanline_scroll = ScrollableTabContent(self.color_scanline_tab_frame)
        self.notebook.add(self.preparation_tab, text="1. Подготовка изображения")
        self.notebook.add(self.execution_tab, text="2. Исполнение рисунка")
        self.notebook.add(self.palette_tab, text="3. Палитра браузера")
        self.notebook.add(self.quantization_tab, text="4. Преобразование в палитру")
        self.notebook.add(self.color_scanline_tab_frame, text="5. Цветной scanline-план")
        self.notebook.add(self.paint_limit_tab_frame, text="6. Тест лимита краски")

        self.workbench = AutoDrawWorkbench(
            root,
            parent=self.preparation_scroll.content,
            embedded=True,
            on_select_canvas_area=self._select_target_area_for_preparation,
        )
        self.executor = Stage6App(root, parent=self.execution_tab, embedded=True)
        # A single selected browser area controls both the executor's screen
        # coordinates and the preparation canvas dimensions. No separate canvas
        # profile import is needed in the preparation tab.
        self.executor.area_change_callback = self._synchronize_area_with_preparation
        self.palette_detector = PaletteDetectionTab(root, self.palette_scroll.content, self.data_paths["palettes"])
        self.palette_quantizer = PaletteQuantizationTab(
            root,
            self.quantization_tab,
            self.data_paths["palettes"] / "profiles",
            self.data_paths["palette_conversions"],
            get_prepared_image=self._get_prepared_color_image,
        )
        self.color_scanline_tab = ColorScanlineTab(
            root,
            self.color_scanline_scroll.content,
            self.data_paths["color_plans"],
            get_quantized_data=self._get_quantized_data,
        )
        self.paint_limit_tab = PaintLimitTestTab(
            root,
            self.paint_limit_tab_frame,
            self.data_paths["paint_limit_tests"],
            self.data_paths["palettes"] / "profiles",
            get_canvas_size=self._get_execution_canvas_size,
            on_transfer_plan=self._transfer_paint_limit_plan,
        )

        for scrollable in (
            self.preparation_scroll,
            self.palette_scroll,
            self.color_scanline_scroll,
        ):
            scrollable.bind_mousewheel_events()

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(7, 0))
        self.status_var = tk.StringVar(value="Готово. Подготовьте изображение, постройте цветной план или исследуйте лимит краски.")
        ttk.Label(footer, textvariable=self.status_var, wraplength=950).pack(side="left", fill="x", expand=True)
        for label, folder in (
            ("Профили", "profiles"),
            ("Палитры", "palettes"),
            ("Проекты", "projects"),
            ("Результаты", "results"),
            ("Цветные планы", "color_plans"),
            ("Тест лимита краски", "paint_limit_tests"),
            ("Журналы", "logs"),
        ):
            ttk.Button(footer, text=label, command=lambda name=folder: self._open_folder(name)).pack(side="right", padx=(5, 0))

        root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Stage 6 may have loaded a target profile during its constructor. Sync
        # once all preparation tabs and their output views are ready.
        if self.executor.area is not None:
            self.executor._notify_area_change()

    def _select_target_area_for_preparation(self) -> None:
        """Open the exact same screen-area selector used by the executor."""
        if not hasattr(self, "executor"):
            return
        if self.executor.running:
            messagebox.showwarning(
                "Исполнение запущено",
                "Нельзя менять область рисования во время исполнения.",
                parent=self.root,
            )
            return
        self.executor._select_area()

    def _synchronize_area_with_preparation(
        self, area: dict[str, int], screen_size: tuple[int, int] | None = None
    ) -> None:
        """Update preparation dimensions whenever the executor area is captured/loaded."""
        self.workbench.set_target_area(area, screen_size)
        x, y, width, height = (int(area[key]) for key in ("x", "y", "width", "height"))
        if hasattr(self, "palette_quantizer"):
            self.palette_quantizer.set_target_canvas_size(width, height)
        if hasattr(self, "color_scanline_tab"):
            self.color_scanline_tab.invalidate_source(
                f"Область рисования изменилась на {width} × {height}. "
                "Повторно передайте подготовленное изображение на вкладку 4 и постройте цветной план заново."
            )
        if hasattr(self, "status_var"):
            self.status_var.set(
                f"Область синхронизирована: X={x}, Y={y}, размер изображения/холста {width} × {height} px."
            )

    def _get_quantized_data(self):
        tab = getattr(self, "palette_quantizer", None)
        result = getattr(tab, "result", None) if tab is not None else None
        profile = getattr(tab, "palette_profile", None) if tab is not None else None
        if result is None or profile is None:
            return None
        source_name = getattr(getattr(tab, "image_name_var", None), "get", lambda: "")()
        return {
            "result": result,
            "profile": profile,
            "report": getattr(result, "report", None),
            "source_name": source_name or "Результат этапа 18",
        }

    def _get_prepared_color_image(self):
        result = getattr(self.workbench, "result", None)
        image = getattr(result, "prepared_color", None) if result is not None else None
        return image.copy() if image is not None else None

    def _transfer_plan_to_executor(self) -> None:
        if self.executor.running:
            messagebox.showwarning(
                "Исполнение уже запущено",
                "Нельзя заменить план во время рисования.",
                parent=self.root,
            )
            return
        plan = self.workbench.plan
        if not isinstance(plan, dict) or not plan.get("strokes"):
            messagebox.showinfo(
                "Нет готового плана",
                "Сначала обработайте изображение и постройте растровый план на первой вкладке.",
                parent=self.root,
            )
            self.notebook.select(self.preparation_tab)
            return
        if self.workbench.quality_result is None:
            proceed = messagebox.askyesno(
                "Качество ещё не проверено",
                "План создан, но проверка качества на вкладке подготовки ещё не выполнялась.\n\n"
                "Передать план в исполнитель всё равно?",
                parent=self.root,
            )
            if not proceed:
                self.notebook.select(self.preparation_tab)
                return

        destination = self.data_paths["runtime"] / "current_plan_for_execution.json"
        try:
            path = write_validated_execution_plan(plan, destination, save_plan, DrawingPlan)
            self.executor.load_plan_from_path(path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
            messagebox.showerror(
                "Не удалось передать план",
                f"План не был передан исполнителю. Исходный план не изменён.\n\n{exc}",
                parent=self.root,
            )
            self.status_var.set(f"Ошибка передачи плана: {exc}")
            return

        self.notebook.select(self.execution_tab)
        self.status_var.set(
            f"План передан исполнителю: {path.name}. Проверьте область доски и параметры перед запуском."
        )

    def _transfer_color_plan_to_executor(self) -> None:
        """Pass the current Stage 19 plan and its actual Stage 18/17 palette profile."""
        if self.executor.running:
            messagebox.showwarning(
                "Исполнение уже запущено",
                "Нельзя заменить план во время рисования.",
                parent=self.root,
            )
            return
        plan_tab = getattr(self, "color_scanline_tab", None)
        color_plan = getattr(plan_tab, "plan", None) if plan_tab is not None else None
        palette_profile = getattr(plan_tab, "palette_profile", None) if plan_tab is not None else None
        if not isinstance(color_plan, dict) or not color_plan.get("strokes"):
            messagebox.showinfo(
                "Нет цветного плана",
                "Сначала постройте цветной scanline-план на вкладке 5.",
                parent=self.root,
            )
            self.notebook.select(self.color_scanline_tab_frame)
            return
        if not isinstance(palette_profile, dict) or not palette_profile.get("colors"):
            messagebox.showwarning(
                "Нет профиля палитры",
                "Профиль палитры этапа 17, использованный для преобразования, не найден. "
                "Повторно загрузите профиль и выполните этапы 18 и 19.",
                parent=self.root,
            )
            self.notebook.select(self.quantization_tab)
            return

        try:
            plan_type = color_plan.get("plan_type")
            if plan_type == "autodraw_geometry_color_plan":
                # Geometry plans have their own schema and validator. Saving one with
                # the scanline serializer makes a direct Stage 5 -> executor transfer fail.
                destination = self.data_paths["runtime"] / "current_geometry_color_plan_for_execution.json"
                save_geometry_color_plan(destination, color_plan)
            elif plan_type == "autodraw_color_scanline_plan":
                destination = self.data_paths["runtime"] / "current_color_plan_for_execution.json"
                save_color_scanline_plan(destination, color_plan)
            else:
                raise ValueError(
                    "Раздел 5 передал неподдерживаемый тип цветного плана: "
                    f"{plan_type!r}."
                )

            # The profile is passed from the same Stage 19 source state that produced the plan,
            # not from a potentially different palette selected afterwards on another tab.
            self.executor.load_color_palette_profile_document(palette_profile)
            self.executor.load_color_plan_from_path(destination)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            messagebox.showerror(
                "Не удалось передать цветной план",
                f"Цветной план не был передан исполнителю. Исходные данные не изменены.\n\n{exc}",
                parent=self.root,
            )
            self.status_var.set(f"Ошибка передачи цветного плана: {exc}")
            return

        self.notebook.select(self.execution_tab)
        self.status_var.set(
            f"Цветной план передан исполнителю: {destination.name}. "
            "Проверьте точный размер холста, экранную область и профиль палитры до запуска."
        )

    def _get_execution_canvas_size(self) -> tuple[int, int] | None:
        area = getattr(self.executor, "area", None)
        if area is None:
            return None
        try:
            return int(area.width), int(area.height)
        except (AttributeError, TypeError, ValueError):
            return None

    def _transfer_paint_limit_plan(
        self, plan: dict[str, Any], palette_profile: dict[str, Any], source_path: Path
    ) -> bool:
        """Load an experimental paint-limit plan into the existing color executor."""
        if self.executor.running:
            messagebox.showwarning(
                "Исполнение уже запущено",
                "Нельзя заменить план во время рисования.",
                parent=self.root,
            )
            return False
        area = getattr(self.executor, "area", None)
        if area is None:
            messagebox.showwarning(
                "Не выбрана область рисования",
                "Сначала выберите область рисования на вкладке 1 или 2, затем создайте тест заново.",
                parent=self.root,
            )
            self.notebook.select(self.preparation_tab)
            return False
        canvas = plan.get("canvas", {})
        if (int(canvas.get("width", -1)), int(canvas.get("height", -1))) != (area.width, area.height):
            messagebox.showwarning(
                "Размер теста не совпадает с областью",
                "Размер тестового плана должен точно совпадать с текущей областью рисования. "
                "Создайте тестовый план заново после выбора области.",
                parent=self.root,
            )
            self.notebook.select(self.paint_limit_tab_frame)
            return False
        try:
            scenario = plan.get("source", {}).get("paint_limit_test", {}).get("scenario_id", "test")
            destination = self.data_paths["paint_limit_tests"] / f"current_paint_limit_plan_{scenario}.json"
            save_color_scanline_plan(destination, plan)
            self.executor.load_color_palette_profile_document(palette_profile)
            self.executor.load_color_plan_from_path(destination)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            messagebox.showerror(
                "Не удалось передать тестовый план",
                f"Тест не передан в исполнитель.\n\n{exc}",
                parent=self.root,
            )
            return False
        self.notebook.select(self.execution_tab)
        self.status_var.set(
            f"Тест лимита краски передан: {destination.name}. Проверьте область и профиль палитры перед запуском."
        )
        return True

    def _open_folder(self, folder_name: str) -> None:
        path = self.data_paths.get(folder_name)
        if path is None:
            return
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(path)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(path)])
        except (OSError, AttributeError) as exc:
            messagebox.showerror("Не удалось открыть папку", str(exc), parent=self.root)

    def _on_close(self) -> None:
        if self.executor.running:
            should_close = messagebox.askyesno(
                "Исполнение запущено",
                "Запросить остановку, освободить кнопку мыши и закрыть AutoDraw после завершения остановки?",
                parent=self.root,
            )
            if not should_close:
                return
            self.workbench.cleanup()
            self.executor.close_after_execution = True
            self.executor._stop_execution()
            return
        self.workbench.cleanup()
        self.root.destroy()


def main() -> int:
    # Create user folders only when the application is launched, not on module import.
    for path in DATA_PATHS.values():
        path.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    AutoDrawUnifiedApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
