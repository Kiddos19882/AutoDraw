from __future__ import annotations

import json
import uuid
import ctypes
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

import pyautogui
from PIL import Image, ImageGrab

from stage8_optimizer import save_plan
from brush_experiment_capture import (
    compare_images, crop_calibrated_regions,
    measure_meter_fill_against_baseline, evaluate_meter_restoration,
)


TEST_CASES: dict[str, dict[str, Any]] = {
    "Расход краски — серия длинных линий": {
        "id": "paint_consumption_long_lines",
        "description": (
            "Измерение расхода краски на серии из 12 длинных параллельных линий. "
            "Ориентировочная суммарная длина траектории — 4800 px; выполняй на чистой доске "
            "и записывай запас краски до и после."
        ),
        "strokes": [
            {
                "name": f"consumption_line_{index:02d}",
                "points": [[20, 10 + index * 18], [420, 10 + index * 18]],
            }
            for index in range(12)
        ],
    },
    "Горизонтальные линии": {
        "id": "horizontal_lengths",
        "description": "Проверка длины и фактической ширины следа на прямых линиях.",
        "strokes": [
            {"name": "horizontal_10", "points": [[20, 20], [30, 20]]},
            {"name": "horizontal_20", "points": [[20, 45], [40, 45]]},
            {"name": "horizontal_50", "points": [[20, 70], [70, 70]]},
            {"name": "horizontal_100", "points": [[20, 95], [120, 95]]},
            {"name": "horizontal_200", "points": [[20, 120], [220, 120]]},
        ],
    },
    "Вертикальные линии": {
        "id": "vertical_lengths",
        "description": "Проверка ширины следа по X и окончания вертикального штриха.",
        "strokes": [
            {"name": "vertical_10", "points": [[20, 20], [20, 30]]},
            {"name": "vertical_20", "points": [[45, 20], [45, 40]]},
            {"name": "vertical_50", "points": [[70, 20], [70, 70]]},
            {"name": "vertical_100", "points": [[95, 20], [95, 120]]},
        ],
    },
    "Диагонали": {
        "id": "diagonal_lengths",
        "description": "Проверка кривизны диагонали, формы концов и эффективной длины.",
        "strokes": [
            {"name": "diagonal_20", "points": [[20, 20], [40, 40]]},
            {"name": "diagonal_50", "points": [[20, 55], [70, 105]]},
            {"name": "diagonal_100", "points": [[20, 120], [120, 220]]},
        ],
    },
    "Короткие линии и точки": {
        "id": "short_strokes",
        "description": "Поиск минимальной длины, которая стабильно появляется в игре.",
        "strokes": [
            {"name": "length_0", "points": [[15, 20], [15, 20]]},
            {"name": "length_1", "points": [[35, 20], [36, 20]]},
            {"name": "length_2", "points": [[55, 20], [57, 20]]},
            {"name": "length_3", "points": [[75, 20], [78, 20]]},
            {"name": "length_5", "points": [[95, 20], [100, 20]]},
            {"name": "length_8", "points": [[115, 20], [123, 20]]},
            {"name": "length_10", "points": [[135, 20], [145, 20]]},
        ],
    },
    "Прямоугольник и углы": {
        "id": "rectangle_corners",
        "description": "Проверка соединения линий, скругления углов и замыкания контура.",
        "strokes": [
            {"name": "top", "points": [[20, 20], [120, 20]]},
            {"name": "right", "points": [[120, 20], [120, 80]]},
            {"name": "bottom", "points": [[120, 80], [20, 80]]},
            {"name": "left", "points": [[20, 80], [20, 20]]},
        ],
    },
}


def build_brush_test_record(
    *, brush_value: int, test_case: str, canvas_area: dict[str, int] | None = None,
    screen_area: dict[str, int] | None = None, screenshot_path: str | None = None,
    drawing_plan_path: str | None = None, drawing_plan: dict[str, Any] | None = None,
    execution_report_path: str | None = None, execution_report: dict[str, Any] | None = None,
    measurements: dict[str, Any] | None = None, notes: str = "", outcome: str = "not_reviewed",
    screen_resolution: dict[str, int] | None = None, brush_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a versioned, portable observation record for later brush-model fitting."""
    if isinstance(brush_value, bool) or not isinstance(brush_value, int) or not 1 <= brush_value <= 30:
        raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
    if test_case not in TEST_CASES:
        raise ValueError(f"Неизвестный тест кисти: {test_case}")
    scenario = TEST_CASES[test_case]
    return {
        "schema_version": 1,
        "record_type": "autodraw_brush_behavior_observation",
        "record_id": uuid.uuid4().hex,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "brush_value": brush_value,
        "test_case": {"id": scenario["id"], "name": test_case, "description": scenario["description"]},
        "canvas_area": canvas_area,
        "board_selection_origin": ({"x": canvas_area["x"], "y": canvas_area["y"]} if canvas_area else None),
        "board_selection_size": ({"width": canvas_area["width"], "height": canvas_area["height"]} if canvas_area else None),
        "screen_resolution": screen_resolution,
        "screen_area": screen_area,
        "brush_control": brush_control,
        "screenshot_path": screenshot_path,
        "drawing_plan_path": drawing_plan_path,
        "drawing_plan": drawing_plan,
        "execution_report_path": execution_report_path,
        "execution_report": execution_report,
        "outcome": outcome,
        "notes": notes.strip(),
        "planned_strokes": scenario["strokes"],
        "measurement_fields": {
            "observed_stroke_count": None,
            "visible_stroke_names": [],
            "missing_stroke_names": [],
            "measured_footprint_width_px": None,
            "measured_footprint_height_px": None,
            "endpoints_offset_px": None,
            "paint_points_before": None,
            "paint_points_after": None,
            "browser_zoom_percent": None,
            "device_pixel_ratio": None,
            **(measurements or {}),
        },
        "interpretation": {
            "status": "raw_observation",
            "automatic_execution_allowed": False,
            "note": "Запись фиксирует тестовый шаблон и наблюдение; модель кисти строится после заполнения измерений.",
        },
    }


def build_brush_test_drawing_plan(test_case: str, canvas_size: tuple[int, int]) -> dict[str, Any]:
    """Build a standard local-canvas DrawingPlan that the existing executor can load."""
    if test_case not in TEST_CASES:
        raise ValueError(f"Неизвестный тест кисти: {test_case}")
    width, height = (int(canvas_size[0]), int(canvas_size[1]))
    if width < 1 or height < 1:
        raise ValueError("Размер тестового холста должен быть положительным.")
    scenario = TEST_CASES[test_case]
    strokes = []
    for item in scenario["strokes"]:
        points = item["points"]
        if any(x < 0 or y < 0 or x >= width or y >= height for x, y in points):
            raise ValueError(
                f"Штрих {item['name']} выходит за пределы холста {width} × {height}."
            )
        strokes.append({
            "name": item["name"],
            "points": [{"x": float(x), "y": float(y)} for x, y in points],
            "closed": False,
            "metadata": {"role": "brush_behavior_test", "test_case": scenario["id"]},
        })
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "schema_version": 1,
        "name": f"Brush behavior test — {scenario['id']}",
        "created_at": now,
        "coordinate_system": "local_canvas_pixels",
        "canvas": {"width": width, "height": height},
        "width": width,
        "height": height,
        "strokes": strokes,
        "generation": {
            "method": "manual_brush_behavior_test",
            "test_case": scenario["id"],
            "brush_value_must_be_set_manually": True,
            "note": "Set the requested brush size in the browser before executing this plan.",
        },
    }


class BrushBehaviorTestTab:
    """Manual browser brush test matrix, screenshot capture, and raw-data storage."""

    def __init__(
        self, root: tk.Misc, parent: tk.Widget, output_dir: str | Path,
        area_selector_cls, *, get_canvas_size, get_canvas_area, on_transfer_plan, get_brush_control=None,
        get_calibration_profile=None,
    ):
        self.root = root
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.area_selector_cls = area_selector_cls
        self.get_canvas_size = get_canvas_size
        self.get_canvas_area = get_canvas_area
        self.get_brush_control = get_brush_control
        self.get_calibration_profile = get_calibration_profile
        self.on_transfer_plan = on_transfer_plan
        self.experiment_dir: Path | None = None
        self.experiment_phases: dict[str, dict[str, Any]] = {}
        self.current_plan: dict[str, Any] | None = None
        self.current_plan_path: Path | None = None
        self.canvas_area: dict[str, int] | None = None
        self.screen_area: dict[str, int] | None = None
        self.screen_resolution: dict[str, int] | None = None
        self.brush_slider_start: tuple[int, int] | None = None
        self.brush_slider_end: tuple[int, int] | None = None
        self.screenshot_path: Path | None = None
        self.execution_report_path: Path | None = None
        self.execution_report: dict[str, Any] | None = None
        self.last_record_path: Path | None = None
        self.brush_var = tk.StringVar(value="7")
        self.case_var = tk.StringVar(value=next(iter(TEST_CASES)))
        self.outcome_var = tk.StringVar(value="not_reviewed")
        self.notes_var = tk.StringVar()
        self.visible_strokes_var = tk.StringVar()
        self.missing_strokes_var = tk.StringVar()
        self.footprint_width_var = tk.StringVar()
        self.footprint_height_var = tk.StringVar()
        self.paint_before_var = tk.StringVar()
        self.paint_after_var = tk.StringVar()
        self.zoom_var = tk.StringVar(value="100")
        self.area_var = tk.StringVar(value="Область доски берётся из профиля исполнения.")
        self.slider_start_var = tk.StringVar()
        self.slider_end_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Выбери радиус и тест. Автоустановка 1–30 работает только с расширенным ползунком игры.")
        self._build(parent)

    def _build(self, parent: tk.Widget) -> None:
        outer = ttk.Frame(parent, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Тест поведения кистей", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Для каждой кисти выполняй тест отдельно на чистой тестовой доске. Сначала запиши исходный запас краски, "
                  "затем выполни указанные штрихи через исполнитель AutoDraw. После завершения выбери область снимка: "
                  "в JSON сохраняются параметры, координаты запланированных штрихов, путь к скриншоту и поля для измерений. "
                  "Размер задаётся радиусом: обычный режим предлагает радиусы 7, 14 и 20; расширенный ползунок меняет радиус от 30 слева до 1 справа."),
            wraplength=1150, justify="left",
        ).pack(anchor="w", pady=(4, 10))

        controls = ttk.LabelFrame(outer, text="Настройки серии", padding=8)
        controls.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(controls)
        row.pack(fill="x")
        ttk.Label(row, text="Радиус кисти (1–30)").pack(side="left")
        ttk.Entry(row, textvariable=self.brush_var, width=6).pack(side="left", padx=(6, 16))
        ttk.Label(row, text="Тест").pack(side="left")
        ttk.Combobox(row, textvariable=self.case_var, values=tuple(TEST_CASES), state="readonly", width=30).pack(side="left", padx=6)
        ttk.Label(controls, textvariable=self.area_var, wraplength=1100).pack(anchor="w", pady=(8, 0))
        slider = ttk.LabelFrame(controls, text="Автоматическая установка кисти", padding=6)
        slider.pack(fill="x", pady=(8, 0))
        ttk.Label(slider, text="Левый край 30 (X,Y)").pack(side="left")
        ttk.Entry(slider, textvariable=self.slider_start_var, width=12).pack(side="left", padx=4)
        ttk.Label(slider, text="Правый край 1 (X,Y)").pack(side="left", padx=(8, 0))
        ttk.Entry(slider, textvariable=self.slider_end_var, width=12).pack(side="left", padx=4)
        ttk.Button(slider, text="Установить кисть", command=self.set_brush_size).pack(side="left", padx=6)
        ttk.Label(slider, text="Координаты расширенного ползунка: слева радиус 30, справа радиус 1. После перетаскивания проверь значение в игре.", wraplength=350).pack(side="left", padx=6)
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Создать и передать тест в исполнитель →", command=self.create_and_transfer_plan).pack(side="left")
        ttk.Button(actions, text="Снять скриншот сейчас", command=self.capture_screenshot).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Привязать отчёт исполнения…", command=self.load_execution_report).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Эксперимент: снимок ДО", command=lambda: self.capture_experiment_phase("before_draw")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Эксперимент: ПОСЛЕ рисования", command=lambda: self.capture_experiment_phase("after_draw")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Очистить и снять ПОСЛЕ", command=lambda: self.capture_experiment_phase("after_clear")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Сохранить запись теста…", command=self.save_record_dialog).pack(side="left", padx=(6, 0))

        details = ttk.LabelFrame(outer, text="Шаблон и фиксация результата", padding=8)
        details.pack(fill="both", expand=True)
        self.template_text = tk.Text(details, height=13, wrap="word")
        self.template_text.pack(fill="both", expand=True)
        self.template_text.configure(state="disabled")
        self.case_var.trace_add("write", lambda *_: self._refresh_template())
        self._refresh_template()
        result = ttk.Frame(details)
        result.pack(fill="x", pady=(8, 0))
        ttk.Label(result, text="Наблюдение").pack(side="left")
        ttk.Combobox(
            result, textvariable=self.outcome_var, state="readonly", width=22,
            values=("not_reviewed", "all_visible", "partial", "none_visible", "distorted"),
        ).pack(side="left", padx=(6, 14))
        ttk.Label(result, text="Заметки").pack(side="left")
        ttk.Entry(result, textvariable=self.notes_var).pack(side="left", fill="x", expand=True, padx=6)
        measurements = ttk.LabelFrame(details, text="Измерения для будущей модели", padding=6)
        measurements.pack(fill="x", pady=(8, 0))
        measure_row1 = ttk.Frame(measurements)
        measure_row1.pack(fill="x")
        for label, variable, width in (
            ("Видимые штрихи", self.visible_strokes_var, 24),
            ("Пропущенные", self.missing_strokes_var, 20),
            ("Ширина следа, px", self.footprint_width_var, 7),
            ("Высота, px", self.footprint_height_var, 7),
        ):
            ttk.Label(measure_row1, text=label).pack(side="left", padx=(0, 3))
            ttk.Entry(measure_row1, textvariable=variable, width=width).pack(side="left", padx=(0, 10))
        measure_row2 = ttk.Frame(measurements)
        measure_row2.pack(fill="x", pady=(6, 0))
        for label, variable in (
            ("Краска до", self.paint_before_var),
            ("Краска после", self.paint_after_var),
            ("Масштаб браузера, %", self.zoom_var),
        ):
            ttk.Label(measure_row2, text=label).pack(side="left", padx=(0, 3))
            ttk.Entry(measure_row2, textvariable=variable, width=9).pack(side="left", padx=(0, 12))
        ttk.Label(
            measurements,
            text="Видимые/пропущенные штрихи указывай через запятую по именам из шаблона. Числовые поля можно оставить пустыми.",
            wraplength=1100,
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1150).pack(anchor="w", pady=(8, 0))

    def _refresh_template(self) -> None:
        scenario = TEST_CASES.get(self.case_var.get())
        if not scenario:
            return
        lines = [scenario["description"], "", "Координаты тестового шаблона (локальные координаты выбранной тестовой области):"]
        for stroke in scenario["strokes"]:
            points = stroke["points"]
            lines.append(f"• {stroke['name']}: ({points[0][0]}, {points[0][1]}) → ({points[1][0]}, {points[1][1]})")
        lines.extend(["", "Рекомендации:", "1. Выполняй каждый штрих отдельно и не соединяй соседние линии.",
                      "2. Не меняй масштаб браузера и размер кисти в середине серии.",
                      "3. Запиши размер кисти, видимые/пропущенные штрихи и остаток краски в заметках или заполни measurement_fields в JSON.",
                      "4. Снимок должен включать всю тестовую область и не закрывать её окнами приложения."])
        self.template_text.configure(state="normal")
        self.template_text.delete("1.0", "end")
        self.template_text.insert("1.0", "\n".join(lines))
        self.template_text.configure(state="disabled")

    def create_and_transfer_plan(self) -> None:
        canvas_size = self.get_canvas_size()
        if not canvas_size:
            messagebox.showwarning(
                "Не выбрана область холста",
                "Сначала выбери реальную область рисования на вкладке исполнения. "
                "Тестовый план должен совпадать с её размером.",
                parent=self.root,
            )
            return
        try:
            plan = build_brush_test_drawing_plan(self.case_var.get(), canvas_size)
            area = self.get_canvas_area()
            self.canvas_area = dict(area) if area else None
            brush = int(self.brush_var.get().strip())
            if not 1 <= brush <= 30:
                raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / (
                f"brush-plan-{plan['generation']['test_case']}-b{brush}-"
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            )
            plan["generation"]["requested_brush_value"] = brush
            save_plan(path, plan)
            self.current_plan = plan
            self.current_plan_path = path
            if not self.on_transfer_plan(plan, path):
                return
            self._reset_observation_fields()
            if self.set_brush_size():
                self.status_var.set(
                    f"План передан: {path.name}. Переключись в браузер за 3 секунды; затем проверь кисть {brush}."
                )
            else:
                self.status_var.set(
                    f"План передан: {path.name}, но кисть не установлена автоматически. Проверь режим управления кистью и задай нужные координаты на вкладке 8."
                )
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось создать тестовый план", str(exc), parent=self.root)

    def _reset_observation_fields(self) -> None:
        """Prevent evidence from a previous run being attached to a new test plan."""
        self.screenshot_path = None
        self.experiment_dir = None
        self.experiment_phases = {}
        self.execution_report_path = None
        self.execution_report = None
        self.brush_slider_start = None
        self.brush_slider_end = None
        self.outcome_var.set("not_reviewed")
        self.notes_var.set("")
        self.visible_strokes_var.set("")
        self.missing_strokes_var.set("")
        self.footprint_width_var.set("")
        self.footprint_height_var.set("")
        self.paint_before_var.set("")
        self.paint_after_var.set("")
        self.zoom_var.set("100")

    def select_screenshot_area(self) -> None:
        def selected(area) -> None:
            if area is None:
                self.status_var.set("Выбор области снимка отменён.")
                return
            self.screen_area = {"x": int(area.x), "y": int(area.y), "width": int(area.width), "height": int(area.height)}
            self.area_var.set(f"Область снимка: X={area.x}, Y={area.y}, {area.width} × {area.height} px.")
            self.status_var.set("Область сохранена. После завершения теста нажми «Снять скриншот сейчас».")
        self.area_selector_cls(self.root, selected, instruction="Выдели область завершённого теста кисти. Esc — отмена.")

    @staticmethod
    def _parse_point(raw: str, field: str) -> tuple[int, int]:
        parts = [part.strip() for part in raw.replace(";", ",").split(",")]
        if len(parts) != 2:
            raise ValueError(f"{field}: введи координаты X,Y.")
        try:
            return int(parts[0]), int(parts[1])
        except ValueError as exc:
            raise ValueError(f"{field}: X и Y должны быть целыми числами.") from exc

    def set_brush_size(self) -> bool:
        """Use a calibrated preset click or drag the extended-mode slider."""
        try:
            brush = int(self.brush_var.get().strip())
            if not 1 <= brush <= 30:
                raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
            if platform.system() != "Windows":
                raise RuntimeError("Автоматическая установка кисти доступна только в Windows.")
            calibrated = self.get_brush_control() if callable(self.get_brush_control) else None
            if calibrated:
                mode = calibrated.get("mode")
                if mode == "unsaved":
                    raise ValueError("Сначала сохрани профиль калибровки на вкладке 8.")
                if mode == "presets":
                    preset = calibrated.get("presets", {}).get(str(brush))
                    if brush not in (7, 14, 20):
                        raise ValueError("В режиме обычных пресетов доступны только кисти 7, 14 и 20. Выбери расширенный ползунок для других значений.")
                    if preset is None:
                        raise ValueError(f"Не заданы координаты пресета кисти {brush}. Настрой его на вкладке 8.")
                    x, y = int(preset[0]), int(preset[1])
                    self.status_var.set(
                        f"Через 3 секунды будет выбран пресет кисти {brush} в ({x}, {y}). "
                        "Переключись в браузер и не трогай мышь."
                    )
                    self.root.after(3000, lambda: self._apply_brush_preset_click(x, y, brush))
                    return True
                if mode == "slider":
                    if not calibrated.get("start") or not calibrated.get("end"):
                        raise ValueError("Для режима ползунка задай и сохрани положения кисти 1 и 30 на вкладке 8.")
                    # The engine slider runs from brush 30 at the left endpoint to brush 1 at the right.
                    start = self._parse_point(
                        f"{calibrated['start'][0]},{calibrated['start'][1]}", "Край 30 из профиля"
                    )
                    end = self._parse_point(
                        f"{calibrated['end'][0]},{calibrated['end'][1]}", "Край 1 из профиля"
                    )
                    self.slider_start_var.set(f"{start[0]}, {start[1]}")
                    self.slider_end_var.set(f"{end[0]}, {end[1]}")
                else:
                    raise ValueError("Выбери режим управления кистью на вкладке 8 и сохрани профиль.")
            else:
                start = self._parse_point(self.slider_start_var.get(), "Край 30")
                end = self._parse_point(self.slider_end_var.get(), "Край 1")
            ratio = (30 - brush) / 29
            x = round(start[0] + (end[0] - start[0]) * ratio)
            y = round(start[1] + (end[1] - start[1]) * ratio)
            self.brush_slider_start, self.brush_slider_end = start, end
            self.status_var.set(
                f"Через 3 секунды ползунок будет перетащен к радиусу кисти {brush}. "
                "Переключись в браузер и не трогай мышь."
            )
            self.root.after(3000, lambda: self._apply_brush_drag(start, x, y, brush))
            return True
        except (ValueError, RuntimeError, AttributeError) as exc:
            messagebox.showwarning("Не настроен ползунок кисти", str(exc), parent=self.root)
            return False

    def _apply_brush_preset_click(self, x: int, y: int, brush: int) -> None:
        """Select one of the ordinary game brush presets at its calibrated screen point."""
        try:
            pyautogui.click(x, y)
        except Exception as exc:
            self.status_var.set(f"Не удалось выбрать пресет кисти {brush}: {exc}")
            return
        self.status_var.set(
            f"Выполнен клик по пресету кисти {brush} ({x}, {y}). Проверь, что игра выбрала нужный размер."
        )

    def _apply_brush_drag(
        self, start: tuple[int, int], target_x: int, target_y: int, brush: int
    ) -> None:
        """Drag from the calibrated minimum to the requested slider position."""
        user32 = ctypes.windll.user32
        start_x, start_y = start
        distance = max(abs(target_x - start_x), abs(target_y - start_y))
        steps = max(10, min(100, distance))
        user32.SetCursorPos(start_x, start_y)
        time.sleep(0.15)
        user32.mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
        try:
            for step in range(1, steps + 1):
                ratio = step / steps
                current_x = round(start_x + (target_x - start_x) * ratio)
                current_y = round(start_y + (target_y - start_y) * ratio)
                user32.SetCursorPos(current_x, current_y)
                time.sleep(0.01)
        finally:
            user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
        self.status_var.set(
            f"Выполнено перетаскивание ползунка к радиусу кисти {brush} "
            f"({target_x}, {target_y}). Проверь значение, показанное игрой."
        )

    def capture_screenshot(self) -> None:
        self.status_var.set("Через 3 секунды будет сохранён полный скриншот экрана. Переключись в браузер.")
        self.root.after(3000, self._capture_screenshot_now)

    def _capture_screenshot_now(self) -> None:
        try:
            image = ImageGrab.grab()
            if image.width < 1 or image.height < 1:
                raise ValueError("Получился пустой снимок.")
            self.screen_resolution = {"width": int(image.width), "height": int(image.height)}
            area = self.get_canvas_area()
            self.canvas_area = ({key: int(area[key]) for key in ("x", "y", "width", "height")} if area else None)
            self.screen_area = {"x": 0, "y": 0, "width": image.width, "height": image.height}
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"brush-screenshot-full-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            image.save(path)
            self.screenshot_path = path
            self.area_var.set(f"Экран: {image.width} × {image.height}; доска: {self.canvas_area or 'не найдена в профиле'}")
            self.status_var.set(f"Полный скриншот сохранён: {path}")
        except Exception as exc:
            messagebox.showerror("Не удалось снять скриншот", str(exc), parent=self.root)

    def capture_experiment_phase(self, phase: str) -> None:
        """Capture calibrated board/meter evidence for before, after-draw and after-clear phases."""
        labels = {
            "before_draw": "до рисования",
            "after_draw": "после рисования",
            "after_clear": "после очистки",
        }
        if phase not in labels:
            messagebox.showerror("Неизвестный этап", phase, parent=self.root)
            return
        if self.current_plan is None:
            messagebox.showwarning(
                "Нет тестового плана",
                "Сначала создай и передай тестовый план в исполнитель.",
                parent=self.root,
            )
            return
        if phase == "before_draw":
            self.experiment_dir = None
            self.experiment_phases = {}
        elif phase == "after_draw" and "before_draw" not in self.experiment_phases:
            messagebox.showwarning(
                "Нет исходного снимка",
                "Сначала сделай снимок ДО рисования, затем выполни тест и сними результат.",
                parent=self.root,
            )
            return
        elif phase == "after_clear" and "after_draw" not in self.experiment_phases:
            messagebox.showwarning(
                "Нет снимка после рисования",
                "Сначала сохрани снимок ПОСЛЕ рисования. Очистка доски необратима для текущего рисунка.",
                parent=self.root,
            )
            return

        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        if not isinstance(config, dict):
            messagebox.showwarning(
                "Профиль калибровки недоступен",
                "Сохрани профиль на вкладке 8 и проверь области доски, полоски краски и координату Clear.",
                parent=self.root,
            )
            return
        regions = config.get("regions", {})
        points = config.get("points", {})
        statuses = config.get("status", {})
        region_status = statuses.get("regions", {}) if isinstance(statuses, dict) else {}
        point_status = statuses.get("points", {}) if isinstance(statuses, dict) else {}
        for key in ("board_area", "paint_meter_area"):
            if not isinstance(regions.get(key), dict) or region_status.get(key) == "needs_review":
                messagebox.showwarning(
                    "Область требует калибровки",
                    f"Область {key} отсутствует или требует повторной проверки на вкладке 8.",
                    parent=self.root,
                )
                return
        clear_point = points.get("clear_board")
        if phase == "after_clear":
            if not isinstance(clear_point, dict) or point_status.get("clear_board") == "needs_review":
                messagebox.showwarning(
                    "Координата Clear недоступна",
                    "Проверь координату кнопки очистки на вкладке 8.",
                    parent=self.root,
                )
                return
            confirmed = messagebox.askyesno(
                "Очистить игровую доску?",
                "Сейчас AutoDraw нажмёт откалиброванную кнопку Clear и уничтожит текущий рисунок. "
                "Продолжать только если тестовый рисунок можно удалить.",
                icon="warning",
                parent=self.root,
            )
            if not confirmed:
                return

        if phase == "before_draw":
            brush = self.brush_var.get().strip() or "unknown"
            case = TEST_CASES.get(self.case_var.get(), {}).get("id", "unknown")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.experiment_dir = self.output_dir / f"experiment-{stamp}-b{brush}-{case}"
            self.experiment_dir.mkdir(parents=True, exist_ok=False)
            self.experiment_phases = {}

        if self.experiment_dir is None:
            messagebox.showwarning(
                "Нет папки эксперимента",
                "Начни серию со снимка ДО рисования.",
                parent=self.root,
            )
            return
        self.status_var.set(
            f"Через 3 секунды будет сохранён снимок {labels[phase]}. Переключись в браузер."
        )
        self.root.withdraw()
        self.root.after(3000, lambda: self._capture_experiment_phase_now(phase, config, clear_point if phase == "after_clear" else None))

    def _capture_experiment_phase_now(
        self, phase: str, config: dict[str, Any], clear_point: dict[str, int] | None,
    ) -> None:
        try:
            if clear_point is not None:
                pyautogui.click(int(clear_point["x"]), int(clear_point["y"]))
                time.sleep(1.5)
            screen = ImageGrab.grab()
            expected_size = config.get("screen_size", {})
            expected_width = expected_size.get("width") if isinstance(expected_size, dict) else None
            expected_height = expected_size.get("height") if isinstance(expected_size, dict) else None
            if (
                expected_width is not None and expected_height is not None
                and (int(expected_width), int(expected_height)) != (screen.width, screen.height)
            ):
                raise ValueError(
                    "Размер снимка экрана не совпадает с сохранённым профилем калибровки: "
                    f"профиль {expected_width} × {expected_height}, снимок "
                    f"{screen.width} × {screen.height}. Проверь DPI/масштаб и откалибруй заново."
                )
            crops = crop_calibrated_regions(screen, config.get("regions", {}))
            if self.experiment_dir is None:
                raise ValueError("Папка эксперимента не создана.")
            screen_path = self.experiment_dir / f"{phase}-screen.png"
            board_path = self.experiment_dir / f"{phase}-board.png"
            meter_path = self.experiment_dir / f"{phase}-paint-meter.png"
            screen.save(screen_path)
            crops["board_area"].save(board_path)
            crops["paint_meter_area"].save(meter_path)
            self.screen_resolution = {"width": int(screen.width), "height": int(screen.height)}

            phase_record: dict[str, Any] = {
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": int(screen.width), "height": int(screen.height)},
                "clear_click_sent": clear_point is not None,
                "files": {
                    "full_screen": screen_path.name,
                    "board_roi": board_path.name,
                    "paint_meter_roi": meter_path.name,
                },
            }
            before = self.experiment_phases.get("before_draw")
            after = self.experiment_phases.get("after_draw")
            if before is not None:
                baseline_meter_path = self.experiment_dir / before["files"]["paint_meter_roi"]
                with Image.open(baseline_meter_path) as baseline_meter, Image.open(meter_path) as current_meter:
                    phase_record["paint_meter_measurement"] = measure_meter_fill_against_baseline(baseline_meter, current_meter)
                    if phase == "after_clear":
                        phase_record["paint_meter_restoration"] = evaluate_meter_restoration(baseline_meter, current_meter)
            for baseline_name, baseline in (("before_draw", before), ("after_draw", after)):
                if baseline is None or baseline_name == phase:
                    continue
                for roi_key, file_key in (("board_area", "board_roi"), ("paint_meter_area", "paint_meter_roi")):
                    baseline_path = self.experiment_dir / baseline["files"][file_key]
                    current_path = board_path if roi_key == "board_area" else meter_path
                    with Image.open(baseline_path) as first, Image.open(current_path) as second:
                        phase_record.setdefault("visual_comparisons", {})[f"{roi_key}_vs_{baseline_name}"] = compare_images(first, second)

            self.experiment_phases[phase] = phase_record
            manifest = {
                "schema_version": 1,
                "record_type": "autodraw_brush_paint_experiment",
                "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "test_case": TEST_CASES.get(self.case_var.get(), {}).get("id"),
                "brush_value_requested": int(self.brush_var.get().strip()),
                "drawing_plan_path": str(self.current_plan_path) if self.current_plan_path else None,
                "execution_report_path": str(self.execution_report_path) if self.execution_report_path else None,
                "calibration_profile_path": str(config.get("profile_path", "")) or None,
                "phases": self.experiment_phases,
                "interpretation_limits": [
                    "Screenshots are captured from the configured screen-coordinate system.",
                    "Meter fill is a provisional estimate against the before-draw baseline, not OCR or a direct reading of the game's resource counter.",
                    "Ambiguous or non-contiguous changes are marked inconclusive and require manual review.",
                    "A successful executor report does not prove that every stroke was registered by the game.",
                    "The after-clear phase clicks Clear only after explicit confirmation.",
                ],
            }
            manifest_path = self.experiment_dir / "experiment.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.screenshot_path = screen_path
            self.area_var.set(
                f"Эксперимент: {self.experiment_dir.name}; снимок {phase}: "
                f"доска {crops['board_area'].width} × {crops['board_area'].height}, "
                f"полоска краски {crops['paint_meter_area'].width} × {crops['paint_meter_area'].height}."
            )
            self.status_var.set(
                f"Сохранён этап {phase}. ROI и experiment.json записаны в {self.experiment_dir}. "
                "Оценка заполнения полоски предварительная; это не OCR и не чтение внутреннего счётчика."
            )
        except Exception as exc:
            messagebox.showerror("Не удалось сохранить этап эксперимента", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка снимка эксперимента: {exc}")
        finally:
            self.root.deiconify()
            self.root.lift()

    def load_execution_report(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выбери JSON-отчёт последнего исполнения AutoDraw",
            initialdir=str(self.output_dir.parent),
            filetypes=(("JSON", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Отчёт должен содержать JSON-объект.")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Не удалось прочитать отчёт", str(exc), parent=self.root)
            return
        self.execution_report_path = Path(path).resolve()
        self.execution_report = document
        self.status_var.set(f"Отчёт исполнения привязан к тесту: {self.execution_report_path}")

    def _measurement_values(self) -> dict[str, Any]:
        def optional_number(raw: str, field: str):
            value = raw.strip()
            if not value:
                return None
            try:
                number = float(value.replace(",", "."))
            except ValueError as exc:
                raise ValueError(f"Поле «{field}» должно быть числом.") from exc
            if number < 0:
                raise ValueError(f"Поле «{field}» не может быть отрицательным.")
            return int(number) if number.is_integer() else number

        visible = [item.strip() for item in self.visible_strokes_var.get().split(",") if item.strip()]
        missing = [item.strip() for item in self.missing_strokes_var.get().split(",") if item.strip()]
        return {
            "observed_stroke_count": len(visible) if visible or missing else None,
            "visible_stroke_names": visible,
            "missing_stroke_names": missing,
            "measured_footprint_width_px": optional_number(self.footprint_width_var.get(), "ширина следа"),
            "measured_footprint_height_px": optional_number(self.footprint_height_var.get(), "высота следа"),
            "paint_points_before": optional_number(self.paint_before_var.get(), "краска до"),
            "paint_points_after": optional_number(self.paint_after_var.get(), "краска после"),
            "browser_zoom_percent": optional_number(self.zoom_var.get(), "масштаб браузера"),
        }

    def _build_record(self) -> dict[str, Any]:
        try:
            brush = int(self.brush_var.get().strip())
        except ValueError as exc:
            raise ValueError("Размер кисти должен быть целым числом от 1 до 30.") from exc
        calibrated = self.get_brush_control() if callable(self.get_brush_control) else None
        if calibrated and calibrated.get("mode") == "presets":
            brush_control = {
                "type": "preset_click",
                "mode": "presets",
                "selected_brush_point": calibrated.get("presets", {}).get(str(brush)),
                "presets": calibrated.get("presets", {}),
            }
        elif calibrated and calibrated.get("mode") == "slider":
            brush_control = {
                "type": "linear_drag_slider_inverse_radius_1_to_30",
                "mode": "slider",
                "min_value": 1,
                "max_value": 30,
                "start": calibrated.get("start"),
                "end": calibrated.get("end"),
            }
        else:
            brush_control = {
                "type": "manual_or_unconfigured",
                "mode": calibrated.get("mode") if calibrated else None,
                "start": list(self.brush_slider_start) if self.brush_slider_start else None,
                "end": list(self.brush_slider_end) if self.brush_slider_end else None,
            }
        return build_brush_test_record(
            brush_value=brush,
            test_case=self.case_var.get(),
            canvas_area=self.canvas_area,
            screen_area=self.screen_area,
            screenshot_path=str(self.screenshot_path) if self.screenshot_path else None,
            drawing_plan_path=str(self.current_plan_path) if self.current_plan_path else None,
            drawing_plan=self.current_plan,
            execution_report_path=str(self.execution_report_path) if self.execution_report_path else None,
            execution_report=self.execution_report,
            measurements=self._measurement_values(),
            notes=self.notes_var.get(),
            outcome=self.outcome_var.get(),
            screen_resolution=self.screen_resolution,
            brush_control=brush_control,
        )

    def save_record_dialog(self) -> None:
        try:
            record = self._build_record()
        except ValueError as exc:
            messagebox.showerror("Параметры теста", str(exc), parent=self.root)
            return
        suggested = f"brush-test-{record['test_case']['id']}-b{record['brush_value']}-{record['record_id'][:8]}.json"
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить данные теста кисти",
            initialdir=str(self.output_dir), initialfile=suggested,
            defaultextension=".json", filetypes=(("JSON", "*.json"),),
        )
        if not path:
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.last_record_path = target
        self.status_var.set(f"Данные теста сохранены: {target}")
