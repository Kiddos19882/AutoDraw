from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Callable

from PIL import Image, ImageTk

from palette_detection import (
    PaletteFormatError,
    build_palette_entry,
    create_palette_document,
    detect_color_candidates,
    load_palette,
    merge_palette_entries,
    parse_hex_color,
    rgb_to_hex,
    save_palette,
)
from palette_reduction import select_representative_palette_colors
from palette_profiles import (
    PaletteProfileError,
    check_profile_freshness,
    check_profile_against_screenshot,
    create_palette_profile,
    get_windows_scale_percent,
    load_palette_profile,
    save_palette_profile,
    validate_palette_profile,
)


def map_display_rect_to_image(
    rect: tuple[float, float, float, float],
    *,
    source_size: tuple[int, int],
    display_size: tuple[int, int],
    offset: tuple[float, float] = (0.0, 0.0),
) -> tuple[int, int, int, int]:
    """Map an inclusive canvas rectangle to an image crop (left, top, width, height)."""
    x1, y1, x2, y2 = rect
    ox, oy = offset
    display_width, display_height = display_size
    source_width, source_height = source_size
    if min(display_width, display_height, source_width, source_height) <= 0:
        raise ValueError("Размеры снимка и предпросмотра должны быть положительными.")
    left_display, right_display = sorted((x1 - ox, x2 - ox))
    top_display, bottom_display = sorted((y1 - oy, y2 - oy))
    left_display = min(max(left_display, 0.0), display_width - 1.0)
    top_display = min(max(top_display, 0.0), display_height - 1.0)
    right_display = min(max(right_display, 0.0), display_width - 1.0)
    bottom_display = min(max(bottom_display, 0.0), display_height - 1.0)
    left = int(left_display * source_width / display_width)
    top = int(top_display * source_height / display_height)
    right = int((right_display + 1.0) * source_width / display_width)
    bottom = int((bottom_display + 1.0) * source_height / display_height)
    left = min(max(0, left), source_width - 1)
    top = min(max(0, top), source_height - 1)
    right = min(source_width, max(left + 1, right))
    bottom = min(source_height, max(top + 1, bottom))
    return left, top, right - left, bottom - top


class ScreenRegionPicker:
    """Modal selector for a rectangular region in a captured desktop screenshot."""

    def __init__(self, root: tk.Misc, screenshot: Image.Image, on_selected: Callable[[tuple[int, int, int, int]], None]):
        self.root = root
        self.screenshot = screenshot
        self.on_selected = on_selected
        self.selection: tuple[int, int, int, int] | None = None
        self.start: tuple[int, int] | None = None
        self.end: tuple[int, int] | None = None
        self.scale = 1.0
        self.display_size = (screenshot.width, screenshot.height)
        self.photo: ImageTk.PhotoImage | None = None

        self.window = tk.Toplevel(root)
        self.window.title("AutoDraw — выделите область палитры")
        self.window.transient(root)
        self.window.geometry("1100x730")
        self.window.minsize(620, 420)
        self.window.grab_set()

        ttk.Label(
            self.window,
            text="Зажмите левую кнопку мыши и выделите прямоугольник, в котором расположены цветовые образцы. "
                 "Затем нажмите «Использовать область».",
            wraplength=1060,
        ).pack(fill="x", padx=10, pady=(10, 6))
        self.canvas = tk.Canvas(self.window, background="#303030", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas.bind("<Configure>", lambda _event: self._render())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self._display_offset = (0.0, 0.0)

        buttons = ttk.Frame(self.window)
        buttons.pack(fill="x", padx=10, pady=(5, 10))
        self.selection_var = tk.StringVar(value="Область не выбрана.")
        ttk.Label(buttons, textvariable=self.selection_var).pack(side="left", fill="x", expand=True)
        ttk.Button(buttons, text="Отмена", command=self.window.destroy).pack(side="right", padx=(6, 0))
        self.use_button = ttk.Button(buttons, text="Использовать область", command=self._accept, state="disabled")
        self.use_button.pack(side="right")
        self.window.protocol("WM_DELETE_WINDOW", self.window.destroy)
        self.window.after(30, self._render)

    def _render(self) -> None:
        if not self.window.winfo_exists():
            return
        width = max(20, self.canvas.winfo_width() - 8)
        height = max(20, self.canvas.winfo_height() - 8)
        scale = min(width / self.screenshot.width, height / self.screenshot.height, 1.0)
        scale = max(0.05, scale)
        display_width = max(1, round(self.screenshot.width * scale))
        display_height = max(1, round(self.screenshot.height * scale))
        resized = self.screenshot.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        x0 = (self.canvas.winfo_width() - display_width) / 2
        y0 = (self.canvas.winfo_height() - display_height) / 2
        self._display_offset = (x0, y0)
        self.scale = scale
        self.display_size = (display_width, display_height)
        self.canvas.create_image(x0, y0, anchor="nw", image=self.photo)
        if self.start and self.end:
            self.canvas.create_rectangle(*self.start, *self.end, outline="#ff9f1c", width=2, dash=(4, 2))

    def _clamp_canvas(self, x: float, y: float) -> tuple[int, int] | None:
        x0, y0 = self._display_offset
        width, height = self.display_size
        if x < x0 or y < y0 or x > x0 + width or y > y0 + height:
            return None
        return (int(min(max(x - x0, 0), width - 1)), int(min(max(y - y0, 0), height - 1)))

    def _press(self, event: tk.Event) -> None:
        point = self._clamp_canvas(event.x, event.y)
        if point is None:
            self.start = self.end = None
            self._render()
            return
        ox, oy = self._display_offset
        self.start = (ox + point[0], oy + point[1])
        self.end = self.start
        self.selection = None
        self.use_button.configure(state="disabled")
        self.selection_var.set("Выделите область мышью…")
        self._render()

    def _drag(self, event: tk.Event) -> None:
        if self.start is None:
            return
        point = self._clamp_canvas(event.x, event.y)
        if point is None:
            ox, oy = self._display_offset
            width, height = self.display_size
            point = (int(min(max(event.x - ox, 0), width - 1)), int(min(max(event.y - oy, 0), height - 1)))
        ox, oy = self._display_offset
        self.end = (ox + point[0], oy + point[1])
        self._render()

    def _release(self, event: tk.Event) -> None:
        if self.start is None:
            return
        self._drag(event)
        if self.end is None:
            return
        x1, x2 = sorted((self.start[0], self.end[0]))
        y1, y2 = sorted((self.start[1], self.end[1]))
        if x2 - x1 < 4 or y2 - y1 < 4:
            self.selection = None
            self.use_button.configure(state="disabled")
            self.selection_var.set("Область слишком маленькая — выделите её ещё раз.")
            return
        self.selection = map_display_rect_to_image(
            (x1, y1, x2, y2),
            source_size=self.screenshot.size,
            display_size=self.display_size,
            offset=self._display_offset,
        )
        left, top, width, height = self.selection
        right, bottom = left + width, top + height
        self.use_button.configure(state="normal")
        self.selection_var.set(f"Область: X={left}, Y={top}, ширина={right-left}, высота={bottom-top}")

    def _accept(self) -> None:
        if self.selection is None:
            return
        selection = self.selection
        self.window.grab_release()
        self.window.destroy()
        self.on_selected(selection)


class PaletteDetectionTab:
    """Screenshot-based browser palette discovery with automatic suggestions and manual sampling."""

    def __init__(self, root: tk.Misc, parent: tk.Widget, store_dir: str | Path):
        self.root = root
        self.parent = parent
        self.store_dir = Path(store_dir).resolve()
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.profile_dir = self.store_dir / "profiles"
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot: Image.Image | None = None
        self.palette_captured_at: str | None = None
        self.region_image: Image.Image | None = None
        self.region: dict[str, int] | None = None
        self.screen_size: tuple[int, int] | None = None
        self.colors: list[dict[str, Any]] = []
        self.palette_reduction_report: dict[str, Any] | None = None
        self.active_path: Path | None = None
        self.active_profile_path: Path | None = None
        self.active_profile: dict[str, Any] | None = None
        self._calibration_screenshot: Image.Image | None = None
        self._calibration_profile_snapshot: dict[str, Any] | None = None
        self._calibration_check_active = False
        self._preview_photo: ImageTk.PhotoImage | None = None
        self._preview_rect: tuple[float, float, float, float] | None = None
        self._render_after_id: str | None = None

        outer = ttk.Frame(parent, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Этап 17 — профили и калибровка палитры браузера", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Снимите экран с открытой доской, выделите область палитры, затем запустите поиск цветных образцов "
                  "и вручную добавьте отсутствующие цвета щелчком по их центру. Это этап обнаружения и проверки палитры; "
                  "цветное рисование пока не выполняется. Сохранённые профили можно перепроверить по новому снимку."),
            wraplength=1220,
        ).pack(anchor="w", pady=(3, 9))

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Button(toolbar, text="Снять экран через 3 секунды…", command=self.request_screenshot).pack(side="left")
        ttk.Button(toolbar, text="Выделить область палитры…", command=self.choose_region).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Автопоиск цветных образцов", command=self.auto_detect).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Оставить 32 основных цвета", command=self._ensure_palette_limit).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Загрузить палитру…", command=self.load_dialog).pack(side="right")
        ttk.Button(toolbar, text="Сохранить палитру…", command=self.save_dialog).pack(side="right", padx=(0, 6))

        profile_toolbar = ttk.LabelFrame(outer, text="Профиль палитры и калибровка", padding=(8, 5))
        profile_toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(profile_toolbar, text="Имя:").grid(row=0, column=0, sticky="w")
        self.profile_name_var = tk.StringVar(value="Browser palette")
        ttk.Entry(profile_toolbar, textvariable=self.profile_name_var, width=23).grid(row=0, column=1, padx=(4, 12), sticky="w")
        ttk.Label(profile_toolbar, text="Браузер/доска:").grid(row=0, column=2, sticky="w")
        self.browser_label_var = tk.StringVar(value="")
        ttk.Entry(profile_toolbar, textvariable=self.browser_label_var, width=19).grid(row=0, column=3, padx=(4, 12), sticky="w")
        ttk.Label(profile_toolbar, text="Масштаб Windows, %:").grid(row=0, column=4, sticky="w")
        self.dpi_scale_var = tk.StringVar(value=str(get_windows_scale_percent()))
        ttk.Spinbox(profile_toolbar, from_=50, to=300, increment=5, textvariable=self.dpi_scale_var, width=5).grid(
            row=0, column=5, padx=(4, 12), sticky="w"
        )
        ttk.Button(profile_toolbar, text="Сохранить профиль…", command=self.save_profile_dialog).grid(row=0, column=6, padx=(0, 5))
        ttk.Button(profile_toolbar, text="Загрузить профиль…", command=self.load_profile_dialog).grid(row=0, column=7, padx=(0, 5))
        ttk.Button(profile_toolbar, text="Проверить калибровку…", command=self.check_calibration).grid(row=0, column=8)
        ttk.Label(profile_toolbar, text="Сохранённые профили:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.saved_profile_var = tk.StringVar(value="")
        self.saved_profile_combo = ttk.Combobox(
            profile_toolbar, textvariable=self.saved_profile_var, state="readonly", width=36,
        )
        self.saved_profile_combo.grid(row=1, column=1, columnspan=3, sticky="w", padx=(4, 12), pady=(6, 0))
        ttk.Button(profile_toolbar, text="Обновить список", command=self.refresh_saved_profiles).grid(
            row=1, column=4, padx=(0, 5), pady=(6, 0)
        )
        ttk.Button(profile_toolbar, text="Открыть выбранный", command=self.load_selected_profile).grid(
            row=1, column=5, padx=(0, 5), pady=(6, 0)
        )
        ttk.Button(profile_toolbar, text="Удалить выбранный", command=self.delete_selected_profile).grid(
            row=1, column=6, columnspan=2, sticky="w", pady=(6, 0)
        )

        splitter = ttk.Panedwindow(outer, orient="horizontal")
        splitter.pack(fill="both", expand=True)
        preview_frame = ttk.LabelFrame(splitter, text="Область палитры — щёлкните по центру образца, чтобы добавить цвет", padding=6)
        table_frame = ttk.LabelFrame(splitter, text="Обнаруженные цвета", padding=6)
        splitter.add(preview_frame, weight=3)
        splitter.add(table_frame, weight=2)

        self.preview_canvas = tk.Canvas(preview_frame, background="#303030", highlightthickness=1, highlightbackground="#9b9b9b", cursor="crosshair")
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", self._schedule_preview_render)
        self.preview_canvas.bind("<Button-1>", self._on_preview_click)

        self.table = ttk.Treeview(
            table_frame,
            columns=("name", "hex", "rgb", "x", "y", "source", "status"),
            show="headings",
            height=16,
            selectmode="browse",
        )
        for key, title, width in (
            ("name", "Имя", 78), ("hex", "HEX", 78), ("rgb", "RGB", 98), ("x", "X", 62),
            ("y", "Y", 62), ("source", "Источник", 74), ("status", "Статус", 94),
        ):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=55, stretch=key in ("hex", "rgb"))
        table_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=table_scroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        table_scroll.pack(side="right", fill="y")

        table_buttons = ttk.Frame(outer)
        table_buttons.pack(fill="x", pady=(8, 4))
        ttk.Button(table_buttons, text="Изменить HEX выбранного…", command=self.edit_selected_hex).pack(side="left")
        ttk.Button(table_buttons, text="Имя выбранного…", command=self.edit_selected_name).pack(side="left", padx=(6, 0))
        ttk.Button(table_buttons, text="Подтвердить выбранный", command=self.confirm_selected_color).pack(side="left", padx=(6, 0))
        ttk.Button(table_buttons, text="Подтвердить все…", command=self.confirm_all_colors).pack(side="left", padx=(6, 0))
        ttk.Button(table_buttons, text="Удалить выбранный", command=self.remove_selected).pack(side="left", padx=(6, 0))
        ttk.Button(table_buttons, text="Очистить список", command=self.clear_colors).pack(side="left", padx=(6, 0))
        self.status_var = tk.StringVar(value="Готово. Сначала снимите экран с открытой палитрой в браузере.")
        ttk.Label(outer, textvariable=self.status_var, wraplength=1220).pack(fill="x", pady=(6, 0))
        self.refresh_saved_profiles()
        self._render_preview()

    def request_screenshot(self) -> None:
        self._calibration_check_active = False
        self.status_var.set("Переключитесь на браузер и оставьте палитру видимой. Снимок будет сделан через 3 секунды…")
        self.root.after(3000, self._capture_screenshot)

    def _capture_screenshot(self) -> None:
        try:
            import pyautogui
            image = pyautogui.screenshot().convert("RGB")
        except Exception as exc:
            self.status_var.set(f"Не удалось снять экран: {exc}")
            messagebox.showerror(
                "Ошибка снимка экрана",
                "Не удалось получить снимок экрана. Проверьте разрешения захвата экрана и доступность PyAutoGUI.\n\n" + str(exc),
                parent=self.root,
            )
            return
        self.screenshot = image
        self.palette_captured_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self.status_var.set(f"Снимок получен: {image.width}×{image.height}. Выделите прямоугольную область палитры.")
        self._open_region_picker()

    def _open_region_picker(self) -> None:
        if self.screenshot is None:
            self.status_var.set("Сначала снимите экран.")
            return
        ScreenRegionPicker(self.root, self.screenshot, self._apply_selected_region)

    def choose_region(self) -> None:
        if self.screenshot is None:
            messagebox.showinfo("Нет снимка", "Сначала нажмите «Снять экран через 3 секунды…» и переключитесь на браузер.", parent=self.root)
            return
        self._open_region_picker()

    def _apply_selected_region(self, selection: tuple[int, int, int, int]) -> None:
        left, top, width, height = selection
        if self.colors:
            should_clear = messagebox.askyesno(
                "Изменение области палитры",
                "Выбранная область изменилась. Очистить текущие цвета, чтобы случайно не сохранить старые координаты?",
                parent=self.root,
            )
            if not should_clear:
                return
            self.colors.clear()
            self._refresh_table()
        assert self.screenshot is not None
        self.region = {"x": left, "y": top, "width": width, "height": height}
        self.palette_reduction_report = None
        self.region_image = self.screenshot.crop((left, top, left + width, top + height)).convert("RGB")
        self.screen_size = self.screenshot.size
        self.active_path = None
        self.active_profile_path = None
        self.active_profile = None
        self._render_preview()
        self.status_var.set(
            f"Область выбрана: X={left}, Y={top}, {width}×{height}. "
            "Запустите автопоиск и вручную добавьте серые, белые и чёрные образцы, если они есть."
        )

    def auto_detect(self) -> None:
        if self.region_image is None or self.region is None:
            messagebox.showinfo("Не выбрана область", "Сначала снимите экран и выделите область палитры.", parent=self.root)
            return
        try:
            candidates = detect_color_candidates(
                self.region_image,
                origin_x=self.region["x"],
                origin_y=self.region["y"],
            )
            self.colors, added = merge_palette_entries(self.colors, candidates)
            if added:
                self.palette_reduction_report = None
            self._refresh_table()
            self.status_var.set(
                f"Автопоиск: найдено кандидатов {len(candidates)}, добавлено новых цветов {added}. "
                "Проверьте координаты и HEX; недостающие образцы добавьте щелчком по превью."
            )
        except Exception as exc:
            self.status_var.set(f"Автопоиск завершился ошибкой: {exc}")
            messagebox.showerror("Ошибка автопоиска", str(exc), parent=self.root)

    def _schedule_preview_render(self, _event=None) -> None:
        if self._render_after_id is not None:
            try:
                self.root.after_cancel(self._render_after_id)
            except tk.TclError:
                pass
        self._render_after_id = self.root.after(40, self._render_preview)

    def _render_preview(self) -> None:
        self._render_after_id = None
        if not self.preview_canvas.winfo_exists():
            return
        self.preview_canvas.delete("all")
        self._preview_photo = None
        self._preview_rect = None
        width = max(2, self.preview_canvas.winfo_width())
        height = max(2, self.preview_canvas.winfo_height())
        if self.region_image is None:
            self.preview_canvas.create_text(
                width / 2, height / 2,
                text="Снимите экран и выделите область палитры",
                fill="#eeeeee", width=max(200, width - 30),
            )
            return
        available_width = max(1, width - 12)
        available_height = max(1, height - 12)
        scale = min(available_width / self.region_image.width, available_height / self.region_image.height, 4.0)
        display_width = max(1, round(self.region_image.width * scale))
        display_height = max(1, round(self.region_image.height * scale))
        display = self.region_image.resize((display_width, display_height), Image.Resampling.NEAREST)
        self._preview_photo = ImageTk.PhotoImage(display)
        x0 = (width - display_width) / 2
        y0 = (height - display_height) / 2
        self._preview_rect = (x0, y0, x0 + display_width, y0 + display_height)
        self.preview_canvas.create_image(x0, y0, anchor="nw", image=self._preview_photo)
        for item in self.colors:
            lx = int(item.get("local_x", -1))
            ly = int(item.get("local_y", -1))
            if 0 <= lx < self.region_image.width and 0 <= ly < self.region_image.height:
                px = x0 + (lx + 0.5) * display_width / self.region_image.width
                py = y0 + (ly + 0.5) * display_height / self.region_image.height
                self.preview_canvas.create_oval(px - 4, py - 4, px + 4, py + 4, outline="#ffffff", width=2)
                self.preview_canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill=item["hex"], outline="#000000")

    def _on_preview_click(self, event: tk.Event) -> None:
        if self.region_image is None or self.region is None or self._preview_rect is None:
            return
        x0, y0, x1, y1 = self._preview_rect
        if not (x0 <= event.x < x1 and y0 <= event.y < y1):
            return
        local_x = int((event.x - x0) * self.region_image.width / max(1, x1 - x0))
        local_y = int((event.y - y0) * self.region_image.height / max(1, y1 - y0))
        local_x = min(self.region_image.width - 1, max(0, local_x))
        local_y = min(self.region_image.height - 1, max(0, local_y))
        try:
            entry = build_palette_entry(
                self.region_image,
                local_x,
                local_y,
                origin_x=self.region["x"],
                origin_y=self.region["y"],
                source="manual",
                radius=2,
            )
        except ValueError as exc:
            self.status_var.set(str(exc))
            return
        if any(existing["hex"].upper() == entry["hex"].upper() for existing in self.colors):
            self.status_var.set(f"Цвет {entry['hex']} уже есть в списке. Выберите центр другого образца.")
            return
        entry["name"] = f"Цвет {len(self.colors) + 1}"
        entry["status"] = "detected"
        self.palette_reduction_report = None
        self.colors.append(entry)
        self._refresh_table()
        self._render_preview()
        self.status_var.set(
            f"Добавлен {entry['hex']} RGB{tuple(entry['rgb'])} по экранным координатам "
            f"({entry['screen_x']}, {entry['screen_y']})."
        )

    def _refresh_table(self) -> None:
        selected_hex = None
        selection = self.table.selection() if hasattr(self, "table") else ()
        if selection:
            try:
                selected_hex = self.table.item(selection[0], "values")[1]
            except (IndexError, tk.TclError):
                pass
        for row in self.table.get_children():
            self.table.delete(row)
        for index, item in enumerate(self.colors, start=1):
            status = item.get("status") or ("corrected" if item.get("source") == "manual-edit" else "detected")
            status_label = {"detected": "Найден", "confirmed": "Подтверждён", "corrected": "Исправлен"}.get(status, status)
            self.table.insert(
                "", "end", iid=f"palette-{index}",
                values=(item.get("name", f"Цвет {index}"), item["hex"], tuple(item["rgb"]), item["screen_x"], item["screen_y"], item.get("source", "manual"), status_label),
            )
            if selected_hex and item["hex"] == selected_hex:
                self.table.selection_set(f"palette-{index}")
        self._render_preview()

    def _selected_index(self) -> int | None:
        selected = self.table.selection()
        if not selected:
            return None
        try:
            return int(selected[0].split("-", 1)[1]) - 1
        except (ValueError, IndexError):
            return None

    def edit_selected_hex(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Цвет не выбран", "Выберите строку в таблице.", parent=self.root)
            return
        entry = self.colors[index]
        value = simpledialog.askstring(
            "Изменение цвета",
            "Введите правильный HEX-цвет (например, #E84E43). Координаты выбора не изменятся.",
            initialvalue=entry["hex"], parent=self.root,
        )
        if value is None:
            return
        try:
            rgb = parse_hex_color(value)
        except ValueError as exc:
            messagebox.showerror("Некорректный HEX", str(exc), parent=self.root)
            return
        hex_value = rgb_to_hex(rgb)
        if any(i != index and item["hex"] == hex_value for i, item in enumerate(self.colors)):
            messagebox.showwarning("Дубликат", f"Цвет {hex_value} уже присутствует.", parent=self.root)
            return
        entry["hex"] = hex_value
        entry["rgb"] = list(rgb)
        entry["source"] = "manual-edit"
        entry["status"] = "corrected"
        self.palette_reduction_report = None
        self._refresh_table()
        self.status_var.set(f"Цвет обновлён: {hex_value}. Перед использованием проверьте соответствие образцу на экране.")

    def edit_selected_name(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Цвет не выбран", "Выберите строку в таблице.", parent=self.root)
            return
        item = self.colors[index]
        value = simpledialog.askstring(
            "Имя цвета", "Введите понятное имя цвета (например, Небо или Трава):",
            initialvalue=item.get("name", f"Цвет {index + 1}"), parent=self.root,
        )
        if value is None:
            return
        value = value.strip()
        if not value:
            messagebox.showwarning("Пустое имя", "Имя цвета не может быть пустым.", parent=self.root)
            return
        item["name"] = value[:80]
        self._refresh_table()
        self.status_var.set(f"Имя цвета изменено: {item['name']}.")

    def confirm_selected_color(self) -> None:
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Цвет не выбран", "Выберите строку в таблице.", parent=self.root)
            return
        item = self.colors[index]
        item["status"] = "confirmed"
        self._refresh_table()
        self.status_var.set(
            f"Цвет {item.get('name', item['hex'])} отмечен как подтверждённый. "
            "Подтверждение здесь означает, что вы проверили образец и координату вручную."
        )

    def confirm_all_colors(self) -> None:
        if not self.colors:
            return
        if not messagebox.askyesno(
            "Подтвердить все цвета",
            "Отметить все цвета как проверенные вручную? Выполняйте это только если действительно проверили каждый образец.",
            parent=self.root,
        ):
            return
        for item in self.colors:
            item["status"] = "confirmed"
        self._refresh_table()
        self.status_var.set(f"Подтверждены все цвета: {len(self.colors)}.")

    def remove_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            return
        removed = self.colors.pop(index)
        self.palette_reduction_report = None
        self._refresh_table()
        self.status_var.set(f"Удалён цвет {removed['hex']}.")

    def clear_colors(self) -> None:
        if not self.colors:
            return
        if not messagebox.askyesno("Очистить палитру", "Удалить все найденные цвета?", parent=self.root):
            return
        self.colors.clear()
        self.palette_reduction_report = None
        self._refresh_table()
        self.status_var.set("Список цветов очищен.")

    def _ensure_palette_limit(self) -> bool:
        """Reduce a large palette to 32 real, representative game swatches."""
        if len(self.colors) <= 32:
            self.status_var.set(f"В палитре {len(self.colors)} цветов; сокращение до 32 не требуется.")
            return True
        if not messagebox.askyesno(
            "Сократить палитру до 32 цветов",
            f"Найдено {len(self.colors)} цветов. AutoDraw выберет 32 репрезентативных цвета из исходных образцов. "
            "RGB и экранные координаты выбранных образцов сохранятся; остальные цвета не войдут в активный список. "
            "Это уменьшит число доступных оттенков в преобразовании. Продолжить?",
            parent=self.root,
        ):
            return False
        try:
            reduced, report = select_representative_palette_colors(self.colors, target_count=32)
        except (ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Не удалось сократить палитру", str(exc), parent=self.root)
            return False
        self.colors = reduced
        self.palette_reduction_report = report
        self._refresh_table()
        preserved = ", ".join(report.get("preserved_required_colors", [])) or "нет обязательных цветов в исходной палитре"
        missing = ", ".join(report.get("missing_required_colors", [])) or "нет"
        self.status_var.set(
            f"Палитра сокращена: {report['input_color_count']} → {report['output_color_count']} реальных образцов. "
            f"Обязательные цвета сохранены: {preserved}; отсутствуют в источнике: {missing}. "
            f"Среднее отличие ΔE76={report['mean_delta_e76']:.2f}; "
            f"максимум={report['max_delta_e76']:.2f}. Координаты образцов сохранены."
        )
        return True

    def _current_palette_document(self) -> dict[str, Any]:
        if self.region is None or self.screen_size is None:
            raise PaletteProfileError("Сначала снимите экран и выделите область палитры.")
        if not self.colors:
            raise PaletteProfileError("Нельзя сохранить пустую палитру.")
        return create_palette_document(
            self.colors,
            screen_size=self.screen_size,
            region=self.region,
            metadata={
                "source": "desktop-screenshot",
                "method": "screenshot-assisted",
                **({"captured_at": self.palette_captured_at} if self.palette_captured_at else {}),
                **({"palette_reduction": self.palette_reduction_report} if self.palette_reduction_report else {}),
            },
        )

    def _make_current_profile(self) -> dict[str, Any]:
        palette_document = self._current_palette_document()
        scale_text = self.dpi_scale_var.get().strip()
        try:
            scale = int(scale_text)
        except ValueError as exc:
            raise PaletteProfileError("Масштаб Windows должен быть целым числом от 50 до 300.") from exc
        profile_name = self.profile_name_var.get().strip()
        previous = None
        if self.active_profile and self.active_profile.get("profile_name") == profile_name:
            previous = self.active_profile
        profile = create_palette_profile(
            palette_document,
            profile_name,
            browser_label=self.browser_label_var.get(),
            dpi_scale_percent=scale,
            previous_profile=previous,
        )
        # Preserve explicit status/id metadata held by the current UI state.
        current_by_hex = {str(item.get("hex", "")).upper(): item for item in self.colors}
        for item in profile["colors"]:
            current = current_by_hex.get(item["hex"].upper())
            if current:
                if current.get("id"):
                    item["id"] = current["id"]
                if current.get("status") in {"detected", "confirmed", "corrected"}:
                    item["status"] = current["status"]
                item["name"] = str(current.get("name") or item["name"])
        return validate_palette_profile(profile)

    def save_profile_dialog(self) -> None:
        if not self._ensure_palette_limit():
            return
        try:
            profile = self._make_current_profile()
        except (PaletteProfileError, ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Не удалось создать профиль", str(exc), parent=self.root)
            return
        suggested = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in profile["profile_name"]).strip()
        suggested = (suggested or "browser_palette").replace(" ", "_") + ".autodraw-palette.json"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить профиль палитры",
            initialdir=str(self.profile_dir),
            initialfile=suggested,
            defaultextension=".json",
            filetypes=(("Профиль палитры AutoDraw", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            actual = save_palette_profile(path, profile)
        except (OSError, PaletteProfileError, ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Не удалось сохранить профиль", str(exc), parent=self.root)
            return
        self.active_profile = profile
        self.active_profile_path = actual
        self.colors = [dict(item) for item in profile["colors"]]
        self.profile_name_var.set(profile["profile_name"])
        self.status_var.set(
            f"Профиль сохранён: {actual.name}. Цветов: {len(profile['colors'])}; "
            f"подтверждено: {sum(c['status'] == 'confirmed' for c in profile['colors'])}; "
            f"исправлено: {sum(c['status'] == 'corrected' for c in profile['colors'])}."
        )
        self._refresh_table()
        self.refresh_saved_profiles()

    def load_profile_dialog(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть профиль палитры",
            initialdir=str(self.profile_dir),
            filetypes=(("Профили палитры AutoDraw", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            profile = load_palette_profile(path)
        except (OSError, PaletteProfileError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось открыть профиль", str(exc), parent=self.root)
            return
        self._install_profile(profile, Path(path).resolve())

    def refresh_saved_profiles(self) -> None:
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        names = sorted((item.name for item in self.profile_dir.glob("*.json") if item.is_file()), key=str.casefold)
        self.saved_profile_combo.configure(values=names)
        preferred = self.active_profile_path.name if self.active_profile_path and self.active_profile_path.parent == self.profile_dir else ""
        current = self.saved_profile_var.get()
        if preferred in names:
            self.saved_profile_var.set(preferred)
        elif current in names:
            self.saved_profile_var.set(current)
        else:
            self.saved_profile_var.set(names[0] if names else "")

    def load_selected_profile(self) -> None:
        selected = self.saved_profile_var.get().strip()
        if not selected:
            messagebox.showinfo("Профиль не выбран", "Сначала сохраните профиль или выберите его в списке.", parent=self.root)
            return
        path = (self.profile_dir / selected).resolve()
        try:
            # Restrict selection to the managed profile directory.
            if path.parent != self.profile_dir.resolve() or not path.is_file():
                raise PaletteProfileError("Выбранный файл отсутствует в каталоге профилей.")
            profile = load_palette_profile(path)
        except (OSError, PaletteProfileError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось открыть профиль", str(exc), parent=self.root)
            return
        self._install_profile(profile, path)

    def delete_selected_profile(self) -> None:
        selected = self.saved_profile_var.get().strip()
        if not selected:
            messagebox.showinfo("Профиль не выбран", "Выберите профиль в списке.", parent=self.root)
            return
        path = (self.profile_dir / selected).resolve()
        if path.parent != self.profile_dir.resolve() or path.suffix.lower() != ".json" or not path.is_file():
            messagebox.showerror("Нельзя удалить профиль", "Файл не находится в каталоге профилей AutoDraw.", parent=self.root)
            return
        if not messagebox.askyesno("Удалить профиль", f"Удалить профиль «{selected}»? Это удалит файл профиля.", parent=self.root):
            return
        try:
            path.unlink()
        except OSError as exc:
            messagebox.showerror("Не удалось удалить профиль", str(exc), parent=self.root)
            return
        if self.active_profile_path and self.active_profile_path.resolve() == path:
            self.active_profile_path = None
            self.active_profile = None
        self.refresh_saved_profiles()
        self.status_var.set(f"Профиль удалён: {selected}.")

    def _install_profile(self, profile: dict[str, Any], path: Path) -> None:
        self.active_profile = profile
        self.active_profile_path = path.resolve()
        self.profile_name_var.set(profile["profile_name"])
        self.browser_label_var.set(profile["calibration"]["browser_label"])
        self.dpi_scale_var.set(str(profile["calibration"]["dpi_scale_percent"]))
        self.screen_size = (profile["screen"]["width"], profile["screen"]["height"])
        self.region = dict(profile["region"])
        self.colors = [dict(item) for item in profile["colors"]]
        reduction = profile.get("metadata", {}).get("palette_reduction")
        self.palette_reduction_report = reduction if isinstance(reduction, dict) else None
        # The saved profile intentionally does not contain a screenshot. Users need a fresh
        # capture to validate coordinates/colors or to view the source region again.
        self.screenshot = None
        self.region_image = None
        self.palette_captured_at = profile["calibration"].get("captured_at")
        self._refresh_table()
        screen_now = self._get_current_screen_size()
        freshness = check_profile_freshness(
            profile,
            current_screen_size=screen_now,
            current_region=None,
            current_dpi_scale_percent=get_windows_scale_percent(),
            observed_colors=None,
        )
        if freshness["status"] == "stale":
            detail = "\n".join(freshness["issues"])
            messagebox.showwarning(
                "Требуется перекалибровка",
                "Часть сохранённых настроек не совпадает с текущей системой:\n\n" + detail +
                "\n\nНе используйте старые координаты, пока не проверите калибровку.",
                parent=self.root,
            )
        self.status_var.set(
            f"Загружен профиль «{profile['profile_name']}»: {len(self.colors)} цветов. "
            "Координаты пока не считаются проверенными — нажмите «Проверить калибровку…». "
            f"Текущее состояние: {'устарел' if freshness['status'] == 'stale' else 'не проверен'}."
        )
        self.refresh_saved_profiles()

    @staticmethod
    def _get_current_screen_size() -> tuple[int, int] | None:
        try:
            import pyautogui
            size = pyautogui.size()
            return int(size.width), int(size.height)
        except Exception:
            return None

    def check_calibration(self) -> None:
        try:
            self._calibration_profile_snapshot = self._make_current_profile()
        except (PaletteProfileError, ValueError, TypeError, KeyError) as exc:
            messagebox.showinfo("Нет палитры для проверки", str(exc), parent=self.root)
            return
        self._calibration_check_active = True
        region = self._calibration_profile_snapshot["region"]
        self.status_var.set(
            "Переключитесь в браузер; через 3 секунды будет сделан снимок. "
            f"Проверка пройдёт автоматически по сохранённой области "
            f"({region['x']}, {region['y']}, {region['width']}×{region['height']}) — "
            "повторно выделять область не нужно."
        )
        self.root.after(3000, self._capture_calibration_screenshot)

    def _capture_calibration_screenshot(self) -> None:
        if not self._calibration_check_active:
            return
        try:
            import pyautogui
            self._calibration_screenshot = pyautogui.screenshot().convert("RGB")
        except Exception as exc:
            self._calibration_check_active = False
            self._calibration_profile_snapshot = None
            self.status_var.set(f"Не удалось снять экран для проверки: {exc}")
            messagebox.showerror("Ошибка снимка экрана", str(exc), parent=self.root)
            return

        profile = self._calibration_profile_snapshot
        screenshot = self._calibration_screenshot
        self._calibration_check_active = False
        self._calibration_screenshot = None
        self._calibration_profile_snapshot = None
        if profile is None or screenshot is None:
            self.status_var.set("Проверка калибровки отменена: отсутствуют данные профиля или снимок.")
            return

        try:
            result = check_profile_against_screenshot(
                profile,
                screenshot,
                current_dpi_scale_percent=get_windows_scale_percent(
                    default=int(self.dpi_scale_var.get())
                ),
            )
            if result["status"] == "current":
                text = (
                    f"Калибровка соответствует текущей системе. Проверено цветов: {len(profile['colors'])}. "
                    "Область взята из сохранённого профиля; повторное выделение не потребовалось."
                )
                self.status_var.set(text)
                messagebox.showinfo("Калибровка актуальна", text, parent=self.root)
            else:
                parts = result["issues"] + result["warnings"]
                text = "\n".join(f"• {part}" for part in parts) or "Калибровку не удалось подтвердить."
                self.status_var.set("Калибровка устарела или проверена не полностью. Посмотрите подробности.")
                messagebox.showwarning(
                    "Калибровку нужно проверить",
                    text + "\n\nКоординаты профиля не изменены автоматически.",
                    parent=self.root,
                )
        except (PaletteProfileError, ValueError, TypeError, KeyError) as exc:
            self.status_var.set(f"Ошибка проверки калибровки: {exc}")
            messagebox.showerror("Ошибка калибровки", str(exc), parent=self.root)

    def save_dialog(self) -> None:
        if self.region is None or self.screen_size is None:
            messagebox.showinfo("Нет области", "Сначала снимите экран и выделите область палитры.", parent=self.root)
            return
        if not self.colors:
            messagebox.showinfo("Палитра пуста", "Найдите или добавьте хотя бы один цвет.", parent=self.root)
            return
        if not self._ensure_palette_limit():
            return
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Сохранить палитру браузера",
            initialdir=str(self.store_dir),
            initialfile="browser_palette.json",
            defaultextension=".json",
            filetypes=(("Палитра AutoDraw", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            document = create_palette_document(
                self.colors,
                screen_size=self.screen_size,
                region=self.region,
                metadata={
                    "source": "desktop-screenshot",
                    "method": "screenshot-assisted",
                    **({"captured_at": self.palette_captured_at} if self.palette_captured_at else {}),
                    **({"palette_reduction": self.palette_reduction_report} if self.palette_reduction_report else {}),
                },
            )
            actual = save_palette(path, document)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            messagebox.showerror("Не удалось сохранить палитру", str(exc), parent=self.root)
            return
        self.active_path = actual
        self.status_var.set(f"Палитра сохранена: {actual} ({len(self.colors)} цветов).")

    def load_dialog(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть палитру браузера",
            initialdir=str(self.store_dir),
            filetypes=(("Палитра AutoDraw", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            document = load_palette(path)
        except (PaletteFormatError, OSError, ValueError) as exc:
            messagebox.showerror("Не удалось открыть палитру", str(exc), parent=self.root)
            return
        self.screen_size = (document["screen"]["width"], document["screen"]["height"])
        self.region = dict(document["region"])
        self.colors = [dict(item) for item in document["colors"]]
        reduction = document.get("metadata", {}).get("palette_reduction")
        self.palette_reduction_report = reduction if isinstance(reduction, dict) else None
        self.screenshot = None
        self.region_image = None
        self.palette_captured_at = str(document.get("metadata", {}).get("captured_at") or document.get("created_at") or "") or None
        self.active_profile = None
        self.active_profile_path = None
        self.profile_name_var.set(str(document.get("metadata", {}).get("profile_name") or "Импортированная палитра"))
        self.browser_label_var.set(str(document.get("metadata", {}).get("browser_label") or ""))
        self.dpi_scale_var.set(str(document.get("metadata", {}).get("dpi_scale_percent") or get_windows_scale_percent()))
        self.active_path = Path(path).resolve()
        self._refresh_table()
        self.status_var.set(
            f"Загружена палитра {self.active_path.name}: {len(self.colors)} цветов. "
            "Координаты относятся к сохранённому разрешению экрана; перед использованием сделайте новый снимок и проверьте область."
        )
