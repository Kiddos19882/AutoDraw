from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import ImageGrab

from stage8_optimizer import save_plan


TEST_CASES: dict[str, dict[str, Any]] = {
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
    execution_report_path: str | None = None, execution_report: dict[str, Any] | None = None,
    notes: str = "", outcome: str = "not_reviewed",
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
        "screen_area": screen_area,
        "screenshot_path": screenshot_path,
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
        area_selector_cls, *, get_canvas_size, get_canvas_area, on_transfer_plan,
    ):
        self.root = root
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.area_selector_cls = area_selector_cls
        self.get_canvas_size = get_canvas_size
        self.get_canvas_area = get_canvas_area
        self.on_transfer_plan = on_transfer_plan
        self.current_plan: dict[str, Any] | None = None
        self.current_plan_path: Path | None = None
        self.canvas_area: dict[str, int] | None = None
        self.screen_area: dict[str, int] | None = None
        self.canvas_area: dict[str, int] | None = None
        self.screenshot_path: Path | None = None
        self.execution_report_path: Path | None = None
        self.execution_report: dict[str, Any] | None = None
        self.last_record_path: Path | None = None
        self.brush_var = tk.StringVar(value="7")
        self.case_var = tk.StringVar(value=next(iter(TEST_CASES)))
        self.outcome_var = tk.StringVar(value="not_reviewed")
        self.notes_var = tk.StringVar()
        self.area_var = tk.StringVar(value="Область снимка не выбрана.")
        self.status_var = tk.StringVar(value="Выбери кисть и тест. В игре вручную установи указанную кисть и выполни тестовый шаблон.")
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
                  "Программа не запускает рисование автоматически из этой вкладки."),
            wraplength=1150, justify="left",
        ).pack(anchor="w", pady=(4, 10))

        controls = ttk.LabelFrame(outer, text="Настройки серии", padding=8)
        controls.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(controls)
        row.pack(fill="x")
        ttk.Label(row, text="Размер кисти (1–30)").pack(side="left")
        ttk.Entry(row, textvariable=self.brush_var, width=6).pack(side="left", padx=(6, 16))
        ttk.Label(row, text="Тест").pack(side="left")
        ttk.Combobox(row, textvariable=self.case_var, values=tuple(TEST_CASES), state="readonly", width=30).pack(side="left", padx=6)
        ttk.Label(controls, textvariable=self.area_var, wraplength=1100).pack(anchor="w", pady=(8, 0))
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Создать и передать тест в исполнитель →", command=self.create_and_transfer_plan).pack(side="left")
        ttk.Button(actions, text="Выбрать область снимка…", command=self.select_screenshot_area).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Снять скриншот сейчас", command=self.capture_screenshot).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Привязать отчёт исполнения…", command=self.load_execution_report).pack(side="left", padx=(6, 0))
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
            self.status_var.set(
                f"План передан исполнителю: {path.name}. Установи в браузере кисть {brush} перед запуском."
            )
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось создать тестовый план", str(exc), parent=self.root)

    def select_screenshot_area(self) -> None:
        def selected(area) -> None:
            if area is None:
                self.status_var.set("Выбор области снимка отменён.")
                return
            self.screen_area = {"x": int(area.x), "y": int(area.y), "width": int(area.width), "height": int(area.height)}
            self.area_var.set(f"Область снимка: X={area.x}, Y={area.y}, {area.width} × {area.height} px.")
            self.status_var.set("Область сохранена. После завершения теста нажми «Снять скриншот сейчас».")
        self.area_selector_cls(self.root, selected, instruction="Выдели область завершённого теста кисти. Esc — отмена.")

    def capture_screenshot(self) -> None:
        if not self.screen_area:
            messagebox.showwarning("Не выбрана область", "Сначала выбери область снимка.", parent=self.root)
            return
        self.status_var.set("Через 3 секунды будет снята выбранная область. Переключись в браузер и не двигай окно игры.")
        self.root.after(3000, self._capture_screenshot_now)

    def _capture_screenshot_now(self) -> None:
        if not self.screen_area:
            return
        area = self.screen_area
        try:
            image = ImageGrab.grab(bbox=(area["x"], area["y"], area["x"] + area["width"], area["y"] + area["height"]))
            if image.width < 1 or image.height < 1:
                raise ValueError("Получился пустой снимок.")
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"brush-screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            image.save(path)
            self.screenshot_path = path
            self.status_var.set(f"Снимок сохранён: {path}")
        except Exception as exc:
            messagebox.showerror("Не удалось снять скриншот", str(exc), parent=self.root)

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

    def _build_record(self) -> dict[str, Any]:
        try:
            brush = int(self.brush_var.get().strip())
        except ValueError as exc:
            raise ValueError("Размер кисти должен быть целым числом от 1 до 30.") from exc
        return build_brush_test_record(
            brush_value=brush,
            test_case=self.case_var.get(),
            canvas_area=self.canvas_area,
            screen_area=self.screen_area,
            screenshot_path=str(self.screenshot_path) if self.screenshot_path else None,
            execution_report_path=str(self.execution_report_path) if self.execution_report_path else None,
            execution_report=self.execution_report,
            notes=self.notes_var.get(),
            outcome=self.outcome_var.get(),
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
