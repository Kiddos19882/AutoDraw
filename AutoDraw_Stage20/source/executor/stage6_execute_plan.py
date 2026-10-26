from __future__ import annotations

import ctypes
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

# Make Tkinter, PyAutoGUI and screen coordinates use physical pixels on Windows.
try:
    if hasattr(ctypes, "windll"):
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

try:
    import pyautogui
except ImportError as exc:
    raise SystemExit("Не установлены зависимости. Выполните: python -m pip install -r requirements.txt") from exc

from drawing.mouse_executor import ExecutorConfig, ExecutionSummary, MouseExecutor
from drawing.color_plan_execution import (
    BrushSliderCalibration, ColorPlanExecutionError, ColorPlanExecutionHooks,
    adaptive_brush_plan_to_drawing_plan, build_palette_targets, color_plan_to_drawing_plan,
    normalize_brush_slider_points, validate_color_plan,
)
from brush_planner import BrushPlannerError, load_adaptive_brush_plan
from drawing.execution_diagnostics import (
    build_crash_summary, build_execution_report, validate_target_area, write_execution_report,
)
from drawing.plan_transform import PlanFitInfo, fit_plan_to_size
from models import DrawingPlan
from color_scanline import load_color_scanline_plan, render_color_scanline_preview
from paint_cost_model import estimate_color_plan_paint_cost
from palette_profiles import load_palette_profile, validate_palette_profile
from path_planning.stroke_optimizer import measure_plan, render_plan_preview

_DEFAULT_APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("AUTODRAW_APP_DIR", _DEFAULT_APP_DIR)).resolve()
_HAS_SHARED_DATA_DIR = "AUTODRAW_DATA_DIR" in os.environ
DATA_DIR = Path(os.environ.get("AUTODRAW_DATA_DIR", APP_DIR)).resolve()
# Standalone Stage 14 keeps its historical file locations; the Stage 15 launcher
# explicitly redirects user data to the portable package's shared data/ folder.
_default_profile_path = DATA_DIR / "profiles" / "target_profile.json" if _HAS_SHARED_DATA_DIR else APP_DIR / "target_profile.json"
_default_settings_path = DATA_DIR / "profiles" / "execution_settings.json" if _HAS_SHARED_DATA_DIR else APP_DIR / "execution_settings.json"
PROFILE_PATH = Path(os.environ.get("AUTODRAW_TARGET_PROFILE_PATH", _default_profile_path)).resolve()
RESULTS_DIR = Path(os.environ.get("AUTODRAW_RESULTS_DIR", DATA_DIR / "results" if _HAS_SHARED_DATA_DIR else APP_DIR / "results")).resolve()
SETTINGS_PATH = Path(os.environ.get("AUTODRAW_EXECUTION_SETTINGS_PATH", _default_settings_path)).resolve()


@dataclass(frozen=True, slots=True)
class TargetArea:
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}

    @classmethod
    def from_dict(cls, data: dict) -> "TargetArea":
        return cls(
            x=int(data["x"]),
            y=int(data["y"]),
            width=int(data["width"]),
            height=int(data["height"]),
        )


class AreaSelector:
    """Полноэкранный селектор области доски без конфликтующего -fullscreen."""

    def __init__(self, parent: tk.Tk, on_done):
        self.parent = parent
        self.on_done = on_done
        self.start: tuple[int, int] | None = None
        self.rect_id: int | None = None
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.screen_w = self.window.winfo_screenwidth()
        self.screen_h = self.window.winfo_screenheight()
        self.window.overrideredirect(True)
        self.window.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-alpha", 0.32)
        except tk.TclError:
            pass
        self.window.configure(bg="#202020")
        self.canvas = tk.Canvas(self.window, bg="#202020", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            20, 20, anchor="nw", fill="white", font=("Segoe UI", 16, "bold"),
            text="Выделите рабочую область холста перетаскиванием. Esc — отмена.",
        )
        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish)
        self.window.bind("<Escape>", self._cancel)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _start(self, event) -> None:
        self.start = (int(event.x), int(event.y))
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y, outline="#00ff90", width=3
        )

    def _drag(self, event) -> None:
        if self.start is not None and self.rect_id is not None:
            self.canvas.coords(self.rect_id, self.start[0], self.start[1], event.x, event.y)

    def _finish(self, event) -> None:
        if self.start is None:
            return
        x1, x2 = sorted((self.start[0], int(event.x)))
        y1, y2 = sorted((self.start[1], int(event.y)))
        if x2 - x1 < 50 or y2 - y1 < 50:
            messagebox.showwarning(
                "Область слишком маленькая", "Выберите область размером не менее 50 × 50 px.", parent=self.window
            )
            self.start = None
            return
        area = TargetArea(x1, y1, x2 - x1, y2 - y1)
        self.window.destroy()
        self.on_done(area)

    def _cancel(self, _event=None) -> None:
        self.window.destroy()
        self.on_done(None)



class BrushSliderSelector:
    """Fullscreen two-point picker for the brush-slider track."""

    def __init__(self, parent: tk.Tk, on_done):
        self.on_done = on_done
        self.points: list[tuple[int, int]] = []
        self.marker_ids: list[int] = []
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.screen_w = self.window.winfo_screenwidth()
        self.screen_h = self.window.winfo_screenheight()
        self.window.overrideredirect(True)
        self.window.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-alpha", 0.32)
        except tk.TclError:
            pass
        self.window.configure(bg="#202020")
        self.canvas = tk.Canvas(self.window, bg="#202020", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            20, 20, anchor="nw", fill="white", font=("Segoe UI", 16, "bold"),
            text=(
                "Калибровка ползунка кисти: щёлкните позицию бегунка при значении 1, "
                "затем позицию при значении 30.\n"
                "Выбирайте центр одной горизонтальной дорожки; менять значение ползунка между щелчками не нужно. "
                "Esc — отмена."
            ),
        )
        self.status_id = self.canvas.create_text(
            20, 92, anchor="nw", fill="#ffeb3b", font=("Segoe UI", 12, "bold"),
            text="Точка 1 из 2: значение 1.",
        )
        self.cursor_id = self.canvas.create_text(
            self.screen_w - 20, 20, anchor="ne", fill="white", font=("Consolas", 12, "bold"),
            text="X=0  Y=0",
        )
        self.crosshair_v = self.canvas.create_line(
            0, 0, 0, self.screen_h, fill="#ffeb3b", dash=(4, 4), width=1
        )
        self.crosshair_h = self.canvas.create_line(
            0, 0, self.screen_w, 0, fill="#ffeb3b", dash=(4, 4), width=1
        )
        self.canvas.tag_lower(self.crosshair_v)
        self.canvas.tag_lower(self.crosshair_h)
        self.canvas.bind("<Motion>", self._track_cursor)
        self.canvas.bind("<ButtonPress-1>", self._select_point)
        self.window.bind("<Escape>", self._cancel)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _track_cursor(self, event) -> None:
        x, y = int(event.x), int(event.y)
        self.canvas.coords(self.crosshair_v, x, 0, x, self.screen_h)
        self.canvas.coords(self.crosshair_h, 0, y, self.screen_w, y)
        self.canvas.itemconfigure(self.cursor_id, text=f"X={x}  Y={y}")

    def _mark_point(self, number: int, point: tuple[int, int]) -> None:
        x, y = point
        radius = 7
        self.marker_ids.append(self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            outline="#00ff90", width=3,
        ))
        self.marker_ids.append(self.canvas.create_text(
            x + 11, y - 13, anchor="sw", fill="#00ff90",
            font=("Segoe UI", 11, "bold"), text=f"{number}: ({x}, {y})",
        ))

    def _select_point(self, event) -> None:
        point = (int(event.x), int(event.y))
        if not self.points:
            self.points.append(point)
            self._mark_point(1, point)
            self.canvas.itemconfigure(
                self.status_id,
                text="Точка 1 сохранена. Теперь щёлкните позицию бегунка при значении 30.",
            )
            return

        try:
            x_min, x_max, y = normalize_brush_slider_points(self.points[0], point)
        except ColorPlanExecutionError as exc:
            for marker_id in self.marker_ids:
                self.canvas.delete(marker_id)
            self.marker_ids.clear()
            self.points.clear()
            self.canvas.itemconfigure(
                self.status_id,
                text=f"{exc} Попробуйте ещё раз: сначала значение 1, затем 30.",
            )
            return

        self.points.append(point)
        self._mark_point(2, point)
        self.window.destroy()
        self.on_done((x_min, x_max, y))

    def _cancel(self, _event=None) -> None:
        self.window.destroy()
        self.on_done(None)


class PlanPreview(ttk.Frame):
    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        ttk.Label(self, text="Предпросмотр плана, зелёные точки — начало штрихов", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", pady=(0, 4)
        )
        self.canvas = tk.Canvas(self, background="#eeeeee", highlightthickness=1, highlightbackground="#b8b8b8")
        self.canvas.pack(fill="both", expand=True)
        self.image = None
        self.photo = None
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_plan(self, plan: DrawingPlan | None) -> None:
        self.image = render_plan_preview(plan) if plan is not None else None
        self.redraw()

    def set_image(self, image: Image.Image | None) -> None:
        self.image = image.copy() if image is not None else None
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        self.photo = None
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if self.image is None:
            self.canvas.create_text(width / 2, height / 2, text="Сначала откройте DrawingPlan JSON", fill="#555555")
            return
        margin = 12
        scale = min((width - margin * 2) / self.image.width, (height - margin * 2) / self.image.height)
        if scale <= 0:
            return
        display_w = max(1, round(self.image.width * scale))
        display_h = max(1, round(self.image.height * scale))
        display = self.image.resize((display_w, display_h), Image.Resampling.NEAREST)
        self.photo = ImageTk.PhotoImage(display)
        x = (width - display_w) / 2
        y = (height - display_h) / 2
        self.canvas.create_image(x, y, anchor="nw", image=self.photo)
        self.canvas.create_text(x + 4, y + 4, anchor="nw", fill="#16704b",
                                text=f"{self.image.width} × {self.image.height} px")


class Stage6App:
    def __init__(self, root: tk.Tk, parent: tk.Widget | None = None, *, embedded: bool = False):
        self.root = root
        self.container = parent if parent is not None else root
        self.embedded = embedded
        for directory in (PROFILE_PATH.parent, SETTINGS_PATH.parent, RESULTS_DIR):
            directory.mkdir(parents=True, exist_ok=True)
        if not embedded:
            self.root.title("AutoDraw — исполнение рисунка")
            self.root.geometry("1320x900")
            self.root.minsize(1050, 720)

        self.plan_path: Path | None = None
        self.source_plan: DrawingPlan | None = None
        self.execution_plan: DrawingPlan | None = None
        self.color_plan_data: dict[str, Any] | None = None
        self.adaptive_brush_plan: dict[str, Any] | None = None
        self.adaptive_brush_plan_path: Path | None = None
        self.color_palette_profile: dict[str, Any] | None = None
        self.color_palette_profile_path: Path | None = None
        self.fit_info: PlanFitInfo | None = None
        self.area: TargetArea | None = None
        # Optional callback used by the unified app to synchronize the preparation
        # canvas dimensions with the same selected browser drawing area.
        self.area_change_callback = None
        self.running = False
        self.close_after_execution = False
        self.stop_event = threading.Event()
        self.stop_reason: str | None = None
        self.execution_controls: list[tk.Widget] = []

        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.w_var = tk.StringVar()
        self.h_var = tk.StringVar()
        self.fit_var = tk.BooleanVar(value=True)
        self.point_step_var = tk.StringVar(value="2.0")
        self.line_extension_var = tk.StringVar(value="2.0")
        self.point_delay_var = tk.StringVar(value="10")
        self.after_up_var = tk.StringVar(value="20")
        self.before_down_var = tk.StringVar(value="20")
        self.after_down_var = tk.StringVar(value="40")
        self.end_hold_var = tk.StringVar(value="50")
        self.countdown_var = tk.StringVar(value="5")
        self.brush_slider_x_min_var = tk.StringVar(value="")
        self.brush_slider_x_max_var = tk.StringVar(value="")
        self.brush_slider_y_var = tk.StringVar(value="")
        self.brush_slider_initial_value_var = tk.StringVar(value="7")
        self.brush_slider_confirmed_var = tk.BooleanVar(value=False)
        self.brush_slider_screen_size: tuple[int, int] | None = None
        self.brush_slider_status_var = tk.StringVar(value="Ползунок кисти не откалиброван; обычные цветные планы работают без него.")
        self.status_var = tk.StringVar(value="Откройте одноцветный DrawingPlan или цветной план этапа 19 и выберите область доски.")
        self.plan_stats_var = tk.StringVar(value="План не загружен.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="Ожидание")
        self.execution_state_var = tk.StringVar(value="Состояние: готово к запуску")
        self.last_report_path: Path | None = None

        self._build_ui()
        self._load_settings()
        for variable in (
            self.brush_slider_x_min_var, self.brush_slider_x_max_var,
            self.brush_slider_y_var, self.brush_slider_initial_value_var,
        ):
            variable.trace_add("write", self._invalidate_brush_slider_calibration)
        self._load_profile_if_available()
        if not self.embedded:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.container, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Этапы 6/20 — исполнение одноцветного или цветного плана", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Откройте обычный DrawingPlan для одноцветного рисования или цветной scanline JSON вместе с профилем палитры. "
                  "Цветной план требует точного размера области: масштабирование отключено, чтобы не смещать пиксельные штрихи. "
                  "Перед запуском убедитесь, что открыта нужная доска браузера."),
            wraplength=1280,
        ).pack(anchor="w", pady=(3, 8))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        open_plan_button = ttk.Button(toolbar, text="Открыть DrawingPlan JSON…", command=self._open_plan)
        open_plan_button.pack(side="left")
        self.execution_controls.append(open_plan_button)
        open_color_plan_button = ttk.Button(toolbar, text="Открыть цветной план…", command=self._open_color_plan)
        open_color_plan_button.pack(side="left", padx=(6, 0))
        self.execution_controls.append(open_color_plan_button)
        load_adaptive_brush_button = ttk.Button(
            toolbar, text="Адаптивный план кистей…", command=self._open_adaptive_brush_plan
        )
        load_adaptive_brush_button.pack(side="left", padx=(6, 0))
        self.execution_controls.append(load_adaptive_brush_button)
        load_color_profile_button = ttk.Button(
            toolbar, text="Профиль палитры…", command=self._load_color_palette_profile_dialog
        )
        load_color_profile_button.pack(side="left", padx=(6, 0))
        self.execution_controls.append(load_color_profile_button)
        load_profile_button = ttk.Button(toolbar, text="Профиль области…", command=self._load_profile_dialog)
        load_profile_button.pack(side="left", padx=(6, 0))
        self.execution_controls.append(load_profile_button)
        select_area_button = ttk.Button(toolbar, text="Выбрать область…", command=self._select_area)
        select_area_button.pack(side="left", padx=(6, 0))
        self.execution_controls.append(select_area_button)
        ttk.Button(toolbar, text="Открыть папку проекта", command=self._open_project_folder).pack(side="right")

        area_frame = ttk.LabelFrame(outer, text="Область целевого холста на экране", padding=8)
        area_frame.pack(fill="x", pady=(0, 8))
        for col, (label, variable) in enumerate([
            ("X", self.x_var), ("Y", self.y_var), ("Ширина", self.w_var), ("Высота", self.h_var)
        ]):
            cell = ttk.Frame(area_frame)
            cell.grid(row=0, column=col, sticky="ew", padx=4)
            ttk.Label(cell, text=label).pack(anchor="w")
            entry = ttk.Entry(cell, textvariable=variable, width=10)
            entry.pack(fill="x", pady=(2, 0))
            self.execution_controls.append(entry)
            area_frame.columnconfigure(col, weight=1)
        apply_area_button = ttk.Button(area_frame, text="Применить координаты", command=self._apply_area)
        apply_area_button.grid(row=0, column=4, padx=(8, 0), sticky="nsew")
        self.execution_controls.append(apply_area_button)
        self.fit_check = ttk.Checkbutton(
            area_frame,
            text="Подгонять план под область с сохранением пропорций",
            variable=self.fit_var,
            command=self._refresh_execution_plan,
        )
        self.fit_check.grid(row=1, column=0, columnspan=5, sticky="w", padx=4, pady=(7, 0))
        self.execution_controls.append(self.fit_check)

        settings = ttk.LabelFrame(outer, text="Параметры исполнителя (начальные значения по калибровке)", padding=8)
        settings.pack(fill="x", pady=(0, 8))
        controls = [
            ("Шаг точек, px", self.point_step_var, 0.5, 20, 0.5),
            ("Продление конца линии, px", self.line_extension_var, 0, 20, 0.5),
            ("Задержка точки, мс", self.point_delay_var, 0, 100, 1),
            ("После mouseUp, мс", self.after_up_var, 0, 500, 5),
            ("Перед mouseDown, мс", self.before_down_var, 0, 500, 5),
            ("После mouseDown, мс", self.after_down_var, 0, 500, 5),
            ("Удержание в конце, мс", self.end_hold_var, 0, 500, 5),
            ("Обратный отсчёт, с", self.countdown_var, 1, 30, 1),
        ]
        for index, (label, variable, low, high, increment) in enumerate(controls):
            col = index % 4
            row = index // 4
            cell = ttk.Frame(settings)
            cell.grid(row=row, column=col, sticky="ew", padx=5, pady=2)
            ttk.Label(cell, text=label).pack(anchor="w")
            spinbox = ttk.Spinbox(cell, textvariable=variable, from_=low, to=high, increment=increment, width=12)
            spinbox.pack(anchor="w")
            self.execution_controls.append(spinbox)
            settings.columnconfigure(col, weight=1)
        ttk.Label(
            settings,
            text="Продление применяется к конечной точке каждого открытого штриха; замкнутые контуры не изменяются. У границы холста продление ограничивается его размерами.",
            wraplength=1180,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(5, 0))

        brush_settings = ttk.LabelFrame(
            outer, text="Калибровка ползунка кисти (только для адаптивного плана)", padding=8
        )
        brush_settings.pack(fill="x", pady=(0, 8))
        brush_fields = [
            ("X при значении 1", self.brush_slider_x_min_var),
            ("X при значении 30", self.brush_slider_x_max_var),
            ("Y ползунка", self.brush_slider_y_var),
            ("Текущее значение до запуска", self.brush_slider_initial_value_var),
        ]
        for col, (label, variable) in enumerate(brush_fields):
            cell = ttk.Frame(brush_settings)
            cell.grid(row=0, column=col, sticky="ew", padx=4, pady=2)
            ttk.Label(cell, text=label).pack(anchor="w")
            entry = ttk.Entry(cell, textvariable=variable, width=12)
            entry.pack(anchor="w", pady=(2, 0))
            self.execution_controls.append(entry)
            brush_settings.columnconfigure(col, weight=1)
        select_brush_button = ttk.Button(
            brush_settings,
            text="Выбрать точки мышью…",
            command=self._select_brush_slider,
        )
        select_brush_button.grid(row=1, column=0, sticky="w", padx=4, pady=(6, 2))
        self.execution_controls.append(select_brush_button)
        confirm_brush_button = ttk.Button(
            brush_settings,
            text="Подтвердить калибровку",
            command=self._confirm_brush_slider_calibration,
        )
        confirm_brush_button.grid(row=1, column=1, sticky="w", padx=4, pady=(6, 2))
        self.execution_controls.append(confirm_brush_button)
        ttk.Label(
            brush_settings,
            textvariable=self.brush_slider_status_var,
            wraplength=1180,
            justify="left",
        ).grid(row=1, column=2, columnspan=2, sticky="w", padx=4, pady=(6, 2))
        ttk.Label(
            brush_settings,
            text=("В расширенном режиме игры сначала откройте ползунок. Нажмите «Выбрать точки мышью…» и отметьте "
                  "позиции бегунка для значений 1 и 30: поля X/Y заполнятся автоматически. Затем укажите фактическое "
                  "начальное значение ползунка и подтвердите калибровку. Координаты ползунка обязаны быть вне холста."),
            wraplength=1180,
            justify="left",
        ).grid(row=2, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))

        stats_frame = ttk.LabelFrame(outer, text="План и ожидаемая работа", padding=8)
        stats_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(stats_frame, textvariable=self.plan_stats_var, justify="left", wraplength=1270).pack(anchor="w")

        self.preview = PlanPreview(outer)
        self.preview.pack(fill="both", expand=True, pady=(0, 8))

        actions = ttk.Frame(outer)
        actions.pack(fill="x")
        self.start_button = ttk.Button(actions, text="Выполнить план на доске…", command=self._start_execution, state="disabled")
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Остановить (F12)", command=self._stop_execution, state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))
        ttk.Label(actions, textvariable=self.execution_state_var).pack(side="left", padx=(12, 0))
        ttk.Button(actions, text="Открыть результаты", command=self._open_results_folder).pack(side="right")

        self.progress = ttk.Progressbar(outer, variable=self.progress_var, maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(8, 2))
        ttk.Label(outer, textvariable=self.progress_text_var).pack(anchor="w")
        ttk.Label(outer, textvariable=self.status_var, foreground="#245b42", wraplength=1280).pack(anchor="w", pady=(5, 0))

    def _load_settings(self) -> None:
        if not SETTINGS_PATH.exists():
            return
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            mappings = {
                "point_step_px": self.point_step_var,
                "line_extension_px": self.line_extension_var,
                "point_delay_ms": self.point_delay_var,
                "after_mouse_up_ms": self.after_up_var,
                "before_mouse_down_ms": self.before_down_var,
                "after_mouse_down_ms": self.after_down_var,
                "end_hold_ms": self.end_hold_var,
                "countdown_seconds": self.countdown_var,
            }
            for key, variable in mappings.items():
                if key in data:
                    variable.set(str(data[key]))
            brush_data = data.get("brush_slider_calibration", {})
            if isinstance(brush_data, dict):
                for key, variable in (
                    ("x_at_min", self.brush_slider_x_min_var),
                    ("x_at_max", self.brush_slider_x_max_var),
                    ("y", self.brush_slider_y_var),
                    ("initial_value", self.brush_slider_initial_value_var),
                ):
                    if brush_data.get(key) is not None:
                        variable.set(str(brush_data[key]))
                try:
                    if brush_data.get("screen_width") and brush_data.get("screen_height"):
                        self.brush_slider_screen_size = (
                            int(brush_data["screen_width"]), int(brush_data["screen_height"])
                        )
                except (TypeError, ValueError):
                    self.brush_slider_screen_size = None
                confirmed = brush_data.get("confirmed") is True and self.brush_slider_screen_size is not None
                self.brush_slider_confirmed_var.set(confirmed)
                self.brush_slider_status_var.set(
                    f"Калибровка загружена для {self.brush_slider_screen_size[0]}×{self.brush_slider_screen_size[1]} px."
                    if confirmed else "Ползунок кисти не откалиброван; подтвердите координаты на текущем экране."
                )
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self.status_var.set("Файл настроек исполнителя повреждён; используются значения по умолчанию.")

    def _save_settings(self, config: ExecutorConfig) -> None:
        data = config.to_dict()
        data["brush_slider_calibration"] = {
            "x_at_min": self._optional_int(self.brush_slider_x_min_var.get()),
            "x_at_max": self._optional_int(self.brush_slider_x_max_var.get()),
            "y": self._optional_int(self.brush_slider_y_var.get()),
            "initial_value": self._optional_int(self.brush_slider_initial_value_var.get()),
            "min_value": 1,
            "max_value": 30,
            "screen_width": self.brush_slider_screen_size[0] if self.brush_slider_screen_size else None,
            "screen_height": self.brush_slider_screen_size[1] if self.brush_slider_screen_size else None,
            "confirmed": bool(self.brush_slider_confirmed_var.get()),
        }
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _optional_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _invalidate_brush_slider_calibration(self, *_args) -> None:
        if self.brush_slider_confirmed_var.get():
            self.brush_slider_confirmed_var.set(False)
            self.brush_slider_status_var.set(
                "Калибровка сброшена: координаты или начальный размер изменены. Подтвердите её заново."
            )

    def _select_brush_slider(self) -> None:
        if self.running:
            return
        self.root.withdraw()
        self.root.after(120, lambda: BrushSliderSelector(self.root, self._brush_slider_points_selected))

    def _brush_slider_points_selected(self, coordinates: tuple[int, int, int] | None) -> None:
        self.root.deiconify()
        self.root.lift()
        if self.running:
            return
        if coordinates is None:
            self.brush_slider_status_var.set("Выбор координат ползунка отменён.")
            return
        x_min, x_max, y = coordinates
        self.brush_slider_x_min_var.set(str(x_min))
        self.brush_slider_x_max_var.set(str(x_max))
        self.brush_slider_y_var.set(str(y))
        self.brush_slider_status_var.set(
            f"Точки выбраны мышью: X(1)={x_min}, X(30)={x_max}, Y={y}. "
            "Укажите фактическое текущее значение бегунка и подтвердите калибровку."
        )
        self.status_var.set(
            "Координаты ползунка заполнены по двум щелчкам. Перед подтверждением проверьте, "
            "что выбран именно ползунок кисти расширенного режима."
        )

    def _confirm_brush_slider_calibration(self) -> None:
        try:
            x_min = int(self.brush_slider_x_min_var.get())
            x_max = int(self.brush_slider_x_max_var.get())
            y = int(self.brush_slider_y_var.get())
            initial = int(self.brush_slider_initial_value_var.get())
            screen = pyautogui.size()
            screen_size = (int(screen.width), int(screen.height))
            candidate = BrushSliderCalibration(
                x_at_min=x_min, x_at_max=x_max, y=y, initial_value=initial,
                screen_width=screen_size[0], screen_height=screen_size[1], confirmed=True,
            )
            candidate.validate(screen_size, self.area.to_dict() if self.area else None)
        except (ValueError, TypeError, ColorPlanExecutionError) as exc:
            messagebox.showerror("Калибровка ползунка не подтверждена", str(exc), parent=self.root)
            self.brush_slider_confirmed_var.set(False)
            self.brush_slider_status_var.set(f"Калибровка не подтверждена: {exc}")
            return
        self.brush_slider_screen_size = screen_size
        self.brush_slider_confirmed_var.set(True)
        self.brush_slider_status_var.set(
            f"Калибровка подтверждена на {screen_size[0]}×{screen_size[1]} px. "
            f"Перед запуском вручную установите бегунок на значение {initial}."
        )
        try:
            self._save_settings(self._read_executor_config())
        except (ValueError, OSError):
            # Keep the live calibration; it will be persisted with the next valid run.
            pass

    def _read_brush_slider_calibration(self) -> dict[str, Any]:
        if not self.brush_slider_confirmed_var.get() or self.brush_slider_screen_size is None:
            raise ColorPlanExecutionError(
                "Для адаптивного плана нужно подтвердить координаты ползунка кисти на текущем экране."
            )
        try:
            candidate = BrushSliderCalibration(
                x_at_min=int(self.brush_slider_x_min_var.get()),
                x_at_max=int(self.brush_slider_x_max_var.get()),
                y=int(self.brush_slider_y_var.get()),
                initial_value=int(self.brush_slider_initial_value_var.get()),
                screen_width=self.brush_slider_screen_size[0],
                screen_height=self.brush_slider_screen_size[1],
                confirmed=True,
            )
            screen = pyautogui.size()
            candidate.validate(screen, self.area.to_dict() if self.area else None)
        except (ValueError, TypeError) as exc:
            raise ColorPlanExecutionError(f"Неверная калибровка ползунка кисти: {exc}") from exc
        return {
            "x_at_min": candidate.x_at_min,
            "x_at_max": candidate.x_at_max,
            "y": candidate.y,
            "initial_value": candidate.initial_value,
            "screen_width": candidate.screen_width,
            "screen_height": candidate.screen_height,
            "confirmed": candidate.confirmed,
            "min_value": candidate.min_value,
            "max_value": candidate.max_value,
        }

    def _load_profile_if_available(self) -> None:
        if not PROFILE_PATH.exists():
            return
        try:
            self._set_area_from_file(PROFILE_PATH, update_status=False)
            self.status_var.set(f"Загружен профиль области: {self.area.width} × {self.area.height} px.")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.status_var.set(f"Не удалось загрузить профиль области: {exc}. Выберите область вручную.")

    def _load_profile_dialog(self) -> None:
        if self.running:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите target_profile.json из этапа 1 или 2",
            initialdir=str(PROFILE_PATH.parent),
            filetypes=[("Профиль AutoDraw", "target_profile.json"), ("JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self._set_area_from_file(Path(path), update_status=True)
            self._save_profile()
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка профиля", f"Не удалось загрузить профиль:\n{exc}", parent=self.root)

    def _set_area_from_file(self, path: Path, *, update_status: bool) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        area_data = data.get("area", data)
        area = TargetArea.from_dict(area_data)
        self._validate_area(area)
        self.area = area
        self._set_area_fields(area)
        self._refresh_execution_plan()
        self._notify_area_change()
        if update_status:
            self.status_var.set(f"Загружена область из {path.name}: {area.width} × {area.height} px.")

    def _set_area_fields(self, area: TargetArea) -> None:
        self.x_var.set(str(area.x))
        self.y_var.set(str(area.y))
        self.w_var.set(str(area.width))
        self.h_var.set(str(area.height))

    def _select_area(self) -> None:
        if self.running:
            return
        self.root.withdraw()
        self.root.after(120, lambda: AreaSelector(self.root, self._area_selected))

    def _area_selected(self, area: TargetArea | None) -> None:
        self.root.deiconify()
        self.root.lift()
        if self.running:
            return
        if area is None:
            self.status_var.set("Выбор области отменён.")
            return
        try:
            self._validate_area(area)
            self.area = area
            self._set_area_fields(area)
            self._save_profile()
            self._refresh_execution_plan()
            self._notify_area_change()
            self.status_var.set(f"Область применена: экран X={area.x}, Y={area.y}, размер {area.width} × {area.height} px.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Ошибка области", str(exc), parent=self.root)

    def _apply_area(self) -> None:
        if self.running:
            return
        try:
            area = TargetArea(
                int(self.x_var.get()), int(self.y_var.get()), int(self.w_var.get()), int(self.h_var.get())
            )
            self._validate_area(area)
            self.area = area
            self._save_profile()
            self._refresh_execution_plan()
            self._notify_area_change()
            self.status_var.set(f"Область применена: X={area.x}, Y={area.y}, {area.width} × {area.height} px.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Неверная область", str(exc), parent=self.root)

    def _notify_area_change(self) -> None:
        """Notify the unified preparation tab whenever the executor area changes."""
        callback = self.area_change_callback
        if callback is None or self.area is None:
            return
        try:
            size = pyautogui.size()
            callback(self.area.to_dict(), (int(size.width), int(size.height)))
        except Exception as exc:
            # A synchronization failure should be visible but must not invalidate
            # an already validated executor area.
            self.status_var.set(
                f"Область исполнителя применена, но подготовка не синхронизирована: {exc}"
            )

    @staticmethod
    def _validate_area(area: TargetArea) -> None:
        screen_width, screen_height = pyautogui.size()
        validate_target_area(area.x, area.y, area.width, area.height, screen_width, screen_height)

    def _save_profile(self) -> None:
        if self.area is None:
            return
        PROFILE_PATH.write_text(json.dumps({"area": self.area.to_dict()}, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_plan_from_path(self, path: str | Path) -> None:
        """Load a legacy monochrome DrawingPlan; reject color-plan JSON in this route."""
        if self.running:
            raise RuntimeError("Нельзя заменить план во время исполнения.")
        plan_path = Path(path).resolve()
        document = json.loads(plan_path.read_text(encoding="utf-8"))
        if isinstance(document, dict) and document.get("plan_type") == "autodraw_color_scanline_plan":
            raise ValueError("Это цветной план. Загрузите его кнопкой «Открыть цветной план…» вместе с профилем палитры.")
        plan = DrawingPlan.from_dict(document)
        plan.validate_bounds()
        self.color_plan_data = None
        self.adaptive_brush_plan = None
        self.adaptive_brush_plan_path = None
        self.plan_path = plan_path
        self.source_plan = plan
        self.status_var.set(f"Загружен одноцветный план {self.plan_path.name}; проверьте область и предпросмотр.")
        self._refresh_execution_plan()

    def load_color_plan_from_path(self, path: str | Path) -> None:
        """Load a validated Stage 19 color plan without silently downgrading it to mono."""
        if self.running:
            raise RuntimeError("Нельзя заменить план во время исполнения.")
        plan_path = Path(path).resolve()
        color_plan = load_color_scanline_plan(plan_path)
        converted = color_plan_to_drawing_plan(color_plan)
        converted.validate_bounds()
        self.color_plan_data = color_plan
        self.adaptive_brush_plan = None
        self.adaptive_brush_plan_path = None
        self.plan_path = plan_path
        self.source_plan = converted
        self.fit_var.set(False)
        self.status_var.set(
            f"Загружен цветной план {plan_path.name}: {len(color_plan['strokes'])} штрихов, "
            f"{color_plan['summary']['used_palette_color_count']} используемых цветов. "
            "Монохромный исполнитель для этого файла запрещён."
        )
        self._refresh_execution_plan()

    def load_adaptive_brush_plan_from_path(self, path: str | Path) -> None:
        """Load the brush recommendation sidecar for the exact currently loaded color plan."""
        if self.running:
            raise RuntimeError("Нельзя менять план во время исполнения.")
        if self.color_plan_data is None:
            raise ColorPlanExecutionError(
                "Сначала откройте исходный цветной scanline-план этапа 19, затем его адаптивный план кистей."
            )
        brush_path = Path(path).resolve()
        brush_plan = load_adaptive_brush_plan(brush_path)
        converted = adaptive_brush_plan_to_drawing_plan(brush_plan, self.color_plan_data)
        self.adaptive_brush_plan = brush_plan
        self.adaptive_brush_plan_path = brush_path
        self.plan_path = brush_path
        self.source_plan = converted
        self.fit_var.set(False)
        self._refresh_execution_plan()
        self.status_var.set(
            f"Адаптивный план кистей загружен: {len(converted.strokes):,} штрихов, "
            f"{brush_plan['summary']['stroke_count_by_brush']} по размерам. "
            "Перед запуском подтвердите калибровку ползунка кисти на текущем экране."
        )

    def load_color_palette_profile_document(self, document: dict[str, Any], path: str | Path | None = None) -> None:
        """Install a palette profile received directly from Stage 18/19 or loaded from disk."""
        if self.running:
            raise RuntimeError("Нельзя менять профиль палитры во время исполнения.")
        self.color_palette_profile = validate_palette_profile(document)
        self.color_palette_profile_path = Path(path).resolve() if path is not None else None
        self._refresh_execution_plan()
        self.status_var.set(
            f"Профиль палитры загружен: «{self.color_palette_profile['profile_name']}», "
            f"цветов: {len(self.color_palette_profile['colors'])}. Перед цветным рисованием профиль будет "
            "повторно проверен по снимку экрана после обратного отсчёта."
        )

    def _open_color_plan(self) -> None:
        if self.running:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите цветной scanline-план этапа 19",
            initialdir=str(self.plan_path.parent if self.plan_path else APP_DIR),
            filetypes=[("Цветной scanline-план", "*.json"), ("JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.load_color_plan_from_path(path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
            messagebox.showerror("Ошибка цветного плана", f"Не удалось открыть цветной план:\n{exc}", parent=self.root)

    def _open_adaptive_brush_plan(self) -> None:
        if self.running:
            return
        if self.color_plan_data is None:
            messagebox.showwarning(
                "Нет исходного цветного плана",
                "Сначала откройте цветной scanline-план этапа 19, затем соответствующий адаптивный план кистей.",
                parent=self.root,
            )
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите экспортированный адаптивный план кистей Stage 19",
            initialdir=str(self.plan_path.parent if self.plan_path else APP_DIR),
            filetypes=[("Адаптивный план кистей AutoDraw", "*.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            self.load_adaptive_brush_plan_from_path(path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError, BrushPlannerError) as exc:
            messagebox.showerror("Ошибка адаптивного плана кистей", str(exc), parent=self.root)

    def _load_color_palette_profile_dialog(self) -> None:
        if self.running:
            return
        profile_dir = Path(os.environ.get("AUTODRAW_PALETTES_DIR", DATA_DIR / "palettes")) / "profiles"
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите сохранённый профиль палитры этапа 17",
            initialdir=str(profile_dir if profile_dir.is_dir() else APP_DIR),
            filetypes=[("Профиль палитры AutoDraw", "*.json"), ("JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.load_color_palette_profile_document(load_palette_profile(path), path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
            messagebox.showerror("Ошибка профиля палитры", str(exc), parent=self.root)

    def _open_plan(self) -> None:
        if self.running:
            return
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите DrawingPlan JSON AutoDraw",
            initialdir=str(self.plan_path.parent if self.plan_path else APP_DIR),
            filetypes=[("DrawingPlan JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.load_plan_from_path(path)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, RuntimeError) as exc:
            messagebox.showerror("Ошибка DrawingPlan", f"Не удалось открыть план:\n{exc}", parent=self.root)

    def _refresh_execution_plan(self) -> None:
        # Do not let area/profile/fit edits change the visible plan during a captured run.
        if self.running:
            return
        self.execution_plan = None
        self.fit_info = None
        if self.source_plan is None:
            self.preview.set_plan(None)
            self.plan_stats_var.set("План не загружен.")
            self.start_button.configure(state="disabled")
            return

        base_metrics = measure_plan(self.source_plan)
        if self.color_plan_data is not None:
            try:
                self.fit_check.configure(state="disabled")
            except tk.TclError:
                pass
            preview_image = render_color_scanline_preview(self.color_plan_data, expand_single_pixel_strokes=True)
            self.preview.set_image(preview_image)
            if self.area is None:
                self.execution_plan = self.source_plan
                self.plan_stats_var.set(
                    f"Цветной план: {self.source_plan.width} × {self.source_plan.height} px; "
                    f"{base_metrics.stroke_count} штрихов; "
                    f"{self.color_plan_data['summary']['used_palette_color_count']} цвета. "
                    "Выберите область доски точного размера."
                )
                self.start_button.configure(state="disabled")
                return
            if (self.source_plan.width, self.source_plan.height) != (self.area.width, self.area.height):
                self.execution_plan = None
                self.plan_stats_var.set(
                    f"Цветной план {self.source_plan.width} × {self.source_plan.height} px, область "
                    f"{self.area.width} × {self.area.height} px. Цветной режим требует точного совпадения размера; "
                    "подгонка отключена, чтобы не сместить пиксельные штрихи. Измените область доски."
                )
                self.start_button.configure(state="disabled")
                return
            self.execution_plan = self.source_plan
            self.fit_info = PlanFitInfo(
                self.source_plan.width, self.source_plan.height, self.area.width, self.area.height,
                1.0, 1.0, 0.0, 0.0, False,
            )
            try:
                if self.color_palette_profile is None:
                    raise ColorPlanExecutionError("Сначала загрузите профиль палитры этапа 17 или передайте его с вкладки 5.")
                targets = build_palette_targets(
                    self.color_plan_data, self.color_palette_profile, current_screen_size=pyautogui.size()
                )
                color_summary = ", ".join(f"{target.hex} ({target.name})" for target in targets.values())
                try:
                    ink_estimate = self.color_plan_data["summary"].get("paint_cost_estimate")
                    if not isinstance(ink_estimate, dict):
                        ink_estimate = estimate_color_plan_paint_cost(self.color_plan_data)
                    highest = ink_estimate.get("highest_use_color")
                    per_color_text = (
                        f"Максимум одного цвета: {highest.get('hex', '')} {highest.get('estimated_usage_percent', 0):.1f}%. "
                        if isinstance(highest, dict) else ""
                    )
                    ink_text = (
                        f"Если запас общий: {ink_estimate['estimated_total_ink_px_equivalent']:,.0f}/"
                        f"{ink_estimate['estimated_budget_px_equivalent']:,.0f} px-экв. "
                        f"({ink_estimate['estimated_usage_percent']:.1f}%); {per_color_text}{ink_estimate['risk_label']}."
                    )
                except (ValueError, KeyError, TypeError):
                    ink_text = "Оценка краски недоступна для этого плана."
                self.plan_stats_var.set(
                    f"Цветной план: {self.source_plan.width} × {self.source_plan.height} px; "
                    f"штрихов: {base_metrics.stroke_count}; переключения цвета: "
                    f"{self.color_plan_data['summary']['color_switch_count']}; "
                    f"выборов цвета ожидается: {self.color_plan_data['summary']['color_selection_count_estimate']}.\n"
                    f"{ink_text}\n"
                    f"Профиль: {self.color_palette_profile['profile_name']}; цвета: {color_summary}. "
                    "Перед началом исполнитель проверит палитру по свежему снимку экрана."
                )
                self.start_button.configure(state="normal")
            except (ColorPlanExecutionError, ValueError, TypeError, IndexError) as exc:
                self.plan_stats_var.set(f"Цветной план не готов к запуску: {exc}")
                self.start_button.configure(state="disabled")
            return
        else:
            try:
                self.fit_check.configure(state="normal")
            except tk.TclError:
                pass

        if self.area is None:
            self.execution_plan = self.source_plan
            self.preview.set_plan(self.execution_plan)
            self.plan_stats_var.set(
                f"План: {self.source_plan.name}; размер {self.source_plan.width} × {self.source_plan.height} px; "
                f"{base_metrics.stroke_count} штрихов, {base_metrics.point_count} точек; "
                "область доски не выбрана — выполнение недоступно."
            )
            self.start_button.configure(state="disabled")
            return

        if (self.source_plan.width, self.source_plan.height) == (self.area.width, self.area.height):
            self.execution_plan = self.source_plan
            self.fit_info = PlanFitInfo(
                self.source_plan.width, self.source_plan.height, self.area.width, self.area.height,
                1.0, 1.0, 0.0, 0.0, bool(self.fit_var.get()),
            )
        elif self.fit_var.get():
            try:
                self.execution_plan, self.fit_info = fit_plan_to_size(
                    self.source_plan, self.area.width, self.area.height, preserve_aspect_ratio=True
                )
            except ValueError as exc:
                self.plan_stats_var.set(f"Не удалось подогнать план: {exc}")
                self.preview.set_plan(None)
                self.start_button.configure(state="disabled")
                return
        else:
            self.preview.set_plan(self.source_plan)
            self.plan_stats_var.set(
                f"Размер плана {self.source_plan.width} × {self.source_plan.height} px не совпадает с областью "
                f"{self.area.width} × {self.area.height} px. Включите подгонку или выберите точную область."
            )
            self.start_button.configure(state="disabled")
            return

        metrics = measure_plan(self.execution_plan, point_step_px=self._safe_point_step_for_stats())
        fit_text = "размер совпадает с областью"
        if self.fit_info and not self.fit_info.is_identity:
            fit_text = (
                f"масштаб X={self.fit_info.scale_x:.4f}, Y={self.fit_info.scale_y:.4f}; "
                f"смещение X={self.fit_info.offset_x:.1f}, Y={self.fit_info.offset_y:.1f} px"
            )
        self.preview.set_plan(self.execution_plan)
        self.plan_stats_var.set(
            f"Источник: {self.source_plan.width} × {self.source_plan.height} px → цель: "
            f"{self.execution_plan.width} × {self.execution_plan.height} px ({fit_text}).\n"
            f"Штрихи: {metrics.stroke_count}; точки: {metrics.point_count}; длина рисования: "
            f"{metrics.drawing_length_px:.1f} px; переходы без рисования: {metrics.pen_up_distance_px:.1f} px; "
            f"оценка интервалов движения при текущем шаге: {metrics.estimated_move_calls}."
        )
        self.start_button.configure(state="normal")

    def _safe_point_step_for_stats(self) -> float:
        try:
            value = float(self.point_step_var.get())
            return value if value > 0 else 2.0
        except (ValueError, TypeError):
            return 2.0

    def _read_executor_config(self) -> ExecutorConfig:
        try:
            config = ExecutorConfig(
                point_step_px=float(self.point_step_var.get()),
                line_extension_px=float(self.line_extension_var.get()),
                point_delay_ms=int(self.point_delay_var.get()),
                after_mouse_up_ms=int(self.after_up_var.get()),
                before_mouse_down_ms=int(self.before_down_var.get()),
                after_mouse_down_ms=int(self.after_down_var.get()),
                end_hold_ms=int(self.end_hold_var.get()),
                countdown_seconds=int(self.countdown_var.get()),
            )
            config.validate()
            return config
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Проверьте параметры исполнителя: {exc}") from exc

    def _start_execution(self) -> None:
        if self.running:
            return
        if self.execution_plan is None or self.area is None or self.plan_path is None:
            messagebox.showwarning("План не готов", "Сначала загрузите план и выберите область доски.", parent=self.root)
            return
        try:
            config = self._read_executor_config()
            self.execution_plan.validate_bounds()
            # Revalidate against the current display: resolution/monitor can change after profile load.
            self._validate_area(self.area)
            brush_slider_calibration = None
            if self.adaptive_brush_plan is not None:
                if self.color_plan_data is None:
                    raise ColorPlanExecutionError("Адаптивному плану нужен исходный цветной план этапа 19.")
                brush_slider_calibration = self._read_brush_slider_calibration()
                if int(self.adaptive_brush_plan["summary"].get("legacy_fallback_source_stroke_count", 0)) > 0:
                    raise ColorPlanExecutionError(
                        "Адаптивный план содержит штрихи без подтверждённой геометрической безопасности. "
                        "Пересчитайте рекомендации или используйте обычный цветной план."
                    )
            if self.color_plan_data is not None:
                if self.color_palette_profile is None:
                    raise ColorPlanExecutionError("Загрузите профиль палитры прежде, чем запускать цветной план.")
                if (self.execution_plan.width, self.execution_plan.height) != (self.area.width, self.area.height):
                    raise ColorPlanExecutionError("Размер цветного плана не совпадает с областью доски. Подгонка запрещена.")
                build_palette_targets(
                    self.color_plan_data, self.color_palette_profile, current_screen_size=pyautogui.size()
                )
            self._save_settings(config)
        except (ValueError, OSError, ColorPlanExecutionError) as exc:
            messagebox.showerror("Неверные настройки", str(exc), parent=self.root)
            return

        color_plan = self.color_plan_data
        color_profile = self.color_palette_profile if color_plan is not None else None
        if color_plan is not None:
            used_color_count = int(color_plan["summary"]["used_palette_color_count"])
            single_pixel_count = int(color_plan["summary"].get("single_pixel_stroke_count", 0))
            single_pixel_note = (
                f"\nОдиночных пикселей: {single_pixel_count}. Вместо клика каждый будет выполнен "
                f"горизонтальным штрихом базовой длиной 1 px; затем исполнитель продлит конец на "
                f"{config.line_extension_px:g} px. На границе холста продление ограничивается его размерами. "
                "Предпросмотр показывает базовый план; добавка применяется при исполнении."
                if single_pixel_count else ""
            )
            try:
                ink_estimate = color_plan["summary"].get("paint_cost_estimate")
                if not isinstance(ink_estimate, dict):
                    ink_estimate = estimate_color_plan_paint_cost(color_plan)
                ink_text = (
                    f"Оценка при общем запасе краски: {ink_estimate['estimated_total_ink_px_equivalent']:,.0f}/"
                    f"{ink_estimate['estimated_budget_px_equivalent']:,.0f} px-экв. "
                    f"({ink_estimate['estimated_usage_percent']:.1f}%; консервативно "
                    f"{ink_estimate['conservative_usage_percent']:.1f}%).\n"
                    f"{ink_estimate['risk_label']}. Это экспериментальный прогноз, не счётчик игры.\n"
                    + (
                        f"Если запас отдельный для каждого цвета, максимум: "
                        f"{ink_estimate['highest_use_color'].get('hex', '')} — "
                        f"{ink_estimate['highest_use_color'].get('estimated_usage_percent', 0):.1f}% "
                        f"({ink_estimate['highest_use_color'].get('stroke_count', 0)} штрихов).\n"
                        if isinstance(ink_estimate.get("highest_use_color"), dict) else ""
                    )
                )
            except (ValueError, KeyError, TypeError):
                ink_text = "Оценка краски недоступна; проверьте план вручную.\n"
            color_mode_text = (
                f"Режим: ЦВЕТНОЙ\nПрофиль палитры: {color_profile['profile_name']}\n"
                f"Используемых цветов: {used_color_count}; ожидаемых выборов цвета: "
                f"{color_plan['summary']['color_selection_count_estimate']}\n"
                f"{ink_text}"
                "После обратного отсчёта AutoDraw проверит палитру по снимку экрана. "
                "При несовпадении рисование не начнётся.\n"
                f"{single_pixel_note}\n"
            )
        else:
            color_mode_text = "Режим: одноцветный\n\n"
        details = (
            f"Файл: {self.plan_path.name}\n"
            f"Размер плана: {self.execution_plan.width} × {self.execution_plan.height} px\n"
            f"Экранная область: X={self.area.x}, Y={self.area.y}, "
            f"{self.area.width} × {self.area.height} px\n\n"
            f"Штрихов: {len(self.execution_plan.strokes)}\n"
            f"Интервал между точками: {config.point_delay_ms} мс\n"
            f"Продление конца открытого штриха: +{config.line_extension_px:g} px (с ограничением по границе холста)\n"
            f"Паузы после mouseUp / перед mouseDown: {config.after_mouse_up_ms} / {config.before_mouse_down_ms} мс\n\n"
            f"{color_mode_text}"
            + (
                f"АДАПТИВНЫЕ КИСТИ: {self.adaptive_brush_plan['summary']['stroke_count_by_brush']}\n"
                f"Калибровка ползунка подтверждена на {self.brush_slider_screen_size[0]}×{self.brush_slider_screen_size[1]} px. "
                f"Исполнитель начнёт с указанного значения {self.brush_slider_initial_value_var.get()} и будет перетаскивать бегунок.\n"
                "Продление концов принудительно равно 0 для адаптивных штрихов, чтобы не выйти за проверенную область.\n"
                if self.adaptive_brush_plan is not None else ""
            )
            + "После подтверждения начнётся обратный отсчёт. Переключитесь на правильную вкладку браузера.\n"
            "F12 или кнопка остановки прекращает рисование; кнопка мыши будет отпущена."
        )
        if not messagebox.askokcancel("Подтвердите рисование", details, icon="warning", parent=self.root):
            self.execution_state_var.set("Состояние: запуск отменён")
            return

        self.running = True
        self.stop_event = threading.Event()
        self.stop_reason = None
        self.execution_state_var.set("Состояние: подготовка")
        self._set_execution_controls_enabled(False)
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress_var.set(0)
        self.progress_text_var.set("Подготовка исполнителя…")
        self.status_var.set("Исполнение запущено. Во время обратного отсчёта переключитесь на браузер.")
        plan = self.execution_plan
        area = self.area
        fit_info = self.fit_info
        plan_path = self.plan_path
        thread = threading.Thread(
            target=self._execute_in_worker,
            args=(plan, area, config, fit_info, plan_path, color_plan, color_profile, brush_slider_calibration),
            name="AutoDraw-Executor",
            daemon=True,
        )
        try:
            thread.start()
        except Exception as exc:
            self._execution_crashed(
                f"{type(exc).__name__}: не удалось запустить рабочий поток: {exc}",
                config, plan, area, fit_info, plan_path,
            )

    def _set_execution_controls_enabled(self, enabled: bool) -> None:
        for widget in self.execution_controls:
            state = "normal" if enabled else "disabled"
            if enabled and widget is self.fit_check and self.color_plan_data is not None:
                state = "disabled"
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass

    def _execute_in_worker(
        self,
        plan: DrawingPlan,
        area: TargetArea,
        config: ExecutorConfig,
        fit_info: PlanFitInfo | None,
        plan_path: Path,
        color_plan: dict[str, Any] | None = None,
        color_profile: dict[str, Any] | None = None,
        brush_slider_calibration: dict[str, Any] | None = None,
    ) -> None:
        hooks: ColorPlanExecutionHooks | None = None
        try:
            executor = MouseExecutor(
                self.stop_event, config, stop_reason_provider=lambda: self.stop_reason
            )
            execute_options: dict[str, Any] = {}
            if color_plan is not None:
                if color_profile is None:
                    raise ColorPlanExecutionError("Профиль палитры не был передан исполнителю.")
                hooks = ColorPlanExecutionHooks(
                    color_plan,
                    color_profile,
                    current_screen_size_provider=pyautogui.size,
                    brush_slider_calibration=brush_slider_calibration,
                    brush_target_area=area.to_dict() if brush_slider_calibration is not None else None,
                )
                execute_options["preflight"] = hooks.preflight
                execute_options["before_stroke"] = hooks.before_stroke
            summary = executor.execute(
                plan,
                area.x,
                area.y,
                progress=lambda current, total, detail: self.root.after(
                    0, self._update_progress, current, total, detail
                ),
                **execute_options,
            )
            color_details = hooks.to_report() if hooks is not None else None
            self.root.after(
                0, self._finish_execution, summary, config, plan, area, fit_info, plan_path, color_details
            )
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            color_details = hooks.to_report() if hooks is not None else None
            if color_plan is not None and color_details is None:
                # Keep a Stage 20 report even if validating/creating hooks fails before preflight.
                color_details = {
                    "profile_name": (color_profile or {}).get("profile_name"),
                    "selected_color_count": 0,
                    "selection_order": [],
                    "used_colors": [],
                    "selection_policy": "select_only_when_color_changes; preserve_scanline_stroke_order",
                    "screenshot_preflight": "not_completed",
                    "setup_error": error,
                }
            self.root.after(
                0, self._execution_crashed, error, config, plan, area, fit_info, plan_path, color_details
            )

    def _update_progress(self, current: int, total: int, detail: str) -> None:
        if detail.startswith("Начало через"):
            self.execution_state_var.set("Состояние: обратный отсчёт")
        elif "Выбрана кисть" in detail or "Кисть " in detail:
            self.execution_state_var.set("Состояние: выбор кисти")
        elif detail.startswith("Проверка палитры"):
            self.execution_state_var.set("Состояние: проверка палитры")
        elif detail.startswith("Выбрана кисть") or "Кисть " in detail:
            self.execution_state_var.set("Состояние: выбор кисти")
        elif detail.startswith("Выбран цвет") or detail.startswith("Цвет "):
            self.execution_state_var.set("Состояние: выбор цвета")
        elif detail.startswith("Штрих") or detail.startswith("Завершён штрих"):
            self.execution_state_var.set("Состояние: рисование")
        if total > 0:
            self.progress_var.set(current * 100 / total)
        else:
            self.progress_var.set(0)
        self.progress_text_var.set(f"{current}/{total}: {detail}")

    def _finish_execution(
        self,
        summary: ExecutionSummary,
        config: ExecutorConfig,
        plan: DrawingPlan,
        area: TargetArea,
        fit_info: PlanFitInfo | None,
        plan_path: Path,
        color_details: dict[str, Any] | None = None,
    ) -> None:
        summary_data = summary.to_dict(config)
        if color_details is not None:
            summary_data["color_execution"] = color_details
        report = build_execution_report(
            stage=20 if color_details is not None else 14,
            source_plan_path=plan_path,
            source_plan=self.source_plan,
            executed_plan=plan,
            target_area=area.to_dict(),
            fit_info=fit_info,
            summary=summary_data,
            config=config.to_dict(),
            status=summary.status,
            error=summary.error,
        )
        if color_details is not None and self.color_plan_data is not None:
            from drawing.execution_diagnostics import canonical_sha256
            report["color_plan"] = {
                "plan_type": self.color_plan_data.get("plan_type"),
                "name": self.color_plan_data.get("name"),
                "sha256": canonical_sha256(self.color_plan_data),
                "paint_cost_estimate": self.color_plan_data.get("summary", {}).get("paint_cost_estimate"),
                "palette_profile_name": color_details.get("profile_name"),
                "selection_count": color_details.get("selected_color_count"),
                "selection_order": color_details.get("selection_order", []),
                "used_colors": color_details.get("used_colors", []),
            }
            if self.adaptive_brush_plan is not None:
                report["adaptive_brush_plan"] = {
                    "path": str(self.adaptive_brush_plan_path) if self.adaptive_brush_plan_path else None,
                    "source_plan_sha256": self.adaptive_brush_plan.get("source_plan_sha256"),
                    "summary": self.adaptive_brush_plan.get("summary", {}),
                    "brush_slider_selection_count": color_details.get("brush_size_selection_count", 0),
                    "brush_slider_selection_order": color_details.get("brush_size_selection_order", []),
                    "slider_calibration": color_details.get("brush_slider_calibration"),
                }
        try:
            report_path = write_execution_report(RESULTS_DIR, report)
            self.last_report_path = report_path
            report_status = f"Отчёт: {report_path}"
        except OSError as exc:
            report_status = f"Не удалось сохранить отчёт: {exc}"

        self.running = False
        self._set_execution_controls_enabled(True)
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="normal" if self.execution_plan is not None and self.area is not None else "disabled")
        self.execution_state_var.set({"completed": "Состояние: завершено", "stopped": "Состояние: остановлено", "failed": "Состояние: ошибка"}.get(summary.status, f"Состояние: {summary.status}"))
        self.progress_var.set(100 if summary.status == "completed" else self.progress_var.get())
        self.progress_text_var.set(
            f"{summary.completed_strokes}/{summary.total_strokes} штрихов; "
            f"{summary.duration_seconds:.1f} с; {summary.move_calls} вызовов перемещения; статус: {summary.status}."
        )
        if summary.status == "completed":
            self.status_var.set(f"План выполнен. {report_status}")
            message = f"Исполнение завершено.\nШтрихов: {summary.completed_strokes}/{summary.total_strokes}\n"
            message += f"Время: {summary.duration_seconds:.1f} с\n{report_status}"
            messagebox.showinfo("AutoDraw — выполнение завершено", message, parent=self.root)
        elif summary.status == "stopped":
            if summary.mouse_release_succeeded:
                self.status_var.set(f"Исполнение остановлено; команда mouseUp выполнена без ошибки. {report_status}")
            else:
                self.status_var.set(f"ОСТАНОВЛЕНО, НО НЕ УДАЛОСЬ ПОДТВЕРДИТЬ ОТПУСКАНИЕ МЫШИ. Проверьте ввод вручную. {report_status}")
            reason = summary.stop_reason or "причина не определена"
            release_line = "Команда mouseUp выполнена без ошибки." if summary.mouse_release_succeeded else "ВНИМАНИЕ: команда mouseUp завершилась с ошибкой; проверьте состояние мыши вручную."
            messagebox.showinfo("AutoDraw — остановлено", f"Причина: {reason}\nВыполнено штрихов: {summary.completed_strokes}/{summary.total_strokes}.\n{release_line}\n{report_status}", parent=self.root)
        else:
            self.status_var.set(f"Исполнение завершилось с ошибкой: {summary.error or 'неизвестная ошибка'}. {report_status}")
            release_info = "" if summary.mouse_release_succeeded else "\nВНИМАНИЕ: команда mouseUp не подтверждена. Проверьте состояние мыши вручную."
            messagebox.showerror("Ошибка исполнения", f"{summary.error or 'Неизвестная ошибка'}{release_info}\n{report_status}", parent=self.root)

        if self.close_after_execution:
            self.root.destroy()

    def _execution_crashed(
        self,
        error: str,
        config: ExecutorConfig,
        plan: DrawingPlan,
        area: TargetArea,
        fit_info: PlanFitInfo | None,
        plan_path: Path,
        color_details: dict[str, Any] | None = None,
    ) -> None:
        # Also create a report if failure happened before MouseExecutor returned its summary.
        summary = build_crash_summary(error)
        if color_details is not None:
            summary["color_execution"] = color_details
        report = build_execution_report(
            stage=20 if color_details is not None else 14,
            source_plan_path=plan_path,
            source_plan=self.source_plan,
            executed_plan=plan,
            target_area=area.to_dict(),
            fit_info=fit_info,
            summary=summary,
            config=config.to_dict(),
            status="failed",
            error=error,
        )
        if color_details is not None and self.color_plan_data is not None:
            from drawing.execution_diagnostics import canonical_sha256
            report["color_plan"] = {
                "plan_type": self.color_plan_data.get("plan_type"),
                "name": self.color_plan_data.get("name"),
                "sha256": canonical_sha256(self.color_plan_data),
                "paint_cost_estimate": self.color_plan_data.get("summary", {}).get("paint_cost_estimate"),
                "palette_profile_name": color_details.get("profile_name"),
                "selection_count": color_details.get("selected_color_count"),
                "selection_order": color_details.get("selection_order", []),
                "used_colors": color_details.get("used_colors", []),
            }
        try:
            report_path = write_execution_report(RESULTS_DIR, report)
            report_text = f"Отчёт: {report_path}"
        except OSError as report_exc:
            report_text = f"Не удалось сохранить отчёт: {report_exc}"
        self.running = False
        self._set_execution_controls_enabled(True)
        self.stop_button.configure(state="disabled")
        self.start_button.configure(state="normal" if self.execution_plan is not None and self.area is not None else "disabled")
        self.execution_state_var.set("Состояние: ошибка")
        self.status_var.set(f"Ошибка исполнителя: {error}. Состояние кнопки мыши автоматически подтвердить не удалось. {report_text}")
        messagebox.showerror(
            "Ошибка исполнителя",
            f"{error}\n\nПроверьте, что кнопка мыши отпущена.\n{report_text}",
            parent=self.root,
        )
        if self.close_after_execution:
            self.root.destroy()

    def _stop_execution(self) -> None:
        if self.running:
            if self.stop_reason is None:
                self.stop_reason = "stop_button"
            self.stop_event.set()
            self.execution_state_var.set("Состояние: выполняется остановка")
            self.status_var.set("Запрошена остановка. Прерываются обратный отсчёт/задержки; исполнитель отпустит кнопку мыши в блоке очистки.")
            self.stop_button.configure(state="disabled")

    def _open_project_folder(self) -> None:
        try:
            os.startfile(str(APP_DIR))
        except (OSError, AttributeError) as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку проекта: {exc}", parent=self.root)

    def _open_results_folder(self) -> None:
        try:
            RESULTS_DIR.mkdir(parents=True, exist_ok=True)
            os.startfile(str(RESULTS_DIR))
        except (OSError, AttributeError) as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку результатов: {exc}", parent=self.root)

    def _on_close(self) -> None:
        if not self.running:
            self.root.destroy()
            return
        if messagebox.askyesno(
            "Исполнение запущено",
            "Запросить остановку и закрыть приложение после безопасного отпускания кнопки мыши?",
            parent=self.root,
        ):
            self.close_after_execution = True
            self._stop_execution()


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    Stage6App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
