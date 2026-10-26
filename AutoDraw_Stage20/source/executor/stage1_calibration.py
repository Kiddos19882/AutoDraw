"""Этап 1 AutoDraw: калибровка области браузерной доски и проверка ввода мыши.

Windows 10/11, Python 3.11+.
Перед запуском откройте в браузере доску, выберите инструмент рисования
и убедитесь, что тестовые линии можно рисовать на текущем холсте.
"""

from __future__ import annotations

import json
import threading
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

# На Windows стараемся согласовать координаты Tkinter и системной мыши
# с физическими пикселями экрана (важно при масштабе Windows 125%/150%).
try:
    import ctypes

    if hasattr(ctypes, "windll"):
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

try:
    import pyautogui
    from pynput import keyboard
except ImportError as exc:
    raise SystemExit(
        "Не установлены зависимости. Выполните:\n"
        "python -m pip install -r requirements.txt"
    ) from exc

APP_DIR = Path(__file__).resolve().parent
PROFILE_PATH = APP_DIR / "target_profile.json"
RESULTS_PATH = APP_DIR / "calibration_results.json"

pyautogui.FAILSAFE = True  # перенос мыши в верхний левый угол — аварийный останов
pyautogui.PAUSE = 0

# Тест длины не предполагает заранее существование минимальной длины: проверяем и 1 px.
LENGTHS_PX = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 30, 40, 60, 80]

# Новый тест отдельно проверяет паузы между штрихами.
# Внутри штриха используем 10 мс: по предварительным наблюдениям 8 и 10 мс стабильнее.
STROKE_POINT_DELAY_MS = 10
INTERSTROKE_PAUSE_VALUES_MS = [0, 10, 20, 40]
INTERSTROKE_REPETITIONS = 10
INTERSTROKE_LINE_LENGTH_PX = 100
INTERSTROKE_POINT_STEP_PX = 2
INTERSTROKE_COLUMN_GAP_PX = 15
INTERSTROKE_MIN_WIDTH_PX = 475
INTERSTROKE_TOP_MARGIN_PX = 18
INTERSTROKE_BOTTOM_MARGIN_PX = 12
INTERSTROKE_BLOCK_GAP_PX = 20
INTERSTROKE_WARMUP_ROWS = 1
INTERSTROKE_FIXED_PAUSE_MS = 20
INTERSTROKE_AFTER_MOUSE_DOWN_MS = 40
INTERSTROKE_END_HOLD_MS = 50
INTERSTROKE_MAX_ROW_GAP_PX = 12
BOTH_TESTS_LEFT_STRIP_PX = 120  # слева тест длины, справа тест пауз между штрихами

# Контрольный тест стабильности длины: параметры, подобранные предыдущими опытами.
STABILITY_LENGTHS_PX = [100, 200, 400]
STABILITY_REPETITIONS = 10
STABILITY_POINT_STEP_PX = 2
STABILITY_POINT_DELAY_MS = 10
STABILITY_AFTER_MOUSE_UP_MS = 20
STABILITY_BEFORE_MOUSE_DOWN_MS = 20
STABILITY_AFTER_MOUSE_DOWN_MS = 40
STABILITY_END_HOLD_MS = 50
STABILITY_MARGIN_X_PX = 15
STABILITY_TOP_MARGIN_PX = 10
STABILITY_BOTTOM_MARGIN_PX = 10
STABILITY_BLOCK_GAP_PX = 12
STABILITY_MAX_ROW_GAP_PX = 10
STABILITY_MIN_WIDTH_PX = max(STABILITY_LENGTHS_PX) + 2 * STABILITY_MARGIN_X_PX
STABILITY_MIN_HEIGHT_PX = 300


@dataclass
class TargetArea:
    x: int
    y: int
    width: int
    height: int


@dataclass
class CalibrationProfile:
    area: TargetArea
    measured_min_length_px: int | None = None
    reliable_length_px: int | None = None
    preferred_move_interval_ms: float | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "area": asdict(self.area),
            "measured_min_length_px": self.measured_min_length_px,
            "reliable_length_px": self.reliable_length_px,
            "preferred_move_interval_ms": self.preferred_move_interval_ms,
            "notes": self.notes,
        }


class AreaSelector:
    """Полноэкранное выделение области холста перетаскиванием мыши."""

    def __init__(self, parent: tk.Tk, on_done: Callable[[TargetArea | None], None]):
        self.parent = parent
        self.on_done = on_done
        self.start_x: int | None = None
        self.start_y: int | None = None
        self.rect_id: int | None = None
        self.area: TargetArea | None = None

        self.window = tk.Toplevel(parent)
        # На Windows Tkinter нельзя включать -fullscreen после overrideredirect:
        # это вызывает TclError. Для полноэкранного слоя задаём геометрию вручную.
        self.window.withdraw()
        self.screen_w = self.window.winfo_screenwidth()
        self.screen_h = self.window.winfo_screenheight()
        self.window.overrideredirect(True)
        self.window.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        self.window.attributes("-topmost", True)
        try:
            self.window.attributes("-alpha", 0.32)
        except tk.TclError:
            pass
        self.window.configure(bg="#202020")

        self.canvas = tk.Canvas(
            self.window,
            width=self.screen_w,
            height=self.screen_h,
            bg="#202020",
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(
            20,
            20,
            anchor="nw",
            fill="white",
            font=("Segoe UI", 16, "bold"),
            text="Выделите мышью только область рисования на доске. Esc — отмена.",
        )
        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish)
        self.window.bind("<Escape>", self._cancel)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _start(self, event: tk.Event) -> None:
        self.start_x, self.start_y = int(event.x), int(event.y)
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="#00ff90",
            width=3,
        )

    def _drag(self, event: tk.Event) -> None:
        if self.start_x is None or self.start_y is None or self.rect_id is None:
            return
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def _finish(self, event: tk.Event) -> None:
        if self.start_x is None or self.start_y is None:
            return
        x1, x2 = sorted((self.start_x, int(event.x)))
        y1, y2 = sorted((self.start_y, int(event.y)))
        if x2 - x1 < 100 or y2 - y1 < 100:
            messagebox.showwarning(
                "Область слишком маленькая",
                "Выберите область не менее 100 × 100 пикселей.\n"
                "Для полного теста длины желательно иметь высоту около 300 пикселей.",
                parent=self.window,
            )
            self.start_x = self.start_y = None
            return
        self.area = TargetArea(x=x1, y=y1, width=x2 - x1, height=y2 - y1)
        self.window.destroy()
        self.on_done(self.area)

    def _cancel(self, _event: tk.Event | None = None) -> None:
        self.window.destroy()
        self.on_done(None)


class CalibrationApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AutoDraw — этап 1: калибровка")
        root.geometry("720x740")
        root.minsize(670, 680)

        self.area: TargetArea | None = None
        self.stop_event = threading.Event()
        self.running = False
        self.last_task = ""
        self.last_error: str | None = None

        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        self.w_var = tk.StringVar(value="0")
        self.h_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="Область доски не выбрана")

        self._build_ui()
        self._load_profile_if_available()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Калибровка доски и тест движений мыши",
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Выделите область самого холста, не включая панели браузера. "
                "Тесты оставляют линии на доске. Используйте пустой холст или "
                "доску, которую можно очистить."
            ),
            wraplength=640,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))

        area_frame = ttk.LabelFrame(outer, text="Область рисования на экране (физические пиксели)", padding=10)
        area_frame.pack(fill="x")
        fields = [
            ("X", self.x_var),
            ("Y", self.y_var),
            ("Ширина", self.w_var),
            ("Высота", self.h_var),
        ]
        for col, (label, var) in enumerate(fields):
            cell = ttk.Frame(area_frame)
            cell.grid(row=0, column=col, sticky="ew", padx=4)
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Entry(cell, textvariable=var, width=12).pack(fill="x", pady=(3, 0))
            area_frame.columnconfigure(col, weight=1)

        selector_row = ttk.Frame(area_frame)
        selector_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Button(selector_row, text="Выбрать область перетаскиванием", command=self._select_area).pack(side="left")
        ttk.Button(selector_row, text="Проверить координаты", command=self._validate_area).pack(side="left", padx=(8, 0))

        ttk.Label(outer, textvariable=self.status_var, foreground="#1a6e46", wraplength=640).pack(anchor="w", pady=10)

        tests = ttk.LabelFrame(outer, text="Тесты", padding=10)
        tests.pack(fill="x", pady=(0, 10))
        ttk.Button(
            tests,
            text="1. Проверить длину линий",
            command=lambda: self._start_task("length"),
        ).pack(fill="x", pady=3)
        ttk.Label(
            tests,
            text=(
                "Рисует отдельные линии одним перемещением мыши, включая длину 1 px. "
                "Тест проверяет длину, но не считает её минимальный порог заранее известным."
            ),
            foreground="#555555",
            wraplength=620,
        ).pack(anchor="w", padx=4, pady=(0, 5))
        ttk.Button(
            tests,
            text="2. Проверить паузы между штрихами",
            command=lambda: self._start_task("interstroke"),
        ).pack(fill="x", pady=3)
        ttk.Label(
            tests,
            text=(
                "Внутри каждой линии фиксированный интервал 10 мс. Верхний блок меняет "
                "паузу после отпускания мыши (0/10/20/40 мс), сохраняя паузу перед нажатием 20 мс. "
                "Нижний блок меняет паузу перед нажатием, сохраняя паузу после отпускания 20 мс. "
                "По 10 учитываемых линий на условие, плюс по одной разминочной линии."
            ),
            foreground="#555555",
            wraplength=620,
        ).pack(anchor="w", padx=4, pady=(0, 5))
        ttk.Button(
            tests,
            text="3. Проверить стабильность длины 100 / 200 / 400 px",
            command=lambda: self._start_task("line_stability"),
        ).pack(fill="x", pady=3)
        ttk.Label(
            tests,
            text=(
                "Контрольный тест: по 10 линий длиной 100, 200 и 400 px. "
                "Интервал внутри линии — 10 мс; после отпускания и перед нажатием — по 20 мс. "
                "Сверху вниз идут три блока: 100, 200 и 400 px."
            ),
            foreground="#555555",
            wraplength=620,
        ).pack(anchor="w", padx=4, pady=(0, 5))
        ttk.Button(
            tests,
            text="4. Запустить тест длины и тест пауз",
            command=lambda: self._start_task("both"),
        ).pack(fill="x", pady=3)

        notes = ttk.LabelFrame(outer, text="Безопасность и результаты", padding=10)
        notes.pack(fill="x")
        ttk.Label(
            notes,
            text=(
                "Аварийная остановка: F12. Также сработает PyAutoGUI FAILSAFE, "
                "если переместить курсор в верхний левый угол экрана.\n"
                "Программа не может определить, какие линии сервер доски сохранил: "
                "после теста нужно визуально проверить результат."
            ),
            wraplength=630,
            justify="left",
        ).pack(anchor="w")
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Button(bottom, text="Открыть папку проекта", command=self._show_paths).pack(side="left")
        ttk.Button(bottom, text="Закрыть", command=self._on_close).pack(side="right")

    def _select_area(self) -> None:
        if self.running:
            return
        self.root.withdraw()
        self.root.after(150, lambda: AreaSelector(self.root, self._area_selected))

    def _area_selected(self, area: TargetArea | None) -> None:
        self.root.deiconify()
        self.root.lift()
        if area is None:
            self.status_var.set("Выделение области отменено")
            return
        self.area = area
        self.x_var.set(str(area.x))
        self.y_var.set(str(area.y))
        self.w_var.set(str(area.width))
        self.h_var.set(str(area.height))
        self.status_var.set(
            f"Область выбрана: X={area.x}, Y={area.y}, {area.width} × {area.height} px"
        )
        self._save_profile()

    def _validate_area(self) -> bool:
        try:
            area = TargetArea(
                x=int(self.x_var.get()),
                y=int(self.y_var.get()),
                width=int(self.w_var.get()),
                height=int(self.h_var.get()),
            )
        except ValueError:
            messagebox.showerror("Ошибка координат", "Все поля должны содержать целые числа.", parent=self.root)
            return False
        screen_w, screen_h = pyautogui.size()
        if area.x < 0 or area.y < 0 or area.width < 100 or area.height < 100:
            messagebox.showerror(
                "Неверная область",
                "X и Y должны быть неотрицательными, ширина и высота — не менее 100 px.",
                parent=self.root,
            )
            return False
        if area.x + area.width > screen_w or area.y + area.height > screen_h:
            messagebox.showerror(
                "Область выходит за экран",
                f"Размер экрана: {screen_w} × {screen_h} px. Проверьте координаты.",
                parent=self.root,
            )
            return False
        self.area = area
        self.status_var.set(f"Область проверена: {area.width} × {area.height} px")
        self._save_profile()
        return True

    def _start_task(self, task: str) -> None:
        if self.running:
            return
        if not self._validate_area():
            return
        assert self.area is not None
        if self.area.width < 140:
            messagebox.showerror(
                "Недостаточная ширина",
                "Для теста длины выберите холст шириной не менее 140 px.",
                parent=self.root,
            )
            return
        minimum_width = INTERSTROKE_MIN_WIDTH_PX
        if task == "both":
            minimum_width += BOTH_TESTS_LEFT_STRIP_PX
        if task in ("interstroke", "both") and self.area.width < minimum_width:
            messagebox.showerror(
                "Недостаточная ширина для теста пауз",
                f"Для теста нужны четыре колонки линий по {INTERSTROKE_LINE_LENGTH_PX} px. "
                + ("При запуске обоих тестов ещё нужна отдельная левая область для теста длины. " if task == "both" else "")
                + f"Выберите область шириной не менее {minimum_width} px.",
                parent=self.root,
            )
            return
        if task == "line_stability" and self.area.width < STABILITY_MIN_WIDTH_PX:
            messagebox.showerror(
                "Недостаточная ширина",
                f"Для контрольного теста нужны линии до {max(STABILITY_LENGTHS_PX)} px. "
                f"Выберите область шириной не менее {STABILITY_MIN_WIDTH_PX} px.",
                parent=self.root,
            )
            return
        if task == "line_stability" and self.area.height < STABILITY_MIN_HEIGHT_PX:
            messagebox.showerror(
                "Недостаточная высота",
                f"Для 30 раздельных линий нужна область высотой не менее {STABILITY_MIN_HEIGHT_PX} px.",
                parent=self.root,
            )
            return
        if task in ("length", "both") and self.area.height < 220:
            if not messagebox.askyesno(
                "Низкая область",
                "Высоты может не хватить для раздельного размещения всех тестовых линий. Продолжить?",
                parent=self.root,
            ):
                return
        if task in ("interstroke", "both") and self.area.height < 290:
            messagebox.showerror(
                "Недостаточная высота для теста пауз",
                "Для двух блоков с разминочной линией и 10 повторами нужна область высотой не менее 290 px. "
                "Это помогает не смешивать соседние линии.",
                parent=self.root,
            )
            return
        ok = messagebox.askokcancel(
            "Подготовка к тесту",
            "Убедитесь, что:\n"
            "• браузер открыт и видна целевая доска;\n"
            "• выбран инструмент рисования и нужный цвет;\n"
            "• для теста пауз используется тот же инструмент и по возможности тонкая кисть;\n"
            "• область выделена только внутри холста;\n"
            "• холст можно очистить после испытаний.\n\n"
            "После подтверждения у вас будет 5 секунд, чтобы переключиться на браузер.\n"
            + ("При запуске теста длины и пауз линии длины рисуются слева, тест пауз — справа.\n" if task == "both" else "")
            + ("Контрольный тест рисует сверху вниз три блока длиной 100, 200 и 400 px; параметры задержек фиксированы на 10/20/20 мс.\n" if task == "line_stability" else "")
            + "F12 — аварийная остановка.",
            parent=self.root,
        )
        if not ok:
            return

        self.running = True
        self.stop_event.clear()
        self.last_task = task
        self.status_var.set("Тест выполняется… Переключитесь на браузер. F12 — остановить.")
        self.root.withdraw()
        threading.Thread(target=self._worker, args=(task, self.area), daemon=True).start()

    def _worker(self, task: str, area: TargetArea) -> None:
        error: str | None = None
        was_stopped = False
        listener = None
        try:
            # F12 работает глобально, даже когда окно программы скрыто.
            listener = keyboard.GlobalHotKeys({"<f12>": self.stop_event.set})
            listener.start()
            for _ in range(5, 0, -1):
                if self.stop_event.is_set():
                    was_stopped = True
                    return
                time.sleep(1)

            if task in ("length", "both"):
                self._draw_length_test(area)
            if task == "both" and not self.stop_event.is_set():
                time.sleep(1.0)
            if task == "line_stability" and not self.stop_event.is_set():
                self._draw_line_stability_test(area)
            if task in ("interstroke", "both") and not self.stop_event.is_set():
                if task == "both":
                    # Тесты размещаются рядом, чтобы линии не накладывались друг на друга.
                    interstroke_area = TargetArea(
                        x=area.x + BOTH_TESTS_LEFT_STRIP_PX,
                        y=area.y,
                        width=area.width - BOTH_TESTS_LEFT_STRIP_PX,
                        height=area.height,
                    )
                else:
                    interstroke_area = area
                self._draw_interstroke_test(interstroke_area)
            was_stopped = self.stop_event.is_set()
        except (pyautogui.FailSafeException, InterruptedError):
            was_stopped = True
        except Exception:
            error = traceback.format_exc()
            self.last_error = error
        finally:
            # Даже при исключении не оставляем кнопку мыши зажатой.
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
            self.root.after(0, lambda: self._finish_task(was_stopped, error))

    def _check_stop(self) -> None:
        if self.stop_event.is_set():
            raise InterruptedError("Тест остановлен пользователем через F12")

    def _draw_single_move(self, x1: int, y: int, length: int) -> None:
        self._check_stop()
        pyautogui.moveTo(x1, y, duration=0)
        time.sleep(0.06)
        pyautogui.mouseDown()
        try:
            time.sleep(0.04)
            # Одно перемещение с зажатой кнопкой: тестируем длину, а не плотность точек.
            pyautogui.moveTo(x1 + length, y, duration=0)
            time.sleep(0.10)
        finally:
            pyautogui.mouseUp()
        time.sleep(0.15)

    def _draw_length_test(self, area: TargetArea) -> None:
        margin_x = 15
        max_length = max(1, area.width - margin_x * 2)
        lengths = [length for length in LENGTHS_PX if length <= max_length]
        if not lengths:
            raise ValueError("В выделенной области не помещается ни одна тестовая линия.")
        top = 25
        bottom = 18
        available_h = max(1, area.height - top - bottom)
        row_gap = min(22, available_h / max(len(lengths), 1))
        if row_gap < 8:
            raise ValueError("Область слишком низкая для теста длины. Выделите более высокий участок холста.")
        x_start = area.x + margin_x
        pyautogui.moveTo(x_start, area.y + top, duration=0)
        for index, length in enumerate(lengths):
            self._check_stop()
            y = int(area.y + top + index * row_gap)
            self._draw_single_move(x_start, y, length)

        # Записываем порядок строк: верхняя — первая длина списка.
        self._write_result(
            "length",
            {
                "description": "Каждая строка — один прямой штрих, выполненный одним перемещением мыши.",
                "area": asdict(area),
                "rows_top_to_bottom_px": lengths,
                "screen_coordinate_note": "Длины измеряются в экранных пикселях.",
                "user_observation": None,
            },
        )

    def _draw_interstroke_test(self, area: TargetArea) -> None:
        """Раздельно проверяет паузу после mouseUp и паузу перед следующим mouseDown.

        Внутри каждого штриха используется постоянный интервал 10 мс между точками.
        Верхний блок: варьируется пауза после отпускания кнопки; перед нажатием фиксировано 20 мс.
        Нижний блок: варьируется пауза перед нажатием; после отпускания фиксировано 20 мс.
        Для каждой колонки первая линия — разминочная, следующие 10 оцениваются пользователем.
        """
        margin_x = 15
        line_length = min(INTERSTROKE_LINE_LENGTH_PX, area.width)
        column_pitch = line_length + INTERSTROKE_COLUMN_GAP_PX
        required_width = 2 * margin_x + 4 * line_length + 3 * INTERSTROKE_COLUMN_GAP_PX
        if area.width < required_width:
            raise ValueError(
                f"Для четырёх колонок нужна ширина {required_width} px; сейчас {area.width} px."
            )

        repetitions = INTERSTROKE_REPETITIONS
        rows_per_condition = repetitions + INTERSTROKE_WARMUP_ROWS
        top_margin = INTERSTROKE_TOP_MARGIN_PX
        bottom_margin = INTERSTROKE_BOTTOM_MARGIN_PX
        block_gap = INTERSTROKE_BLOCK_GAP_PX
        # Два блока по 11 строк; ограничиваем расстояние строк, чтобы тест помещался.
        available_for_rows = area.height - top_margin - bottom_margin - block_gap
        row_gap = min(
            INTERSTROKE_MAX_ROW_GAP_PX,
            available_for_rows // (2 * repetitions),
        )
        if row_gap < 8:
            raise ValueError(
                "Область слишком низкая для теста. Выберите холст высотой не менее 290 px."
            )

        steps = max(1, round(line_length / INTERSTROKE_POINT_STEP_PX))
        trials: list[dict] = []
        previous_mouse_up_at: float | None = None

        phases = [
            {
                "id": "after_mouse_up",
                "label": "Верхний блок: пауза после отпускания",
                "vary": "after_mouse_up",
            },
            {
                "id": "before_mouse_down",
                "label": "Нижний блок: пауза перед нажатием",
                "vary": "before_mouse_down",
            },
        ]

        for phase_index, phase in enumerate(phases):
            for column_index, variable_pause_ms in enumerate(INTERSTROKE_PAUSE_VALUES_MS):
                x_start = area.x + margin_x + column_index * column_pitch

                for row_index in range(rows_per_condition):
                    self._check_stop()
                    is_warmup = row_index < INTERSTROKE_WARMUP_ROWS
                    evaluated_repetition = (
                        row_index - INTERSTROKE_WARMUP_ROWS + 1 if not is_warmup else None
                    )
                    y = int(
                        area.y
                        + top_margin
                        + phase_index * ((rows_per_condition - 1) * row_gap + block_gap)
                        + row_index * row_gap
                    )

                    if phase["vary"] == "after_mouse_up":
                        after_mouse_up_delay_ms = variable_pause_ms
                        before_mouse_down_delay_ms = INTERSTROKE_FIXED_PAUSE_MS
                    else:
                        after_mouse_up_delay_ms = INTERSTROKE_FIXED_PAUSE_MS
                        before_mouse_down_delay_ms = variable_pause_ms

                    # Пауза после предыдущего mouseUp. Она применяется к переходу
                    # к текущей линии, а не к линии, которая только что завершилась.
                    if previous_mouse_up_at is not None and after_mouse_up_delay_ms > 0:
                        time.sleep(after_mouse_up_delay_ms / 1000.0)

                    pyautogui.moveTo(x_start, y, duration=0)
                    if before_mouse_down_delay_ms > 0:
                        time.sleep(before_mouse_down_delay_ms / 1000.0)

                    mouse_down_started_at = time.perf_counter()
                    actual_gap_up_to_down_ms = (
                        (mouse_down_started_at - previous_mouse_up_at) * 1000.0
                        if previous_mouse_up_at is not None
                        else None
                    )
                    pyautogui.mouseDown()
                    time.sleep(INTERSTROKE_AFTER_MOUSE_DOWN_MS / 1000.0)
                    stroke_started_at = time.perf_counter()

                    try:
                        for step in range(1, steps + 1):
                            self._check_stop()
                            x = x_start + round(line_length * step / steps)
                            pyautogui.moveTo(x, y, duration=0)
                            if step < steps and STROKE_POINT_DELAY_MS > 0:
                                time.sleep(STROKE_POINT_DELAY_MS / 1000.0)
                        time.sleep(INTERSTROKE_END_HOLD_MS / 1000.0)
                        stroke_duration_ms = (time.perf_counter() - stroke_started_at) * 1000.0
                    finally:
                        pyautogui.mouseUp()
                        previous_mouse_up_at = time.perf_counter()

                    trials.append(
                        {
                            "phase": phase["id"],
                            "phase_label": phase["label"],
                            "varied_pause_ms": variable_pause_ms,
                            "varied_parameter": phase["vary"],
                            "after_mouse_up_delay_ms": after_mouse_up_delay_ms,
                            "before_mouse_down_delay_ms": before_mouse_down_delay_ms,
                            "is_warmup_line_ignore_for_evaluation": is_warmup,
                            "evaluation_repetition": evaluated_repetition,
                            "column_left_to_right": column_index + 1,
                            "row_top_to_bottom": row_index + 1,
                            "expected_length_px": line_length,
                            "point_step_px": INTERSTROKE_POINT_STEP_PX,
                            "point_delay_ms": STROKE_POINT_DELAY_MS,
                            "pyautogui_move_calls_during_stroke": steps,
                            "actual_gap_from_previous_mouse_up_to_mouse_down_call_ms": (
                                round(actual_gap_up_to_down_ms, 3)
                                if actual_gap_up_to_down_ms is not None
                                else None
                            ),
                            "actual_stroke_duration_ms": round(stroke_duration_ms, 3),
                        }
                    )

        self._write_result(
            "interstroke_timing",
            {
                "description": (
                    "Раздельно проверяет паузу после отпускания кнопки и паузу перед нажатием "
                    "для следующего штриха. Внутри штриха задержка между точками фиксирована 10 мс."
                ),
                "area": asdict(area),
                "line_length_px": line_length,
                "point_step_px": INTERSTROKE_POINT_STEP_PX,
                "point_delay_ms_inside_stroke": STROKE_POINT_DELAY_MS,
                "variable_pause_values_ms": INTERSTROKE_PAUSE_VALUES_MS,
                "fixed_pause_ms_for_other_parameter": INTERSTROKE_FIXED_PAUSE_MS,
                "repetitions_per_condition": repetitions,
                "warmup_lines_per_condition": INTERSTROKE_WARMUP_ROWS,
                "fixed_after_mouse_down_ms": INTERSTROKE_AFTER_MOUSE_DOWN_MS,
                "fixed_end_hold_before_mouse_up_ms": INTERSTROKE_END_HOLD_MS,
                "condition_layout": {
                    "upper_block": {
                        "varied_parameter": "after_mouse_up_delay_ms",
                        "fixed_before_mouse_down_delay_ms": INTERSTROKE_FIXED_PAUSE_MS,
                        "columns_left_to_right_ms": INTERSTROKE_PAUSE_VALUES_MS,
                    },
                    "lower_block": {
                        "varied_parameter": "before_mouse_down_delay_ms",
                        "fixed_after_mouse_up_delay_ms": INTERSTROKE_FIXED_PAUSE_MS,
                        "columns_left_to_right_ms": INTERSTROKE_PAUSE_VALUES_MS,
                    },
                    "rows_top_to_bottom": "first line is warm-up and is ignored; next 10 lines are evaluation repetitions",
                    "repeat_vertical_spacing_px": row_gap,
                    "column_gap_px": INTERSTROKE_COLUMN_GAP_PX,
                    "actual_gap_note": (
                        "actual_gap_from_previous_mouse_up_to_mouse_down_call_ms includes the configured pause, "
                        "moving the pointer to the next start point, and runtime overhead. It is measured "
                        "between mouseUp completion and the next mouseDown call."
                    ),
                },
                "trials": trials,
                "user_observation": None,
            },
        )

    def _draw_line_stability_test(self, area: TargetArea) -> None:
        """Проверяет отклонение длины на 100, 200 и 400 px при фиксированных задержках.

        Блоки идут сверху вниз. Для каждой длины выполняется 10 повторений.
        Внутри линии между точками задержка 10 мс; переход между штрихами:
        20 мс после mouseUp и 20 мс после перемещения к началу перед mouseDown.
        """
        max_length = max(STABILITY_LENGTHS_PX)
        if area.width < max_length + 2 * STABILITY_MARGIN_X_PX:
            raise ValueError(
                f"Для линии {max_length} px нужна ширина не менее "
                f"{max_length + 2 * STABILITY_MARGIN_X_PX} px."
            )

        total_rows = len(STABILITY_LENGTHS_PX) * STABILITY_REPETITIONS
        rows_height = (
            area.height
            - STABILITY_TOP_MARGIN_PX
            - STABILITY_BOTTOM_MARGIN_PX
            - STABILITY_BLOCK_GAP_PX * (len(STABILITY_LENGTHS_PX) - 1)
        )
        row_gap = min(STABILITY_MAX_ROW_GAP_PX, rows_height // total_rows)
        if row_gap < 7:
            raise ValueError(
                f"Область слишком низкая: при 30 линиях нужен вертикальный шаг не менее 7 px. "
                f"Выберите высоту около {STABILITY_MIN_HEIGHT_PX} px или больше."
            )

        x_start = area.x + STABILITY_MARGIN_X_PX
        previous_mouse_up_at: float | None = None
        trials: list[dict] = []

        for length_index, line_length in enumerate(STABILITY_LENGTHS_PX):
            block_y = (
                area.y
                + STABILITY_TOP_MARGIN_PX
                + length_index * (STABILITY_REPETITIONS * row_gap + STABILITY_BLOCK_GAP_PX)
            )
            steps = max(1, round(line_length / STABILITY_POINT_STEP_PX))

            for repetition in range(1, STABILITY_REPETITIONS + 1):
                self._check_stop()
                y = int(block_y + (repetition - 1) * row_gap)

                # Пауза после завершения предыдущего штриха — отдельный параметр.
                if previous_mouse_up_at is not None:
                    time.sleep(STABILITY_AFTER_MOUSE_UP_MS / 1000.0)

                # Переход к началу линии выполняется при отпущенной кнопке.
                pyautogui.moveTo(x_start, y, duration=0)
                time.sleep(STABILITY_BEFORE_MOUSE_DOWN_MS / 1000.0)
                mouse_down_started_at = time.perf_counter()
                actual_gap_ms = (
                    (mouse_down_started_at - previous_mouse_up_at) * 1000.0
                    if previous_mouse_up_at is not None
                    else None
                )

                pyautogui.mouseDown()
                try:
                    time.sleep(STABILITY_AFTER_MOUSE_DOWN_MS / 1000.0)
                    stroke_started_at = time.perf_counter()
                    for step in range(1, steps + 1):
                        self._check_stop()
                        x = x_start + round(line_length * step / steps)
                        pyautogui.moveTo(x, y, duration=0)
                        if step < steps:
                            time.sleep(STABILITY_POINT_DELAY_MS / 1000.0)
                    time.sleep(STABILITY_END_HOLD_MS / 1000.0)
                    stroke_duration_ms = (time.perf_counter() - stroke_started_at) * 1000.0
                finally:
                    pyautogui.mouseUp()
                    previous_mouse_up_at = time.perf_counter()

                trials.append(
                    {
                        "line_length_group_px": line_length,
                        "repetition": repetition,
                        "row_top_to_bottom": length_index * STABILITY_REPETITIONS + repetition,
                        "screen_start_x": x_start,
                        "screen_end_x_expected": x_start + line_length,
                        "screen_y": y,
                        "expected_length_px": line_length,
                        "point_step_px": STABILITY_POINT_STEP_PX,
                        "point_delay_ms": STABILITY_POINT_DELAY_MS,
                        "after_mouse_up_pause_ms": STABILITY_AFTER_MOUSE_UP_MS,
                        "before_mouse_down_pause_ms": STABILITY_BEFORE_MOUSE_DOWN_MS,
                        "after_mouse_down_delay_ms": STABILITY_AFTER_MOUSE_DOWN_MS,
                        "end_hold_before_mouse_up_ms": STABILITY_END_HOLD_MS,
                        "pyautogui_move_calls_during_stroke": steps,
                        "actual_gap_from_previous_mouse_up_to_mouse_down_call_ms": (
                            round(actual_gap_ms, 3) if actual_gap_ms is not None else None
                        ),
                        "actual_stroke_duration_ms": round(stroke_duration_ms, 3),
                    }
                )

        self._write_result(
            "line_stability",
            {
                "description": (
                    "Контроль отклонения длины штриха для 100, 200 и 400 px. "
                    "Все задержки зафиксированы по результатам предыдущих опытов."
                ),
                "area": asdict(area),
                "line_lengths_px_top_to_bottom": STABILITY_LENGTHS_PX,
                "repetitions_per_length": STABILITY_REPETITIONS,
                "point_step_px": STABILITY_POINT_STEP_PX,
                "point_delay_ms_inside_stroke": STABILITY_POINT_DELAY_MS,
                "after_mouse_up_pause_ms": STABILITY_AFTER_MOUSE_UP_MS,
                "before_mouse_down_pause_ms": STABILITY_BEFORE_MOUSE_DOWN_MS,
                "after_mouse_down_delay_ms": STABILITY_AFTER_MOUSE_DOWN_MS,
                "end_hold_before_mouse_up_ms": STABILITY_END_HOLD_MS,
                "row_gap_px": row_gap,
                "block_gap_px": STABILITY_BLOCK_GAP_PX,
                "row_order_note": (
                    "Сверху вниз: первые 10 линий по 100 px, следующие 10 по 200 px, "
                    "последние 10 по 400 px. В каждом блоке строки пронумерованы сверху вниз."
                ),
                "measurement_note": (
                    "Фактическая длина в браузере не считывается автоматически. "
                    "Сравните видимую длину линий в каждом блоке. Отклонение 1-2 px "
                    "может быть связано с растеризацией/толщиной кисти; если отклонение растёт "
                    "с длиной, проверьте масштаб и координаты."
                ),
                "trials": trials,
                "user_observation": None,
            },
        )

    @staticmethod
    def _write_result(test_name: str, result: dict) -> None:
        data = {"test": test_name, "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), **result}
        existing: list[dict] = []
        if RESULTS_PATH.exists():
            try:
                old = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
                if isinstance(old, list):
                    existing = old
            except (OSError, json.JSONDecodeError):
                existing = []
        existing.append(data)
        RESULTS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    def _finish_task(self, was_stopped: bool, error: str | None) -> None:
        self.running = False
        self.root.deiconify()
        self.root.lift()
        if error:
            self.status_var.set("Во время теста произошла ошибка")
            messagebox.showerror(
                "Ошибка исполнения",
                "Тест завершился с ошибкой. Кнопка мыши отпущена.\n\n"
                + error[-1800:],
                parent=self.root,
            )
        elif was_stopped:
            self.status_var.set("Тест остановлен. Кнопка мыши отпущена.")
            messagebox.showinfo("Тест остановлен", "Исполнение остановлено. Проверьте состояние доски.", parent=self.root)
        else:
            self.status_var.set("Тест завершён. Осмотрите линии в браузере и запишите, какие распознаны.")
            result_details = ""
            if self.last_task in ("length", "both"):
                result_details += (
                    "\n\nТест длины: строки сверху вниз — "
                    + ", ".join(str(length) for length in LENGTHS_PX)
                    + " px."
                )
            if self.last_task in ("interstroke", "both"):
                result_details += (
                    "\n\nТест пауз: верхний блок меняет ожидание после отпускания (0/10/20/40 мс), "
                    "нижний — ожидание перед нажатием (0/10/20/40 мс). Другая пауза в каждом блоке фиксирована 20 мс. "
                    "Внутри линии — 10 мс между точками; первая строка каждого столбца разминочная, следующие 10 оцениваются."
                )
            if self.last_task == "line_stability":
                result_details += (
                    "\n\nКонтроль стабильности: сверху вниз 10 линий по 100 px, "
                    "10 по 200 px и 10 по 400 px. Внутри линий — 10 мс между точками; "
                    "после отпускания и перед нажатием — по 20 мс. Сравните видимую длину "
                    "линий внутри каждого блока и между блоками."
                )
            if self.last_task == "both":
                result_details += "\nТест длины размещён слева, тест пауз — справа."
            messagebox.showinfo(
                "Тест завершён",
                f"Тест выполнен. Параметры записаны в:\n{RESULTS_PATH}\n\n"
                "Теперь проверьте результат в браузере вручную. Программа не может автоматически "
                "определить, какие линии доска приняла на сервере."
                + result_details,
                parent=self.root,
            )

    def _save_profile(self) -> None:
        if self.area is None:
            return
        profile = CalibrationProfile(area=self.area)
        PROFILE_PATH.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_profile_if_available(self) -> None:
        if not PROFILE_PATH.exists():
            return
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            area_data = data.get("area", {})
            area = TargetArea(
                x=int(area_data["x"]),
                y=int(area_data["y"]),
                width=int(area_data["width"]),
                height=int(area_data["height"]),
            )
            self.area = area
            self.x_var.set(str(area.x))
            self.y_var.set(str(area.y))
            self.w_var.set(str(area.width))
            self.h_var.set(str(area.height))
            self.status_var.set(f"Загружена сохранённая область: {area.width} × {area.height} px")
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            self.status_var.set("Не удалось загрузить профиль; выберите область заново")

    def _show_paths(self) -> None:
        try:
            import os
            os.startfile(str(APP_DIR))  # Windows
        except Exception as exc:
            messagebox.showerror("Не удалось открыть папку", str(exc), parent=self.root)

    def _on_close(self) -> None:
        if self.running:
            if messagebox.askyesno("Остановить тест?", "Тест выполняется. Отправить сигнал остановки и закрыть окно?", parent=self.root):
                self.stop_event.set()
                self.root.after(300, self._on_close)
            return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    CalibrationApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
