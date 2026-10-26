from __future__ import annotations

import json
import os
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import traceback

try:
    import ctypes
    if hasattr(ctypes, "windll"):
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

try:
    import pyautogui
except ImportError as exc:
    raise SystemExit("Не установлены зависимости. Выполните: python -m pip install -r requirements.txt") from exc

from drawing.mouse_executor import ExecutorConfig, MouseExecutor
from models import DrawingPlan, Point
from path_planning.test_shape import create_test_shape

APP_DIR = Path(__file__).resolve().parent
PROFILE_PATH = APP_DIR / "target_profile.json"
PLAN_PATH = APP_DIR / "drawing_plan.json"
EXECUTION_RESULTS_PATH = APP_DIR / "execution_results.json"


class TargetArea:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x, self.y, self.width, self.height = x, y, width, height

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


class AreaSelector:
    """Полноэкранный селектор области холста."""

    def __init__(self, parent: tk.Tk, on_done):
        self.parent = parent
        self.on_done = on_done
        self.start: tuple[int, int] | None = None
        self.rect_id: int | None = None
        self.window = tk.Toplevel(parent)
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
        self.canvas = tk.Canvas(self.window, bg="#202020", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(20, 20, anchor="nw", fill="white", font=("Segoe UI", 16, "bold"),
                                text="Выделите область холста. Esc — отмена.")
        self.canvas.bind("<ButtonPress-1>", self._start)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._finish)
        self.window.bind("<Escape>", self._cancel)
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()

    def _start(self, event):
        self.start = (int(event.x), int(event.y))
        if self.rect_id is not None:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                    outline="#00ff90", width=3)

    def _drag(self, event):
        if self.start is not None and self.rect_id is not None:
            self.canvas.coords(self.rect_id, self.start[0], self.start[1], event.x, event.y)

    def _finish(self, event):
        if self.start is None:
            return
        x1, x2 = sorted((self.start[0], int(event.x)))
        y1, y2 = sorted((self.start[1], int(event.y)))
        if x2 - x1 < 460 or y2 - y1 < 250:
            messagebox.showwarning("Область слишком маленькая", "Для тестовой фигуры нужно минимум 460 × 250 px.", parent=self.window)
            self.start = None
            return
        area = TargetArea(x1, y1, x2 - x1, y2 - y1)
        self.window.destroy()
        self.on_done(area)

    def _cancel(self, _event=None):
        self.window.destroy()
        self.on_done(None)


class DrawingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AutoDraw — этап 2: планирование штрихов")
        root.geometry("1120x820")
        root.minsize(900, 680)
        self.area: TargetArea | None = None
        self.plan: DrawingPlan | None = None
        self.running = False
        self.stop_event = threading.Event()
        self.last_summary: dict | None = None

        self.x_var = tk.StringVar()
        self.y_var = tk.StringVar()
        self.w_var = tk.StringVar()
        self.h_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Загрузите профиль или выберите область холста.")
        self.summary_var = tk.StringVar(value="План ещё не сформирован.")
        self._build_ui()
        self._load_profile()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Этап 2 — геометрия плана и исполнение тестовой фигуры",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(outer,
                  text="План хранит точки относительно холста. Исполнитель отдельно переводит их в координаты экрана и воспроизводит штрихи.",
                  wraplength=1050).pack(anchor="w", pady=(4, 10))

        area_frame = ttk.LabelFrame(outer, text="Область холста на экране", padding=8)
        area_frame.pack(fill="x")
        fields = [("X", self.x_var), ("Y", self.y_var), ("Ширина", self.w_var), ("Высота", self.h_var)]
        for col, (label, variable) in enumerate(fields):
            cell = ttk.Frame(area_frame)
            cell.grid(row=0, column=col, sticky="ew", padx=4)
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Entry(cell, textvariable=variable, width=10).pack(fill="x", pady=(2, 0))
            area_frame.columnconfigure(col, weight=1)
        ttk.Button(area_frame, text="Выбрать область перетаскиванием", command=self._select_area).grid(
            row=0, column=4, padx=(8, 0), sticky="nsew")
        ttk.Button(area_frame, text="Применить координаты", command=self._apply_area).grid(
            row=0, column=5, padx=(6, 0), sticky="nsew")

        preview_frame = ttk.LabelFrame(outer, text="Предпросмотр плана", padding=6)
        preview_frame.pack(fill="both", expand=True, pady=(10, 8))
        self.preview = tk.Canvas(preview_frame, bg="#ffffff", highlightthickness=1,
                                 highlightbackground="#c8c8c8", height=430)
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _event: self._draw_preview())
        ttk.Label(outer, textvariable=self.summary_var, wraplength=1050).pack(anchor="w", pady=(0, 6))
        ttk.Label(outer, textvariable=self.status_var, foreground="#245b42", wraplength=1050).pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Построить тестовый план", command=self._build_plan).pack(side="left")
        ttk.Button(buttons, text="Сохранить план JSON", command=self._save_plan).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Выполнить на доске", command=self._start_execution).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Открыть папку", command=self._open_folder).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Остановить (F12)", command=self._stop_execution).pack(side="right")
        ttk.Label(outer,
                  text="Профиль исполнителя: шаг 2 px, 10 мс между точками, 20 мс после mouseUp и перед mouseDown, 40 мс после mouseDown, 50 мс перед mouseUp. F12 — аварийная остановка.",
                  foreground="#555555", wraplength=1050).pack(anchor="w", pady=(8, 0))

    def _load_profile(self):
        if not PROFILE_PATH.exists():
            return
        try:
            data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
            values = data.get("area", data)
            self.x_var.set(str(int(values["x"])))
            self.y_var.set(str(int(values["y"])))
            self.w_var.set(str(int(values["width"])))
            self.h_var.set(str(int(values["height"])))
            self._apply_area(show_errors=False)
            self.status_var.set(f"Загружен профиль холста: {self.area.width} × {self.area.height} px.")
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            self.status_var.set("Профиль не удалось прочитать. Выберите область заново.")

    def _select_area(self):
        if self.running:
            return
        self.root.withdraw()
        self.root.after(120, lambda: AreaSelector(self.root, self._area_selected))

    def _area_selected(self, area: TargetArea | None):
        self.root.deiconify()
        self.root.lift()
        if area is None:
            self.status_var.set("Выбор области отменён.")
            return
        self.x_var.set(str(area.x)); self.y_var.set(str(area.y))
        self.w_var.set(str(area.width)); self.h_var.set(str(area.height))
        self._apply_area()

    def _apply_area(self, show_errors: bool = True) -> bool:
        try:
            x, y, width, height = (int(v.get()) for v in (self.x_var, self.y_var, self.w_var, self.h_var))
        except ValueError:
            if show_errors:
                messagebox.showerror("Неверные координаты", "Все поля должны содержать целые числа.", parent=self.root)
            return False
        screen_width, screen_height = pyautogui.size()
        if x < 0 or y < 0 or width < 460 or height < 250 or x + width > screen_width or y + height > screen_height:
            if show_errors:
                messagebox.showerror("Неверная область", f"Нужна область не меньше 460 × 250 px внутри экрана {screen_width} × {screen_height}.", parent=self.root)
            return False
        self.area = TargetArea(x, y, width, height)
        PROFILE_PATH.write_text(json.dumps({"area": self.area.to_dict()}, ensure_ascii=False, indent=2), encoding="utf-8")
        self._build_plan()
        self.status_var.set(f"Область применена: экран X={x}, Y={y}, {width} × {height} px.")
        return True

    def _build_plan(self):
        if self.area is None:
            try:
                width, height = int(self.w_var.get()), int(self.h_var.get())
            except ValueError:
                messagebox.showinfo("Выберите холст", "Сначала выберите область холста.", parent=self.root)
                return
        else:
            width, height = self.area.width, self.area.height
        try:
            self.plan = create_test_shape(width, height)
        except ValueError as exc:
            messagebox.showerror("Не удалось построить план", str(exc), parent=self.root)
            self.plan = None
            self._draw_preview()
            return
        self.plan.validate_bounds()
        length = self.plan.total_drawing_length_px
        pen_up = self.plan.pen_up_distance_px
        moves = self.plan.estimated_move_calls(2.0)
        estimated_seconds = 5 + moves * 0.010 + len(self.plan.strokes) * (0.020 + 0.020 + 0.040 + 0.050)
        self.summary_var.set(
            f"{self.plan.stroke_count} штрихов; длина с рисованием {length:.0f} px; "
            f"переходы без рисования {pen_up:.0f} px; примерно {moves} перемещений точек; "
            f"оценка времени около {estimated_seconds:.0f} с (без гарантии точного времени браузера)."
        )
        self._draw_preview()
        self.status_var.set("План создан. Проверьте предпросмотр, затем сохраните его или выполните на доске.")

    def _draw_preview(self):
        canvas = self.preview
        canvas.delete("all")
        if self.plan is None:
            canvas.create_text(20, 20, anchor="nw", text="Выберите область и постройте план.", fill="#555555", font=("Segoe UI", 11))
            return
        cw = max(100, canvas.winfo_width())
        ch = max(100, canvas.winfo_height())
        margin = 24
        scale = min((cw - 2 * margin) / self.plan.width, (ch - 2 * margin) / self.plan.height)
        draw_w = self.plan.width * scale
        draw_h = self.plan.height * scale
        x0 = (cw - draw_w) / 2
        y0 = (ch - draw_h) / 2
        canvas.create_rectangle(x0, y0, x0 + draw_w, y0 + draw_h, outline="#aaaaaa", width=1)

        # Номера и начало/конец каждого штриха помогают увидеть порядок геометрии.
        for index, stroke in enumerate(self.plan.strokes, start=1):
            coords: list[float] = []
            stroke_points = list(stroke.points)
            if stroke.closed:
                stroke_points.append(stroke.points[0])
            for point in stroke_points:
                coords.extend((x0 + point.x * scale, y0 + point.y * scale))
            canvas.create_line(*coords, fill="#172b4d", width=2, capstyle=tk.ROUND, joinstyle=tk.ROUND)
            first = stroke.points[0]
            sx, sy = x0 + first.x * scale, y0 + first.y * scale
            last = stroke.points[-1]
            ex, ey = x0 + last.x * scale, y0 + last.y * scale
            canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill="#16834a", outline="white")
            canvas.create_oval(ex - 3, ey - 3, ex + 3, ey + 3, fill="#d04747", outline="white")
            label_x, label_y = sx + 6, sy - 8
            canvas.create_text(label_x, label_y, text=str(index), anchor="sw", fill="#16834a", font=("Segoe UI", 8, "bold"))
        canvas.create_text(x0 + 8, y0 + 8, text=f"Холст {self.plan.width} × {self.plan.height} px", anchor="nw",
                           fill="#777777", font=("Segoe UI", 8))
        canvas.create_text(cw - 8, ch - 8, text="Зелёный — начало · красный — последняя заданная вершина",
                           anchor="se", fill="#555555", font=("Segoe UI", 8))

    def _save_plan(self):
        if self.plan is None:
            self._build_plan()
        if self.plan is None:
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Сохранить план рисования",
                                            initialdir=str(APP_DIR), initialfile="drawing_plan.json",
                                            defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.plan.save(path)
            self.status_var.set(f"План сохранён: {path}")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc), parent=self.root)

    def _start_execution(self):
        if self.running:
            return
        if not self._apply_area():
            return
        if self.plan is None:
            self._build_plan()
        if self.plan is None:
            return
        try:
            self.plan.validate_bounds()
        except ValueError as exc:
            messagebox.showerror("Ошибка плана", str(exc), parent=self.root)
            return
        ok = messagebox.askokcancel(
            "Подтвердите рисование",
            f"Будет нарисовано {self.plan.stroke_count} штрихов в области X={self.area.x}, Y={self.area.y}, "
            f"{self.area.width} × {self.area.height} px.\n\n"
            "Очистите холст или используйте тестовую область. После подтверждения приложение скроется, "
            "у вас будет 5 секунд переключиться на браузер. F12 — остановка.\n\n"
            "Исполнитель использует профиль: шаг 2 px; 10 мс между точками; паузы 20/20 мс между штрихами.",
            parent=self.root,
        )
        if not ok:
            return
        self.running = True
        self.stop_event.clear()
        self.status_var.set("Исполнение начнётся через 5 секунд…")
        self.root.withdraw()
        thread = threading.Thread(target=self._execution_worker, daemon=True)
        thread.start()

    def _execution_worker(self):
        summary = None
        error_trace = None
        try:
            assert self.area is not None and self.plan is not None
            executor = MouseExecutor(self.stop_event, ExecutorConfig())
            summary = executor.execute(self.plan, self.area.x, self.area.y, self._progress_from_worker)
            self.last_summary = summary.to_dict(executor.config)
            self.last_summary["plan_name"] = self.plan.name
            self.last_summary["plan_strokes"] = self.plan.stroke_count
            existing = []
            if EXECUTION_RESULTS_PATH.exists():
                try:
                    loaded = json.loads(EXECUTION_RESULTS_PATH.read_text(encoding="utf-8"))
                    if isinstance(loaded, list):
                        existing = loaded
                except (OSError, json.JSONDecodeError):
                    existing = []
            existing.append(self.last_summary)
            EXECUTION_RESULTS_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            error_trace = traceback.format_exc()
        self.root.after(0, lambda: self._execution_finished(summary, error_trace))

    def _progress_from_worker(self, current: int, total: int, detail: str):
        self.root.after(0, lambda: self.status_var.set(detail))

    def _execution_finished(self, summary, error_trace):
        self.running = False
        self.root.deiconify()
        self.root.lift()
        if error_trace:
            self.status_var.set("Ошибка во время исполнения. Кнопка мыши отпущена.")
            messagebox.showerror("Ошибка исполнения", error_trace[-2500:], parent=self.root)
            return
        if summary is None:
            self.status_var.set("Исполнение завершилось без итоговой записи.")
            return
        self.status_var.set(f"Завершено: {summary.completed_strokes}/{summary.total_strokes} штрихов; статус {summary.status}.")
        if summary.status == "failed":
            messagebox.showerror("Ошибка рисования", summary.error or "Неизвестная ошибка", parent=self.root)
        elif summary.status == "stopped":
            messagebox.showinfo("Остановлено", f"Остановлено после {summary.completed_strokes} штрихов. Кнопка мыши отпущена.", parent=self.root)
        else:
            messagebox.showinfo("Тест завершён", f"Выполнено {summary.completed_strokes} штрихов за {summary.duration_seconds:.1f} с.\n\n"
                                f"Журнал: {EXECUTION_RESULTS_PATH}\n\nПроверьте на доске диагонали, углы, ломаные и замкнутые контуры.", parent=self.root)

    def _stop_execution(self):
        if self.running:
            self.stop_event.set()
            self.status_var.set("Отправлен запрос на остановку. Кнопка мыши будет отпущена.")

    def _open_folder(self):
        try:
            os.startfile(str(APP_DIR))
        except Exception as exc:
            messagebox.showerror("Не удалось открыть папку", str(exc), parent=self.root)

    def _on_close(self):
        if self.running:
            if messagebox.askyesno("Остановить рисование?", "Отправить остановку и закрыть приложение?", parent=self.root):
                self.stop_event.set()
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style(root).theme_use("vista")
    except tk.TclError:
        pass
    DrawingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
