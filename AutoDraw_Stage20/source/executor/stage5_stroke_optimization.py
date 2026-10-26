from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from models import DrawingPlan
from path_planning.stroke_optimizer import (
    OptimizationResult,
    StrokeOptimizationSettings,
    measure_plan,
    optimize_plan,
    render_plan_preview,
)

APP_DIR = Path(__file__).resolve().parent


class PlanPreview(ttk.Frame):
    """Масштабируемый предпросмотр плана на белом фоне."""

    def __init__(self, parent: tk.Widget, title: str):
        super().__init__(parent)
        ttk.Label(self, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.canvas = tk.Canvas(self, background="#eeeeee", highlightthickness=1, highlightbackground="#b8b8b8")
        self.canvas.pack(fill="both", expand=True)
        self.image: Image.Image | None = None
        self.photo: ImageTk.PhotoImage | None = None
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_image(self, image: Image.Image | None) -> None:
        self.image = image.copy() if image is not None else None
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        self.photo = None
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if self.image is None:
            self.canvas.create_text(width / 2, height / 2, text="Сначала загрузите DrawingPlan", fill="#555555")
            return
        margin = 12
        scale = min((width - margin * 2) / self.image.width, (height - margin * 2) / self.image.height)
        if scale <= 0:
            return
        display_width = max(1, round(self.image.width * scale))
        display_height = max(1, round(self.image.height * scale))
        display = self.image.resize((display_width, display_height), Image.Resampling.NEAREST)
        self.photo = ImageTk.PhotoImage(display)
        x = (width - display_width) / 2
        y = (height - display_height) / 2
        self.canvas.create_image(x, y, anchor="nw", image=self.photo)
        self.canvas.create_text(x + 4, y + 4, anchor="nw", fill="#16704b",
                                text=f"{self.image.width} × {self.image.height} px")


class StrokeOptimizationApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoDraw — этап 5: оптимизация штрихов")
        self.root.geometry("1380x920")
        self.root.minsize(1050, 720)

        self.input_path: Path | None = None
        self.input_plan: DrawingPlan | None = None
        self.result: OptimizationResult | None = None

        self.tolerance_var = tk.DoubleVar(value=0.5)
        self.reorder_var = tk.BooleanVar(value=True)
        self.reverse_open_var = tk.BooleanVar(value=True)
        self.rotate_closed_var = tk.BooleanVar(value=True)
        self.minimum_length_var = tk.DoubleVar(value=0.0)
        self.remove_short_var = tk.BooleanVar(value=False)
        self.merge_open_var = tk.BooleanVar(value=False)
        self.merge_gap_var = tk.DoubleVar(value=2.0)
        self.merge_angle_var = tk.DoubleVar(value=25.0)

        self.stats_var = tk.StringVar(value="План не загружен.")
        self.status_var = tk.StringVar(value="Загрузите DrawingPlan JSON, сохранённый на этапе 4.")

        self._build_ui()
        self._bind_settings()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Этап 5 — оптимизация DrawingPlan", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Загрузите DrawingPlan из этапа 4. Сравните исходные и оптимизированные траектории. "
                  "Мышь на этом этапе не используется; исходный план не изменяется."),
            wraplength=1320,
        ).pack(anchor="w", pady=(3, 8))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Открыть DrawingPlan JSON…", command=self._open_plan).pack(side="left")
        self.optimize_button = ttk.Button(toolbar, text="Построить оптимизированный план", command=self._optimize, state="disabled")
        self.optimize_button.pack(side="left", padx=(6, 0))
        self.save_plan_button = ttk.Button(toolbar, text="Сохранить оптимизированный JSON…", command=self._save_plan, state="disabled")
        self.save_plan_button.pack(side="left", padx=(6, 0))
        self.save_preview_button = ttk.Button(toolbar, text="Сохранить предпросмотр PNG…", command=self._save_preview, state="disabled")
        self.save_preview_button.pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Открыть папку проекта", command=self._open_project_folder).pack(side="right")

        settings = ttk.LabelFrame(outer, text="Настройки оптимизации", padding=8)
        settings.pack(fill="x", pady=(0, 8))
        settings.columnconfigure(0, weight=1)
        settings.columnconfigure(1, weight=1)
        settings.columnconfigure(2, weight=1)

        ttk.Label(settings, text="Упрощение траектории (допуск, px; 0 — выключено)").grid(row=0, column=0, sticky="w", padx=4)
        tk.Scale(settings, from_=0, to=5, resolution=0.1, orient="horizontal", variable=self.tolerance_var,
                 showvalue=True, length=310).grid(row=1, column=0, sticky="ew", padx=4)

        ttk.Label(settings, text="Минимальная длина штриха для диагностики (px; 0 — отключено)").grid(row=0, column=1, sticky="w", padx=4)
        tk.Scale(settings, from_=0, to=200, resolution=1, orient="horizontal", variable=self.minimum_length_var,
                 showvalue=True, length=310).grid(row=1, column=1, sticky="ew", padx=4)

        options = ttk.Frame(settings)
        options.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=8)
        ttk.Checkbutton(options, text="Сократить расстояние между штрихами", variable=self.reorder_var).pack(anchor="w")
        ttk.Checkbutton(options, text="Разрешить разворот открытых штрихов", variable=self.reverse_open_var).pack(anchor="w")
        ttk.Checkbutton(options, text="Менять начальную точку замкнутых контуров", variable=self.rotate_closed_var).pack(anchor="w")
        ttk.Checkbutton(options, text="Удалять короткие штрихи (осторожно)", variable=self.remove_short_var).pack(anchor="w")

        ttk.Separator(settings, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Checkbutton(settings, text="Объединять совместимые открытые штрихи (может добавить соединительную линию)",
                        variable=self.merge_open_var).grid(row=3, column=0, columnspan=3, sticky="w", padx=4)

        ttk.Label(settings, text="Максимальный промежуток объединения (px)").grid(row=4, column=0, sticky="w", padx=4)
        tk.Scale(settings, from_=0, to=10, resolution=0.5, orient="horizontal", variable=self.merge_gap_var,
                 showvalue=True, length=310).grid(row=5, column=0, sticky="ew", padx=4)
        ttk.Label(settings, text="Максимальное отклонение направления (градусы)").grid(row=4, column=1, sticky="w", padx=4)
        tk.Scale(settings, from_=0, to=90, resolution=5, orient="horizontal", variable=self.merge_angle_var,
                 showvalue=True, length=310).grid(row=5, column=1, sticky="ew", padx=4)
        ttk.Label(settings, text="Советы: короткие штрихи по умолчанию только подсчитываются;\nобъединение открытых штрихов выключено, чтобы не портить контуры.",
                  wraplength=390).grid(row=4, column=2, rowspan=2, sticky="w", padx=8)

        ttk.Label(outer, textvariable=self.stats_var, wraplength=1320, justify="left").pack(anchor="w", pady=(0, 6))

        previews = ttk.Frame(outer)
        previews.pack(fill="both", expand=True)
        previews.columnconfigure(0, weight=1, uniform="preview")
        previews.columnconfigure(1, weight=1, uniform="preview")
        previews.rowconfigure(0, weight=1)
        self.original_preview = PlanPreview(previews, "1. Исходный DrawingPlan — зелёным отмечено начало штрихов")
        self.optimized_preview = PlanPreview(previews, "2. Оптимизированный план")
        self.original_preview.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.optimized_preview.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Label(outer, textvariable=self.status_var, foreground="#245b42", wraplength=1320).pack(anchor="w", pady=(7, 0))

    def _bind_settings(self) -> None:
        for variable in (
            self.tolerance_var, self.reorder_var, self.reverse_open_var, self.rotate_closed_var,
            self.minimum_length_var, self.remove_short_var, self.merge_open_var,
            self.merge_gap_var, self.merge_angle_var,
        ):
            variable.trace_add("write", self._on_settings_changed)

    def _on_settings_changed(self, *_args) -> None:
        if self.input_plan is None:
            return
        self.result = None
        self.optimized_preview.set_image(None)
        self.save_plan_button.configure(state="disabled")
        self.save_preview_button.configure(state="disabled")
        metrics = measure_plan(self.input_plan)
        self.stats_var.set(
            f"Исходный план: {metrics.stroke_count} штрихов, {metrics.point_count} точек, "
            f"длина рисования {metrics.drawing_length_px:.1f} px, переходы без рисования "
            f"{metrics.pen_up_distance_px:.1f} px. Параметры изменены — запустите оптимизацию повторно."
        )
        self.status_var.set("Настройки изменены. Исходный DrawingPlan не затронут.")

    def _open_plan(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите DrawingPlan JSON из этапа 4",
            initialdir=str(self.input_path.parent if self.input_path else APP_DIR),
            filetypes=[("DrawingPlan JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            plan = DrawingPlan.load(path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Ошибка загрузки плана", f"Не удалось загрузить DrawingPlan:\n{exc}", parent=self.root)
            return
        self.input_path = Path(path)
        self.input_plan = plan
        self.result = None
        self.original_preview.set_image(render_plan_preview(plan))
        self.optimized_preview.set_image(None)
        self.optimize_button.configure(state="normal")
        self.save_plan_button.configure(state="disabled")
        self.save_preview_button.configure(state="disabled")
        metrics = measure_plan(plan)
        self.stats_var.set(
            f"Исходный план: {metrics.stroke_count} штрихов, {metrics.point_count} точек, "
            f"длина рисования {metrics.drawing_length_px:.1f} px, переходы без рисования "
            f"{metrics.pen_up_distance_px:.1f} px, оценка вызовов перемещения при шаге 2 px: "
            f"{metrics.estimated_move_calls}."
        )
        self.status_var.set(f"Загружен план: {self.input_path.name}, холст {plan.width} × {plan.height} px.")

    def _current_settings(self) -> StrokeOptimizationSettings:
        return StrokeOptimizationSettings(
            simplify_tolerance_px=float(self.tolerance_var.get()),
            reorder_strokes=bool(self.reorder_var.get()),
            reverse_open_strokes=bool(self.reverse_open_var.get()),
            rotate_closed_strokes=bool(self.rotate_closed_var.get()),
            minimum_stroke_length_px=float(self.minimum_length_var.get()),
            remove_short_strokes=bool(self.remove_short_var.get()),
            merge_open_strokes=bool(self.merge_open_var.get()),
            max_merge_gap_px=float(self.merge_gap_var.get()),
            max_join_angle_deg=float(self.merge_angle_var.get()),
        )

    def _optimize(self) -> None:
        if self.input_plan is None:
            return
        try:
            self.result = optimize_plan(self.input_plan, self._current_settings())
            preview = render_plan_preview(self.result.optimized_plan)
        except (ValueError, TypeError) as exc:
            self.result = None
            self.optimized_preview.set_image(None)
            self.save_plan_button.configure(state="disabled")
            self.save_preview_button.configure(state="disabled")
            messagebox.showerror("Не удалось оптимизировать план", str(exc), parent=self.root)
            return

        result = self.result
        self.optimized_preview.set_image(preview)
        self.save_plan_button.configure(state="normal")
        self.save_preview_button.configure(state="normal")

        before = result.original_metrics
        after = result.optimized_metrics
        drawing_delta = _percent_change(before.drawing_length_px, after.drawing_length_px)
        travel_delta = _percent_change(before.pen_up_distance_px, after.pen_up_distance_px)
        self.stats_var.set(
            f"Штрихи: {before.stroke_count} → {after.stroke_count}; точки: {before.point_count} → "
            f"{after.point_count} (упрощением удалено точек: {result.points_removed_by_simplification});\n"
            f"Длина рисования: {before.drawing_length_px:.1f} → {after.drawing_length_px:.1f} px "
            f"({drawing_delta:+.1f}%); переходы без рисования: {before.pen_up_distance_px:.1f} → "
            f"{after.pen_up_distance_px:.1f} px ({travel_delta:+.1f}%); оценка вызовов перемещения: "
            f"{before.estimated_move_calls} → {after.estimated_move_calls}.\n"
            f"Коротких штрихов ниже порога: {result.short_strokes_detected}; удалено: "
            f"{result.short_strokes_removed}; объединено пар открытых штрихов: {result.merged_stroke_pairs}."
        )
        self.status_var.set("Оптимизированный план готов. Проверьте оба предпросмотра перед сохранением.")

    def _save_plan(self) -> None:
        if self.result is None:
            messagebox.showinfo("Нет результата", "Сначала выполните оптимизацию.", parent=self.root)
            return
        default_name = f"{self.input_path.stem if self.input_path else 'drawing'}_optimized.json"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить оптимизированный DrawingPlan",
            initialdir=str(self.input_path.parent if self.input_path else APP_DIR),
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        destination = Path(path)
        if self.input_path is not None and destination.resolve() == self.input_path.resolve():
            messagebox.showerror(
                "Нельзя перезаписать исходный план",
                "Сохраните оптимизированный план под новым именем, чтобы исходный DrawingPlan из этапа 4 остался неизменным.",
                parent=self.root,
            )
            return
        result = self.result
        data = result.optimized_plan.to_dict()
        data["optimization"] = {
            "source_plan_file": self.input_path.name if self.input_path else None,
            "settings": result.settings.to_dict(),
            "metrics_before": result.original_metrics.to_dict(),
            "metrics_after": result.optimized_metrics.to_dict(),
            "short_strokes_detected": result.short_strokes_detected,
            "short_strokes_removed": result.short_strokes_removed,
            "points_removed_by_simplification": result.points_removed_by_simplification,
            "merged_stroke_pairs": result.merged_stroke_pairs,
            "notes": [
                "Short strokes are not removed unless explicitly enabled.",
                "Joining open strokes may add a connector and is disabled by default.",
                "Stroke ordering uses a greedy nearest-neighbour heuristic, not a globally optimal route.",
            ],
        }
        try:
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)
            return
        self.status_var.set(f"Оптимизированный DrawingPlan сохранён: {path}")

    def _save_preview(self) -> None:
        if self.result is None:
            messagebox.showinfo("Нет предпросмотра", "Сначала выполните оптимизацию.", parent=self.root)
            return
        default_name = f"{self.input_path.stem if self.input_path else 'drawing'}_optimized_preview.png"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить предпросмотр оптимизированного плана",
            initialdir=str(self.input_path.parent if self.input_path else APP_DIR),
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        try:
            render_plan_preview(self.result.optimized_plan).save(path)
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)
            return
        self.status_var.set(f"Предпросмотр сохранён: {path}")

    def _open_project_folder(self) -> None:
        try:
            os.startfile(APP_DIR)
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку проекта: {exc}", parent=self.root)

    def _on_close(self) -> None:
        self.root.destroy()


def _percent_change(before: float, after: float) -> float:
    if abs(before) <= 1e-9:
        return 0.0
    return (after - before) / before * 100.0


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    StrokeOptimizationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
