from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

import numpy as np
from PIL import Image, ImageOps, ImageTk

from palette_profiles import PaletteProfileError, load_palette_profile
from palette_quantization import (
    PaletteQuantizationError,
    PaletteQuantizationResult,
    quantize_image_to_palette,
    merge_rare_palette_colors,
    remove_edge_connected_background,
    remove_white_palette_pixels,
)


class _PreviewPanel(ttk.LabelFrame):
    def __init__(self, parent: tk.Widget, title: str):
        super().__init__(parent, text=title, padding=5)
        # Keep each preview a predictable height. The enclosing tab is vertically
        # scrollable, so these panels never consume all remaining space and hide
        # the report/table below them on shorter screens.
        self.canvas = tk.Canvas(self, background="#242424", highlightthickness=0, height=220)
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
            self.canvas.create_text(width / 2, height / 2, text="Изображение не выбрано", fill="#dddddd")
            return
        source = self.image.convert("RGBA")
        scale = min((width - 12) / max(1, source.width), (height - 12) / max(1, source.height))
        scaled_size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
        if scaled_size != source.size:
            source = source.resize(scaled_size, Image.Resampling.NEAREST if self.image.size[0] <= 1000 and self.image.size[1] <= 1000 else Image.Resampling.LANCZOS)
        # Checkerboard makes transparent areas visible in the preview.
        checker = Image.new("RGB", source.size, "#f0f0f0")
        from PIL import ImageDraw
        draw = ImageDraw.Draw(checker)
        tile = max(4, min(12, min(source.size) // 12 if min(source.size) >= 12 else 4))
        for y in range(0, source.height, tile):
            for x in range(0, source.width, tile):
                if ((x // tile) + (y // tile)) % 2:
                    draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill="#bdbdbd")
        checker.paste(source.convert("RGB"), mask=source.getchannel("A"))
        self.photo = ImageTk.PhotoImage(checker)
        self.canvas.create_image(width / 2, height / 2, image=self.photo, anchor="center")


class PaletteQuantizationTab:
    """Stage 18: convert an image to a saved browser palette for color planning."""

    def __init__(
        self,
        root: tk.Misc,
        parent: tk.Widget,
        profile_dir: str | Path,
        output_dir: str | Path,
        get_prepared_image: Callable[[], Image.Image | None] | None = None,
    ):
        self.root = root
        self.parent = parent
        self.profile_dir = Path(profile_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.get_prepared_image = get_prepared_image
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.profile_paths: dict[str, Path] = {}
        self.palette_profile: dict | None = None
        self.palette_path: Path | None = None
        self.source_path: Path | None = None
        self.source_image: Image.Image | None = None
        self.result: PaletteQuantizationResult | None = None
        self.expected_canvas_size: tuple[int, int] | None = None

        # Put the whole workflow into a vertical scrolling surface. The previous
        # fixed-height layout could clip the report and used-color table on screens
        # with limited vertical resolution.
        scroll_host = ttk.Frame(parent)
        scroll_host.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(scroll_host, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(scroll_host, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        outer = ttk.Frame(self.scroll_canvas, padding=10)
        self.scroll_content = outer
        self._scroll_window = self.scroll_canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", self._update_scroll_region)
        self.scroll_canvas.bind("<Configure>", self._resize_scroll_content)
        # Mouse wheel is handled only when the pointer is inside this tab. Other
        # tabs in the unified app keep their own scrolling behaviour.
        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_mousewheel_linux, add="+")
        self.root.bind_all("<Button-5>", self._on_mousewheel_linux, add="+")
        ttk.Label(outer, text="Этап 18 — преобразование изображения в палитру", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Каждый видимый пиксель сопоставляется с ближайшим цветом сохранённого профиля по CIEDE2000. "
                  "Размер изображения и положение деталей сохраняются; сглаживание, дизеринг и удаление пикселей не применяются."),
            wraplength=1100,
        ).pack(anchor="w", pady=(3, 9))

        image_toolbar = ttk.LabelFrame(outer, text="Изображение", padding=7)
        image_toolbar.pack(fill="x", pady=(0, 7))
        ttk.Button(image_toolbar, text="Открыть изображение…", command=self.open_image_dialog).pack(side="left")
        ttk.Button(image_toolbar, text="Использовать подготовленное изображение", command=self.use_prepared_image).pack(side="left", padx=(6, 0))
        self.image_name_var = tk.StringVar(value="Изображение не выбрано")
        ttk.Label(image_toolbar, textvariable=self.image_name_var).pack(side="left", padx=(10, 0), fill="x", expand=True)

        palette_toolbar = ttk.LabelFrame(outer, text="Профиль палитры", padding=7)
        palette_toolbar.pack(fill="x", pady=(0, 7))
        ttk.Label(palette_toolbar, text="Сохранённый профиль:").pack(side="left")
        self.profile_choice_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(palette_toolbar, textvariable=self.profile_choice_var, state="readonly", width=44)
        self.profile_combo.pack(side="left", padx=(6, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)
        ttk.Button(palette_toolbar, text="Обновить список", command=self.refresh_profiles).pack(side="left")
        ttk.Button(palette_toolbar, text="Загрузить файл…", command=self.load_profile_file_dialog).pack(side="left", padx=(6, 0))
        ttk.Button(palette_toolbar, text="Преобразовать", command=self.quantize).pack(side="left", padx=(14, 0))

        self.palette_info_var = tk.StringVar(value="Профиль палитры не загружен.")
        ttk.Label(outer, textvariable=self.palette_info_var).pack(anchor="w", pady=(0, 6))

        background_frame = ttk.LabelFrame(outer, text="Фон изображения", padding=7)
        background_frame.pack(fill="x", pady=(0, 7))
        self.background_mode_var = tk.StringVar(value="preserve")
        # Kept as a compatibility variable for existing automation/tests from Stage 20.
        # The visible UI now presents mutually exclusive, explicit background modes.
        self.remove_white_background_var = tk.BooleanVar(value=False)
        background_modes = ttk.Frame(background_frame)
        background_modes.pack(fill="x", anchor="w")
        for row, (mode, label) in enumerate((
            ("preserve", "Не удалять белый цвет — сохранить прежнее поведение"),
            ("edge", "Удалять белый/почти белый фон только по краям; внутренние белые детали сохранять"),
            ("all_white", "Удалять белый цвет везде, включая белые детали внутри фигуры"),
            ("auto_white_30", "Удалять белый цвет везде, только если после преобразования он занимает больше 30% видимых пикселей"),
        )):
            ttk.Radiobutton(
                background_modes,
                text=label,
                value=mode,
                variable=self.background_mode_var,
                command=lambda selected=mode: self._set_background_mode(selected),
            ).grid(row=row, column=0, sticky="w", pady=1)
        background_options = ttk.Frame(background_frame)
        background_options.pack(fill="x", pady=(4, 0))
        ttk.Label(background_options, text="Допуск для распознавания белого (каждый RGB-компонент):").pack(side="left")
        self.background_tolerance_var = tk.IntVar(value=24)
        self.background_tolerance_spinbox = ttk.Spinbox(
            background_options,
            from_=0,
            to=120,
            increment=1,
            width=5,
            textvariable=self.background_tolerance_var,
            state="disabled",
        )
        self.background_tolerance_spinbox.pack(side="left", padx=(5, 9))
        ttk.Label(
            background_frame,
            text="Для удаления белого цвета анализируются цвета палитры после преобразования. Порог — строго больше 30% видимых пикселей.",
            wraplength=1100,
            justify="left",
        ).pack(fill="x", anchor="w", pady=(4, 0))

        optimization_frame = ttk.LabelFrame(outer, text="Уменьшение цветового шума", padding=7)
        optimization_frame.pack(fill="x", pady=(0, 7))
        self.merge_rare_colors_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            optimization_frame,
            text="Объединять редкие цвета с похожими более частыми цветами",
            variable=self.merge_rare_colors_var,
            command=self._toggle_rare_color_controls,
        ).grid(row=0, column=0, columnspan=6, sticky="w")
        ttk.Label(optimization_frame, text="Редкий цвет: пикселей не больше").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.rare_color_min_pixels_var = tk.IntVar(value=20)
        self.rare_color_min_pixels_spinbox = ttk.Spinbox(
            optimization_frame, from_=0, to=1_000_000, increment=1, width=8,
            textvariable=self.rare_color_min_pixels_var,
        )
        self.rare_color_min_pixels_spinbox.grid(row=1, column=1, sticky="w", padx=(5, 12), pady=(4, 0))
        ttk.Label(optimization_frame, text="или доля меньше (%)").grid(row=1, column=2, sticky="w", pady=(4, 0))
        self.rare_color_min_percentage_var = tk.DoubleVar(value=0.05)
        self.rare_color_min_percentage_spinbox = ttk.Spinbox(
            optimization_frame, from_=0.0, to=100.0, increment=0.01, format="%.2f", width=8,
            textvariable=self.rare_color_min_percentage_var,
        )
        self.rare_color_min_percentage_spinbox.grid(row=1, column=3, sticky="w", padx=(5, 12), pady=(4, 0))
        ttk.Label(optimization_frame, text="Максимальное отличие ΔE00").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.rare_color_max_delta_var = tk.DoubleVar(value=8.0)
        self.rare_color_max_delta_spinbox = ttk.Spinbox(
            optimization_frame, from_=0.0, to=100.0, increment=0.5, format="%.1f", width=7,
            textvariable=self.rare_color_max_delta_var,
        )
        self.rare_color_max_delta_spinbox.grid(row=2, column=1, sticky="w", padx=(5, 0), pady=(4, 0))
        ttk.Label(
            optimization_frame,
            text=("Редкий цвет заменяется только на цвет, который используется минимум в 2 раза чаще "
                  "и достаточно похож (по умолчанию ΔE00 ≤ 8). Если похожего частого цвета нет, редкий цвет сохраняется. "
                  "Исходник не изменяется; ниже будет отчёт о заменах и оценке сокращения штрихов."),
            wraplength=1100,
            justify="left",
        ).grid(row=3, column=0, columnspan=6, sticky="w", pady=(4, 0))
        self._toggle_rare_color_controls()

        previews = ttk.Panedwindow(outer, orient="horizontal", height=238)
        previews.pack(fill="x", expand=False)
        self.source_preview = _PreviewPanel(previews, "Исходное изображение")
        self.output_preview = _PreviewPanel(previews, "Изображение в цветах палитры")
        self.difference_preview = _PreviewPanel(previews, "Карта изменений RGB")
        previews.add(self.source_preview, weight=1)
        previews.add(self.output_preview, weight=1)
        previews.add(self.difference_preview, weight=1)

        bottom = ttk.Panedwindow(outer, orient="horizontal", height=245)
        bottom.pack(fill="x", expand=False, pady=(8, 0))
        stats_frame = ttk.LabelFrame(bottom, text="Отчёт преобразования", padding=7)
        colors_frame = ttk.LabelFrame(bottom, text="Использованные цвета", padding=7)
        bottom.add(stats_frame, weight=2)
        bottom.add(colors_frame, weight=3)
        self.stats_var = tk.StringVar(value="Выберите изображение и профиль палитры.")
        ttk.Label(stats_frame, textvariable=self.stats_var, justify="left", wraplength=530).pack(anchor="w", fill="x")
        actions = ttk.Frame(stats_frame)
        actions.pack(anchor="w", pady=(7, 0))
        ttk.Button(actions, text="Сохранить PNG…", command=self.save_image_dialog).pack(side="left")
        ttk.Button(actions, text="Сохранить отчёт JSON…", command=self.save_report_dialog).pack(side="left", padx=(6, 0))

        table_wrap = ttk.Frame(colors_frame)
        table_wrap.pack(fill="both", expand=True)
        columns = ("hex", "name", "pixels", "percent")
        self.colors_table = ttk.Treeview(table_wrap, columns=columns, show="headings", height=9)
        for column, title, width in (
            ("hex", "HEX", 90), ("name", "Название", 160), ("pixels", "Пиксели", 90), ("percent", "% видимых", 85),
        ):
            self.colors_table.heading(column, text=title)
            self.colors_table.column(column, width=width, anchor="w" if column in ("hex", "name") else "e")
        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.colors_table.yview)
        self.colors_table.configure(yscrollcommand=scrollbar.set)
        self.colors_table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.status_var = tk.StringVar(value="Преобразуйте изображение, затем передайте его на вкладку 5 для построения цветного плана.")
        ttk.Label(outer, textvariable=self.status_var, wraplength=1300).pack(anchor="w", pady=(7, 0))
        self.refresh_profiles()

    def _update_scroll_region(self, _event=None) -> None:
        try:
            self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        except tk.TclError:
            pass

    def _resize_scroll_content(self, event) -> None:
        try:
            self.scroll_canvas.itemconfigure(self._scroll_window, width=max(1, event.width))
            self._update_scroll_region()
        except tk.TclError:
            pass

    def _widget_is_in_scroll_content(self, widget: tk.Widget) -> bool:
        current = widget
        while current is not None:
            if current is self.scroll_content or current is self.scroll_canvas:
                return True
            current = getattr(current, "master", None)
        return False

    def _on_mousewheel(self, event):
        if not self._widget_is_in_scroll_content(event.widget):
            return
        delta = getattr(event, "delta", 0)
        if delta:
            units = -1 if delta > 0 else 1
            # Windows emits multiples of 120, trackpads may emit smaller deltas.
            if abs(delta) >= 120:
                units = -int(delta / 120)
            self.scroll_canvas.yview_scroll(units, "units")
        return "break"

    def _on_mousewheel_linux(self, event):
        if not self._widget_is_in_scroll_content(event.widget):
            return
        self.scroll_canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
        return "break"

    def set_target_canvas_size(self, width: int, height: int) -> None:
        """Set the target's pixel size and invalidate any stale conversion."""
        width, height = int(width), int(height)
        if width <= 0 or height <= 0 or width * height > 40_000_000:
            raise ValueError("Размер целевого холста должен быть положительным и не превышать 40 млн пикселей.")
        new_size = (width, height)
        if self.expected_canvas_size == new_size and self.result is None:
            return
        self.expected_canvas_size = new_size
        self.result = None
        self.output_preview.set_image(None)
        self.difference_preview.set_image(None)
        for row in self.colors_table.get_children():
            self.colors_table.delete(row)
        if self.source_image is not None:
            self.stats_var.set(
                f"Размер целевого холста изменён на {width} × {height}. "
                "Нажмите «Использовать подготовленное изображение», затем «Преобразовать» заново."
            )
            self.status_var.set(
                "Предыдущий результат сброшен: требуется повторно передать подготовленное изображение "
                "и выполнить преобразование для текущей области рисования."
            )
        else:
            self.stats_var.set(f"Целевой холст: {width} × {height}. Выберите подготовленное изображение и палитру.")

    def _set_background_mode(self, mode: str) -> None:
        self.background_mode_var.set(mode)
        self.remove_white_background_var.set(mode == "edge")
        self._toggle_background_tolerance()

    def _toggle_background_tolerance(self) -> None:
        # Backward compatibility: older tests/automation set the old checkbox
        # variable directly. Interpret that as the original edge-connected mode.
        if self.remove_white_background_var.get() and self.background_mode_var.get() == "preserve":
            self.background_mode_var.set("edge")
        mode = self.background_mode_var.get()
        self.remove_white_background_var.set(mode == "edge")
        state = "disabled" if mode == "preserve" else "normal"
        self.background_tolerance_spinbox.configure(state=state)

    def _toggle_rare_color_controls(self) -> None:
        state = "normal" if self.merge_rare_colors_var.get() else "disabled"
        for widget in (
            self.rare_color_min_pixels_spinbox,
            self.rare_color_min_percentage_spinbox,
            self.rare_color_max_delta_spinbox,
        ):
            widget.configure(state=state)

    def refresh_profiles(self) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        paths = sorted((p for p in self.profile_dir.glob("*.json") if p.is_file()), key=lambda p: p.name.casefold())
        choices: dict[str, Path] = {}
        for path in paths:
            label = path.name
            if label in choices:
                label = f"{path.stem} ({path.parent.name})"
            choices[label] = path
        self.profile_paths = choices
        labels = list(choices)
        self.profile_combo.configure(values=labels)
        if self.profile_choice_var.get() not in choices:
            self.profile_choice_var.set(labels[0] if labels else "")
        self.status_var.set(f"Найдено профилей палитры: {len(labels)}.")

    def _on_profile_selected(self, _event=None) -> None:
        # Load immediately on a deliberate selection so Convert can never use a stale profile.
        if self.profile_choice_var.get():
            self.load_selected_profile()

    def _read_profile(self, path: Path) -> dict:
        profile = load_palette_profile(path)
        colors = profile.get("colors", [])
        if not colors:
            raise PaletteQuantizationError("В профиле нет цветов.")
        return profile

    def load_selected_profile(self) -> bool:
        path = self.profile_paths.get(self.profile_choice_var.get())
        if path is None:
            messagebox.showwarning("Профиль не выбран", "Выберите сохранённый профиль палитры.", parent=self.root)
            return False
        try:
            profile = self._read_profile(path)
        except (OSError, ValueError, TypeError, PaletteProfileError, PaletteQuantizationError) as exc:
            messagebox.showerror("Не удалось загрузить палитру", str(exc), parent=self.root)
            return False
        self.palette_profile = profile
        self.palette_path = path
        self.palette_info_var.set(self._format_palette_info(profile, path))
        self.status_var.set(f"Загружен профиль «{profile['profile_name']}»: {len(profile['colors'])} цветов.")
        return True

    def load_profile_file_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Загрузить профиль палитры",
            initialdir=str(self.profile_dir),
            filetypes=(("Профили и палитры JSON", "*.json"), ("Все файлы", "*.*")),
        )
        if not selected:
            return
        path = Path(selected).resolve()
        try:
            profile = self._read_profile(path)
        except (OSError, ValueError, TypeError, PaletteProfileError, PaletteQuantizationError) as exc:
            messagebox.showerror("Не удалось загрузить палитру", str(exc), parent=self.root)
            return
        self.palette_profile = profile
        self.palette_path = path
        # Also show selected external profiles as the active profile, without copying or changing them.
        self.palette_info_var.set(self._format_palette_info(profile, path))
        self.status_var.set(f"Загружен профиль «{profile['profile_name']}»: {len(profile['colors'])} цветов.")

    @staticmethod
    def _format_palette_info(profile: dict, path: Path | None) -> str:
        colors = profile.get("colors", [])
        confirmed = sum(1 for item in colors if item.get("status") in {"confirmed", "corrected"})
        source = path.name if path else "без файла"
        return f"Профиль: {profile.get('profile_name', 'Без имени')} · цветов: {len(colors)} · подтверждено/исправлено: {confirmed} · файл: {source}"

    def open_image_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть изображение для преобразования",
            filetypes=(("Изображения", "*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff"), ("Все файлы", "*.*")),
        )
        if not selected:
            return
        try:
            with Image.open(selected) as opened:
                image = ImageOps.exif_transpose(opened).copy()
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            messagebox.showerror("Не удалось открыть изображение", str(exc), parent=self.root)
            return
        self._set_source_image(image, Path(selected).resolve(), Path(selected).name)

    def use_prepared_image(self) -> None:
        if self.get_prepared_image is None:
            messagebox.showinfo("Нет подготовленного изображения", "Загрузка изображения из этапа подготовки недоступна.", parent=self.root)
            return
        image = self.get_prepared_image()
        if image is None:
            messagebox.showwarning(
                "Нет подготовленного изображения",
                "Сначала загрузите изображение и выполните обработку на вкладке «1. Подготовка изображения».",
                parent=self.root,
            )
            return
        self._set_source_image(image.copy(), None, "Подготовленное изображение с вкладки 1")

    def _set_source_image(self, image: Image.Image, path: Path | None, display_name: str) -> None:
        if image.width * image.height > 40_000_000:
            messagebox.showerror("Изображение слишком большое", "Допустимо не более 40 миллионов пикселей.", parent=self.root)
            return
        self.source_image = image.copy()
        self.source_path = path
        self.result = None
        self.image_name_var.set(f"{display_name} · {image.width} × {image.height}")
        self.source_preview.set_image(image)
        self.output_preview.set_image(None)
        self.difference_preview.set_image(None)
        self.stats_var.set("Изображение загружено. Загрузите профиль палитры и нажмите «Преобразовать».")
        for row in self.colors_table.get_children():
            self.colors_table.delete(row)
        self.status_var.set("Исходное изображение готово к преобразованию.")

    def quantize(self) -> None:
        if self.source_image is None:
            messagebox.showwarning("Нет изображения", "Сначала откройте изображение или используйте подготовленное.", parent=self.root)
            return
        if self.expected_canvas_size is not None and self.source_image.size != self.expected_canvas_size:
            expected = f"{self.expected_canvas_size[0]} × {self.expected_canvas_size[1]}"
            actual = f"{self.source_image.width} × {self.source_image.height}"
            messagebox.showwarning(
                "Размер изображения не совпадает с областью рисования",
                f"Текущий источник: {actual} px; выбранная область: {expected} px. "
                "Нажмите «Использовать подготовленное изображение» на вкладке 1, затем повторите преобразование.",
                parent=self.root,
            )
            self.status_var.set("Преобразование отменено: размер источника не совпадает с размером целевого холста.")
            return
        if self.palette_profile is None and not self.load_selected_profile():
            return
        assert self.palette_profile is not None
        mode = self.background_mode_var.get()
        try:
            tolerance = int(self.background_tolerance_var.get())
        except (tk.TclError, TypeError, ValueError) as exc:
            if mode != "preserve":
                messagebox.showerror("Некорректный допуск", "Допуск белого цвета должен быть целым числом от 0 до 120.", parent=self.root)
                return
            tolerance = 24
        if mode != "preserve" and not 0 <= tolerance <= 120:
            messagebox.showerror("Некорректный допуск", "Допуск белого цвета должен быть от 0 до 120.", parent=self.root)
            return

        quantization_source = self.source_image
        background_report: dict = {
            "enabled": False,
            "mode": "preserve_original_background",
            "method": "preserve_original_background",
            "removed_pixel_count": 0,
            "note": "Сохранён прежний режим: белый цвет обрабатывается как обычный цвет изображения.",
        }
        try:
            if mode == "edge":
                background_result = remove_edge_connected_background(
                    self.source_image,
                    background_rgb=(255, 255, 255),
                    tolerance=tolerance,
                )
                quantization_source = background_result.image
                background_report = {
                    "enabled": True,
                    "mode": "edge_connected_white_background",
                    **background_result.report,
                }

            result = quantize_image_to_palette(quantization_source, self.palette_profile)

            if mode == "all_white":
                result, background_report = remove_white_palette_pixels(
                    result,
                    self.palette_profile,
                    quantization_source,
                    tolerance=tolerance,
                )
            elif mode == "auto_white_30":
                result, background_report = remove_white_palette_pixels(
                    result,
                    self.palette_profile,
                    quantization_source,
                    tolerance=tolerance,
                    threshold_percentage=30.0,
                )
            elif mode == "preserve":
                background_report = {
                    "enabled": False,
                    "mode": "preserve_original_background",
                    "method": "preserve_original_background",
                    "removed_pixel_count": 0,
                    "note": "Сохранён прежний режим: белый цвет обрабатывается как обычный цвет изображения.",
                }

            rare_color_merge_report: dict = {
                "enabled": False,
                "method": "frequency_weighted_nearest_palette_color_ciede2000",
                "rare_color_count_merged": 0,
                "remapped_pixel_count": 0,
                "estimated_scanline_strokes_before": None,
                "estimated_scanline_strokes_after": None,
                "estimated_scanline_strokes_reduced": 0,
                "note": "Оптимизация редких цветов отключена.",
            }
            if self.merge_rare_colors_var.get():
                try:
                    min_pixels = int(self.rare_color_min_pixels_var.get())
                    min_percentage = float(self.rare_color_min_percentage_var.get())
                    max_delta = float(self.rare_color_max_delta_var.get())
                except (tk.TclError, TypeError, ValueError) as exc:
                    raise PaletteQuantizationError(
                        "Параметры оптимизации редких цветов должны быть корректными числами."
                    ) from exc
                result, rare_color_merge_report = merge_rare_palette_colors(
                    result,
                    self.palette_profile,
                    min_pixel_count=min_pixels,
                    min_percentage=min_percentage,
                    max_delta_e=max_delta,
                    min_frequency_ratio=2.0,
                )
        except (PaletteQuantizationError, ValueError, TypeError, MemoryError) as exc:
            messagebox.showerror("Преобразование не выполнено", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка преобразования: {exc}")
            return

        result.report["background_removal"] = background_report
        result.report["rare_color_merge"] = rare_color_merge_report
        result.report["palette_profile"] = {
            "name": self.palette_profile.get("profile_name", "Без имени"),
            "file": self.palette_path.name if self.palette_path else None,
            "profile_schema_version": self.palette_profile.get("profile_schema_version"),
        }
        if self.source_path:
            result.report["source_file"] = self.source_path.name
        self.result = result
        self.output_preview.set_image(result.image)
        self.difference_preview.set_image(self._difference_preview(self.source_image, result.image))
        report = result.report
        white_percentage = background_report.get("white_percentage_of_visible_pixels")
        white_percentage_text = f"Доля белого до решения: {white_percentage:.2f}%\n" if white_percentage is not None else ""
        merge_strokes_before = rare_color_merge_report.get("estimated_scanline_strokes_before")
        merge_strokes_after = rare_color_merge_report.get("estimated_scanline_strokes_after")
        stroke_line = (
            f"Оценка штрихов: {merge_strokes_before:,} → {merge_strokes_after:,} "
            f"(−{rare_color_merge_report.get('estimated_scanline_strokes_reduced', 0):,})\n"
            if isinstance(merge_strokes_before, int) and isinstance(merge_strokes_after, int)
            else ""
        )
        self.stats_var.set(
            f"Размер: {report['source_size']['width']} × {report['source_size']['height']}\n"
            f"Цветов в палитре: {report['palette_color_count']}; использовано после оптимизации: {report['used_palette_color_count']}\n"
            f"Изменено видимых пикселей при первичном преобразовании: {report['changed_pixel_count']:,} ({report['changed_pixel_percentage']:.2f}%)\n"
            f"Средняя ΔE00 до объединения редких цветов: {report['mean_delta_e_2000']:.3f}; "
            f"95-й процентиль: {report['p95_delta_e_2000']:.3f}; максимум: {report['max_delta_e_2000']:.3f}\n"
            f"Точные совпадения: {report['exact_color_pixel_count']:,}; прозрачные пиксели: {report['transparent_pixel_count']:,}\n"
            f"Редкие цвета объединены: {rare_color_merge_report.get('rare_color_count_merged', 0)}; "
            f"переназначено пикселей: {rare_color_merge_report.get('remapped_pixel_count', 0):,}; "
            f"среднее отличие объединения ΔE00: {rare_color_merge_report.get('mean_delta_e_2000_for_merged_colors', 0):.3f}\n"
            f"{stroke_line}{white_percentage_text}Удалено пикселей фона/белого цвета: {background_report.get('removed_pixel_count', 0):,}"
        )
        self._populate_color_table(report)

        if mode == "edge":
            self.status_var.set(
                f"Преобразование завершено. Белый фон по краям сделан прозрачным: "
                f"{background_report.get('removed_pixel_count', 0):,} пикс. Внутренний белый цвет сохраняется."
            )
        elif mode == "all_white":
            self.status_var.set(
                f"Преобразование завершено. Удалён белый цвет по всему изображению: "
                f"{background_report.get('removed_pixel_count', 0):,} пикс. Все такие участки теперь прозрачны."
            )
        elif mode == "auto_white_30":
            percent = float(background_report.get("white_percentage_of_visible_pixels", 0.0))
            if background_report.get("applied"):
                self.status_var.set(
                    f"Белый цвет занимал {percent:.2f}% видимых пикселей (>30%). "
                    f"Удалено {background_report.get('removed_pixel_count', 0):,} белых пикселей."
                )
            else:
                self.status_var.set(
                    f"Белый цвет занимал {percent:.2f}% видимых пикселей (не больше 30%). "
                    "Белый цвет оставлен."
                )
        else:
            self.status_var.set("Преобразование завершено. Белый цвет и фон сохранены как раньше.")

        if rare_color_merge_report.get("enabled"):
            merged_colors = int(rare_color_merge_report.get("rare_color_count_merged", 0))
            remapped_pixels = int(rare_color_merge_report.get("remapped_pixel_count", 0))
            reduced_strokes = int(rare_color_merge_report.get("estimated_scanline_strokes_reduced", 0))
            self.status_var.set(
                f"{self.status_var.get()} Оптимизация: объединено редких цветов — {merged_colors}, "
                f"переназначено пикселей — {remapped_pixels:,}, оценочное сокращение штрихов — {reduced_strokes:,}."
            )

    @staticmethod
    def _difference_preview(original: Image.Image, converted: Image.Image) -> Image.Image:
        original_rgba = np.asarray(original.convert("RGBA"), dtype=np.int16)
        converted_rgba = np.asarray(converted.convert("RGBA"), dtype=np.int16)
        difference = np.max(np.abs(original_rgba[..., :3] - converted_rgba[..., :3]), axis=2).astype(np.uint8)
        alpha_changed = original_rgba[..., 3] != converted_rgba[..., 3]
        # Scale RGB changes for the view only; transparent-background removal is
        # shown in magenta so the change remains visible even if RGB values match.
        visible = (difference > 0) & (original_rgba[..., 3] > 0) & (converted_rgba[..., 3] > 0)
        result = np.full((*difference.shape, 3), 35, dtype=np.uint8)
        intensity = np.clip(difference.astype(np.float32) * 2.0, 0, 255).astype(np.uint8)
        result[..., 0] = np.where(visible, intensity, result[..., 0])
        result[..., 1] = np.where(visible, 48, result[..., 1])
        result[..., 2] = np.where(visible, 48, result[..., 2])
        result[alpha_changed] = (255, 0, 255)
        return Image.fromarray(result, mode="RGB")

    def _populate_color_table(self, report: dict) -> None:
        for row in self.colors_table.get_children():
            self.colors_table.delete(row)
        for item in sorted(report["used_colors"], key=lambda item: (-item["pixel_count"], item["index"])):
            self.colors_table.insert("", "end", values=(item["hex"], item["name"], f"{item['pixel_count']:,}", f"{item['percentage_visible']:.2f}%"))

    def save_image_dialog(self) -> None:
        if self.result is None:
            messagebox.showinfo("Нет результата", "Сначала выполните преобразование изображения.", parent=self.root)
            return
        initial = "image_palette.png"
        if self.source_path:
            initial = f"{self.source_path.stem}_palette.png"
        selected = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить изображение в цветах палитры", initialdir=str(self.output_dir),
            initialfile=initial, defaultextension=".png", filetypes=(("PNG", "*.png"),),
        )
        if not selected:
            return
        try:
            destination = Path(selected)
            destination.parent.mkdir(parents=True, exist_ok=True)
            self.result.image.save(destination, format="PNG")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Не удалось сохранить PNG", str(exc), parent=self.root)
            return
        self.status_var.set(f"Изображение сохранено: {selected}")

    def save_report_dialog(self) -> None:
        if self.result is None:
            messagebox.showinfo("Нет отчёта", "Сначала выполните преобразование изображения.", parent=self.root)
            return
        initial = "palette_quantization_report.json"
        if self.source_path:
            initial = f"{self.source_path.stem}_palette_report.json"
        selected = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить отчёт преобразования", initialdir=str(self.output_dir),
            initialfile=initial, defaultextension=".json", filetypes=(("JSON", "*.json"),),
        )
        if not selected:
            return
        try:
            destination = Path(selected)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.stem}.tmp")
            temporary.write_text(json.dumps(self.result.report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(destination)
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Не удалось сохранить отчёт", str(exc), parent=self.root)
            return
        self.status_var.set(f"Отчёт сохранён: {selected}")
