from __future__ import annotations

import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

from PIL import Image, ImageTk

try:
    from image_processing import ProcessingSettings, load_rgb_image, process_image
    from image_processing.pipeline import FitMode
    from image_processing.preview_pane import PreviewPane
except ImportError as exc:
    raise SystemExit("Не удалось загрузить модуль обработки. Запускайте stage3_image_processing.py из папки проекта.") from exc

APP_DIR = Path(__file__).resolve().parent
PROFILE_PATH = APP_DIR / "target_profile.json"

FIT_LABELS = {
    "Вписать с белыми полями": "contain",
    "Заполнить холст с обрезкой краёв": "cover",
    "Растянуть до размера холста": "stretch",
}
FIT_LABELS_BY_VALUE = {value: label for label, value in FIT_LABELS.items()}
THRESHOLD_LABELS = {"Автоматический порог (Otsu)": "otsu", "Ручной порог": "manual"}
THRESHOLD_LABELS_BY_VALUE = {value: label for label, value in THRESHOLD_LABELS.items()}


class ImageProcessingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoDraw — этап 3: подготовка изображения")
        self.root.geometry("1420x980")
        self.root.minsize(1080, 760)

        self.original_image: Image.Image | None = None
        self.source_path: Path | None = None
        self.crop_box: tuple[int, int, int, int] | None = None
        self.result = None
        self._pending_update: str | None = None
        self._loading_controls = False

        self.width_var = tk.StringVar(value="646")
        self.height_var = tk.StringVar(value="323")
        self.fit_mode_var = tk.StringVar(value="Вписать с белыми полями")
        self.brightness_var = tk.IntVar(value=0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.denoise_var = tk.IntVar(value=0)
        self.threshold_mode_var = tk.StringVar(value="Автоматический порог (Otsu)")
        self.threshold_var = tk.IntVar(value=128)
        self.threshold_display_var = tk.StringVar(value="Порог: —")
        self.stats_var = tk.StringVar(value="Изображение не загружено.")
        self.status_var = tk.StringVar(value="Загрузите изображение. Автоматическая обработка пока не рисует на доске.")

        self._build_ui()
        self._load_default_profile()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Этап 3 — подготовка изображения и бинарная маска",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(outer,
                  text="Здесь настраивается изображение для будущего извлечения контуров. Этот этап не управляет мышью и не рисует на доске.",
                  wraplength=1360).pack(anchor="w", pady=(3, 8))

        top = ttk.Frame(outer)
        top.pack(fill="x", pady=(0, 8))
        ttk.Button(top, text="Загрузить изображение…", command=self._load_image).pack(side="left")
        ttk.Button(top, text="Загрузить профиль холста…", command=self._load_profile_dialog).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Сбросить обрезку", command=self._reset_crop).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Сохранить комплект…", command=self._save_bundle).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Сохранить серое PNG…", command=self._save_grayscale).pack(side="left", padx=(6, 0))
        ttk.Button(top, text="Сохранить маску PNG…", command=self._save_mask).pack(side="left", padx=(6, 0))

        settings_frame = ttk.LabelFrame(outer, text="Размер холста и масштабирование", padding=8)
        settings_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(settings_frame, text="Ширина (px)").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(settings_frame, textvariable=self.width_var, width=9).grid(row=1, column=0, sticky="ew", padx=4)
        ttk.Label(settings_frame, text="Высота (px)").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Entry(settings_frame, textvariable=self.height_var, width=9).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(settings_frame, text="Как подогнать изображение").grid(row=0, column=2, sticky="w", padx=4)
        fit_combo = ttk.Combobox(settings_frame, textvariable=self.fit_mode_var,
                                 values=list(FIT_LABELS), state="readonly", width=34)
        fit_combo.grid(row=1, column=2, sticky="ew", padx=4)
        fit_combo.bind("<<ComboboxSelected>>", lambda _event: self._schedule_processing())
        ttk.Button(settings_frame, text="Применить размер", command=self._apply_target_size).grid(
            row=1, column=3, sticky="ew", padx=4)
        for column in range(4):
            settings_frame.columnconfigure(column, weight=1 if column in (2, 3) else 0)

        adjustments = ttk.LabelFrame(outer, text="Параметры обработки", padding=8)
        adjustments.pack(fill="x", pady=(0, 8))
        ttk.Label(adjustments, text="Яркость").grid(row=0, column=0, sticky="w", padx=4)
        self.brightness_scale = tk.Scale(adjustments, from_=-100, to=100, orient="horizontal",
                                         variable=self.brightness_var, showvalue=True, length=190,
                                         command=self._on_setting_changed)
        self.brightness_scale.grid(row=1, column=0, sticky="ew", padx=4)

        ttk.Label(adjustments, text="Контраст").grid(row=0, column=1, sticky="w", padx=4)
        self.contrast_scale = tk.Scale(adjustments, from_=0.5, to=2.5, resolution=0.05, orient="horizontal",
                                       variable=self.contrast_var, showvalue=True, length=190,
                                       command=self._on_setting_changed)
        self.contrast_scale.grid(row=1, column=1, sticky="ew", padx=4)

        ttk.Label(adjustments, text="Подавление шума (median blur)").grid(row=0, column=2, sticky="w", padx=4)
        self.denoise_scale = tk.Scale(adjustments, from_=0, to=4, orient="horizontal",
                                      variable=self.denoise_var, showvalue=True, length=190,
                                      command=self._on_setting_changed)
        self.denoise_scale.grid(row=1, column=2, sticky="ew", padx=4)

        ttk.Label(adjustments, text="Бинаризация").grid(row=0, column=3, sticky="w", padx=4)
        self.threshold_combo = ttk.Combobox(adjustments, textvariable=self.threshold_mode_var,
                                            values=list(THRESHOLD_LABELS), state="readonly", width=25)
        self.threshold_combo.grid(row=1, column=3, sticky="ew", padx=4)
        self.threshold_combo.bind("<<ComboboxSelected>>", self._on_threshold_mode_changed)
        self.threshold_scale = tk.Scale(adjustments, from_=0, to=255, orient="horizontal",
                                         variable=self.threshold_var, showvalue=True, length=190,
                                         command=self._on_setting_changed)
        self.threshold_scale.grid(row=2, column=3, sticky="ew", padx=4, pady=(2, 0))
        ttk.Label(adjustments, textvariable=self.threshold_display_var).grid(row=3, column=3, sticky="w", padx=4)
        for column in range(4):
            adjustments.columnconfigure(column, weight=1)

        ttk.Label(outer, textvariable=self.stats_var, wraplength=1360).pack(anchor="w", pady=(0, 6))

        preview_grid = ttk.Frame(outer)
        preview_grid.pack(fill="both", expand=True)
        for column in range(2):
            preview_grid.columnconfigure(column, weight=1, uniform="preview_col")
        for row in range(2):
            preview_grid.rowconfigure(row, weight=1, uniform="preview_row")

        self.source_pane = PreviewPane(preview_grid, "1. Исходник — перетащите по изображению для обрезки",
                                       selectable=True, on_selection=self._on_crop_selected)
        self.color_pane = PreviewPane(preview_grid, "2. Размер холста и масштабирование")
        self.gray_pane = PreviewPane(preview_grid, "3. Чёрно-белое изображение после фильтров")
        self.mask_pane = PreviewPane(preview_grid, "4. Бинарная маска — чёрное будет считаться передним планом")
        self.source_pane.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.color_pane.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.gray_pane.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.mask_pane.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

        ttk.Label(outer, textvariable=self.status_var, foreground="#245b42", wraplength=1360).pack(anchor="w", pady=(7, 0))

    def _load_default_profile(self) -> None:
        if PROFILE_PATH.exists():
            try:
                self._load_profile_file(PROFILE_PATH, show_status=False)
                self.status_var.set(f"Найден профиль холста: {self.width_var.get()} × {self.height_var.get()} px.")
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                self.status_var.set("Не удалось прочитать target_profile.json. Используются размеры 646 × 323 px.")

    def _load_profile_dialog(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Выберите target_profile.json",
                                         initialdir=str(APP_DIR),
                                         filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            self._load_profile_file(Path(path), show_status=True)
            self._apply_target_size()
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка профиля", str(exc), parent=self.root)

    def _load_profile_file(self, path: Path, show_status: bool) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        area = data.get("area", data)
        width = int(area["width"])
        height = int(area["height"])
        if width <= 0 or height <= 0:
            raise ValueError("Ширина и высота в профиле должны быть больше нуля.")
        self.width_var.set(str(width))
        self.height_var.set(str(height))
        if show_status:
            self.status_var.set(f"Загружен профиль: {path} ({width} × {height} px).")

    def _load_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root, title="Выберите изображение",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            image = load_rgb_image(path)
        except ValueError as exc:
            messagebox.showerror("Не удалось загрузить изображение", str(exc), parent=self.root)
            return
        self.original_image = image
        self.source_path = Path(path)
        self.crop_box = None
        self.source_pane.set_image(self.original_image)
        self.source_pane.set_selection(None)
        self._process_now()
        self.status_var.set(f"Загружено: {self.source_path.name}, {image.width} × {image.height} px.")

    def _on_crop_selected(self, box: tuple[int, int, int, int]) -> None:
        self.crop_box = box
        self.source_pane.set_selection(box)
        self._schedule_processing()
        self.status_var.set(f"Выбрана область обрезки: x={box[0]}, y={box[1]}, {box[2]-box[0]} × {box[3]-box[1]} px.")

    def _reset_crop(self) -> None:
        if self.original_image is None:
            return
        self.crop_box = None
        self.source_pane.set_selection(None)
        self._schedule_processing()
        self.status_var.set("Обрезка сброшена; будет использоваться всё исходное изображение.")

    def _apply_target_size(self) -> None:
        try:
            width, height = int(self.width_var.get()), int(self.height_var.get())
        except ValueError:
            messagebox.showerror("Неверный размер", "Ширина и высота должны быть целыми числами.", parent=self.root)
            return
        if width < 1 or height < 1 or width * height > 40_000_000:
            messagebox.showerror("Неверный размер", "Размер должен быть положительным и не превышать 40 млн пикселей.", parent=self.root)
            return
        self._process_now()

    def _on_setting_changed(self, _value=None) -> None:
        self._schedule_processing()

    def _on_threshold_mode_changed(self, _event=None) -> None:
        mode = THRESHOLD_LABELS.get(self.threshold_mode_var.get(), "otsu")
        self.threshold_scale.configure(state="normal" if mode == "manual" else "disabled")
        self._schedule_processing()

    def _schedule_processing(self) -> None:
        if self.original_image is None:
            return
        if self._pending_update is not None:
            try:
                self.root.after_cancel(self._pending_update)
            except tk.TclError:
                pass
        self._pending_update = self.root.after(120, self._process_now)

    def _current_settings(self) -> ProcessingSettings:
        contrast = round(float(self.contrast_var.get()) * 100) / 100
        mode = THRESHOLD_LABELS.get(self.threshold_mode_var.get(), "otsu")
        return ProcessingSettings(
            brightness=int(self.brightness_var.get()),
            contrast=contrast,
            denoise_level=int(self.denoise_var.get()),
            threshold_mode=mode,  # type: ignore[arg-type]
            threshold=int(self.threshold_var.get()),
        )

    def _process_now(self) -> None:
        self._pending_update = None
        if self.original_image is None:
            return
        try:
            width, height = int(self.width_var.get()), int(self.height_var.get())
            settings = self._current_settings()
            fit_mode: FitMode = FIT_LABELS.get(self.fit_mode_var.get(), "contain")  # type: ignore[assignment]
            result = process_image(self.original_image, width, height, fit_mode, self.crop_box, settings)
        except (ValueError, TypeError) as exc:
            self.status_var.set(f"Не удалось обработать изображение: {exc}")
            return
        self.result = result
        self.color_pane.set_image(result.prepared_color)
        self.gray_pane.set_image(result.grayscale)
        self.mask_pane.set_image(result.binary_mask)
        self.threshold_display_var.set(f"Применённый порог: {result.threshold_used} ({settings.threshold_mode})")
        black_pixels = int((__import__("numpy").asarray(result.binary_mask) == 0).sum())
        total_pixels = result.target_width * result.target_height
        percent = (black_pixels / total_pixels * 100) if total_pixels else 0
        crop_text = "без ручной обрезки" if self.crop_box is None else f"обрезка {self.crop_box[2]-self.crop_box[0]} × {self.crop_box[3]-self.crop_box[1]} px"
        self.stats_var.set(
            f"Холст {width} × {height} px; исходник {self.original_image.width} × {self.original_image.height} px; "
            f"режим: {self.fit_mode_var.get()}; {crop_text}; чёрных пикселей в маске: {percent:.1f}%."
        )
        self.status_var.set("Обработка обновлена. Изображения можно сохранить; построение контуров будет на следующем этапе.")

    def _save_grayscale(self) -> None:
        if self.result is None:
            messagebox.showinfo("Нет результата", "Сначала загрузите изображение.", parent=self.root)
            return
        default_name = f"{self.source_path.stem if self.source_path else 'image'}_grayscale.png"
        path = filedialog.asksaveasfilename(parent=self.root, title="Сохранить обработанное серое изображение",
                                            initialdir=str(APP_DIR), initialfile=default_name,
                                            defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            self.result.grayscale.save(path)
            self.status_var.set(f"Сохранено серое изображение: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)

    def _save_mask(self) -> None:
        if self.result is None:
            messagebox.showinfo("Нет результата", "Сначала загрузите изображение.", parent=self.root)
            return
        default_name = f"{self.source_path.stem if self.source_path else 'image'}_mask.png"
        path = filedialog.asksaveasfilename(parent=self.root, title="Сохранить бинарную маску",
                                            initialdir=str(APP_DIR), initialfile=default_name,
                                            defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            self.result.binary_mask.save(path)
            self.status_var.set(f"Сохранена бинарная маска: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)

    def _save_bundle(self) -> None:
        if self.result is None or self.original_image is None:
            messagebox.showinfo("Нет результата", "Сначала загрузите изображение.", parent=self.root)
            return
        directory = filedialog.askdirectory(parent=self.root, title="Выберите папку для комплекта результатов",
                                            initialdir=str(APP_DIR), mustexist=False)
        if not directory:
            return
        output_dir = Path(directory)
        stem = self.source_path.stem if self.source_path else "image"
        try:
            color_path = output_dir / f"{stem}_prepared_color.png"
            gray_path = output_dir / f"{stem}_grayscale.png"
            mask_path = output_dir / f"{stem}_binary_mask.png"
            metadata_path = output_dir / f"{stem}_processing_result.json"
            self.result.prepared_color.save(color_path)
            self.result.grayscale.save(gray_path)
            self.result.binary_mask.save(mask_path)
            settings = self.result.settings
            metadata = {
                "schema_version": 1,
                "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
                "source_file": str(self.source_path) if self.source_path else None,
                "source_size": {"width": self.original_image.width, "height": self.original_image.height},
                "canvas": {"width": self.result.target_width, "height": self.result.target_height},
                "coordinate_system": "local_canvas_pixels",
                "fit_mode": self.result.fit_mode,
                "crop_box_original_pixels": list(self.crop_box) if self.crop_box else None,
                "settings": {
                    "brightness": settings.brightness,
                    "contrast": settings.contrast,
                    "denoise_level": settings.denoise_level,
                    "threshold_mode": settings.threshold_mode,
                    "requested_threshold": settings.threshold,
                    "threshold_used": self.result.threshold_used,
                },
                "binary_mask_convention": "black=dark_foreground_white=background",
                "outputs": {
                    "prepared_color": color_path.name,
                    "grayscale": gray_path.name,
                    "binary_mask": mask_path.name,
                },
                "note": "This stage prepares images only. No DrawingPlan has been created and no mouse input was sent.",
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status_var.set(f"Комплект сохранён в: {output_dir}")
            messagebox.showinfo("Сохранение завершено", f"Сохранены цветное, серое и бинарное изображения, а также JSON с настройками.\n\n{output_dir}", parent=self.root)
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)

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
    ImageProcessingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
