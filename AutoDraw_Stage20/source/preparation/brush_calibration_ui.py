from __future__ import annotations

"""Tkinter UI for independent screen-coordinate calibration of the brush test."""

import json
import platform
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import pyautogui
from PIL import ImageGrab, Image, ImageTk

from brush_calibration import (
    BrushCalibrationError,
    REGION_KEYS,
    adapt_profile_to_screen,
    create_default_profile,
    load_profile,
    missing_required_fields,
    normalize_point,
    normalize_region,
    save_profile,
    validate_profile,
)

POINT_LABELS = {
    "clear_board": ("Кнопка «Очистить доску»", True),
    "brush_7": ("Выбрать кисть 7", False),
    "brush_14": ("Выбрать кисть 14", False),
    "brush_20": ("Выбрать кисть 20", False),
    "brush_slider_value_1": ("Ползунок: положение кисти 1", False),
    "brush_slider_value_30": ("Ползунок: положение кисти 30", False),
    "editor_open": ("Открыть редактор (необязательно)", False),
    "save_drawing": ("Сохранить рисунок (необязательно)", True),
}
REGION_LABELS = {
    "board_area": ("Область самой доски", True),
    "paint_meter_area": ("Область полоски краски", True),
    "brush_value_area": ("Область индикатора размера кисти (необязательно)", False),
}


class ScreenPointPicker:
    """Full-screen translucent picker returning one primary-screen point."""

    def __init__(self, parent: tk.Tk, instruction: str, on_done: Callable[[tuple[int, int] | None], None]):
        self.parent = parent
        self.on_done = on_done
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.width, self.height = self._screen_size()
        self.window.overrideredirect(True)
        self.window.geometry(f"{self.width}x{self.height}+0+0")
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-alpha", 0.32)
        except tk.TclError:
            pass
        self.window.configure(bg="#202020")
        self.canvas = tk.Canvas(self.window, bg="#202020", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(20, 20, anchor="nw", fill="white", font=("Segoe UI", 15, "bold"),
                                text=instruction + "\nКликните нужную точку. Esc — отмена.")
        self.coords_id = self.canvas.create_text(self.width - 20, 20, anchor="ne", fill="#ffeb3b",
                                                  font=("Consolas", 12, "bold"), text="X=0 Y=0")
        self.vline = self.canvas.create_line(0, 0, 0, self.height, fill="#ffeb3b", dash=(4, 4))
        self.hline = self.canvas.create_line(0, 0, self.width, 0, fill="#ffeb3b", dash=(4, 4))
        self.canvas.tag_lower(self.vline)
        self.canvas.tag_lower(self.hline)
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<ButtonPress-1>", self._select)
        self.window.bind("<Escape>", self._cancel)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    @staticmethod
    def _screen_size() -> tuple[int, int]:
        size = pyautogui.size()
        return int(size.width), int(size.height)

    def _motion(self, event) -> None:
        x, y = int(event.x), int(event.y)
        self.canvas.coords(self.vline, x, 0, x, self.height)
        self.canvas.coords(self.hline, 0, y, self.width, y)
        self.canvas.itemconfigure(self.coords_id, text=f"X={x} Y={y}")

    def _select(self, event) -> None:
        point = (int(event.x), int(event.y))
        self.window.destroy()
        self.on_done(point)

    def _cancel(self, _event=None) -> None:
        self.window.destroy()
        self.on_done(None)


class ScreenRegionPicker:
    """Full-screen drag selector that also supports thin meter-bar regions."""

    def __init__(self, parent: tk.Tk, instruction: str, on_done: Callable[[dict[str, int] | None], None]):
        self.parent = parent
        self.on_done = on_done
        self.start: tuple[int, int] | None = None
        size = pyautogui.size()
        self.width, self.height = int(size.width), int(size.height)
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.geometry(f"{self.width}x{self.height}+0+0")
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-alpha", 0.32)
        except tk.TclError:
            pass
        self.window.configure(bg="#202020")
        self.canvas = tk.Canvas(self.window, bg="#202020", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(20, 20, anchor="nw", fill="white", font=("Segoe UI", 15, "bold"),
                                text=instruction + "\nЗажмите левую кнопку и выделите прямоугольник. Esc — отмена.")
        self.coords_id = self.canvas.create_text(self.width - 20, 20, anchor="ne", fill="#ffeb3b",
                                                  font=("Consolas", 12, "bold"), text="")
        self.rect_id: int | None = None
        self.canvas.bind("<Motion>", self._motion)
        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish)
        self.window.bind("<Escape>", self._cancel)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _motion(self, event) -> None:
        self.canvas.itemconfigure(self.coords_id, text=f"X={int(event.x)} Y={int(event.y)}")

    def _start(self, event) -> None:
        self.start = (int(event.x), int(event.y))
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                    outline="#00ff90", width=3)

    def _drag(self, event) -> None:
        if self.start is not None and self.rect_id is not None:
            self.canvas.coords(self.rect_id, self.start[0], self.start[1], event.x, event.y)

    def _finish(self, event) -> None:
        if self.start is None:
            return
        try:
            region = normalize_region(
                self.start[0], self.start[1], int(event.x), int(event.y),
                (self.width, self.height), min_width=2, min_height=2,
            )
        except BrushCalibrationError as exc:
            messagebox.showwarning("Некорректная область", str(exc), parent=self.window)
            self.start = None
            return
        self.window.destroy()
        self.on_done(region)

    def _cancel(self, _event=None) -> None:
        self.window.destroy()
        self.on_done(None)


class BrushCalibrationTab:
    """Separate point/region calibration profile for repeatable brush experiments."""

    def __init__(
        self,
        root: tk.Tk,
        parent: tk.Widget,
        profile_path: str | Path,
        *,
        on_profile_saved: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.root = root
        self.profile_path = Path(profile_path).expanduser().resolve()
        self.on_profile_saved = on_profile_saved
        self.profile: dict[str, Any]
        self._dirty = False
        self._point_rows: dict[str, tuple[ttk.Label, ttk.Label]] = {}
        self._region_rows: dict[str, tuple[ttk.Label, ttk.Label]] = {}
        self._env_vars = {
            "browser": tk.StringVar(),
            "browser_version": tk.StringVar(),
            "browser_zoom_percent": tk.StringVar(value="100"),
            "windows_scale_percent": tk.StringVar(),
        }
        self.status_var = tk.StringVar(value="Профиль ещё не сохранён.")
        self.summary_var = tk.StringVar(value="")
        self._load_initial_profile()
        self._build(parent)
        self._refresh_view()

    @staticmethod
    def _screen_size() -> tuple[int, int]:
        size = pyautogui.size()
        return int(size.width), int(size.height)

    def _load_initial_profile(self) -> None:
        size = self._screen_size()
        if self.profile_path.is_file():
            try:
                self.profile = load_profile(self.profile_path)
                self.profile, changed = adapt_profile_to_screen(self.profile, size)
                if changed:
                    self._dirty = True
                    self.status_var.set("Разрешение изменилось: координаты помечены для проверки. Сохрани профиль после проверки.")
            except (OSError, BrushCalibrationError) as exc:
                # Keep the damaged file untouched; do not silently overwrite user data.
                self.profile = create_default_profile(size)
                self.status_var.set(f"Профиль не загружен; исходный файл сохранён без изменений: {exc}")
        else:
            self.profile = create_default_profile(size)
        self._sync_environment_vars()

    def _sync_environment_vars(self) -> None:
        env = self.profile["environment"]
        for key, variable in self._env_vars.items():
            value = env.get(key)
            variable.set("" if value is None else str(value))

    def _build(self, parent: tk.Widget) -> None:
        host = ttk.Frame(parent)
        host.pack(fill="both", expand=True)
        canvas = tk.Canvas(host, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(host, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        outer = ttk.Frame(canvas, padding=10)
        window_id = canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120) or (-1 if event.delta > 0 else 1), "units"))

        ttk.Label(outer, text="Калибровка теста кистей и расхода краски",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Каждый элемент калибруется отдельно. Координаты задаются в физических экранных пикселях основного монитора. "
                "Для точки укажи центр кнопки; для положения слайдера — позицию бегунка при указанном размере. "
                "Области доски и полоски краски выбираются независимо. Изменение разрешения помечает старые значения для проверки."
            ),
            wraplength=1050, justify="left",
        ).pack(anchor="w", pady=(4, 10))

        points_frame = ttk.LabelFrame(outer, text="Отдельные точки клика", padding=8)
        points_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(points_frame, text="Элемент", width=36).grid(row=0, column=0, sticky="w")
        ttk.Label(points_frame, text="Координаты", width=23).grid(row=0, column=1, sticky="w")
        ttk.Label(points_frame, text="Статус", width=16).grid(row=0, column=2, sticky="w")
        for row, (key, (label, destructive)) in enumerate(POINT_LABELS.items(), start=1):
            ttk.Label(points_frame, text=label, width=36).grid(row=row, column=0, sticky="w", pady=3)
            value_label = ttk.Label(points_frame, text="Не задано", width=23)
            status_label = ttk.Label(points_frame, text="Не задано", width=16)
            value_label.grid(row=row, column=1, sticky="w")
            status_label.grid(row=row, column=2, sticky="w")
            actions = ttk.Frame(points_frame)
            actions.grid(row=row, column=3, sticky="e", padx=(4, 0), pady=2)
            ttk.Button(actions, text="Задать координаты", command=lambda k=key: self._pick_point(k)).pack(side="left", padx=2)
            ttk.Button(actions, text="Тестовый клик", command=lambda k=key, d=destructive: self._test_point(k, d)).pack(side="left", padx=2)
            ttk.Button(actions, text="Сбросить", command=lambda k=key: self._reset_point(k)).pack(side="left", padx=2)
            self._point_rows[key] = (value_label, status_label)
        points_frame.columnconfigure(0, weight=1)

        regions_frame = ttk.LabelFrame(outer, text="Отдельные прямоугольные области", padding=8)
        regions_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(regions_frame, text="Область", width=42).grid(row=0, column=0, sticky="w")
        ttk.Label(regions_frame, text="X, Y, ширина × высота", width=28).grid(row=0, column=1, sticky="w")
        ttk.Label(regions_frame, text="Статус", width=16).grid(row=0, column=2, sticky="w")
        for row, (key, (label, _required)) in enumerate(REGION_LABELS.items(), start=1):
            ttk.Label(regions_frame, text=label, width=42).grid(row=row, column=0, sticky="w", pady=3)
            value_label = ttk.Label(regions_frame, text="Не задано", width=28)
            status_label = ttk.Label(regions_frame, text="Не задано", width=16)
            value_label.grid(row=row, column=1, sticky="w")
            status_label.grid(row=row, column=2, sticky="w")
            actions = ttk.Frame(regions_frame)
            actions.grid(row=row, column=3, sticky="e", padx=(4, 0), pady=2)
            ttk.Button(actions, text="Задать область", command=lambda k=key: self._pick_region(k)).pack(side="left", padx=2)
            ttk.Button(actions, text="Проверить область", command=lambda k=key: self._preview_region(k)).pack(side="left", padx=2)
            ttk.Button(actions, text="Сбросить", command=lambda k=key: self._reset_region(k)).pack(side="left", padx=2)
            self._region_rows[key] = (value_label, status_label)
        regions_frame.columnconfigure(0, weight=1)

        env_frame = ttk.LabelFrame(outer, text="Параметры среды (для диагностики)", padding=8)
        env_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(env_frame, text=f"Текущий основной экран: {self._screen_size()[0]} × {self._screen_size()[1]} px").grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 5)
        )
        for row, (key, variable) in enumerate(self._env_vars.items(), start=1):
            label = {
                "browser": "Браузер",
                "browser_version": "Версия браузера",
                "browser_zoom_percent": "Масштаб браузера, %",
                "windows_scale_percent": "Масштаб Windows, %",
            }[key]
            ttk.Label(env_frame, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(env_frame, textvariable=variable, width=34).grid(row=row, column=1, sticky="w", padx=(6, 20), pady=2)
        ttk.Label(env_frame, text="Логический размер доски игрового движка: 460 × 240; экранная область может быть масштабирована.",
                  wraplength=800).grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 0))

        profile_frame = ttk.LabelFrame(outer, text="Профиль", padding=8)
        profile_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(profile_frame, text="Файл:").grid(row=0, column=0, sticky="w")
        ttk.Label(profile_frame, text=str(self.profile_path), wraplength=800).grid(row=0, column=1, sticky="w", padx=6)
        buttons = ttk.Frame(profile_frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 0))
        ttk.Button(buttons, text="Сохранить профиль", command=self._save).pack(side="left", padx=(0, 5))
        ttk.Button(buttons, text="Сохранить как…", command=self._save_as).pack(side="left", padx=5)
        ttk.Button(buttons, text="Загрузить профиль…", command=self._load_dialog).pack(side="left", padx=5)
        ttk.Button(buttons, text="Сбросить весь профиль", command=self._reset_all).pack(side="left", padx=5)

        ttk.Label(outer, textvariable=self.summary_var, wraplength=1050, justify="left").pack(anchor="w", pady=(0, 5))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1050, justify="left").pack(anchor="w")

    def _refresh_view(self) -> None:
        for key, (value_label, status_label) in self._point_rows.items():
            point = self.profile["points"][key]
            value_label.configure(text=f"X={point['x']}, Y={point['y']}" if point else "Не задано")
            status_label.configure(text=self._status_label(self.profile["status"]["points"][key]))
        for key, (value_label, status_label) in self._region_rows.items():
            region = self.profile["regions"][key]
            value_label.configure(
                text=f"{region['x']}, {region['y']} — {region['width']} × {region['height']}" if region else "Не задано"
            )
            status_label.configure(text=self._status_label(self.profile["status"]["regions"][key]))
        missing = missing_required_fields(self.profile)
        if missing:
            labels = {**{key: value[0] for key, value in POINT_LABELS.items()},
                      **{key: value[0] for key, value in REGION_LABELS.items()}}
            missing_text = ", ".join(labels.get(key, key) for key in missing)
            summary = f"Обязательные поля ещё не заданы: {missing_text}."
        else:
            summary = "Базовые обязательные поля заданы. Для теста конкретной кисти дополнительно требуется её точка выбора или обе точки слайдера."
        needs_review = any(
            state == "needs_review"
            for group in self.profile["status"].values()
            for state in group.values()
        )
        if needs_review:
            summary += " ВНИМАНИЕ: есть координаты, требующие повторной визуальной проверки."
        self.summary_var.set(summary)

    @staticmethod
    def _status_label(status: str) -> str:
        return {
            "not_set": "Не задано",
            "set": "Задано",
            "verified": "Проверено",
            "needs_review": "Проверить",
        }.get(status, status)

    def _pick_point(self, key: str) -> None:
        label = POINT_LABELS[key][0]
        def selected(point: tuple[int, int] | None) -> None:
            if point is None:
                self.status_var.set(f"Выбор точки «{label}» отменён.")
                return
            try:
                self.profile["points"][key] = normalize_point(*point, self._screen_size())
            except BrushCalibrationError as exc:
                messagebox.showerror("Некорректная точка", str(exc), parent=self.root)
                return
            self.profile["status"]["points"][key] = "set"
            self._dirty = True
            self.status_var.set(f"Точка «{label}» задана. Сохрани профиль, чтобы использовать её в тесте.")
            self._refresh_view()
        ScreenPointPicker(self.root, f"Укажите центр элемента: {label}", selected)

    def _pick_region(self, key: str) -> None:
        label = REGION_LABELS[key][0]
        def selected(region: dict[str, int] | None) -> None:
            if region is None:
                self.status_var.set(f"Выбор области «{label}» отменён.")
                return
            try:
                normalized = normalize_region(
                    region["x"], region["y"], region["x"] + region["width"], region["y"] + region["height"],
                    self._screen_size(),
                )
            except BrushCalibrationError as exc:
                messagebox.showerror("Некорректная область", str(exc), parent=self.root)
                return
            self.profile["regions"][key] = normalized
            self.profile["status"]["regions"][key] = "set"
            self._dirty = True
            self.status_var.set(f"Область «{label}» задана. Нажми «Проверить область», затем сохрани профиль.")
            self._refresh_view()
        ScreenRegionPicker(self.root, f"Укажите область: {label}", selected)

    def _reset_point(self, key: str) -> None:
        self.profile["points"][key] = None
        self.profile["status"]["points"][key] = "not_set"
        self._dirty = True
        self.status_var.set(f"Точка «{POINT_LABELS[key][0]}» сброшена.")
        self._refresh_view()

    def _reset_region(self, key: str) -> None:
        self.profile["regions"][key] = None
        self.profile["status"]["regions"][key] = "not_set"
        self._dirty = True
        self.status_var.set(f"Область «{REGION_LABELS[key][0]}» сброшена.")
        self._refresh_view()

    def _test_point(self, key: str, destructive: bool) -> None:
        point = self.profile["points"].get(key)
        if point is None:
            messagebox.showwarning("Точка не задана", "Сначала задай координаты этой точки.", parent=self.root)
            return
        if platform.system() != "Windows":
            messagebox.showwarning("Недоступно", "Тестовые клики поддерживаются в Windows.", parent=self.root)
            return
        label = POINT_LABELS[key][0]
        warning = (
            f"Будет выполнен реальный клик по экрану в точке ({point['x']}, {point['y']}).\n\n"
            "Перед продолжением убедись, что браузер с игрой — окно за AutoDraw. Приложение свернётся на секунду."
        )
        if destructive:
            warning += "\n\nВНИМАНИЕ: это действие может сохранить или уничтожить текущий рисунок."
        if not messagebox.askyesno("Подтвердить тестовый клик", warning, parent=self.root):
            return
        self.root.iconify()
        def click_now() -> None:
            try:
                pyautogui.click(point["x"], point["y"])
                result = True
            except Exception as exc:
                result = False
                error = str(exc)
            self.root.deiconify()
            self.root.lift()
            if not result:
                messagebox.showerror("Ошибка тестового клика", error, parent=self.root)
                return
            confirmed = messagebox.askyesno(
                "Проверка действия",
                f"Сработал ли правильный элемент «{label}»? Если нет, координаты останутся непроверенными.",
                parent=self.root,
            )
            self.profile["status"]["points"][key] = "verified" if confirmed else "set"
            self._dirty = True
            self.status_var.set("Клик выполнен. Сохрани профиль, чтобы зафиксировать статус.")
            self._refresh_view()
        self.root.after(800, click_now)

    def _preview_region(self, key: str) -> None:
        region = self.profile["regions"].get(key)
        if region is None:
            messagebox.showwarning("Область не задана", "Сначала задай эту область.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Снимок области",
            "AutoDraw свернётся на короткое время, чтобы снять область игры без перекрытия окном приложения. Продолжить?",
            parent=self.root,
        ):
            return
        self.root.iconify()
        def capture() -> None:
            try:
                image = ImageGrab.grab(bbox=(
                    region["x"], region["y"],
                    region["x"] + region["width"], region["y"] + region["height"],
                ))
            except Exception as exc:
                image = None
                error = str(exc)
            self.root.deiconify()
            self.root.lift()
            if image is None:
                messagebox.showerror("Не удалось снять область", error, parent=self.root)
                return
            self._show_region_preview(key, image)
        self.root.after(700, capture)

    def _show_region_preview(self, key: str, image: Image.Image) -> None:
        window = tk.Toplevel(self.root)
        window.title(f"Проверка области — {REGION_LABELS[key][0]}")
        window.transient(self.root)
        preview = image.copy()
        preview.thumbnail((1000, 600), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(preview)
        image_label = ttk.Label(window, image=photo)
        image_label.image = photo
        image_label.pack(padx=10, pady=10)
        ttk.Label(window, text=f"Размер исходного ROI: {image.width} × {image.height} px").pack(anchor="w", padx=10)
        actions = ttk.Frame(window)
        actions.pack(fill="x", padx=10, pady=10)
        def confirm() -> None:
            self.profile["status"]["regions"][key] = "verified"
            self._dirty = True
            self.status_var.set(f"Область «{REGION_LABELS[key][0]}» подтверждена. Сохрани профиль.")
            self._refresh_view()
            window.destroy()
        ttk.Button(actions, text="Область выбрана верно", command=confirm).pack(side="left")
        ttk.Button(actions, text="Закрыть без подтверждения", command=window.destroy).pack(side="right")

    def _apply_environment(self) -> None:
        env = self.profile["environment"]
        size = self._screen_size()
        env["screen_width"], env["screen_height"] = size
        for key in ("browser", "browser_version"):
            env[key] = self._env_vars[key].get().strip()
        for key in ("browser_zoom_percent", "windows_scale_percent"):
            raw = self._env_vars[key].get().strip()
            if not raw:
                env[key] = None
            else:
                try:
                    env[key] = int(raw)
                except ValueError as exc:
                    raise BrushCalibrationError(f"{key}: введи целое число или оставь поле пустым.") from exc

    def _save(self) -> None:
        try:
            self._apply_environment()
            save_profile(self.profile_path, self.profile)
        except (OSError, BrushCalibrationError) as exc:
            messagebox.showerror("Не удалось сохранить профиль", str(exc), parent=self.root)
            return
        self._dirty = False
        self.status_var.set(f"Профиль сохранён: {self.profile_path}")
        self._refresh_view()
        if self.on_profile_saved:
            self.on_profile_saved(self.profile)

    def _save_as(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить профиль калибровки",
            initialfile=self.profile_path.name, defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        self.profile_path = Path(path).expanduser().resolve()
        self._save()

    def _load_dialog(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root, title="Загрузить профиль калибровки",
            filetypes=[("JSON", "*.json"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            profile = load_profile(path)
            profile, changed = adapt_profile_to_screen(profile, self._screen_size())
        except (OSError, BrushCalibrationError) as exc:
            messagebox.showerror("Не удалось загрузить профиль", str(exc), parent=self.root)
            return
        self.profile_path = Path(path).expanduser().resolve()
        self.profile = profile
        self._dirty = changed
        self._sync_environment_vars()
        self._refresh_view()
        self.status_var.set(
            "Профиль загружен. Разрешение экрана изменилось: проверь отмеченные поля и сохрани профиль."
            if changed else f"Профиль загружен: {self.profile_path}"
        )
        if self.on_profile_saved and not changed:
            self.on_profile_saved(self.profile)

    def _reset_all(self) -> None:
        if not messagebox.askyesno(
            "Сбросить профиль",
            "Все координаты и области в текущем профиле будут очищены. Продолжить?",
            parent=self.root,
        ):
            return
        self.profile = create_default_profile(self._screen_size())
        self._sync_environment_vars()
        self._dirty = True
        self._refresh_view()
        self.status_var.set("Профиль очищен в памяти. Нажми «Сохранить профиль», чтобы записать изменения.")

    def get_board_area(self) -> dict[str, int] | None:
        region = self.profile["regions"].get("board_area")
        if region is None or self.profile["status"]["regions"]["board_area"] == "needs_review":
            return None
        return dict(region)

    def get_canvas_size(self) -> tuple[int, int] | None:
        area = self.get_board_area()
        return (area["width"], area["height"]) if area else None

    def get_brush_control(self) -> dict[str, list[int]] | None:
        points = self.profile["points"]
        point_1 = points.get("brush_slider_value_1")
        point_30 = points.get("brush_slider_value_30")
        if not point_1 or not point_30:
            return None
        if (
            self.profile["status"]["points"]["brush_slider_value_1"] == "needs_review"
            or self.profile["status"]["points"]["brush_slider_value_30"] == "needs_review"
        ):
            return None
        return {"start": [point_30["x"], point_30["y"]], "end": [point_1["x"], point_1["y"]]}

    def is_ready(self, brush_value: int | None = None) -> tuple[bool, list[str]]:
        try:
            missing = missing_required_fields(self.profile, brush_value)
        except BrushCalibrationError:
            return False, ["invalid_profile"]
        for key, state in self.profile["status"]["points"].items():
            if state == "needs_review" and self.profile["points"].get(key) is not None:
                missing.append(key)
        for key, state in self.profile["status"]["regions"].items():
            if state == "needs_review" and self.profile["regions"].get(key) is not None:
                missing.append(key)
        return not missing, missing
