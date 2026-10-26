from __future__ import annotations

import io
import json
import math
import os
import sys
import tempfile
import tkinter as tk
import uuid
from datetime import datetime
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from PIL import Image, ImageTk

from image_processing import ProcessingResult, ProcessingSettings, load_rgb_image, process_image
from stage8_optimizer import TimingProfile, analyze_plan, build_scanline_plan, render_plan_preview, save_plan
from stage9_quality import analyze_quality, save_report
from autodraw_project import ProjectFormatError, create_project, open_project, project_summary
from profile_manager import (
    CalibrationSettings, ProfileStore, ProfileValidationError, ScreenArea, WorkspaceProfile,
)

_DEFAULT_APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
APP_DIR = Path(os.environ.get("AUTODRAW_APP_DIR", _DEFAULT_APP_DIR)).resolve()
DATA_DIR = Path(os.environ.get("AUTODRAW_DATA_DIR", APP_DIR)).resolve()
PROFILES_DIR = DATA_DIR / "profiles"
PROJECTS_DIR = Path(os.environ.get("AUTODRAW_PROJECTS_DIR", DATA_DIR / "projects")).resolve()
PROFILE_STORE_PATH = Path(os.environ.get("AUTODRAW_PROFILE_STORE_PATH", PROFILES_DIR / "profiles.json")).resolve()
IMAGE_TYPES = [
    ("Изображения", "*.png *.jpg *.jpeg *.bmp *.webp *.tif *.tiff"),
    ("Все файлы", "*.*"),
]
FIT_LABELS = {
    "Вписать с белыми полями": "contain",
    "Заполнить холст с обрезкой краёв": "cover",
    "Растянуть до размера холста": "stretch",
}
FIT_LABELS_BY_VALUE = {value: label for label, value in FIT_LABELS.items()}
THRESHOLD_LABELS = {"Автоматический порог (Otsu)": "otsu", "Ручной порог": "manual"}
THRESHOLD_LABELS_BY_VALUE = {value: label for label, value in THRESHOLD_LABELS.items()}


class ImagePreview(ttk.Frame):
    """Fit-to-window image preview with optional drag-to-crop selection."""

    def __init__(self, parent, title: str, *, selectable: bool = False, on_selection=None):
        super().__init__(parent)
        self.image: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None
        self.selectable = selectable
        self.on_selection = on_selection
        self.selection: tuple[int, int, int, int] | None = None
        self._display_rect: tuple[float, float, float, float] | None = None
        self._drag_start: tuple[float, float] | None = None
        self._drag_current: tuple[float, float] | None = None

        ttk.Label(self, text=title, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.canvas = tk.Canvas(self, background="#282828", highlightthickness=1, highlightbackground="#b0b0b0")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        if selectable:
            self.canvas.bind("<ButtonPress-1>", self._on_press)
            self.canvas.bind("<B1-Motion>", self._on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def set_image(self, image: Image.Image | None) -> None:
        self.image = image.copy() if image is not None else None
        self._draw()

    def set_selection(self, selection: tuple[int, int, int, int] | None) -> None:
        self.selection = selection
        self._drag_start = None
        self._drag_current = None
        self._draw()

    def _draw(self) -> None:
        self.canvas.delete("all")
        self.tk_image = None
        self._display_rect = None
        width = max(2, self.canvas.winfo_width())
        height = max(2, self.canvas.winfo_height())
        if self.image is None:
            self.canvas.create_text(width / 2, height / 2, text="Изображение не загружено", fill="#dddddd")
            return
        image_width, image_height = self.image.size
        available_width = max(1, width - 16)
        available_height = max(1, height - 16)
        scale = min(available_width / image_width, available_height / image_height)
        preview_width = max(1, round(image_width * scale))
        preview_height = max(1, round(image_height * scale))
        x0 = (width - preview_width) / 2
        y0 = (height - preview_height) / 2
        resized = self.image.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(x0, y0, image=self.tk_image, anchor="nw")
        self._display_rect = (x0, y0, x0 + preview_width, y0 + preview_height)

        if self.selectable and self.selection is not None:
            x1, y1, x2, y2 = self.selection
            sx = preview_width / image_width
            sy = preview_height / image_height
            self.canvas.create_rectangle(
                x0 + x1 * sx, y0 + y1 * sy, x0 + x2 * sx, y0 + y2 * sy,
                outline="#ff9f1c", width=2,
            )
        if self.selectable and self._drag_start and self._drag_current:
            self.canvas.create_rectangle(*self._drag_start, *self._drag_current, outline="#4dabf7", width=2, dash=(4, 2))

    def _canvas_to_image(self, x: float, y: float) -> tuple[int, int] | None:
        if self.image is None or self._display_rect is None:
            return None
        x0, y0, x1, y1 = self._display_rect
        if x < x0 or y < y0 or x > x1 or y > y1:
            return None
        ix = round((x - x0) * self.image.width / max(1.0, x1 - x0))
        iy = round((y - y0) * self.image.height / max(1.0, y1 - y0))
        return min(self.image.width, max(0, ix)), min(self.image.height, max(0, iy))

    def _on_press(self, event) -> None:
        point = self._canvas_to_image(event.x, event.y)
        if point is None:
            self._drag_start = None
            self._drag_current = None
            return
        self._drag_start = (event.x, event.y)
        self._drag_current = (event.x, event.y)
        self._draw()

    def _on_drag(self, event) -> None:
        if self._drag_start is None:
            return
        point = self._canvas_to_image(event.x, event.y)
        if point is None and self._display_rect:
            x0, y0, x1, y1 = self._display_rect
            point = (int(min(max(event.x, x0), x1)), int(min(max(event.y, y0), y1)))
        if point is not None:
            self._drag_current = (event.x, event.y)
            self._draw()

    def _on_release(self, event) -> None:
        if self._drag_start is None or self.image is None:
            return
        start = self._canvas_to_image(*self._drag_start)
        end = self._canvas_to_image(event.x, event.y)
        if start is not None and end is not None:
            x1, x2 = sorted((start[0], end[0]))
            y1, y2 = sorted((start[1], end[1]))
            x2 = min(self.image.width, max(x1, x2))
            y2 = min(self.image.height, max(y1, y2))
            if x2 - x1 >= 2 and y2 - y1 >= 2:
                self.selection = (x1, y1, x2, y2)
                if self.on_selection:
                    self.on_selection(self.selection)
        self._drag_start = None
        self._drag_current = None
        self._draw()


class AutoDrawWorkbench:
    def __init__(
        self,
        root: tk.Tk,
        parent: tk.Widget | None = None,
        *,
        embedded: bool = False,
        on_select_canvas_area: Callable[[], None] | None = None,
    ):
        self.root = root
        self.container = parent if parent is not None else root
        self.embedded = embedded
        self.on_select_canvas_area = on_select_canvas_area
        self._cleaned_up = False
        if not embedded:
            root.title("AutoDraw — подготовка изображения")
            root.geometry("1420x940")
            root.minsize(1050, 720)

        self._temp = tempfile.TemporaryDirectory(prefix="autodraw_stage12_")
        self.workspace = Path(self._temp.name)
        self.source_path: Path | None = None
        self.source_filename: str | None = None
        self.source_image: Image.Image | None = None
        self.crop_box: tuple[int, int, int, int] | None = None
        self.result: ProcessingResult | None = None
        self.plan: dict[str, Any] | None = None
        self.quality_result = None
        self.current_project: Path | None = None
        self._pending_processing: str | None = None
        self._loading_project = False

        for directory in (PROFILES_DIR, PROJECTS_DIR, DATA_DIR / "results", DATA_DIR / "logs"):
            directory.mkdir(parents=True, exist_ok=True)
        self.profile_store = ProfileStore(PROFILE_STORE_PATH)
        self.profiles: list[WorkspaceProfile] = []
        self._profile_labels: dict[str, str] = {}
        self._selected_profile_id: str | None = None
        try:
            self.profiles = self.profile_store.load()
        except ProfileValidationError as exc:
            # Do not overwrite a damaged profile registry automatically; provide a safe in-memory default.
            self.profiles = [WorkspaceProfile.create_default()]
            self._profile_load_error = str(exc)
        else:
            self._profile_load_error = None

        self.width_var = tk.StringVar(value="646")
        self.height_var = tk.StringVar(value="323")
        self.fit_mode_var = tk.StringVar(value="Вписать с белыми полями")
        self.brightness_var = tk.IntVar(value=0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.denoise_var = tk.IntVar(value=0)
        self.threshold_mode_var = tk.StringVar(value="Автоматический порог (Otsu)")
        self.threshold_var = tk.IntVar(value=128)
        self.row_step_var = tk.StringVar(value="1")
        self.project_name_var = tk.StringVar(value="AutoDraw project")
        self.image_stats_var = tk.StringVar(value="Загрузите изображение, задайте холст и проверьте маску.")
        self.plan_stats_var = tk.StringVar(value="План ещё не создан.")
        self.quality_stats_var = tk.StringVar(value="Качество ещё не проверено.")
        self.status_var = tk.StringVar(value="Готово. Этот интерфейс подготавливает план, но не управляет мышью.")
        self.target_area_info_var = tk.StringVar(value="Область рисования ещё не выбрана. Выберите её здесь, чтобы размер изображения совпал с браузерным холстом.")

        self.profile_choice_var = tk.StringVar()
        self.profile_name_var = tk.StringVar(value="Основной")
        self.profile_canvas_width_var = tk.StringVar(value="646")
        self.profile_canvas_height_var = tk.StringVar(value="323")
        self.profile_fit_var = tk.StringVar(value="contain")
        self.profile_row_step_var = tk.StringVar(value="1")
        self.profile_brightness_var = tk.StringVar(value="0")
        self.profile_contrast_var = tk.StringVar(value="1.0")
        self.profile_denoise_var = tk.StringVar(value="0")
        self.profile_threshold_mode_var = tk.StringVar(value="otsu")
        self.profile_threshold_var = tk.StringVar(value="128")
        self.profile_area_x_var = tk.StringVar()
        self.profile_area_y_var = tk.StringVar()
        self.profile_area_width_var = tk.StringVar()
        self.profile_area_height_var = tk.StringVar()
        self.profile_screen_width_var = tk.StringVar()
        self.profile_screen_height_var = tk.StringVar()
        self.profile_point_step_var = tk.StringVar(value="2.0")
        self.profile_point_delay_var = tk.StringVar(value="10")
        self.profile_after_up_var = tk.StringVar(value="20")
        self.profile_before_down_var = tk.StringVar(value="20")
        self.profile_after_down_var = tk.StringVar(value="40")
        self.profile_end_hold_var = tk.StringVar(value="50")
        self.profile_countdown_var = tk.StringVar(value="5")

        self._build_ui()
        if not self.embedded:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.container, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="AutoDraw — единый процесс подготовки рисунка", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Изображение → бинарная маска → scanline-план → проверка качества. Готовый план можно передать во вкладку исполнения или сохранить в проект .autodraw."
                  if self.embedded else "Изображение → бинарная маска → scanline-план → проверка качества → проект .autodraw или JSON для этапа 6. Рисование мышью здесь не запускается."),
            wraplength=1360,
        ).pack(anchor="w", pady=(3, 8))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.image_tab = ttk.Frame(self.notebook, padding=8)
        self.plan_tab = ttk.Frame(self.notebook, padding=8)
        self.quality_tab = ttk.Frame(self.notebook, padding=8)
        self.project_tab = ttk.Frame(self.notebook, padding=8)
        self.profile_tab = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.image_tab, text="1. Изображение")
        self.notebook.add(self.plan_tab, text="2. Растровый план")
        self.notebook.add(self.quality_tab, text="3. Качество")
        self.notebook.add(self.project_tab, text="4. Проект и экспорт")
        self.notebook.add(self.profile_tab, text="5. Профили")

        self._build_image_tab()
        self._build_plan_tab()
        self._build_quality_tab()
        self._build_project_tab()
        self._build_profile_tab()
        ttk.Separator(outer).pack(fill="x", pady=(7, 4))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1360).pack(fill="x", anchor="w")

    def _build_image_tab(self) -> None:
        tab = self.image_tab
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Button(toolbar, text="Загрузить изображение…", command=self._load_image).pack(side="left")
        if self.on_select_canvas_area is None:
            # Standalone workbench keeps the legacy workflow. In the unified app
            # the target area comes directly from the executor instead.
            ttk.Button(toolbar, text="Загрузить профиль холста…", command=self._load_profile).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Сбросить обрезку", command=self._reset_crop).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Обработать изображение", command=self._process_now).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Сохранить комплект PNG + JSON…", command=self._save_processing_bundle).pack(side="left", padx=(6, 0))

        if self.on_select_canvas_area is not None:
            area_row = ttk.LabelFrame(tab, text="Область рисования из браузера", padding=6)
            area_row.pack(fill="x", pady=(0, 6))
            ttk.Button(
                area_row,
                text="Выбрать область рисования…",
                command=self._request_target_area,
            ).pack(side="left", padx=(0, 8))
            ttk.Label(area_row, textvariable=self.target_area_info_var, wraplength=1080).pack(
                side="left", fill="x", expand=True
            )

        size_frame = ttk.LabelFrame(tab, text="Размер холста и масштабирование", padding=6)
        size_frame.pack(fill="x", pady=(0, 6))
        ttk.Label(size_frame, text="Ширина (px)").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Entry(size_frame, textvariable=self.width_var, width=9).grid(row=1, column=0, sticky="ew", padx=4)
        ttk.Label(size_frame, text="Высота (px)").grid(row=0, column=1, sticky="w", padx=4)
        ttk.Entry(size_frame, textvariable=self.height_var, width=9).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(size_frame, text="Как подогнать изображение").grid(row=0, column=2, sticky="w", padx=4)
        fit = ttk.Combobox(size_frame, textvariable=self.fit_mode_var, values=list(FIT_LABELS), state="readonly", width=35)
        fit.grid(row=1, column=2, sticky="ew", padx=4)
        fit.bind("<<ComboboxSelected>>", lambda _event: self._schedule_processing())
        for column in range(3):
            size_frame.columnconfigure(column, weight=1 if column == 2 else 0)

        adjustments = ttk.LabelFrame(tab, text="Обработка", padding=6)
        adjustments.pack(fill="x", pady=(0, 6))
        ttk.Label(adjustments, text="Яркость").grid(row=0, column=0, sticky="w", padx=4)
        tk.Scale(adjustments, from_=-100, to=100, orient="horizontal", variable=self.brightness_var, length=180,
                 command=self._on_setting_changed).grid(row=1, column=0, sticky="ew", padx=4)
        ttk.Label(adjustments, text="Контраст").grid(row=0, column=1, sticky="w", padx=4)
        tk.Scale(adjustments, from_=0.5, to=2.5, resolution=0.05, orient="horizontal", variable=self.contrast_var, length=180,
                 command=self._on_setting_changed).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Label(adjustments, text="Подавление шума").grid(row=0, column=2, sticky="w", padx=4)
        tk.Scale(adjustments, from_=0, to=4, orient="horizontal", variable=self.denoise_var, length=180,
                 command=self._on_setting_changed).grid(row=1, column=2, sticky="ew", padx=4)
        ttk.Label(adjustments, text="Бинаризация").grid(row=0, column=3, sticky="w", padx=4)
        self.threshold_combo = ttk.Combobox(adjustments, textvariable=self.threshold_mode_var, values=list(THRESHOLD_LABELS), state="readonly", width=26)
        self.threshold_combo.grid(row=1, column=3, sticky="ew", padx=4)
        self.threshold_combo.bind("<<ComboboxSelected>>", self._on_threshold_mode_changed)
        self.threshold_scale = tk.Scale(adjustments, from_=0, to=255, orient="horizontal", variable=self.threshold_var, length=180,
                                        command=self._on_setting_changed)
        self.threshold_scale.grid(row=2, column=3, sticky="ew", padx=4)
        for column in range(4):
            adjustments.columnconfigure(column, weight=1)

        ttk.Label(tab, textvariable=self.image_stats_var, wraplength=1320).pack(fill="x", pady=(0, 5))
        previews = ttk.Frame(tab)
        previews.pack(fill="both", expand=True)
        for column in range(2):
            previews.columnconfigure(column, weight=1, uniform="imgcol")
        for row in range(2):
            previews.rowconfigure(row, weight=1, uniform="imgrow")
        self.source_preview = ImagePreview(previews, "1. Исходник — выделите мышью область обрезки", selectable=True, on_selection=self._on_crop_selected)
        self.color_preview = ImagePreview(previews, "2. Подготовленное цветное изображение")
        self.gray_preview = ImagePreview(previews, "3. Серое изображение после фильтров")
        self.mask_preview = ImagePreview(previews, "4. Бинарная маска — чёрное считается передним планом")
        self.source_preview.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 4))
        self.color_preview.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 4))
        self.gray_preview.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.mask_preview.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))

    def _build_plan_tab(self) -> None:
        tab = self.plan_tab
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Label(controls, text="Шаг строк (px)").pack(side="left")
        self.row_step_combo = ttk.Combobox(controls, textvariable=self.row_step_var, values=("1", "2", "3", "4", "5", "8", "10"), state="readonly", width=7)
        self.row_step_combo.pack(side="left", padx=(6, 10))
        ttk.Button(controls, text="Построить scanline-план", command=self._build_plan).pack(side="left")
        ttk.Button(controls, text="Сохранить JSON плана…", command=self._save_plan_json).pack(side="left", padx=(6, 0))
        ttk.Label(tab, text="Алгоритм этапа 8 не меняется: строки сверху вниз, участки слева направо; короткие штрихи и раздельные участки сохраняются.", wraplength=1320).pack(anchor="w", pady=(0, 8))
        ttk.Label(tab, textvariable=self.plan_stats_var, justify="left", wraplength=1320).pack(fill="x", pady=(0, 8))
        self.plan_preview = ImagePreview(tab, "Предпросмотр плана (не симуляция фактического движения мыши)")
        self.plan_preview.pack(fill="both", expand=True)

    def _build_quality_tab(self) -> None:
        tab = self.quality_tab
        controls = ttk.Frame(tab)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="Проверить качество", command=self._check_quality).pack(side="left")
        ttk.Button(controls, text="Сохранить отчёт JSON…", command=self._save_quality_report).pack(side="left", padx=(6, 0))
        ttk.Label(tab, textvariable=self.quality_stats_var, justify="left", wraplength=1320).pack(fill="x", pady=(0, 8))
        previews = ttk.Frame(tab)
        previews.pack(fill="both", expand=True)
        for column in range(3):
            previews.columnconfigure(column, weight=1, uniform="qcol")
        previews.rowconfigure(0, weight=1)
        self.quality_mask_preview = ImagePreview(previews, "Исходная маска переднего плана")
        self.quality_plan_preview = ImagePreview(previews, "Результат восстановления по плану")
        self.quality_diff_preview = ImagePreview(previews, "Различия: серый — совпадение, белый — пропуск, красный — лишнее")
        self.quality_mask_preview.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.quality_plan_preview.grid(row=0, column=1, sticky="nsew", padx=4)
        self.quality_diff_preview.grid(row=0, column=2, sticky="nsew", padx=(4, 0))

    def _build_project_tab(self) -> None:
        tab = self.project_tab
        ttk.Label(tab, text="Сохранить подготовленные материалы в единый проект .autodraw", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        name_row = ttk.Frame(tab)
        name_row.pack(fill="x", pady=(0, 8))
        ttk.Label(name_row, text="Имя проекта", width=20).pack(side="left")
        ttk.Entry(name_row, textvariable=self.project_name_var).pack(side="left", fill="x", expand=True)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Создать / сохранить .autodraw…", command=self._save_project).pack(side="left")
        ttk.Button(actions, text="Открыть проект .autodraw…", command=self._open_project).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Экспортировать JSON для этапа 6…", command=self._export_stage6_json).pack(side="left", padx=(6, 0))
        ttk.Label(
            tab,
            text="В проект входят исходное изображение, бинарная маска, настройки обработки, план, пересчитанный отчёт качества и подготовленные цветное/серое изображения. JSON плана совместим с исполнителем AutoDraw.",
            wraplength=1320,
        ).pack(anchor="w", pady=(0, 10))
        details_frame = ttk.LabelFrame(tab, text="Открытый проект / последний результат", padding=8)
        details_frame.pack(fill="both", expand=True)
        self.project_details = tk.Text(details_frame, wrap="word", height=12, state="disabled", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=self.project_details.yview)
        self.project_details.configure(yscrollcommand=scrollbar.set)
        self.project_details.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_profile_tab(self) -> None:
        tab = self.profile_tab
        ttk.Label(tab, text="Профили рабочей области и калибровки", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        ttk.Label(
            tab,
            text=("Профиль сохраняет размер холста, параметры обработки, шаг строк, экранную область и настройки исполнителя. "
                  "Настройки мыши экспортируются для этапа 6, но здесь рисование не запускается."),
            wraplength=1320,
        ).pack(anchor="w", pady=(0, 8))

        picker = ttk.Frame(tab)
        picker.pack(fill="x", pady=(0, 8))
        ttk.Label(picker, text="Сохранённые профили").pack(side="left")
        self.profile_combo = ttk.Combobox(picker, textvariable=self.profile_choice_var, state="readonly", width=45)
        self.profile_combo.pack(side="left", padx=(8, 6))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)
        ttk.Button(picker, text="Новый из текущих настроек", command=self._new_profile_from_current).pack(side="left", padx=(0, 6))
        ttk.Button(picker, text="Применить к рабочей области", command=self._apply_profile_to_workbench).pack(side="left")

        columns = ttk.Frame(tab)
        columns.pack(fill="both", expand=True)
        columns.columnconfigure(0, weight=1, uniform="profile-column")
        columns.columnconfigure(1, weight=1, uniform="profile-column")

        workspace = ttk.LabelFrame(columns, text="Настройки рабочей области", padding=8)
        workspace.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 6))
        self._profile_entry_row(workspace, 0, "Имя профиля", self.profile_name_var)
        self._profile_entry_row(workspace, 1, "Ширина холста, px", self.profile_canvas_width_var)
        self._profile_entry_row(workspace, 2, "Высота холста, px", self.profile_canvas_height_var)
        self._profile_combo_row(workspace, 3, "Подгонка", self.profile_fit_var,
                                ("contain", "cover", "stretch"))
        self._profile_combo_row(workspace, 4, "Шаг строк, px", self.profile_row_step_var,
                                ("1", "2", "3", "4", "5", "8", "10"))
        self._profile_entry_row(workspace, 5, "Яркость (−100…100)", self.profile_brightness_var)
        self._profile_entry_row(workspace, 6, "Контраст (0.5…2.5)", self.profile_contrast_var)
        self._profile_entry_row(workspace, 7, "Подавление шума (0…4)", self.profile_denoise_var)
        self._profile_combo_row(workspace, 8, "Режим бинаризации", self.profile_threshold_mode_var, ("otsu", "manual"))
        self._profile_entry_row(workspace, 9, "Порог (0…255)", self.profile_threshold_var)
        workspace.columnconfigure(1, weight=1)

        target = ttk.LabelFrame(columns, text="Экранная область для этапа 6", padding=8)
        target.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 6))
        ttk.Label(target, text="Оставьте поля пустыми, если экранную область ещё не калибровали.", wraplength=590).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 5))
        area_fields = [
            ("X", self.profile_area_x_var), ("Y", self.profile_area_y_var),
            ("Ширина", self.profile_area_width_var), ("Высота", self.profile_area_height_var),
        ]
        for index, (label, variable) in enumerate(area_fields):
            cell = ttk.Frame(target)
            cell.grid(row=1, column=index, sticky="ew", padx=3)
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Entry(cell, textvariable=variable, width=10).pack(fill="x", pady=(2, 0))
            target.columnconfigure(index, weight=1)
        ttk.Label(target, text="Разрешение экрана (необязательно)").grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 2))
        for index, (label, variable) in enumerate((("Экран W", self.profile_screen_width_var), ("Экран H", self.profile_screen_height_var))):
            ttk.Label(target, text=label).grid(row=3, column=index * 2, sticky="w", padx=3)
            ttk.Entry(target, textvariable=variable, width=10).grid(row=3, column=index * 2 + 1, sticky="ew", padx=3)

        calibration = ttk.LabelFrame(columns, text="Параметры калибровки исполнителя", padding=8)
        calibration.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        cal_fields = [
            ("Шаг точек, px", self.profile_point_step_var),
            ("Задержка точки, мс", self.profile_point_delay_var),
            ("После mouseUp, мс", self.profile_after_up_var),
            ("Перед mouseDown, мс", self.profile_before_down_var),
            ("После mouseDown, мс", self.profile_after_down_var),
            ("Удержание перед mouseUp, мс", self.profile_end_hold_var),
            ("Обратный отсчёт, с", self.profile_countdown_var),
        ]
        for index, (label, variable) in enumerate(cal_fields):
            cell = ttk.Frame(calibration)
            cell.grid(row=index // 4, column=index % 4, sticky="ew", padx=4, pady=3)
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Entry(cell, textvariable=variable, width=12).pack(anchor="w", pady=(2, 0))
        for column in range(4):
            calibration.columnconfigure(column, weight=1)

        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=(0, 6))
        ttk.Button(actions, text="Сохранить профиль", command=self._save_profile_from_form).pack(side="left")
        ttk.Button(actions, text="Удалить профиль", command=self._delete_selected_profile).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Импорт JSON…", command=self._import_profile).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Экспорт полного профиля…", command=self._export_profile).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Экспорт профиля холста…", command=self._export_canvas_profile).pack(side="left", padx=(6, 0))
        exports = ttk.Frame(tab)
        exports.pack(fill="x")
        ttk.Button(exports, text="Экспорт target_profile.json для этапа 6…", command=self._export_stage6_target_profile).pack(side="left")
        ttk.Button(exports, text="Экспорт execution_settings.json для этапа 6…", command=self._export_stage6_settings).pack(side="left", padx=(6, 0))
        self.profile_status_var = tk.StringVar(value="Профили сохраняются в папке profiles рядом с приложением.")
        ttk.Label(tab, textvariable=self.profile_status_var, wraplength=1320).pack(anchor="w", pady=(7, 0))
        if self._profile_load_error:
            self.profile_status_var.set("Реестр профилей не удалось прочитать: " + self._profile_load_error + ". Создан временный профиль; повреждённый файл не перезаписан автоматически.")
        self._refresh_profile_combo()
        if self.profiles:
            self._load_profile_into_form(self.profiles[0])

    @staticmethod
    def _profile_entry_row(parent, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        ttk.Entry(parent, textvariable=variable, width=18).grid(row=row, column=1, sticky="ew", pady=2)

    @staticmethod
    def _profile_combo_row(parent, row: int, label: str, variable: tk.StringVar, values: tuple[str, ...]) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        ttk.Combobox(parent, textvariable=variable, values=values, state="readonly", width=16).grid(row=row, column=1, sticky="ew", pady=2)

    def _refresh_profile_combo(self) -> None:
        self._profile_labels.clear()
        labels = []
        for profile in self.profiles:
            label = f"{profile.name} [{profile.profile_id[:6]}]"
            self._profile_labels[label] = profile.profile_id
            labels.append(label)
        if hasattr(self, "profile_combo"):
            self.profile_combo.configure(values=labels)
        selected_label = next((label for label, pid in self._profile_labels.items() if pid == self._selected_profile_id), None)
        if selected_label is None and labels:
            selected_label = labels[0]
            self._selected_profile_id = self._profile_labels[selected_label]
        self.profile_choice_var.set(selected_label or "")

    def _on_profile_selected(self, _event=None) -> None:
        profile_id = self._profile_labels.get(self.profile_choice_var.get())
        profile = next((item for item in self.profiles if item.profile_id == profile_id), None)
        if profile is not None:
            self._load_profile_into_form(profile)
            self.profile_status_var.set(f"Выбран профиль «{profile.name}». Для применения к обработке нажмите отдельную кнопку.")

    def _load_profile_into_form(self, profile: WorkspaceProfile) -> None:
        self._selected_profile_id = profile.profile_id
        self.profile_name_var.set(profile.name)
        self.profile_canvas_width_var.set(str(profile.canvas_width))
        self.profile_canvas_height_var.set(str(profile.canvas_height))
        self.profile_fit_var.set(profile.fit_mode)
        self.profile_row_step_var.set(str(profile.row_step_px))
        self.profile_brightness_var.set(str(profile.brightness))
        self.profile_contrast_var.set(str(profile.contrast))
        self.profile_denoise_var.set(str(profile.denoise_level))
        self.profile_threshold_mode_var.set(profile.threshold_mode)
        self.profile_threshold_var.set(str(profile.threshold))
        area = profile.screen_area
        self.profile_area_x_var.set(str(area.x) if area else "")
        self.profile_area_y_var.set(str(area.y) if area else "")
        self.profile_area_width_var.set(str(area.width) if area else "")
        self.profile_area_height_var.set(str(area.height) if area else "")
        self.profile_screen_width_var.set(str(area.screen_width) if area and area.screen_width is not None else "")
        self.profile_screen_height_var.set(str(area.screen_height) if area and area.screen_height is not None else "")
        cal = profile.calibration
        self.profile_point_step_var.set(str(cal.point_step_px))
        self.profile_point_delay_var.set(str(cal.point_delay_ms))
        self.profile_after_up_var.set(str(cal.after_mouse_up_ms))
        self.profile_before_down_var.set(str(cal.before_mouse_down_ms))
        self.profile_after_down_var.set(str(cal.after_mouse_down_ms))
        self.profile_end_hold_var.set(str(cal.end_hold_ms))
        self.profile_countdown_var.set(str(cal.countdown_seconds))
        self._refresh_profile_combo()

    def _profile_from_form(self, *, profile_id: str | None = None, created_at: str = "", updated_at: str = "") -> WorkspaceProfile:
        screen_values = [
            self.profile_area_x_var.get().strip(), self.profile_area_y_var.get().strip(),
            self.profile_area_width_var.get().strip(), self.profile_area_height_var.get().strip(),
        ]
        if any(screen_values) and not all(screen_values):
            raise ProfileValidationError("Для экранной области заполните все четыре поля: X, Y, ширину и высоту.")
        screen_area = None
        if all(screen_values):
            screen_area = ScreenArea(
                x=int(screen_values[0]), y=int(screen_values[1]),
                width=int(screen_values[2]), height=int(screen_values[3]),
                screen_width=int(self.profile_screen_width_var.get()) if self.profile_screen_width_var.get().strip() else None,
                screen_height=int(self.profile_screen_height_var.get()) if self.profile_screen_height_var.get().strip() else None,
            )
        elif self.profile_screen_width_var.get().strip() or self.profile_screen_height_var.get().strip():
            raise ProfileValidationError("Разрешение экрана можно указать только вместе с экранной областью.")
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        profile = WorkspaceProfile(
            profile_id=profile_id or uuid.uuid4().hex,
            name=self.profile_name_var.get().strip(),
            canvas_width=int(self.profile_canvas_width_var.get()),
            canvas_height=int(self.profile_canvas_height_var.get()),
            fit_mode=self.profile_fit_var.get(),
            brightness=int(self.profile_brightness_var.get()),
            contrast=float(self.profile_contrast_var.get()),
            denoise_level=int(self.profile_denoise_var.get()),
            threshold_mode=self.profile_threshold_mode_var.get(),
            threshold=int(self.profile_threshold_var.get()),
            row_step_px=int(self.profile_row_step_var.get()),
            screen_area=screen_area,
            calibration=CalibrationSettings(
                point_step_px=float(self.profile_point_step_var.get()),
                point_delay_ms=int(self.profile_point_delay_var.get()),
                after_mouse_up_ms=int(self.profile_after_up_var.get()),
                before_mouse_down_ms=int(self.profile_before_down_var.get()),
                after_mouse_down_ms=int(self.profile_after_down_var.get()),
                end_hold_ms=int(self.profile_end_hold_var.get()),
                countdown_seconds=int(self.profile_countdown_var.get()),
            ),
            created_at=created_at or now,
            updated_at=updated_at or now,
        )
        profile.validate()
        return profile

    def _new_profile_from_current(self) -> None:
        self._selected_profile_id = None
        self.profile_name_var.set(f"Профиль {len(self.profiles) + 1}")
        self.profile_canvas_width_var.set(self.width_var.get())
        self.profile_canvas_height_var.set(self.height_var.get())
        self.profile_fit_var.set(FIT_LABELS.get(self.fit_mode_var.get(), "contain"))
        self.profile_row_step_var.set(self.row_step_var.get())
        self.profile_brightness_var.set(str(self.brightness_var.get()))
        self.profile_contrast_var.set(str(self.contrast_var.get()))
        self.profile_denoise_var.set(str(self.denoise_var.get()))
        self.profile_threshold_mode_var.set(THRESHOLD_LABELS.get(self.threshold_mode_var.get(), "otsu"))
        self.profile_threshold_var.set(str(self.threshold_var.get()))
        # Don't copy monitor-specific coordinates into a new profile by accident.
        for variable in (self.profile_area_x_var, self.profile_area_y_var, self.profile_area_width_var,
                         self.profile_area_height_var, self.profile_screen_width_var, self.profile_screen_height_var):
            variable.set("")
        self.profile_point_step_var.set("2.0")
        self.profile_point_delay_var.set("10")
        self.profile_after_up_var.set("20")
        self.profile_before_down_var.set("20")
        self.profile_after_down_var.set("40")
        self.profile_end_hold_var.set("50")
        self.profile_countdown_var.set("5")
        self.profile_choice_var.set("")
        self.profile_status_var.set("Новый профиль заполнен текущими настройками этапа 12; экранная область сброшена, тайминги взяты из проверенного базового профиля. Проверьте параметры и нажмите «Сохранить профиль».")

    def _save_profile_from_form(self) -> None:
        try:
            previous = next((item for item in self.profiles if item.profile_id == self._selected_profile_id), None)
            profile = self._profile_from_form(
                profile_id=previous.profile_id if previous else None,
                created_at=previous.created_at if previous else "",
            )
            self.profiles = self.profile_store.upsert(profile)
            self._selected_profile_id = profile.profile_id
            saved = next(item for item in self.profiles if item.profile_id == profile.profile_id)
            self._load_profile_into_form(saved)
            self.profile_status_var.set(f"Профиль «{saved.name}» сохранён в {self.profile_store.path}.")
            self.status_var.set(f"Профиль «{saved.name}» сохранён.")
        except (ProfileValidationError, ValueError, TypeError, OSError) as exc:
            messagebox.showerror("Не удалось сохранить профиль", str(exc), parent=self.root)

    def _apply_profile_to_workbench(self) -> None:
        try:
            profile = self._profile_from_form(
                profile_id=self._selected_profile_id or uuid.uuid4().hex,
            )
        except (ProfileValidationError, ValueError, TypeError) as exc:
            messagebox.showerror("Некорректный профиль", str(exc), parent=self.root)
            return
        self.width_var.set(str(profile.canvas_width))
        self.height_var.set(str(profile.canvas_height))
        self.fit_mode_var.set(FIT_LABELS_BY_VALUE[profile.fit_mode])
        self.row_step_var.set(str(profile.row_step_px))
        self.brightness_var.set(profile.brightness)
        self.contrast_var.set(profile.contrast)
        self.denoise_var.set(profile.denoise_level)
        self.threshold_mode_var.set(THRESHOLD_LABELS_BY_VALUE[profile.threshold_mode])
        self.threshold_var.set(profile.threshold)
        self.threshold_scale.configure(state="normal" if profile.threshold_mode == "manual" else "disabled")
        # Crop selections are source-image-specific, so don't silently carry them across profiles.
        self.crop_box = None
        if self.source_image is not None:
            self.source_preview.set_selection(None)
            self._process_now()
            self.notebook.select(self.image_tab)
        self.profile_status_var.set(
            f"Параметры «{profile.name}» применены к этапу 12. Профиль экрана и задержки мыши экспортируются отдельно для этапа 6."
        )
        self.status_var.set(f"Профиль «{profile.name}» применён к рабочей области.")

    def _delete_selected_profile(self) -> None:
        if not self._selected_profile_id:
            messagebox.showinfo("Профиль не выбран", "Выберите сохранённый профиль для удаления.", parent=self.root)
            return
        profile = next((item for item in self.profiles if item.profile_id == self._selected_profile_id), None)
        if profile is None:
            return
        if len(self.profiles) <= 1:
            messagebox.showwarning("Последний профиль", "Нельзя удалить последний профиль. Сначала создайте другой.", parent=self.root)
            return
        if not messagebox.askyesno("Удалить профиль?", f"Удалить профиль «{profile.name}»?", parent=self.root):
            return
        try:
            self.profiles = self.profile_store.delete(profile.profile_id)
            self._selected_profile_id = self.profiles[0].profile_id
            self._load_profile_into_form(self.profiles[0])
            self.profile_status_var.set(f"Профиль «{profile.name}» удалён.")
        except (ProfileValidationError, OSError) as exc:
            messagebox.showerror("Не удалось удалить профиль", str(exc), parent=self.root)

    def _import_profile(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Импортировать профиль AutoDraw или JSON этапа 6", filetypes=[("JSON профиля", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            profile = WorkspaceProfile.from_external_dict(data, name=Path(path).stem.replace("_", " "))
            profile = replace(profile, profile_id=uuid.uuid4().hex)
            self._load_profile_into_form(profile)
            self._selected_profile_id = None
            self.profile_choice_var.set("")
            self.profile_status_var.set(f"Профиль импортирован из {Path(path).name}. Нажмите «Сохранить профиль», чтобы добавить его в реестр.")
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка импорта профиля", str(exc), parent=self.root)

    def _export_profile(self) -> None:
        try:
            profile = self._profile_from_form(profile_id=self._selected_profile_id or uuid.uuid4().hex)
        except (ProfileValidationError, ValueError, TypeError) as exc:
            messagebox.showerror("Некорректный профиль", str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Экспорт полного профиля", initialdir=str(PROFILES_DIR), initialfile=f"{profile.name.replace(' ', '_')}.autodraw-profile.json", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            ProfileStore.export_json(path, profile.to_dict())
            self.profile_status_var.set(f"Полный профиль экспортирован: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def _export_canvas_profile(self) -> None:
        try:
            profile = self._profile_from_form(profile_id=self._selected_profile_id or uuid.uuid4().hex)
        except (ProfileValidationError, ValueError, TypeError) as exc:
            messagebox.showerror("Некорректный профиль", str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Экспорт размера холста для этапа 12", initialdir=str(PROFILES_DIR), initialfile="canvas_profile.json", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            ProfileStore.export_json(path, profile.to_canvas_profile())
            self.profile_status_var.set(f"Профиль холста экспортирован: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def _export_stage6_target_profile(self) -> None:
        try:
            profile = self._profile_from_form(profile_id=self._selected_profile_id or uuid.uuid4().hex)
            payload = profile.to_stage6_target_profile()
        except (ProfileValidationError, ValueError, TypeError) as exc:
            messagebox.showerror("Экранная область не задана", str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Экспорт target_profile.json для этапа 6", initialdir=str(PROFILES_DIR), initialfile="target_profile.json", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            ProfileStore.export_json(path, payload)
            self.profile_status_var.set(f"Профиль экранной области для этапа 6 экспортирован: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def _export_stage6_settings(self) -> None:
        try:
            profile = self._profile_from_form(profile_id=self._selected_profile_id or uuid.uuid4().hex)
            payload = profile.to_stage6_settings()
        except (ProfileValidationError, ValueError, TypeError) as exc:
            messagebox.showerror("Некорректная калибровка", str(exc), parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Экспорт execution_settings.json для этапа 6", initialdir=str(PROFILES_DIR), initialfile="execution_settings.json", defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            ProfileStore.export_json(path, payload)
            self.profile_status_var.set(f"Настройки исполнителя для этапа 6 экспортированы: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def _set_project_details(self, value: str) -> None:
        self.project_details.configure(state="normal")
        self.project_details.delete("1.0", "end")
        self.project_details.insert("1.0", value)
        self.project_details.configure(state="disabled")

    def _request_target_area(self) -> None:
        """Reuse the executor's area selector and apply the result to image dimensions."""
        if self.on_select_canvas_area is None:
            return
        try:
            self.on_select_canvas_area()
        except (RuntimeError, ValueError, OSError) as exc:
            messagebox.showerror("Не удалось выбрать область", str(exc), parent=self.root)

    def set_target_area(self, area: dict | Any, screen_size: tuple[int, int] | None = None) -> None:
        """Synchronize the preparation canvas and saved-profile form with the executor area."""
        def field(name: str) -> int:
            value = area.get(name) if isinstance(area, dict) else getattr(area, name)
            number = int(value)
            if number < 0 and name in {"x", "y"}:
                raise ValueError(f"Координата {name.upper()} не может быть отрицательной.")
            if number <= 0 and name in {"width", "height"}:
                raise ValueError(f"Размер {name} должен быть положительным.")
            return number

        x, y, width, height = (field(name) for name in ("x", "y", "width", "height"))
        if width * height > 40_000_000:
            raise ValueError("Выбранная область превышает ограничение 40 млн пикселей.")

        self.width_var.set(str(width))
        self.height_var.set(str(height))
        self.profile_canvas_width_var.set(str(width))
        self.profile_canvas_height_var.set(str(height))
        self.profile_area_x_var.set(str(x))
        self.profile_area_y_var.set(str(y))
        self.profile_area_width_var.set(str(width))
        self.profile_area_height_var.set(str(height))
        if screen_size is not None:
            screen_width, screen_height = (int(screen_size[0]), int(screen_size[1]))
            self.profile_screen_width_var.set(str(screen_width))
            self.profile_screen_height_var.set(str(screen_height))
        else:
            self.profile_screen_width_var.set(str(self.root.winfo_screenwidth()))
            self.profile_screen_height_var.set(str(self.root.winfo_screenheight()))

        self.target_area_info_var.set(
            f"Выбрана область: X={x}, Y={y}; размер холста {width} × {height} px. "
            "Размер изображения синхронизирован автоматически — профиль холста отдельно загружать не нужно."
        )
        self.profile_status_var.set(
            "Экранная область синхронизирована с исполнителем. При необходимости сохраните её в выбранном профиле."
        )
        if self.source_image is not None:
            self._process_now()
        self.status_var.set(
            f"Размер холста синхронизирован с браузерной областью: {width} × {height} px."
        )

    def _load_image(self) -> None:
        selected = filedialog.askopenfilename(parent=self.root, title="Выберите исходное изображение", filetypes=IMAGE_TYPES)
        if not selected:
            return
        try:
            image = load_rgb_image(selected)
        except ValueError as exc:
            messagebox.showerror("Не удалось загрузить изображение", str(exc), parent=self.root)
            return
        self.source_path = Path(selected)
        self.source_filename = self.source_path.name
        self.source_image = image
        self.crop_box = None
        self.source_preview.set_image(image)
        self.source_preview.set_selection(None)
        self.project_name_var.set(self.source_path.stem)
        self._process_now()
        self.notebook.select(self.image_tab)
        self.status_var.set(f"Загружено: {self.source_path.name}, {image.width} × {image.height} px.")

    def _load_profile(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Выберите профиль холста JSON", filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
            area = data.get("area", data)
            width, height = int(area["width"]), int(area["height"])
            if width <= 0 or height <= 0 or width * height > 40_000_000:
                raise ValueError("Размеры профиля должны быть положительными и не превышать 40 млн пикселей.")
            self.width_var.set(str(width))
            self.height_var.set(str(height))
            if self.source_image is not None:
                self._process_now()
            self.status_var.set(f"Профиль холста загружен: {width} × {height} px.")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка профиля", str(exc), parent=self.root)

    def _on_crop_selected(self, box: tuple[int, int, int, int]) -> None:
        self.crop_box = box
        self.source_preview.set_selection(box)
        self._schedule_processing()
        self.status_var.set(f"Выбрана обрезка исходника: {box[2]-box[0]} × {box[3]-box[1]} px.")

    def _reset_crop(self) -> None:
        if self.source_image is None:
            return
        self.crop_box = None
        self.source_preview.set_selection(None)
        self._schedule_processing()
        self.status_var.set("Обрезка сброшена; используется весь исходник.")

    def _current_settings(self) -> ProcessingSettings:
        mode = THRESHOLD_LABELS.get(self.threshold_mode_var.get(), "otsu")
        return ProcessingSettings(
            brightness=int(self.brightness_var.get()),
            contrast=round(float(self.contrast_var.get()) * 100) / 100,
            denoise_level=int(self.denoise_var.get()),
            threshold_mode=mode,  # type: ignore[arg-type]
            threshold=int(self.threshold_var.get()),
        )

    def _on_setting_changed(self, _value=None) -> None:
        self._schedule_processing()

    def _on_threshold_mode_changed(self, _event=None) -> None:
        mode = THRESHOLD_LABELS.get(self.threshold_mode_var.get(), "otsu")
        self.threshold_scale.configure(state="normal" if mode == "manual" else "disabled")
        self._schedule_processing()

    def _schedule_processing(self) -> None:
        if self.source_image is None:
            return
        if self._pending_processing is not None:
            try:
                self.root.after_cancel(self._pending_processing)
            except tk.TclError:
                pass
        self._pending_processing = self.root.after(180, self._process_now)

    def _process_now(self) -> None:
        self._pending_processing = None
        if self.source_image is None:
            messagebox.showinfo("Нет изображения", "Сначала загрузите изображение или откройте проект .autodraw.", parent=self.root)
            return
        try:
            width, height = int(self.width_var.get()), int(self.height_var.get())
            if width <= 0 or height <= 0 or width * height > 40_000_000:
                raise ValueError("Размер холста должен быть положительным и не превышать 40 млн пикселей.")
            result = process_image(
                self.source_image, width, height,
                FIT_LABELS.get(self.fit_mode_var.get(), "contain"),
                self.crop_box, self._current_settings(),
            )
        except (ValueError, TypeError, OverflowError) as exc:
            self.status_var.set(f"Обработка не выполнена: {exc}")
            return

        self.result = result
        self.plan = None
        self.quality_result = None
        self.plan_stats_var.set("План ещё не создан. Перейдите на вкладку «Растровый план».")
        self.quality_stats_var.set("Качество ещё не проверено.")
        self.plan_preview.set_image(None)
        self.quality_mask_preview.set_image(None)
        self.quality_plan_preview.set_image(None)
        self.quality_diff_preview.set_image(None)
        self.color_preview.set_image(result.prepared_color)
        self.gray_preview.set_image(result.grayscale)
        self.mask_preview.set_image(result.binary_mask)
        import numpy as np
        dark_pixels = int((np.asarray(result.binary_mask) <= 127).sum())
        percent = 100.0 * dark_pixels / (width * height)
        crop_text = "без обрезки" if self.crop_box is None else f"обрезка {self.crop_box[2]-self.crop_box[0]} × {self.crop_box[3]-self.crop_box[1]} px"
        self.image_stats_var.set(
            f"Холст: {width} × {height}; исходник: {self.source_image.width} × {self.source_image.height}; "
            f"режим: {self.fit_mode_var.get()}; {crop_text}; применённый порог: {result.threshold_used}; "
            f"пикселей переднего плана: {percent:.1f}%."
        )
        self.status_var.set("Обработка готова. Постройте план на следующей вкладке.")

    def _build_plan(self) -> None:
        if self.result is None:
            messagebox.showwarning("Нет маски", "Сначала обработайте изображение на первой вкладке.", parent=self.root)
            return
        try:
            row_step = int(self.row_step_var.get())
            plan = build_scanline_plan(self.result.binary_mask, row_step_px=row_step, threshold=127, foreground="dark")
            if not plan.get("strokes"):
                raise ValueError("В маске нет тёмных участков. Измените порог или настройки обработки.")
            metrics = analyze_plan(plan, TimingProfile())
        except (ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось построить план", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка построения плана: {exc}")
            return
        self.plan = plan
        self.quality_result = None
        self.plan_preview.set_image(render_plan_preview(plan))
        self.plan_stats_var.set(
            f"Холст: {plan['canvas']['width']} × {plan['canvas']['height']} px\n"
            f"Штрихов: {metrics.stroke_count:,}; точек: {metrics.point_count:,}\n"
            f"Длина рисования: {metrics.drawing_length_px:,.1f} px; расстояние между штрихами: {metrics.pen_up_distance_px:,.1f} px\n"
            f"Оценка времени по профилю этапа 1: {metrics.estimated_seconds:,.1f} с\n"
            f"Шаг строк: {row_step} px; порядок штрихов сохранён, короткие штрихи не удаляются."
        )
        self.quality_stats_var.set("План изменился. Запустите проверку качества ещё раз.")
        self.status_var.set(f"План создан: {metrics.stroke_count:,} штрихов. Следующий шаг — проверка качества.")
        self.notebook.select(self.plan_tab)

    def _check_quality(self) -> None:
        if self.result is None or self.plan is None:
            messagebox.showwarning("Недостаточно данных", "Сначала обработайте изображение и постройте план.", parent=self.root)
            return
        try:
            report, source, rendered, difference = analyze_quality(
                self.result.binary_mask, self.plan, threshold=127, foreground="dark"
            )
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Не удалось проверить качество", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка проверки качества: {exc}")
            return
        self.quality_result = (report, source, rendered, difference)
        self.quality_mask_preview.set_image(source)
        self.quality_plan_preview.set_image(rendered)
        self.quality_diff_preview.set_image(difference)
        self.quality_stats_var.set(
            f"Совпадение пикселей (Pixel Accuracy): {report.pixel_accuracy_percent:.2f}%    "
            f"Precision: {report.precision_percent:.2f}%    Recall: {report.recall_percent:.2f}%    F1: {report.f1_percent:.2f}%\n"
            f"Совпало: {report.matched_pixels:,}; пропущено: {report.missing_pixels:,}; лишних: {report.extra_pixels:,}\n"
            f"Штрихов: {report.stroke_count:,}; точек: {report.point_count:,}; точек вне холста: {report.out_of_bounds_points}; пустых штрихов: {report.empty_strokes}."
        )
        self.status_var.set("Проверка завершена. Метрики оценивают DrawingPlan относительно маски, а не след на реальной доске.")
        self.notebook.select(self.quality_tab)

    def _safe_save_dialog(self, *, title: str, initialfile: str, extension: str, filetypes, initialdir: Path | None = None):
        default_directory = self.current_project.parent if self.current_project else (self.source_path.parent if self.source_path else PROJECTS_DIR)
        chosen_directory = initialdir or default_directory
        chosen_directory.mkdir(parents=True, exist_ok=True)
        return filedialog.asksaveasfilename(
            parent=self.root, title=title, initialdir=str(chosen_directory),
            initialfile=initialfile, defaultextension=extension, filetypes=filetypes,
        )

    def _save_plan_json(self) -> None:
        if self.plan is None:
            messagebox.showinfo("Нет плана", "Сначала постройте растровый план.", parent=self.root)
            return
        stem = Path(self.source_filename).stem if self.source_filename else "drawing"
        path = self._safe_save_dialog(title="Сохранить DrawingPlan для этапа 6", initialfile=f"{stem}_stage6_plan.json", extension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            save_plan(path, self.plan)
            self.status_var.set(f"JSON для этапа 6 сохранён: {path}")
            messagebox.showinfo("Экспорт плана", f"План сохранён в совместимом формате Stage 6:\n{path}", parent=self.root)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Ошибка сохранения плана", str(exc), parent=self.root)

    def _save_quality_report(self) -> None:
        if self.quality_result is None:
            messagebox.showinfo("Нет отчёта", "Сначала выполните проверку качества.", parent=self.root)
            return
        report = self.quality_result[0]
        stem = Path(self.source_filename).stem if self.source_filename else "drawing"
        path = self._safe_save_dialog(title="Сохранить отчёт качества", initialfile=f"{stem}_quality_report.json", extension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            save_report(path, report)
            self.status_var.set(f"Отчёт качества сохранён: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения отчёта", str(exc), parent=self.root)

    def _processing_metadata(self) -> dict[str, Any]:
        assert self.source_image is not None and self.result is not None
        settings = self.result.settings
        return {
            "schema_version": 1,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "source_file": self.source_filename or (self.source_path.name if self.source_path else None),
            "source_size": {"width": self.source_image.width, "height": self.source_image.height},
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
                "prepared_color": "prepared_color.png",
                "grayscale": "grayscale.png",
                "binary_mask": "binary_mask.png",
            },
            "note": "Stage 12 workbench. This UI prepares and validates a plan; it does not send mouse input.",
        }

    def _prepare_project_files(self) -> tuple[Path, Path, Path, Path, Path]:
        if not self.source_path or self.source_image is None or self.result is None or self.plan is None:
            raise ValueError("Для создания проекта нужны исходное изображение, обработанная маска и DrawingPlan.")
        mask_path = self.workspace / "binary_mask.png"
        color_path = self.workspace / "prepared_color.png"
        gray_path = self.workspace / "grayscale.png"
        plan_path = self.workspace / "drawing_plan.json"
        metadata_path = self.workspace / "processing_result.json"
        self.result.binary_mask.save(mask_path)
        self.result.prepared_color.save(color_path)
        self.result.grayscale.save(gray_path)
        save_plan(plan_path, self.plan)
        metadata_path.write_text(json.dumps(self._processing_metadata(), ensure_ascii=False, indent=2), encoding="utf-8")
        return mask_path, color_path, gray_path, plan_path, metadata_path

    def _save_project(self) -> None:
        if self.result is None or self.plan is None or self.source_path is None:
            messagebox.showwarning("Недостаточно данных", "Сначала обработайте изображение и постройте растровый план.", parent=self.root)
            return
        stem = (self.project_name_var.get().strip() or self.source_path.stem or "AutoDraw project") + ".autodraw"
        path = self._safe_save_dialog(
            title="Создать проект AutoDraw", initialfile=stem, extension=".autodraw",
            filetypes=[("AutoDraw project", "*.autodraw")],
            initialdir=self.current_project.parent if self.current_project else PROJECTS_DIR,
        )
        if not path:
            return
        if Path(path).exists() and not messagebox.askyesno("Перезаписать проект?", f"Файл уже существует:\n{path}\n\nПерезаписать его?", parent=self.root):
            return
        try:
            mask_path, color_path, gray_path, plan_path, metadata_path = self._prepare_project_files()
            project_path = create_project(
                path, self.source_path, mask_path, plan_path,
                project_name=self.project_name_var.get().strip() or self.source_path.stem,
                processing_metadata_path=metadata_path,
                prepared_color_path=color_path,
                grayscale_path=gray_path,
            )
            self.current_project = project_path
            bundle = open_project(project_path)
            self._set_project_details(project_summary(bundle))
            self.status_var.set(f"Проект сохранён и прошёл проверку: {project_path}")
            messagebox.showinfo("Проект сохранён", f"Создан проект AutoDraw:\n{project_path}\n\nВ архив включены маска, настройки, план, отчёт качества и подготовленные изображения.", parent=self.root)
        except (ProjectFormatError, OSError, ValueError, TypeError) as exc:
            self.status_var.set(f"Не удалось создать проект: {exc}")
            messagebox.showerror("Ошибка создания проекта", str(exc), parent=self.root)

    def _open_project(self) -> None:
        path = filedialog.askopenfilename(parent=self.root, title="Открыть проект AutoDraw", filetypes=[("AutoDraw project", "*.autodraw"), ("ZIP", "*.zip"), ("Все файлы", "*.*")])
        if not path:
            return
        try:
            bundle = open_project(path)
            source_name = bundle.manifest.get("source", {}).get("source_image_filename", "source.img")
            suffix = Path(str(source_name)).suffix.lower()
            if not suffix or len(suffix) > 10 or not suffix[1:].isalnum():
                suffix = ".img"
            source_path = self.workspace / f"loaded_source_{uuid.uuid4().hex}{suffix}"
            source_path.write_bytes(bundle.file_bytes("source_image"))
            source_image = load_rgb_image(source_path)
            width, height = bundle.canvas
            settings_doc = bundle.json_file("processing_settings")
            ip = settings_doc.get("image_processing", {}) if isinstance(settings_doc.get("image_processing"), dict) else {}
            fit_value = ip.get("fit_mode", "contain")
            if fit_value not in ("contain", "cover", "stretch"):
                fit_value = "contain"
            mode = ip.get("threshold_mode", "otsu")
            if mode not in ("manual", "otsu"):
                mode = "otsu"
            settings = ProcessingSettings(
                brightness=_bounded_int(ip.get("brightness", 0), -100, 100, 0),
                contrast=_bounded_float(ip.get("contrast", 1.0), 0.5, 2.5, 1.0),
                denoise_level=_bounded_int(ip.get("denoise_level", 0), 0, 4, 0),
                threshold_mode=mode,
                threshold=_bounded_int(ip.get("requested_threshold", 128), 0, 255, 128),
            )
            crop_data = ip.get("crop_box_original_pixels")
            crop = tuple(int(v) for v in crop_data) if isinstance(crop_data, (list, tuple)) and len(crop_data) == 4 else None
            if crop is not None and not (0 <= crop[0] < crop[2] <= source_image.width and 0 <= crop[1] < crop[3] <= source_image.height and crop[2]-crop[0] >= 2 and crop[3]-crop[1] >= 2):
                crop = None
            computed = process_image(source_image, width, height, fit_value, crop, settings)
            mask = _image_from_bytes(bundle.file_bytes("binary_mask"), "L")
            if mask.size != (width, height):
                raise ProjectFormatError("Размер маски внутри проекта не совпадает с размером холста.")
            color = _optional_image(bundle, "prepared_color", "RGB") or computed.prepared_color
            gray = _optional_image(bundle, "grayscale", "L") or computed.grayscale
            self.source_path = source_path
            self.source_filename = Path(str(source_name)).name
            self.source_image = source_image
            self.crop_box = crop
            self.width_var.set(str(width))
            self.height_var.set(str(height))
            self.fit_mode_var.set(FIT_LABELS_BY_VALUE[fit_value])
            self.brightness_var.set(settings.brightness)
            self.contrast_var.set(settings.contrast)
            self.denoise_var.set(settings.denoise_level)
            self.threshold_mode_var.set(THRESHOLD_LABELS_BY_VALUE[settings.threshold_mode])
            self.threshold_var.set(settings.threshold)
            self.threshold_scale.configure(state="normal" if settings.threshold_mode == "manual" else "disabled")
            self.source_preview.set_image(source_image)
            self.source_preview.set_selection(crop)
            self.result = ProcessingResult(
                prepared_color=color, grayscale=gray, binary_mask=mask,
                threshold_used=_bounded_int(ip.get("threshold_used", computed.threshold_used), 0, 255, computed.threshold_used),
                target_width=width, target_height=height, fit_mode=fit_value,
                crop_box=crop, settings=settings,
            )
            self.plan = bundle.json_file("drawing_plan")
            if self.plan.get("canvas", {}).get("width") != width or self.plan.get("canvas", {}).get("height") != height:
                raise ProjectFormatError("Размеры DrawingPlan внутри проекта не совпадают с холстом.")
            self.quality_result = None
            self.current_project = Path(path)
            self.project_name_var.set(bundle.name)
            self.color_preview.set_image(color)
            self.gray_preview.set_image(gray)
            self.mask_preview.set_image(mask)
            self.image_stats_var.set(f"Проект загружен: холст {width} × {height}; исходник {source_image.width} × {source_image.height}; порог {self.result.threshold_used}.")
            metrics = analyze_plan(self.plan, TimingProfile())
            self.plan_preview.set_image(render_plan_preview(self.plan))
            self.plan_stats_var.set(
                f"Холст: {width} × {height} px\nШтрихов: {metrics.stroke_count:,}; точек: {metrics.point_count:,}\n"
                f"Длина: {metrics.drawing_length_px:,.1f} px; расстояние между штрихами: {metrics.pen_up_distance_px:,.1f} px\n"
                f"Оценка времени: {metrics.estimated_seconds:,.1f} с\nПлан загружен из проекта; повторная генерация не выполнялась."
            )
            self.quality_stats_var.set("Отчёт проекта сохранён внутри архива. Нажмите «Проверить качество», чтобы пересчитать метрики.")
            self._clear_quality_previews()
            self._set_project_details(project_summary(bundle))
            self.notebook.select(self.image_tab)
            self.status_var.set(f"Проект открыт и проверен: {path}")
        except (ProjectFormatError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showerror("Не удалось открыть проект", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка открытия проекта: {exc}")

    def _export_stage6_json(self) -> None:
        if self.plan is None:
            messagebox.showinfo("Нет плана", "Сначала постройте план или откройте проект .autodraw.", parent=self.root)
            return
        stem = Path(self.source_filename).stem if self.source_filename else "drawing"
        path = self._safe_save_dialog(title="Экспорт DrawingPlan для этапа 6", initialfile=f"{stem}_stage6_plan.json", extension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            save_plan(path, self.plan)
            self.status_var.set(f"DrawingPlan экспортирован для этапа 6: {path}")
            messagebox.showinfo("Экспорт готов", f"План сохранён в формате Stage 6:\n{path}", parent=self.root)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Ошибка экспорта", str(exc), parent=self.root)

    def _save_processing_bundle(self) -> None:
        if self.result is None or self.source_image is None:
            messagebox.showinfo("Нет результата", "Сначала загрузите и обработайте изображение.", parent=self.root)
            return
        directory = filedialog.askdirectory(parent=self.root, title="Выберите папку для сохранения комплекта", mustexist=False)
        if not directory:
            return
        output = Path(directory)
        stem = Path(self.source_filename).stem if self.source_filename else "image"
        try:
            output.mkdir(parents=True, exist_ok=True)
            color_path = output / f"{stem}_prepared_color.png"
            gray_path = output / f"{stem}_grayscale.png"
            mask_path = output / f"{stem}_binary_mask.png"
            metadata_path = output / f"{stem}_processing_result.json"
            self.result.prepared_color.save(color_path)
            self.result.grayscale.save(gray_path)
            self.result.binary_mask.save(mask_path)
            metadata = self._processing_metadata()
            metadata["outputs"] = {"prepared_color": color_path.name, "grayscale": gray_path.name, "binary_mask": mask_path.name}
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("Комплект сохранён", f"Сохранены PNG и processing_result.json:\n{output}", parent=self.root)
            self.status_var.set(f"Комплект обработки сохранён: {output}")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)

    def _clear_quality_previews(self) -> None:
        self.quality_mask_preview.set_image(None)
        self.quality_plan_preview.set_image(None)
        self.quality_diff_preview.set_image(None)

    def cleanup(self) -> None:
        """Release temporary files and pending callbacks without closing the host window."""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        if self._pending_processing is not None:
            try:
                self.root.after_cancel(self._pending_processing)
            except tk.TclError:
                pass
            self._pending_processing = None
        try:
            self._temp.cleanup()
        except OSError:
            pass

    def _on_close(self) -> None:
        self.cleanup()
        self.root.destroy()


def _image_from_bytes(data: bytes, mode: str) -> Image.Image:
    with Image.open(io.BytesIO(data)) as image:
        return image.convert(mode)


def _optional_image(bundle, logical_name: str, mode: str) -> Image.Image | None:
    if logical_name not in bundle.manifest.get("files", {}):
        return None
    return _image_from_bytes(bundle.file_bytes(logical_name), mode)


def _bounded_int(value: Any, minimum: int, maximum: int, fallback: int) -> int:
    try:
        result = int(value)
        return result if minimum <= result <= maximum else fallback
    except (TypeError, ValueError, OverflowError):
        return fallback


def _bounded_float(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) and minimum <= result <= maximum else fallback
    except (TypeError, ValueError, OverflowError):
        return fallback


def main() -> None:
    root = tk.Tk()
    AutoDrawWorkbench(root)
    root.mainloop()


if __name__ == "__main__":
    main()
