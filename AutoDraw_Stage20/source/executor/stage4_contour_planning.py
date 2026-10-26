from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk
import cv2

from models import DrawingPlan
from path_planning.contour_planner import ContourSettings, extract_contours, render_contour_preview

APP_DIR = Path(__file__).resolve().parent
PROFILE_PATH = APP_DIR / "target_profile.json"
RETRIEVAL_LABELS = {"Только внешние контуры": "external", "Все контуры, включая внутренние": "all"}
RETRIEVAL_LABELS_BY_VALUE = {value: label for label, value in RETRIEVAL_LABELS.items()}
FOREGROUND_LABELS = {
    "Тёмные области (чёрное на белом)": "dark",
    "Светлые области (белое на чёрном)": "light",
}
FOREGROUND_LABELS_BY_VALUE = {value: label for label, value in FOREGROUND_LABELS.items()}


def load_mask_file(path: str | Path) -> Image.Image:
    """Открывает маску и корректно сводит прозрачность на белый фон."""
    try:
        with Image.open(path) as opened:
            oriented = ImageOps.exif_transpose(opened)
            if oriented.mode in ("RGBA", "LA") or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, rgba).convert("L")
            else:
                image = oriented.convert("L")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(f"Не удалось открыть изображение маски: {exc}") from exc

    if image.width < 1 or image.height < 1:
        raise ValueError("Изображение маски имеет нулевой размер.")
    if image.width * image.height > 40_000_000:
        raise ValueError("Маска слишком велика: более 40 млн пикселей.")
    return image


class ImagePreview(ttk.Frame):
    def __init__(self, parent: tk.Widget, title: str):
        super().__init__(parent)
        ttk.Label(self, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.canvas = tk.Canvas(self, background="#dddddd", highlightthickness=1, highlightbackground="#b8b8b8")
        self.canvas.pack(fill="both", expand=True)
        self.image: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

    def set_image(self, image: Image.Image | None) -> None:
        self.image = image.copy() if image is not None else None
        self.redraw()

    def redraw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if self.image is None:
            self.canvas.create_text(width / 2, height / 2, text="Загрузите бинарную маску", fill="#555555")
            return

        margin = 12
        scale = min((width - margin * 2) / self.image.width, (height - margin * 2) / self.image.height)
        if scale <= 0:
            return
        display_width = max(1, round(self.image.width * scale))
        display_height = max(1, round(self.image.height * scale))
        resampling = Image.Resampling.NEAREST if self.image.mode in ("1", "L") else Image.Resampling.LANCZOS
        display = self.image.resize((display_width, display_height), resampling)
        self._photo = ImageTk.PhotoImage(display)
        x = (width - display_width) / 2
        y = (height - display_height) / 2
        self.canvas.create_image(x, y, anchor="nw", image=self._photo)
        self.canvas.create_text(x + 4, y + 4, anchor="nw", fill="#16704b",
                                text=f"{self.image.width} × {self.image.height} px")


class ContourPlanningApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoDraw — этап 4: извлечение контуров")
        self.root.geometry("1320x900")
        self.root.minsize(1000, 700)

        self.mask: Image.Image | None = None
        self.mask_path: Path | None = None
        self.result = None
        self.plan: DrawingPlan | None = None
        self._pending_update: str | None = None

        self.min_length_var = tk.DoubleVar(value=0.0)
        self.epsilon_var = tk.DoubleVar(value=0.1)
        self.retrieval_var = tk.StringVar(value="Только внешние контуры")
        self.foreground_var = tk.StringVar(value="Тёмные области (чёрное на белом)")
        self.stats_var = tk.StringVar(value="Маска не загружена.")
        self.status_var = tk.StringVar(value="Откройте бинарную маску, сохранённую на этапе 3.")

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Этап 4 — извлечение контуров и построение DrawingPlan",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text="Загрузите бинарную маску из этапа 3. Программа найдёт границы переднего плана, превратит их в штрихи и покажет план. Мышь на этом этапе не используется.",
            wraplength=1280,
        ).pack(anchor="w", pady=(3, 8))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        self.open_button = ttk.Button(toolbar, text="Открыть бинарную маску…", command=self._open_mask)
        self.open_button.pack(side="left")
        self.save_plan_button = ttk.Button(toolbar, text="Сохранить DrawingPlan JSON…", command=self._save_plan, state="disabled")
        self.save_plan_button.pack(side="left", padx=(6, 0))
        self.save_preview_button = ttk.Button(toolbar, text="Сохранить предпросмотр PNG…", command=self._save_preview, state="disabled")
        self.save_preview_button.pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Открыть папку проекта", command=self._open_project_folder).pack(side="right")

        controls = ttk.LabelFrame(outer, text="Настройки извлечения", padding=8)
        controls.pack(fill="x", pady=(0, 8))

        ttk.Label(controls, text="Минимальная длина контура (px; 0 — не фильтровать)").grid(row=0, column=0, sticky="w", padx=4)
        min_scale = tk.Scale(controls, from_=0, to=200, resolution=1, orient="horizontal",
                             variable=self.min_length_var, showvalue=True, length=260,
                             command=self._schedule_extraction)
        min_scale.grid(row=1, column=0, sticky="ew", padx=4)

        ttk.Label(controls, text="Упрощение (доля периметра, %)").grid(row=0, column=1, sticky="w", padx=4)
        epsilon_scale = tk.Scale(controls, from_=0, to=3, resolution=0.05, orient="horizontal",
                                 variable=self.epsilon_var, showvalue=True, length=260,
                                 command=self._schedule_extraction)
        epsilon_scale.grid(row=1, column=1, sticky="ew", padx=4)

        ttk.Label(controls, text="Выбор контуров").grid(row=0, column=2, sticky="w", padx=4)
        retrieval_combo = ttk.Combobox(controls, textvariable=self.retrieval_var,
                                       values=list(RETRIEVAL_LABELS), state="readonly", width=32)
        retrieval_combo.grid(row=1, column=2, sticky="ew", padx=4)
        retrieval_combo.bind("<<ComboboxSelected>>", self._schedule_extraction)

        ttk.Label(controls, text="Передний план маски").grid(row=0, column=3, sticky="w", padx=4)
        foreground_combo = ttk.Combobox(controls, textvariable=self.foreground_var,
                                        values=list(FOREGROUND_LABELS), state="readonly", width=33)
        foreground_combo.grid(row=1, column=3, sticky="ew", padx=4)
        foreground_combo.bind("<<ComboboxSelected>>", self._schedule_extraction)
        for column in range(4):
            controls.columnconfigure(column, weight=1)

        ttk.Label(outer, textvariable=self.stats_var, wraplength=1280).pack(anchor="w", pady=(0, 6))

        preview = ttk.Frame(outer)
        preview.pack(fill="both", expand=True)
        preview.columnconfigure(0, weight=1, uniform="preview")
        preview.columnconfigure(1, weight=1, uniform="preview")
        preview.rowconfigure(0, weight=1)
        self.mask_preview = ImagePreview(preview, "1. Бинарная маска")
        self.plan_preview = ImagePreview(preview, "2. Контуры поверх маски; зелёный — начало штриха")
        self.mask_preview.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.plan_preview.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Label(outer, textvariable=self.status_var, foreground="#245b42", wraplength=1280).pack(anchor="w", pady=(7, 0))

    def _open_mask(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите бинарную маску из этапа 3",
            initialdir=str(self.mask_path.parent if self.mask_path else APP_DIR),
            filetypes=[("Изображения", "*.png *.bmp *.tif *.tiff *.jpg *.jpeg *.webp"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            image = load_mask_file(path)
        except ValueError as exc:
            messagebox.showerror("Ошибка загрузки маски", str(exc), parent=self.root)
            return
        self.mask = image
        self.mask_path = Path(path)
        self.mask_preview.set_image(self.mask)
        self._extract_now()
        self.status_var.set(f"Загружена маска: {self.mask_path.name}, {image.width} × {image.height} px.")

    def _current_settings(self) -> ContourSettings:
        epsilon = round(float(self.epsilon_var.get()) * 100) / 100
        retrieval = RETRIEVAL_LABELS.get(self.retrieval_var.get(), "external")
        foreground = FOREGROUND_LABELS.get(self.foreground_var.get(), "dark")
        return ContourSettings(
            min_contour_length_px=float(self.min_length_var.get()),
            epsilon_percent=epsilon,
            retrieval_mode=retrieval,  # type: ignore[arg-type]
            foreground_mode=foreground,  # type: ignore[arg-type]
        )

    def _schedule_extraction(self, _event=None) -> None:
        if self.mask is None:
            return
        if self._pending_update is not None:
            try:
                self.root.after_cancel(self._pending_update)
            except tk.TclError:
                pass
        self._pending_update = self.root.after(100, self._extract_now)

    def _extract_now(self) -> None:
        self._pending_update = None
        if self.mask is None:
            return
        try:
            settings = self._current_settings()
            result = extract_contours(self.mask, settings, plan_name=f"Contours from {self.mask_path.name if self.mask_path else 'mask'}")
        except (ValueError, TypeError, cv2.error) as exc:
            self.status_var.set(f"Не удалось построить контуры: {exc}")
            return
        self.result = result
        self.plan = result.plan
        preview = render_contour_preview(self.mask, self.plan)
        self.plan_preview.set_image(preview)
        self.save_plan_button.configure(state="normal" if self.plan is not None else "disabled")
        self.save_preview_button.configure(state="normal")

        if self.plan is None:
            self.stats_var.set(
                f"Маска {self.mask.width} × {self.mask.height} px; найдено контуров: {result.contours_found}; "
                f"после фильтрации штрихов нет. Измените передний план или порог/маску на этапе 3."
            )
        else:
            closed_count = sum(stroke.closed for stroke in self.plan.strokes)
            total_length = self.plan.total_drawing_length_px
            pen_up = self.plan.pen_up_distance_px
            self.stats_var.set(
                f"Маска {self.mask.width} × {self.mask.height} px; найдено контуров: {result.contours_found}; "
                f"штрихов в плане: {self.plan.stroke_count} (замкнутых: {closed_count}); "
                f"пропущено по длине: {result.skipped_by_length}; некорректных: {result.skipped_invalid}; "
                f"точек до обработки: {result.source_point_count}; точек в плане: {result.planned_point_count}; "
                f"длина рисования: {total_length:.1f} px; переходы без рисования: {pen_up:.1f} px."
            )
        self.status_var.set("План обновлён. Проверьте предпросмотр: сейчас трассируются границы областей маски, не центральные линии.")

    def _save_plan(self) -> None:
        if self.plan is None or self.result is None:
            messagebox.showinfo("Нет плана", "Сначала загрузите маску и получите хотя бы один контур.", parent=self.root)
            return
        default_name = f"{self.mask_path.stem if self.mask_path else 'image'}_drawing_plan.json"
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить DrawingPlan", initialdir=str(APP_DIR),
            initialfile=default_name, defaultextension=".json", filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        settings = self.result.settings
        data = self.plan.to_dict()
        data["generation"] = {
            "method": "opencv_findContours",
            "source_mask_file": str(self.mask_path) if self.mask_path else None,
            "contours_found": self.result.contours_found,
            "contours_kept": self.result.contours_kept,
            "skipped_by_length": self.result.skipped_by_length,
            "skipped_invalid": self.result.skipped_invalid,
            "settings": settings.to_dict(),
            "note": "Paths trace the boundaries of foreground regions. They are not centerline skeletons.",
        }
        try:
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)
            return
        self.status_var.set(f"DrawingPlan сохранён: {path}")

    def _save_preview(self) -> None:
        if self.mask is None or self.result is None:
            messagebox.showinfo("Нет предпросмотра", "Сначала загрузите маску.", parent=self.root)
            return
        default_name = f"{self.mask_path.stem if self.mask_path else 'image'}_contours_preview.png"
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить предпросмотр", initialdir=str(APP_DIR),
            initialfile=default_name, defaultextension=".png", filetypes=[("PNG", "*.png")],
        )
        if not path:
            return
        try:
            render_contour_preview(self.mask, self.plan).save(path)
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)
            return
        self.status_var.set(f"Предпросмотр сохранён: {path}")

    def _open_project_folder(self) -> None:
        try:
            import os
            os.startfile(APP_DIR)  # Windows only, the target platform of the app
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку проекта: {exc}", parent=self.root)

    def _on_close(self) -> None:
        if self._pending_update is not None:
            try:
                self.root.after_cancel(self._pending_update)
            except tk.TclError:
                pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    ContourPlanningApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
