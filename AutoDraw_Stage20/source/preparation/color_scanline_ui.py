from __future__ import annotations

import copy
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Any

from PIL import Image, ImageTk, ImageDraw

from paint_cost_model import (
    DEFAULT_PAINT_BUDGET_PX_EQUIVALENT, DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    estimate_color_plan_paint_cost,
)
from brush_planner import (
    BrushPlannerError, build_adaptive_brush_plan, save_adaptive_brush_plan,
)
from board_resource_model import GAME_BOARD_LOGICAL_HEIGHT, GAME_BOARD_LOGICAL_WIDTH
from paint_budget_optimizer import PaintBudgetOptimizationError, fit_result_to_paint_budget

from color_scanline import (
    ColorScanlinePlanError,
    build_color_scanline_plan,
    load_color_scanline_plan,
    render_color_scanline_preview,
    save_color_scanline_plan,
    validate_color_scanline_plan,
)

from geometry_color_plan import (
    GeometryColorPlanError,
    _estimate_geometry_paint_cost,
    build_geometry_color_plan,
    load_geometry_color_plan,
    optimize_geometry_plan_across_modes,
    optimize_geometry_plan_to_budget,
    render_geometry_color_preview,
    save_geometry_color_plan,
    save_multi_board_manifest,
    split_geometry_plan_to_boards,
    validate_geometry_color_plan,
)


class _PlanPreview(ttk.LabelFrame):
    def __init__(self, parent: tk.Widget, title: str):
        super().__init__(parent, text=title, padding=5)
        self.canvas = tk.Canvas(self, background="#242424", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.canvas.bind("<Configure>", lambda _event: self.render())

    def set_image(self, image: Image.Image | None) -> None:
        self.image = image.copy() if image is not None else None
        self.render()

    def render(self) -> None:
        self.canvas.delete("all")
        self.photo = None
        width = max(2, self.canvas.winfo_width())
        height = max(2, self.canvas.winfo_height())
        if self.image is None:
            self.canvas.create_text(width / 2, height / 2, text="Цветной план ещё не построен", fill="#dddddd")
            return
        source = self.image.convert("RGBA")
        scale = min((width - 12) / max(1, source.width), (height - 12) / max(1, source.height))
        scaled_size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
        if scaled_size != source.size:
            source = source.resize(scaled_size, Image.Resampling.NEAREST)
        # Checkerboard is only preview decoration; it is not written into the plan.
        checker = Image.new("RGB", source.size, "#eeeeee")
        draw = ImageDraw.Draw(checker)
        tile = max(4, min(12, min(source.size) // 12 if min(source.size) >= 12 else 4))
        for y in range(0, source.height, tile):
            for x in range(0, source.width, tile):
                if ((x // tile) + (y // tile)) % 2:
                    draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill="#bdbdbd")
        checker.paste(source.convert("RGB"), mask=source.getchannel("A"))
        self.photo = ImageTk.PhotoImage(checker)
        self.canvas.create_image(width / 2, height / 2, image=self.photo, anchor="center")


class ColorScanlineTab:
    """Stage 19: build and inspect a colored scanline plan from stage 18 quantization."""

    def __init__(
        self,
        root: tk.Misc,
        parent: tk.Widget,
        output_dir: str | Path,
        get_quantized_data: Callable[[], dict[str, Any] | None],
    ):
        self.root = root
        self.parent = parent
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.get_quantized_data = get_quantized_data
        self.quantization_result = None
        self.palette_profile: dict[str, Any] | None = None
        self.quantization_report: dict[str, Any] | None = None
        self.source_name: str | None = None
        self.plan: dict[str, Any] | None = None
        self.plan_path: Path | None = None
        self.plan_index_map = None
        self.brush_plan: dict[str, Any] | None = None
        self.row_step_var = tk.StringVar(value="1")
        self.paint_target_usage_var = tk.StringVar(value="75")
        self._auto_fit_row_step: int | None = None
        self._auto_fit_row_offset = 0
        self.brush_min_var = tk.StringVar(value="1")
        self.brush_max_var = tk.StringVar(value="20")
        self.brush_scale_x_var = tk.StringVar(value="авто")
        self.brush_scale_y_var = tk.StringVar(value="авто")
        self.brush_scale_calibrated_var = tk.BooleanVar(value=False)
        self.paint_overhead_var = tk.StringVar(value=f"{DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT:.2f}")
        self.paint_budget_var = tk.StringVar(value=f"{DEFAULT_PAINT_BUDGET_PX_EQUIVALENT:.0f}")
        self.geometry_mode_var = tk.StringVar(value="automatic")
        self.geometry_tolerance_var = tk.StringVar(value="0.8")
        self.geometry_min_component_var = tk.StringVar(value="2")

        outer = ttk.Frame(parent, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Этап 19 — цветной scanline-план", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Scanline сохраняет растровые строки; геометрический режим строит траектории по цветовым слоям. "
                  "Геометрический план поддерживает скелетонизацию, контуры, RDP-упрощение и маршрутизацию штрихов. "
                  "Старый scanline-путь остаётся доступен отдельно."),
            wraplength=1120,
        ).pack(anchor="w", pady=(3, 9))

        toolbar = ttk.LabelFrame(outer, text="Источник и scanline-план", padding=7)
        toolbar.pack(fill="x", pady=(0, 7))
        ttk.Button(toolbar, text="Взять результат из этапа 18", command=self.use_latest_quantization).pack(side="left")
        ttk.Label(toolbar, text="Шаг строк (px)").pack(side="left", padx=(12, 4))
        self.row_step_combo = ttk.Combobox(
            toolbar, textvariable=self.row_step_var, values=("1", "2", "3", "4", "5", "8", "10"),
            state="readonly", width=5,
        )
        self.row_step_combo.pack(side="left")
        ttk.Button(toolbar, text="Построить цветной план", command=self.build_plan).pack(side="left", padx=(6, 0))
        ttk.Button(
            toolbar, text="Уложить в краску автоматически…", command=self.fit_to_paint_budget,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Открыть цветной план…", command=self.open_plan_dialog).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Сохранить план JSON…", command=self.save_plan_dialog).pack(side="left", padx=(6, 0))

        geometry_frame = ttk.LabelFrame(outer, text="Геометрический план (новый формат)", padding=7)
        geometry_frame.pack(fill="x", pady=(0, 7))
        ttk.Label(geometry_frame, text="Алгоритм").pack(side="left")
        ttk.Combobox(
            geometry_frame, textvariable=self.geometry_mode_var,
            values=("automatic", "scanline", "contour", "skeleton"), state="readonly", width=10,
        ).pack(side="left", padx=(4, 10))
        ttk.Label(geometry_frame, text="RDP, px").pack(side="left")
        ttk.Entry(geometry_frame, textvariable=self.geometry_tolerance_var, width=6).pack(side="left", padx=(4, 10))
        ttk.Label(geometry_frame, text="Мин. компонент, px").pack(side="left")
        ttk.Entry(geometry_frame, textvariable=self.geometry_min_component_var, width=5).pack(side="left", padx=(4, 10))
        ttk.Button(
            geometry_frame, text="Построить геометрический план",
            command=self.build_geometry_plan,
        ).pack(side="left")
        ttk.Button(
            geometry_frame, text="Оптимизировать под бюджет",
            command=self.fit_geometry_to_paint_budget,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            geometry_frame, text="Разбить на доски…",
            command=self.split_geometry_to_boards_dialog,
        ).pack(side="left", padx=(6, 0))

        model_frame = ttk.LabelFrame(outer, text="Модель расхода краски — экспериментальная оценка", padding=(7, 5))
        model_frame.pack(fill="x", pady=(0, 7))
        self.paint_model_frame = model_frame
        model_controls = ttk.Frame(model_frame)
        model_controls.pack(side="top", anchor="w", fill="x")
        self.paint_model_controls = model_controls
        ttk.Label(model_controls, text="Доп. расход на штрих (px-экв.)").pack(side="left")
        ttk.Entry(model_controls, textvariable=self.paint_overhead_var, width=7).pack(side="left", padx=(5, 12))
        ttk.Label(model_controls, text="Оценочный запас (px-экв.)").pack(side="left")
        ttk.Entry(model_controls, textvariable=self.paint_budget_var, width=9).pack(side="left", padx=(5, 12))
        ttk.Button(model_controls, text="Вернуть значения эксперимента", command=self.reset_paint_model).pack(side="left")
        ttk.Button(model_controls, text="Пересчитать для текущего плана", command=self.recalculate_paint_estimate).pack(side="left", padx=(6, 0))
        ttk.Label(model_controls, text="Цель расхода (%)").pack(side="left", padx=(12, 4))
        ttk.Spinbox(
            model_controls, from_=50, to=90, increment=5, width=4,
            textvariable=self.paint_target_usage_var,
        ).pack(side="left")
        self.paint_model_explanation = ttk.Label(
            model_frame,
            text=("По 4 экспериментальным замерам: ≈6,67 px-эквивалента на штрих; "
                  "оценочный запас ≈25 650 (наблюдавшийся диапазон 25 610–25 730). "
                  "Автоматический режим укрупняет блоки, объединяет соседние цвета и пропускает строки, "
                  "пока расчёт не достигнет целевого процента. Это предварительная модель, а не счётчик игры."),
            wraplength=1120,
            justify="left",
        )
        self.paint_model_explanation.pack(side="top", anchor="w", fill="x", pady=(6, 0))

        brush_frame = ttk.LabelFrame(outer, text="Адаптивный подбор кистей — предварительные рекомендации", padding=(7, 5))
        brush_frame.pack(fill="x", pady=(0, 7))
        brush_controls = ttk.Frame(brush_frame)
        brush_controls.pack(side="top", anchor="w", fill="x")
        ttk.Label(brush_controls, text="Мин. кисть").pack(side="left")
        ttk.Combobox(
            brush_controls, textvariable=self.brush_min_var,
            values=tuple(str(value) for value in range(1, 21)), state="readonly", width=3,
        ).pack(side="left", padx=(4, 10))
        ttk.Label(brush_controls, text="Макс. кисть").pack(side="left")
        ttk.Combobox(
            brush_controls, textvariable=self.brush_max_var,
            values=tuple(str(value) for value in range(1, 21)), state="readonly", width=3,
        ).pack(side="left", padx=(4, 10))
        ttk.Label(brush_controls, text="Авто X: px карты / единицу кисти").pack(side="left")
        ttk.Label(brush_controls, textvariable=self.brush_scale_x_var, width=7).pack(side="left", padx=(4, 8))
        ttk.Label(brush_controls, text="Y:").pack(side="left")
        ttk.Label(brush_controls, textvariable=self.brush_scale_y_var, width=7).pack(side="left", padx=(4, 8))
        ttk.Checkbutton(
            brush_controls,
            text="Подтверждаю, что карта соответствует всему холсту игры (460×240)",
            variable=self.brush_scale_calibrated_var,
        ).pack(side="left", padx=(2, 8))
        ttk.Button(
            brush_controls, text="Рассчитать рекомендации", command=self.build_brush_recommendations,
        ).pack(side="left")
        ttk.Button(
            brush_controls, text="Экспорт плана кистей JSON…", command=self.save_brush_plan_dialog,
        ).pack(side="left", padx=(6, 0))
        self.brush_summary_var = tk.StringVar(
            value="Рекомендации не рассчитаны. Масштаб будет вычислен из размера карты и логического холста 460×240."
        )
        ttk.Label(brush_frame, textvariable=self.brush_summary_var, wraplength=1120, justify="left").pack(
            side="top", anchor="w", fill="x", pady=(5, 0)
        )

        self.source_var = tk.StringVar(value="Результат этапа 18 не загружен.")
        ttk.Label(outer, textvariable=self.source_var, wraplength=1120).pack(anchor="w", pady=(0, 6))
        self.preview = _PlanPreview(outer, "Предпросмотр по цветам штрихов")
        self.preview.pack(fill="both", expand=True)

        bottom = ttk.Panedwindow(outer, orient="horizontal")
        bottom.pack(fill="both", expand=False, pady=(8, 0))
        stats_frame = ttk.LabelFrame(bottom, text="Метрики плана", padding=7)
        colors_frame = ttk.LabelFrame(bottom, text="Цвета и их штрихи", padding=7)
        bottom.add(stats_frame, weight=2)
        bottom.add(colors_frame, weight=3)
        self.stats_var = tk.StringVar(value="Сначала преобразуйте изображение на вкладке 4, затем передайте результат сюда.")
        ttk.Label(stats_frame, textvariable=self.stats_var, justify="left", wraplength=520).pack(anchor="w", fill="x")
        self.table = ttk.Treeview(colors_frame, columns=("hex", "name", "pixels", "strokes", "percent"), show="headings", height=7)
        for column, title, width in (
            ("hex", "HEX", 90), ("name", "Цвет", 150), ("pixels", "Пиксели", 85),
            ("strokes", "Штрихи", 75), ("percent", "% видимых", 85),
        ):
            self.table.heading(column, text=title)
            self.table.column(column, width=width, anchor="w" if column in ("hex", "name") else "e")
        self.table.pack(fill="both", expand=True)
        self.status_var = tk.StringVar(
            value="Цветной план можно передать во вкладку исполнения. Оценка расхода краски экспериментальная; перед запуском учитывайте её как ориентир, а не гарантированный лимит."
        )
        ttk.Label(outer, textvariable=self.status_var, wraplength=1120).pack(anchor="w", pady=(7, 0))

    def invalidate_source(self, reason: str) -> None:
        """Clear a plan whose source image became stale (e.g. target area changed)."""
        self.quantization_result = None
        self.palette_profile = None
        self.quantization_report = None
        self._auto_fit_row_step = None
        self._auto_fit_row_offset = 0
        self.source_name = None
        self.plan = None
        self.plan_path = None
        self.plan_index_map = None
        self.brush_plan = None
        self.brush_summary_var.set("Источник сброшен; пересчитайте исходное изображение перед подбором кистей.")
        self.preview.set_image(None)
        for row in self.table.get_children():
            self.table.delete(row)
        self.source_var.set("Источник преобразования сброшен.")
        self.stats_var.set(reason)
        self.status_var.set("Старый цветной план очищен, чтобы не рисовать изображение неправильного размера.")

    def use_latest_quantization(self) -> None:
        data = self.get_quantized_data()
        if not isinstance(data, dict):
            messagebox.showwarning(
                "Нет результата этапа 18",
                "Сначала загрузите изображение и профиль палитры на вкладке 4, затем выполните преобразование.",
                parent=self.root,
            )
            return
        result = data.get("result")
        profile = data.get("profile")
        report = data.get("report")
        if result is None or getattr(result, "index_map", None) is None or getattr(result, "image", None) is None:
            messagebox.showwarning("Нет карты цветов", "Повторно выполните преобразование на вкладке 4.", parent=self.root)
            return
        if not isinstance(profile, dict) or not profile.get("colors"):
            messagebox.showwarning("Нет профиля палитры", "Загрузите профиль палитры на вкладке 4.", parent=self.root)
            return
        # The active profile can change after conversion. The index_map is only meaningful
        # with the exact color order used by stage 18, so reject stale quantization results.
        report_palette = getattr(result, "report", {}).get("palette", [])
        try:
            converted_rgb = [tuple(int(channel) for channel in entry["rgb"]) for entry in report_palette]
            active_rgb = [tuple(int(channel) for channel in entry["rgb"]) for entry in profile["colors"]]
        except (KeyError, TypeError, ValueError):
            converted_rgb, active_rgb = [], []
        if not converted_rgb or converted_rgb != active_rgb:
            messagebox.showwarning(
                "Результат преобразования устарел",
                "После преобразования состав или порядок цветов палитры изменился. "
                "Вернитесь на вкладку 4 и повторите «Преобразовать», затем передайте результат сюда снова.",
                parent=self.root,
            )
            self.quantization_result = None
            self.palette_profile = None
            self.quantization_report = None
            self.plan = None
            self.preview.set_image(None)
            self.stats_var.set("Повторите преобразование на вкладке 4 для текущего профиля палитры.")
            self.status_var.set("Профиль и карта цветов не совпадают; построение плана отменено.")
            return
        self.quantization_result = result
        self.palette_profile = profile
        self.quantization_report = report if isinstance(report, dict) else getattr(result, "report", None)
        self._auto_fit_row_step = None
        self._auto_fit_row_offset = 0
        self.row_step_var.set("1")
        self.source_name = str(data.get("source_name") or "Результат этапа 18")
        self.plan = None
        self.plan_path = None
        self.plan_index_map = None
        self.brush_plan = None
        self.brush_summary_var.set("Источник обновлён. Постройте цветной план, затем рассчитайте рекомендации кистей.")
        self.preview.set_image(None)
        for row in self.table.get_children():
            self.table.delete(row)
        self.source_var.set(
            f"Источник: {self.source_name} · {result.image.width} × {result.image.height} · "
            f"профиль «{profile.get('profile_name', 'Без имени')}» · цветов в профиле: {len(profile['colors'])}"
        )
        self.stats_var.set("Источник принят. Постройте цветной scanline-план.")
        self.status_var.set("Готово к построению. Прозрачные пиксели будут пропущены, а их участки разделят штрихи.")

    def build_plan(self) -> None:
        if self.quantization_result is None or self.palette_profile is None:
            self.use_latest_quantization()
            if self.quantization_result is None or self.palette_profile is None:
                return
        try:
            stroke_overhead = self._parse_model_number(
                self.paint_overhead_var.get(), "Дополнительный расход на штрих"
            )
            paint_budget = self._parse_model_number(
                self.paint_budget_var.get(), "Оценочный запас краски"
            )
            row_step = int(self.row_step_var.get())
            row_offset = self._auto_fit_row_offset if self._auto_fit_row_step == row_step else 0
            plan = build_color_scanline_plan(
                self.quantization_result.index_map,
                self.palette_profile,
                source_report=self.quantization_report,
                source_name=self.source_name,
                row_step_px=row_step,
                row_offset_px=row_offset,
                paint_stroke_overhead_px_equivalent=stroke_overhead,
                paint_budget_px_equivalent=paint_budget,
            )
        except (ColorScanlinePlanError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror("Не удалось построить цветной план", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка построения плана: {exc}")
            return
        self._display_built_plan(plan, self.quantization_result.index_map)

    def _display_built_plan(
        self,
        plan: dict[str, Any],
        index_map: Any,
        *,
        status_prefix: str | None = None,
    ) -> None:
        self.plan = plan
        self.plan_path = None
        self.plan_index_map = index_map.copy()
        self.brush_plan = None
        self.brush_summary_var.set(
            "Цветной план построен. Рассчитайте рекомендации кистей; без подтверждённого масштаба они останутся предварительными."
        )
        self.preview.set_image(render_color_scanline_preview(plan))
        self._populate_table(plan)
        summary = plan["summary"]
        canvas = plan["canvas"]
        generation = plan["generation"]
        row_step = int(generation.get("row_step_px", 1))
        row_offset = int(generation.get("row_offset_px", 0))
        self.stats_var.set(
            f"Холст: {canvas['width']} × {canvas['height']}\n"
            f"Шаг строк: {row_step} px; смещение: {row_offset} px\n"
            f"Цветных штрихов: {summary['stroke_count']:,}; точек: {summary['point_count']:,}\n"
            f"Нарисовано видимых пикселей: {summary['visible_pixel_count']:,}; "
            f"пропущено шагом строк: {summary.get('omitted_by_row_step_pixel_count', 0):,}; "
            f"прозрачных: {summary['transparent_pixel_count']:,}\n"
            f"Одиночных пикселей: {summary['single_pixel_stroke_count']:,}\n"
            f"Переключений цвета по порядку плана: {summary['color_switch_count']:,}; выборов цвета ориентировочно: {summary['color_selection_count_estimate']:,}\n"
            f"Длина рисующих штрихов: {summary['drawing_length_px']:,.1f} px; перемещение между штрихами: {summary['pen_up_distance_px']:,.1f} px\n"
            f"{self._format_paint_estimate(summary.get('paint_cost_estimate'))}"
        )
        self.source_var.set(
            f"Построен план: {len(plan['strokes']):,} штрихов на холсте "
            f"{canvas['width']} × {canvas['height']} px."
        )
        estimate = summary.get("paint_cost_estimate", {})
        risk = estimate.get("risk_level")
        risk_note = {
            "over_budget": "Модель прогнозирует превышение лимита.",
            "very_high": "Расход очень близок к пределу; оставьте дополнительный запас.",
            "high": "Расход высокий; оценка не гарантирует фактический запас.",
        }.get(risk, "Оценка приблизительная и основана на четырёх экспериментальных замерах.")
        prefix = f"{status_prefix} " if status_prefix else ""
        self.status_var.set(
            f"{prefix}План построен: шаг строк {row_step} px, смещение {row_offset} px; "
            f"пропущено строкой выборки пикселей: {summary.get('omitted_by_row_step_pixel_count', 0):,}. "
            f"{risk_note} Порядок: сверху вниз, внутри строки слева направо."
        )

    def build_geometry_plan(self) -> None:
        if self.quantization_result is None or self.palette_profile is None:
            self.use_latest_quantization()
            if self.quantization_result is None or self.palette_profile is None:
                return
        try:
            tolerance = self._parse_model_number(self.geometry_tolerance_var.get(), "Допуск RDP")
            min_component_area = int(self.geometry_min_component_var.get())
            requested_mode = self.geometry_mode_var.get()
            build_mode = "scanline" if requested_mode == "automatic" else requested_mode
            plan = build_geometry_color_plan(
                self.quantization_result.index_map,
                self.palette_profile,
                mode=build_mode,
                simplify_tolerance_px=tolerance,
                min_component_area=min_component_area,
                source_name=self.source_name,
            )
        except (GeometryColorPlanError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror("Не удалось построить геометрический план", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка геометрического плана: {exc}")
            return
        build_note = (
            "Автовыбор построения без бюджетного ограничения: scanline сохраняет карту цветов."
            if requested_mode == "automatic" else None
        )
        self._display_geometry_plan(
            plan, self.quantization_result.index_map, status_prefix=build_note
        )

    def fit_geometry_to_paint_budget(self) -> None:
        if self.quantization_result is None or self.palette_profile is None:
            self.use_latest_quantization()
            if self.quantization_result is None or self.palette_profile is None:
                return
        try:
            stroke_overhead = self._parse_model_number(
                self.paint_overhead_var.get(), "Дополнительный расход на штрих"
            )
            paint_budget = self._parse_model_number(
                self.paint_budget_var.get(), "Оценочный запас краски"
            )
            target_usage = self._parse_model_number(
                self.paint_target_usage_var.get(), "Целевой расход бюджета"
            )
            tolerance = self._parse_model_number(self.geometry_tolerance_var.get(), "Допуск RDP")
            optimizer = (
                optimize_geometry_plan_across_modes
                if self.geometry_mode_var.get() == "automatic"
                else None
            )
            if optimizer is not None:
                plan, report = optimizer(
                    self.quantization_result.index_map,
                    self.palette_profile,
                    paint_budget_px_equivalent=paint_budget,
                    target_usage_percent=target_usage,
                    stroke_overhead_px_equivalent=stroke_overhead,
                    simplify_tolerance_px=tolerance,
                    source_name=self.source_name,
                )
            else:
                plan, report = optimize_geometry_plan_to_budget(
                    self.quantization_result.index_map,
                    self.palette_profile,
                    mode=self.geometry_mode_var.get(),
                    paint_budget_px_equivalent=paint_budget,
                    target_usage_percent=target_usage,
                    stroke_overhead_px_equivalent=stroke_overhead,
                    simplify_tolerance_px=tolerance,
                    source_name=self.source_name,
                )
        except (GeometryColorPlanError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror(
                "Не удалось оптимизировать геометрический план",
                str(exc),
                parent=self.root,
            )
            self.status_var.set(f"Геометрическая оптимизация не выполнена: {exc}")
            return

        choice_text = (
            f"режим {report['mode']} (выбран автоматическим сравнением), "
            if report.get("requested_mode") == "automatic" else f"режим {report['mode']}, "
        )
        fit_text = (
            f"Подогнано под бюджет: {choice_text}масштаб {report['scale']:.1f}, "
            f"допуск RDP {report['simplify_tolerance_px']:.1f} px, "
            f"минимальный компонент {report['min_component_area']} px; "
            f"расход {report['estimated_ink_after_px_equivalent']:,.0f}/"
            f"{report['target_cost_px_equivalent']:,.0f} px-экв."
        )
        if not report["fits_budget"]:
            fit_text += " В одну доску не укладывается — можно попробовать разбиение."
        self._display_geometry_plan(plan, self.quantization_result.index_map, status_prefix=fit_text)

    def _display_geometry_plan(
        self,
        plan: dict[str, Any],
        index_map: Any | None,
        *,
        plan_path: Path | None = None,
        status_prefix: str | None = None,
    ) -> None:
        validated = validate_geometry_color_plan(plan)
        self.plan = validated
        self.plan_path = plan_path
        self.plan_index_map = index_map.copy() if index_map is not None else None
        self.brush_plan = None
        self._auto_fit_row_step = None
        self._auto_fit_row_offset = 0
        self.brush_summary_var.set(
            "Для геометрических планов адаптивные рекомендации кистей Stage 19 не применяются. "
            "План использует полилинии/контуры и исполняется с обычным размером кисти."
        )
        self.preview.set_image(render_geometry_color_preview(validated))
        self._populate_table(validated)

        summary = validated["summary"]
        canvas = validated["canvas"]
        generation = validated["generation"]
        estimate = summary.get("paint_cost_estimate")
        optimization = generation.get("budget_optimization", {})
        summary_lines = [
            f"Формат: geometry · режим: {generation.get('mode', 'не указан')}",
            f"Холст: {canvas['width']} × {canvas['height']} px",
            f"Штрихов: {summary['stroke_count']:,}; точек: {summary['point_count']:,}",
            f"Пикселей в исходной карте: {summary.get('source_visible_pixel_count', summary['visible_pixel_count']):,}; "
            f"после фильтрации компонентов: {summary.get('retained_visible_pixel_count', summary['visible_pixel_count']):,}",
            f"Прозрачных пикселей: {summary['transparent_pixel_count']:,}; "
            f"удалено фильтром мелких компонентов: {generation.get('removed_component_pixel_count', 0):,}",
            f"Переключений цвета: {summary['color_switch_count']:,}; "
            f"выборов цвета ориентировочно: {summary['color_selection_count_estimate']:,}",
            f"Длина рисующих траекторий: {summary['drawing_length_px']:,.1f} px; "
            f"переходов без рисования: {summary['pen_up_distance_px']:,.1f} px",
            self._format_paint_estimate(estimate),
        ]
        if optimization:
            summary_lines.append(
                f"Бюджетная оптимизация: масштаб {optimization.get('scale', 1.0):.1f}; "
                f"RDP {optimization.get('simplify_tolerance_px', 0.0):.1f} px; "
                f"мин. компонент {optimization.get('min_component_area', 1)} px; "
                f"в бюджет: {'да' if optimization.get('fits_budget') else 'нет'}."
            )
            mode_candidates = optimization.get("mode_candidates", [])
            if mode_candidates:
                summary_lines.append(
                    "Сравнение режимов (точное совпадение пикселей): "
                    + " · ".join(
                        f"{item['mode']}: {item['quality_pixel_accuracy_percent']:.1f}% "
                        f"совпадение, {item['estimated_ink_after_px_equivalent']:,.0f} px-экв."
                        for item in mode_candidates
                    )
                )
        self.stats_var.set("\n".join(summary_lines))
        prefix = f"{status_prefix} " if status_prefix else ""
        estimate_risk = estimate.get("risk_label", "оценка приблизительная") if isinstance(estimate, dict) else "оценка недоступна"
        self.source_var.set(
            f"Геометрический план: {len(validated['strokes']):,} штрихов · "
            f"{canvas['width']} × {canvas['height']} px · режим {generation.get('mode', 'не указан')}"
        )
        self.status_var.set(
            f"{prefix}Геометрический план готов. {estimate_risk}. "
            "Проверьте предпросмотр: скелетонизация и контуры меняют заполненную площадь, "
            "поэтому визуальная точность отличается от scanline."
        )

    def split_geometry_to_boards_dialog(self) -> None:
        if not isinstance(self.plan, dict) or self.plan.get("plan_type") != "autodraw_geometry_color_plan":
            messagebox.showinfo(
                "Нет геометрического плана",
                "Сначала постройте или откройте геометрический план.",
                parent=self.root,
            )
            return
        try:
            budget = self._parse_model_number(self.paint_budget_var.get(), "Оценочный запас краски")
            overhead = self._parse_model_number(
                self.paint_overhead_var.get(), "Дополнительный расход на штрих"
            )
            target = self._parse_model_number(self.paint_target_usage_var.get(), "Целевой расход бюджета")
            manifest = split_geometry_plan_to_boards(
                self.plan,
                paint_budget_px_equivalent=budget,
                target_usage_percent=target,
                stroke_overhead_px_equivalent=overhead,
                board_width=660,
                board_height=340,
            )
        except (GeometryColorPlanError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror("Не удалось разбить план на доски", str(exc), parent=self.root)
            return

        selected = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить манифест геометрического плана",
            initialdir=str(self.output_dir),
            initialfile="geometry_multi_board_manifest.json",
            defaultextension=".json",
            filetypes=(("Манифест досок AutoDraw", "*.json"),),
        )
        if not selected:
            return
        manifest_path = Path(selected).resolve()
        boards_dir = manifest_path.parent / f"{manifest_path.stem}_boards"
        try:
            save_multi_board_manifest(manifest_path, manifest)
            boards_dir.mkdir(parents=True, exist_ok=True)
            for board in manifest["boards"]:
                index = int(board["board_index"])
                save_geometry_color_plan(
                    boards_dir / f"board_{index:02d}.json",
                    board["plan"],
                )
        except (OSError, GeometryColorPlanError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось сохранить манифест досок", str(exc), parent=self.root)
            return
        over_budget_count = sum(not board["fits_budget"] for board in manifest["boards"])
        self.status_var.set(
            f"Создано досок: {manifest['board_count']}. Манифест: {manifest_path}; "
            f"отдельные планы: {boards_dir}. "
            f"Досок с прогнозом выше цели: {over_budget_count}. "
            "Исполняйте каждый board_XX.json отдельно и собирайте изображение по метаданным tile."
        )
        messagebox.showinfo(
            "Разбиение завершено",
            f"Создано досок: {manifest['board_count']}\n"
            f"Манифест: {manifest_path}\nОтдельные JSON-планы: {boards_dir}\n"
            f"Досок выше целевого расхода: {over_budget_count}",
            parent=self.root,
        )

    def fit_to_paint_budget(self) -> None:
        if self.quantization_result is None or self.palette_profile is None:
            self.use_latest_quantization()
            if self.quantization_result is None or self.palette_profile is None:
                return
        try:
            stroke_overhead = self._parse_model_number(
                self.paint_overhead_var.get(), "Дополнительный расход на штрих"
            )
            paint_budget = self._parse_model_number(
                self.paint_budget_var.get(), "Оценочный запас краски"
            )
            target_usage = self._parse_model_number(
                self.paint_target_usage_var.get(), "Целевой расход бюджета"
            )
            optimized_result, row_step, row_offset, report = fit_result_to_paint_budget(
                self.quantization_result,
                self.palette_profile,
                paint_budget_px_equivalent=paint_budget,
                stroke_overhead_px_equivalent=stroke_overhead,
                target_usage_percent=target_usage,
            )
            plan = build_color_scanline_plan(
                optimized_result.index_map,
                self.palette_profile,
                source_report=optimized_result.report,
                source_name=self.source_name,
                row_step_px=row_step,
                row_offset_px=row_offset,
                paint_stroke_overhead_px_equivalent=stroke_overhead,
                paint_budget_px_equivalent=paint_budget,
                plan_name="Цветной план, автоматически подогнанный под запас краски",
            )
        except (
            PaintBudgetOptimizationError, ColorScanlinePlanError, ValueError, TypeError, MemoryError
        ) as exc:
            messagebox.showerror(
                "Не удалось уложить изображение в запас краски", str(exc), parent=self.root
            )
            self.status_var.set(f"Автооптимизация не выполнена: {exc}")
            return

        # fit_result_to_paint_budget returns a new object, leaving Stage 18's shared result intact.
        self.quantization_result = optimized_result
        self.quantization_report = optimized_result.report
        self._auto_fit_row_step = row_step
        self._auto_fit_row_offset = row_offset
        self.row_step_var.set(str(row_step))
        available_steps = {str(value) for value in self.row_step_combo["values"]}
        if str(row_step) not in available_steps:
            self.row_step_combo.configure(
                values=tuple(sorted(available_steps | {str(row_step)}, key=int))
            )
        prefix = (
            f"Автооптимизация: блок {report['block_size_px']} px; "
            f"цветов {report['used_color_count_before']}→{report['used_color_count_after']}; "
            f"штрихов {report['stroke_count_before']:,}→{report['stroke_count_after']:,}; "
            f"оценка {report['estimated_ink_after_px_equivalent']:,.0f}/"
            f"{report['target_cost_px_equivalent']:,.0f} px-экв."
        )
        if report.get("fallback_used"):
            prefix += "; применён резервный режим с максимальным упрощением."
        self._display_built_plan(plan, optimized_result.index_map, status_prefix=prefix)

    def save_brush_plan_dialog(self) -> None:
        if self.brush_plan is None:
            messagebox.showinfo(
                "Нет рекомендаций кистей",
                "Сначала постройте цветной план и рассчитайте рекомендации кистей.",
                parent=self.root,
            )
            return
        selected = filedialog.asksaveasfilename(
            parent=self.root,
            title="Экспорт адаптивного плана кистей",
            initialdir=str(self.output_dir),
            initialfile="adaptive_brush_plan.json",
            defaultextension=".json",
            filetypes=(("Адаптивный план кистей AutoDraw", "*.json"), ("JSON", "*.json")),
        )
        if not selected:
            return
        try:
            path = save_adaptive_brush_plan(selected, self.brush_plan)
        except (OSError, BrushPlannerError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось сохранить план кистей", str(exc), parent=self.root)
            return
        self.status_var.set(
            f"Адаптивный план кистей сохранён: {path}. Это отдельный файл; исходный цветной план не изменён."
        )

    def build_brush_recommendations(self) -> None:
        if self.plan is None:
            messagebox.showinfo("Нет цветного плана", "Сначала постройте или откройте цветной план.", parent=self.root)
            return
        if self.plan.get("plan_type") != "autodraw_color_scanline_plan":
            messagebox.showinfo(
                "Адаптивные кисти недоступны",
                "Этот алгоритм рассчитан на растровые scanline-штрихи. "
                "Для геометрических полилиний адаптивный подбор кисти пока не применяется.",
                parent=self.root,
            )
            self.brush_summary_var.set("Адаптивные рекомендации доступны только для scanline-планов.")
            return
        if self.plan_index_map is None:
            messagebox.showwarning(
                "Нет исходной карты цветов",
                "Для безопасной проверки отпечатка кисти нужна точная карта индексов этапа 18. "
                "Передайте актуальный результат из этапа 18 и заново постройте цветной план.",
                parent=self.root,
            )
            self.brush_summary_var.set("Нельзя проверить кисти для загруженного JSON: исходная карта цветов не связана с этим планом.")
            return
        try:
            min_value = int(self.brush_min_var.get())
            max_value = int(self.brush_max_var.get())
            canvas = self.plan["canvas"]
            scale_x = float(canvas["width"]) / GAME_BOARD_LOGICAL_WIDTH
            scale_y = float(canvas["height"]) / GAME_BOARD_LOGICAL_HEIGHT
            self.brush_scale_x_var.set(f"{scale_x:.4f}")
            self.brush_scale_y_var.set(f"{scale_y:.4f}")
            candidate = build_adaptive_brush_plan(
                self.plan_index_map,
                self.plan,
                brush_scale_x=scale_x,
                brush_scale_y=scale_y,
                min_brush_value=min_value,
                max_brush_value=max_value,
                calibration_confirmed=bool(self.brush_scale_calibrated_var.get()),
            )
        except (BrushPlannerError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror("Не удалось подобрать кисти", str(exc), parent=self.root)
            self.brush_summary_var.set(f"Ошибка подбора кистей: {exc}")
            return
        self.brush_plan = candidate
        summary = candidate["summary"]
        configuration = candidate["brush_configuration"]
        per_brush = summary.get("stroke_count_by_brush", {})
        brush_counts = ", ".join(f"{size}: {count:,}" for size, count in per_brush.items()) or "нет"
        calibration_text = (
            "масштаб помечен как откалиброванный" if configuration["calibration_confirmed"]
            else "масштаб НЕ откалиброван; расчёт предварительный"
        )
        self.brush_summary_var.set(
            f"Рекомендуемые штрихи: {summary['planned_stroke_count']:,} "
            f"(исходно {summary['source_stroke_count']:,}; изменение {summary['additional_stroke_count']:+,}). "
            f"Кисти по значениям: {brush_counts}. Переключений размера по порядку плана: "
            f"{summary['recommended_brush_switch_count']:,}. "
            f"Разбито исходных штрихов: {summary['split_source_stroke_count']:,}; "
            f"резерв без гарантии геометрической безопасности: {summary['legacy_fallback_source_stroke_count']:,}. "
            f"Результат: {calibration_text}. Исполнение Stage 20 этим этапом не активируется."
        )
        self.status_var.set(
            "Рекомендации кистей рассчитаны отдельно от исходного цветного плана. "
            "JSON цветного плана и Stage 20 не изменены; реальный расход точек не проверен."
        )

    @staticmethod
    def _parse_model_number(raw: str, label: str) -> float:
        try:
            value = float(str(raw).strip().replace(",", "."))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: введите число; для дробного значения допустима точка или запятая.") from exc
        if not value >= 0 or value == float("inf") or value != value:
            raise ValueError(f"{label}: введите конечное неотрицательное число.")
        return value

    def reset_paint_model(self) -> None:
        self.paint_overhead_var.set(f"{DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT:.2f}")
        self.paint_budget_var.set(f"{DEFAULT_PAINT_BUDGET_PX_EQUIVALENT:.0f}")
        self.status_var.set("Возвращены параметры модели по четырём экспериментальным замерам. Нажмите «Пересчитать» или постройте план заново.")

    def recalculate_paint_estimate(self) -> None:
        if self.plan is None:
            messagebox.showinfo("Нет плана", "Сначала постройте или откройте цветной план.", parent=self.root)
            return
        try:
            stroke_overhead = self._parse_model_number(self.paint_overhead_var.get(), "Дополнительный расход на штрих")
            paint_budget = self._parse_model_number(self.paint_budget_var.get(), "Оценочный запас краски")
            candidate = copy.deepcopy(self.plan)
            if candidate.get("plan_type") == "autodraw_geometry_color_plan":
                candidate.setdefault("generation", {})["geometry_paint_cost_model"] = {
                    "model_id": "empirical-ink-cost-v1-polyline",
                    "stroke_overhead_px_equivalent": stroke_overhead,
                    "budget_px_equivalent": paint_budget,
                    "single_pixel_execution_length_px": 1.0,
                }
                candidate["summary"]["paint_cost_estimate"] = _estimate_geometry_paint_cost(
                    candidate,
                    stroke_overhead_px_equivalent=stroke_overhead,
                    paint_budget_px_equivalent=paint_budget,
                )
                validate_geometry_color_plan(candidate)
                self._display_geometry_plan(
                    candidate, self.plan_index_map, plan_path=self.plan_path,
                    status_prefix="Оценка расхода пересчитана без изменения геометрии.",
                )
                return
            candidate.setdefault("generation", {})["paint_cost_model"] = {
                "model_id": "empirical-ink-cost-v1",
                "stroke_overhead_px_equivalent": stroke_overhead,
                "budget_px_equivalent": paint_budget,
                "single_pixel_execution_length_px": 1.0,
            }
            candidate["summary"]["paint_cost_estimate"] = estimate_color_plan_paint_cost(
                candidate,
                stroke_overhead_px_equivalent=stroke_overhead,
                paint_budget_px_equivalent=paint_budget,
            )
            validate_color_scanline_plan(candidate)
        except (ColorScanlinePlanError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror("Не удалось пересчитать расход", str(exc), parent=self.root)
            return
        self.plan = candidate
        summary = candidate["summary"]
        canvas = candidate["canvas"]
        self.stats_var.set(
            f"Холст: {canvas['width']} × {canvas['height']} px\n"
            f"Шаг строк: {candidate.get('generation', {}).get('row_step_px', 1)} px\n"
            f"Цветных штрихов: {summary['stroke_count']:,}; точек: {summary['point_count']:,}\n"
            f"Длина пути: {summary['drawing_length_px']:,.1f} px; одиночных пикселей: {summary['single_pixel_stroke_count']:,}\n"
            f"{self._format_paint_estimate(summary['paint_cost_estimate'])}"
        )
        self.status_var.set("Оценка пересчитана для текущего плана; геометрия не менялась. Сохраните JSON повторно, если нужно сохранить новые параметры модели.")

    @staticmethod
    def _format_paint_estimate(estimate: dict[str, Any] | None) -> str:
        if not isinstance(estimate, dict):
            return "Оценка краски не сохранена в старом плане. Постройте план заново, чтобы записать модель."
        total = float(estimate.get("estimated_total_ink_px_equivalent", 0.0))
        budget = float(estimate.get(
            "estimated_budget_px_equivalent",
            estimate.get("paint_budget_px_equivalent", DEFAULT_PAINT_BUDGET_PX_EQUIVALENT),
        ))
        percent = float(estimate.get("estimated_usage_percent", 0.0))
        path = float(estimate.get("effective_path_length_px", estimate.get("drawing_length_px", 0.0)))
        overhead = float(estimate.get("estimated_stroke_overhead_px_equivalent", 0.0))
        remaining = float(estimate.get("estimated_remaining_px_equivalent", budget - total))
        conservative = float(estimate.get("conservative_usage_percent", percent))
        label = str(estimate.get("risk_label", "Оценка приблизительная"))
        highest = estimate.get("highest_use_color")
        if isinstance(highest, dict):
            color_detail = (
                f"При отдельном запасе на цвет максимальная нагрузка: {highest.get('hex', '')} "
                f"{highest.get('name', '')} — {highest.get('estimated_total_ink_px_equivalent', 0):,.0f}/"
                f"{budget:,.0f} px-экв. ({highest.get('estimated_usage_percent', 0):.1f}%), "
                f"{highest.get('stroke_count', 0):,} штрихов."
            )
        else:
            color_detail = "Для отдельной оценки по цветам недостаточно данных."
        return (
            f"ОЦЕНКА ПРИ ОБЩЕМ ЗАПАСЕ: {total:,.0f} / {budget:,.0f} px-экв. ({percent:.1f}%; "
            f"по нижней границе запаса: {conservative:.1f}%).\n"
            f"Модель: путь {path:,.0f} + расход на штрихи {overhead:,.0f}; "
            f"остаток по модели {remaining:,.0f}. {label}.\n"
            f"{color_detail}\n"
            "Не счётчик игры: реальный расход может отличаться. Четыре замера дали бюджет примерно 25 610–25 730 px-экв.; "
            "неизвестно, общий ли запас у всех цветов или отдельный у каждого."
        )

    def _populate_table(self, plan: dict[str, Any]) -> None:
        for row in self.table.get_children():
            self.table.delete(row)
        for color in plan["summary"]["used_colors"]:
            self.table.insert(
                "", "end", values=(color["hex"], color["name"], f"{color['pixel_count']:,}",
                                  f"{color['stroke_count']:,}", f"{color['percentage_visible']:.2f}%")
            )

    def save_plan_dialog(self) -> None:
        if self.plan is None:
            messagebox.showinfo("Нет плана", "Сначала постройте или откройте цветной план.", parent=self.root)
            return
        is_geometry = self.plan.get("plan_type") == "autodraw_geometry_color_plan"
        initial = "geometry_color_plan.json" if is_geometry else "color_scanline_plan.json"
        selected = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить геометрический план" if is_geometry else "Сохранить цветной scanline-план",
            initialdir=str(self.output_dir),
            initialfile=initial,
            defaultextension=".json",
            filetypes=(("Цветной план AutoDraw", "*.json"),),
        )
        if not selected:
            return
        try:
            if is_geometry:
                path = save_geometry_color_plan(selected, self.plan)
            else:
                path = save_color_scanline_plan(selected, self.plan)
        except (OSError, GeometryColorPlanError, ColorScanlinePlanError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось сохранить цветной план", str(exc), parent=self.root)
            return
        self.plan_path = path
        self.status_var.set(f"Цветной план сохранён: {path}")

    def open_plan_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть цветной scanline-план",
            initialdir=str(self.output_dir),
            filetypes=(("Цветные планы AutoDraw", "*.json"), ("Все файлы", "*.*")),
        )
        if not selected:
            return
        try:
            document = json.loads(Path(selected).read_text(encoding="utf-8"))
            document_type = document.get("plan_type") if isinstance(document, dict) else None
            if document_type == "autodraw_geometry_color_plan":
                plan = load_geometry_color_plan(selected)
                self._display_geometry_plan(
                    plan, None, plan_path=Path(selected).resolve(),
                    status_prefix="Геометрический план открыт из JSON.",
                )
                self.plan_index_map = None
                return
            plan = load_color_scanline_plan(selected)
            preview = render_color_scanline_preview(plan)
        except (OSError, GeometryColorPlanError, ColorScanlinePlanError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось открыть цветной план", str(exc), parent=self.root)
            return
        self.plan = plan
        self.plan_path = Path(selected).resolve()
        self._auto_fit_row_step = None
        self._auto_fit_row_offset = 0
        self.plan_index_map = None
        self.brush_plan = None
        self.brush_summary_var.set(
            "Открыт JSON плана без связанной карты цветов. Для рекомендаций заново постройте план "
            "из актуального результата этапа 18."
        )
        generation = plan.get("generation", {})
        self.row_step_var.set(str(generation.get("row_step_px", 1)))
        model_config = generation.get("paint_cost_model", {})
        if isinstance(model_config, dict):
            self.paint_overhead_var.set(str(model_config.get("stroke_overhead_px_equivalent", DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT)))
            self.paint_budget_var.set(str(model_config.get("budget_px_equivalent", DEFAULT_PAINT_BUDGET_PX_EQUIVALENT)))
        self.preview.set_image(preview)
        self._populate_table(plan)
        summary = plan["summary"]
        canvas = plan["canvas"]
        estimate = summary.get("paint_cost_estimate")
        if not isinstance(estimate, dict):
            try:
                estimate = estimate_color_plan_paint_cost(
                    plan,
                    stroke_overhead_px_equivalent=self._parse_model_number(
                        self.paint_overhead_var.get(), "Дополнительный расход на штрих"),
                    paint_budget_px_equivalent=self._parse_model_number(
                        self.paint_budget_var.get(), "Оценочный запас краски"),
                )
                estimate["is_local_legacy_estimate"] = True
            except (ValueError, TypeError):
                estimate = None
        self.stats_var.set(
            f"Холст: {canvas['width']} × {canvas['height']}\n"
            f"Шаг строк: {plan.get('generation', {}).get('row_step_px', 1)} px\n"
            f"Цветных штрихов: {summary['stroke_count']:,}; точек: {summary['point_count']:,}\n"
            f"Нарисовано видимых пикселей: {summary['visible_pixel_count']:,}; "
            f"пропущено шагом строк: {summary.get('omitted_by_row_step_pixel_count', 0):,}; "
            f"прозрачных: {summary['transparent_pixel_count']:,}\n"
            f"Одиночных пикселей: {summary['single_pixel_stroke_count']:,}\n"
            f"Переключений цвета: {summary['color_switch_count']:,}; длина штрихов: {summary['drawing_length_px']:,.1f} px\n"
            f"{self._format_paint_estimate(estimate)}" + ("\nДля старого плана оценка рассчитана при открытии и не записана в JSON." if isinstance(estimate, dict) and estimate.get("is_local_legacy_estimate") else "")
        )
        self.source_var.set(f"Открыт цветной план: {self.plan_path.name} · {canvas['width']} × {canvas['height']}")
        self.status_var.set("План проверен по схеме, порядку штрихов и сохранённой модели расхода краски. Оценка не гарантирует фактический запас.")
