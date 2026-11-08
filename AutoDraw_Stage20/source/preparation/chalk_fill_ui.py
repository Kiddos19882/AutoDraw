from __future__ import annotations

"""Tkinter single-task FILL-001 preflight UI."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from PIL import Image, ImageGrab
import pyautogui
from typing import Any, Callable

from chalk_fill_execution import prepare_fill001_single_task_plan
from chalk_fill_matrix import (
    FillMatrixError,
    build_fill001_matrix,
    build_fill001_rs_matrix,
    load_fill001_matrix,
    write_fill001_matrix,
)
from brush_behavior_test_ui import _cursor_safe_point_outside_region
from chalk_fill_capture_adapter import audit_fill001_png_pair
from fill001_smooth_ab import (
    PROTOCOL as FILL001_AB_PROTOCOL, build_fill001_smooth_ab_matrix,
    analyze_smooth_ab_pair,
)
from fill001_smooth_ab_v2 import (
    PROTOCOL as FILL001_AB_V2_PROTOCOL, SCREEN_MASK as FILL001_V2_MASK,
    V2_IDENTITY_FIELDS, build_fill001_smooth_ab_v2_matrix,
    analyze_smooth_ab_v2_pair,
)
from fill001_smooth_ab_v3 import (
    PROTOCOL as FILL001_AB_V3_PROTOCOL, COORDINATE_PREFLIGHT,
    V3_IDENTITY_FIELDS, build_fill001_smooth_ab_v3_matrix,
    analyze_smooth_ab_v3_pair,
)
from fill001_screen_mask_v2 import audit_screen_mask_v2
from fill001_screen_mask_v2_binding import bind_from_monitor_run
from fill001_monitor_diagnostic import (
    PROTOCOL as FILL001_DIAGNOSTIC_PROTOCOL,
    audit_diagnostic_capture, inspect_diagnostic_preflight,
)


class Fill001Tab:
    """Create/load a FILL-001 manifest and hand one approved task to Stage 6."""

    def __init__(
        self,
        root: tk.Misc,
        parent: tk.Widget,
        output_dir: str | Path,
        *,
        brush_tab: Any,
        on_transfer_plan: Callable[[dict[str, Any], Path], bool],
        on_start: Callable[[int, dict[str, Any], Path], bool],
    ) -> None:
        self.root = root
        self.output_dir = Path(output_dir).resolve() / "fill001"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.brush_tab = brush_tab
        self.on_transfer_plan = on_transfer_plan
        self.on_start = on_start
        self.matrix: dict[str, Any] | None = None
        self.manifest_path: Path | None = None
        self.active_task: dict[str, Any] | None = None
        self.active_plan_path: Path | None = None
        self.active_run_record: Path | None = None
        self.before_png_path: Path | None = None
        self.after_png_path: Path | None = None
        self.capture_region: dict[str, int] | None = None
        self.diagnostic_active = False
        self.diagnostic_readiness: dict[str, Any] | None = None
        self.diagnostic_screens: dict[str, str] = {}
        self.diagnostic_capture_timestamps: dict[str, str] = {}
        self.diagnostic_var = tk.BooleanVar(value=False)
        self.series_var = tk.StringVar(
            value=f"fill001-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.task_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Создайте новую серию или откройте существующий manifest.")
        self.bridge_status_var = tk.StringVar(value="Monitor/Bridge: подключение ещё не проверено.")
        self._build(parent)

    def _build(self, parent: tk.Widget) -> None:
        outer = ttk.Frame(parent, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="FILL-001 — контролируемый одиночный preflight",
                  font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Этот интерфейс запускает только одну выбранную задачу. Матрица из 45 ячеек "
                "остаётся запрещённой для пакетного исполнения. Перед запуском требуется явное "
                "подтверждение оператора, калибровка доски, активный Game Monitor Bridge и "
                "подтверждение фактического радиуса кисти."
            ),
            wraplength=1120,
            justify="left",
        ).pack(anchor="w", pady=(4, 10))

        series = ttk.LabelFrame(outer, text="Серия FILL-001", padding=8)
        series.pack(fill="x", pady=(0, 8))
        ttk.Label(series, text="ID серии").pack(side="left")
        ttk.Entry(series, textvariable=self.series_var, width=32).pack(side="left", padx=6)
        ttk.Button(series, text="Создать manifest (45 задач)", command=self.create_series).pack(side="left", padx=4)
        ttk.Button(series, text="Новый Smooth A/B (2 задачи)", command=self.create_smooth_ab_series).pack(side="left", padx=4)
        ttk.Button(series, text="Новый Smooth A/B V2 (2 задачи)", command=self.create_smooth_ab_v2_series).pack(side="left", padx=4)
        ttk.Button(series, text="Новый Smooth A/B V3 (BoardPane)", command=self.create_smooth_ab_v3_series).pack(side="left", padx=4)
        ttk.Button(series, text="Открыть manifest…", command=self.load_series_dialog).pack(side="left", padx=4)
        self.manifest_label = ttk.Label(series, text="Manifest не загружен")
        self.manifest_label.pack(side="left", padx=10)

        bridge_controls = ttk.LabelFrame(
            outer, text="Game Monitor 0.2.4 + Bridge — для FILL-001 V3", padding=8
        )
        bridge_controls.pack(fill="x", pady=(0, 8))
        controls = ttk.Frame(bridge_controls)
        controls.pack(fill="x")
        ttk.Button(
            controls, text="1. Запустить Bridge (Telemetry ON)",
            command=self.start_fill001_bridge,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            controls, text="2. Копировать Monitor JS",
            command=self.copy_fill001_monitor,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            controls, text="3. Копировать Bridge JS",
            command=self.copy_fill001_bridge_snippet,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            controls, text="4. Проверить подключение",
            command=self.check_fill001_bridge,
        ).pack(side="left", padx=(0, 6))
        ttk.Label(
            bridge_controls,
            text=("Порядок: запустите Bridge; в F12 → Console именно игрового iframe "
                  "вставьте Monitor JS, затем Bridge JS. После подключения проверьте "
                  "статус. Сами кнопки НЕ внедряют код в браузер."),
            wraplength=1080, justify="left",
        ).pack(anchor="w", pady=(6, 2))
        ttk.Label(
            bridge_controls, textvariable=self.bridge_status_var,
            wraplength=1080, justify="left",
        ).pack(anchor="w", pady=(2, 0))

        task = ttk.LabelFrame(outer, text="Одиночная задача", padding=8)
        task.pack(fill="x", pady=(0, 8))
        ttk.Label(task, text="Pending task").pack(side="left")
        self.task_combo = ttk.Combobox(task, textvariable=self.task_var, state="readonly", width=62)
        self.task_combo.pack(side="left", padx=6)
        self.task_combo.bind("<<ComboboxSelected>>", lambda _event: self._show_selected_task())
        ttk.Button(task, text="Обновить список", command=self._refresh_tasks).pack(side="left", padx=4)
        ttk.Button(task, text="Подготовить и запустить одну задачу", command=self.prepare_and_run).pack(side="left", padx=4)
        ttk.Button(task, text="Проверить runtime + PNG и принять capture", command=self.finalize_capture).pack(side="left", padx=4)
        ttk.Checkbutton(
            outer, variable=self.diagnostic_var,
            text="Диагностический одиночный FILL-001: Monitor 0.2.4 + run-bound WebGL + полные PNG (27 штрихов)",
        ).pack(anchor="w", pady=(1, 7))
        ttk.Button(
            outer, text="Сравнить Smooth ON/OFF по двум сохранённым прогонам",
            command=self.analyze_smooth_ab,
        ).pack(anchor="w", pady=(0, 7))

        self.task_details = tk.Text(outer, height=10, wrap="word", state="disabled")
        self.task_details.pack(fill="both", expand=True, pady=(0, 8))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1120).pack(anchor="w")

    def start_fill001_bridge(self) -> None:
        """Use the existing shared Bridge launcher with mandatory V3 telemetry."""
        try:
            accepted = self.brush_tab.start_game_monitor_bridge(
                require_input_telemetry=True,
            )
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            self.bridge_status_var.set(f"Bridge BLOCKED: {exc}")
            messagebox.showerror("FILL-001 Bridge", str(exc), parent=self.root)
            return
        if accepted:
            self.bridge_status_var.set(
                "Bridge запускается с Input Telemetry ON. Вставьте Monitor JS и "
                "одноразовый Bridge JS в Console игрового iframe; затем проверьте связь."
            )
        else:
            self.bridge_status_var.set(
                "Bridge не запущен в требуемом режиме V3. Проверьте диалог и "
                "окно сервера; старый Bridge с Telemetry OFF использовать нельзя."
            )

    def copy_fill001_monitor(self) -> None:
        """Copy the shipped Monitor; user selects the game iframe in DevTools."""
        self.brush_tab.copy_game_monitor_source()

    def copy_fill001_bridge_snippet(self) -> None:
        """Copy the current Bridge token, never a stale or sample token."""
        self.brush_tab.copy_game_monitor_bridge_snippet()

    def check_fill001_bridge(self) -> None:
        """Read actual same-session Bridge diagnostics, never assume connected."""
        bridge_root = self.output_dir.parent / "game_monitor_bridge"
        task = self._selected_task()
        if task is None:
            self.bridge_status_var.set(
                "Сначала создайте/выберите FILL-001 задачу для полной "
                "проверки текущего Monitor и Bridge."
            )
            return
        if (task.get("experiment_protocol") == FILL001_AB_V3_PROTOCOL
                and getattr(self.brush_tab, "bridge_input_telemetry_requested", None)
                    is False):
            self.bridge_status_var.set(
                "BLOCKED: Bridge запущен без обязательной Input Telemetry. "
                "Остановите старый Bridge и запустите кнопку 1 повторно."
            )
            return
        try:
            ready = inspect_diagnostic_preflight(bridge_root, task)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self.bridge_status_var.set(
                f"НЕ ГОТОВО: {exc}. Проверьте игровую Console, "
                "кнопки 1–3 и текущее окно Bridge."
            )
            return
        if task.get("experiment_protocol") == FILL001_AB_V3_PROTOCOL:
            try:
                session = json.loads(Path(ready["session_file"]).read_text(encoding="utf-8"))
                config = session.get("bridge_configuration", {}).get("inputTelemetry", {})
                status = session.get("bridge_diagnostics", {}).get("last_monitor_status", {})
                if (config.get("requested") is not True
                        or config.get("enabled") is not True
                        or status.get("inputTelemetryEnabled") is not True):
                    raise ValueError("Input Telemetry ON не подтверждена текущей сессией.")
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
                self.bridge_status_var.set(f"BLOCKED: {exc}")
                return
        self.bridge_status_var.set(
            f"ГОТОВО: Monitor/Bridge, session={ready['session_id']}, "
            "живая геометрия доски подтверждена. "
            "Для V3 свежий пассивный preflight будет выполнен отдельно перед рисованием."
        )

    def create_series(self) -> None:
        self._create_series(smooth_ab=False)

    def create_smooth_ab_series(self) -> None:
        self._create_series(smooth_ab=True)

    def create_smooth_ab_v2_series(self) -> None:
        self._create_series(smooth_ab=False, smooth_ab_v2=True)

    def create_smooth_ab_v3_series(self) -> None:
        self._create_series(smooth_ab=False, smooth_ab_v3=True)

    def _create_series(self, *, smooth_ab: bool, smooth_ab_v2: bool = False, smooth_ab_v3: bool = False) -> None:
        raw_id = self.series_var.get().strip()
        if not raw_id or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", raw_id) is None:
            messagebox.showwarning(
                "Некорректный ID серии",
                "Используйте 1–64 символа: латинские буквы, цифры, точка, дефис или подчёркивание.",
                parent=self.root,
            )
            return
        try:
            # Opt-in diagnostic reproduces the historical 27-stroke RS
            # geometry, never the legacy 131-stroke default.
            matrix = (
                build_fill001_smooth_ab_v3_matrix(raw_id) if smooth_ab_v3 else
                build_fill001_smooth_ab_v2_matrix(raw_id) if smooth_ab_v2 else
                build_fill001_smooth_ab_matrix(raw_id) if smooth_ab else
                build_fill001_rs_matrix(raw_id) if self.diagnostic_var.get()
                else build_fill001_matrix(raw_id)
            )
            path = self.output_dir / f"{raw_id}.json"
            if path.exists():
                raise FileExistsError(f"Серия уже существует: {path}. Откройте её вместо перезаписи.")
            write_fill001_matrix(matrix, path)
            self.matrix, self.manifest_path = matrix, path
            self.manifest_label.configure(text=path.name)
            self._refresh_tasks()
            label = (
                "FILL-001 Smooth A/B V3 BoardPane" if smooth_ab_v3 else
                "FILL-001 Smooth A/B V2" if smooth_ab_v2 else
                "FILL-001 Smooth A/B" if smooth_ab else
                "Диагностический FILL-001-RS" if self.diagnostic_var.get() else "FILL-001"
            )
            self.status_var.set(
                f"Создан {label}: {len(matrix['tasks'])} задач (batch запрещён): {path}"
            )
        except (OSError, ValueError, TypeError, FillMatrixError) as exc:
            messagebox.showerror("Не удалось создать FILL-001 manifest", str(exc), parent=self.root)

    def load_series_dialog(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Открыть FILL-001 manifest",
            initialdir=str(self.output_dir),
            filetypes=[("FILL-001 JSON", "*.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            matrix = load_fill001_matrix(path)
            self.matrix, self.manifest_path = matrix, Path(path).resolve()
            self.series_var.set(matrix["series_id"])
            self.manifest_label.configure(text=self.manifest_path.name)
            self._refresh_tasks()
            self.status_var.set(f"Manifest загружен и проверен: {self.manifest_path}")
        except (OSError, ValueError, TypeError, FillMatrixError) as exc:
            messagebox.showerror("Некорректный FILL-001 manifest", str(exc), parent=self.root)

    def _refresh_tasks(self) -> None:
        if not isinstance(self.matrix, dict):
            self.task_combo.configure(values=())
            return
        pending = [
            task["task_id"] for task in self.matrix.get("tasks", [])
            if isinstance(task, dict)
            and task.get("capture_status") == "pending"
            and task.get("quality_gate_passed") is True
            and task.get("unsupported") is False
        ]
        self.task_combo.configure(values=pending)
        if self.task_var.get() not in pending:
            preferred = next(
                (
                    task["task_id"] for task in self.matrix.get("tasks", [])
                    if task.get("shape_id") == "rectangle"
                    and task.get("requested_radius") == 10
                    and task.get("repeat_index") == 1
                    and task.get("task_id") in pending
                ),
                None,
            )
            self.task_var.set(preferred or (pending[0] if pending else ""))
        self._show_selected_task()

    def _show_selected_task(self) -> None:
        task = self._selected_task()
        if task is None:
            detail = "Нет выбранной pending задачи. Проверьте manifest и статусы задач."
        else:
            detail = (
                f"Task: {task['task_id']}\n"
                f"Shape: {task['shape_id']}\n"
                f"Radius: {task['requested_radius']}\n"
                f"Repeat: {task['repeat_index']}/{task.get('planned_repeats', 3)}\n"
                + (f"Declared smooth: {task['expected_smooth']}\n"
                   if task.get("experiment_protocol") in (FILL001_AB_PROTOCOL, FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL) else "") +
                f"Expected strokes: {task['expected_strokes']}\n"
                f"Coverage estimate: {task['planned_coverage_fraction']:.6%}\n"
                f"Leakage pixels: {task['planned_leakage_pixels']}\n"
                f"Plan signature: {task['plan_signature']}\n"
                f"Matrix execution_allowed: {self.matrix.get('execution_allowed')} (must remain false)\n"
                "Execution scope: one explicitly approved preflight task only."
            )
        self.task_details.configure(state="normal")
        self.task_details.delete("1.0", "end")
        self.task_details.insert("1.0", detail)
        self.task_details.configure(state="disabled")

    def _selected_task(self) -> dict[str, Any] | None:
        if not isinstance(self.matrix, dict):
            return None
        task_id = self.task_var.get().strip()
        matches = [task for task in self.matrix.get("tasks", []) if task.get("task_id") == task_id]
        return matches[0] if len(matches) == 1 else None

    def prepare_and_run(self) -> None:
        if self.active_task is not None:
            messagebox.showwarning(
                "FILL-001 уже подготовлен",
                "Сначала завершите текущую попытку и сохраните её результат. Параллельные задачи запрещены.",
                parent=self.root,
            )
            return
        if self.matrix is None or self.manifest_path is None:
            messagebox.showwarning("Нет manifest", "Сначала создайте или откройте FILL-001 manifest.", parent=self.root)
            return
        task = self._selected_task()
        if task is None:
            messagebox.showwarning("Нет задачи", "Выберите одну pending задачу.", parent=self.root)
            return
        task_id_value = task.get("task_id")
        if not isinstance(task_id_value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", task_id_value) is None:
            messagebox.showwarning("Некорректный task_id", "Task ID содержит символы, запрещённые для файлов журнала.", parent=self.root)
            return
        try:
            disk_matrix = load_fill001_matrix(self.manifest_path)
        except Exception as exc:
            messagebox.showerror("Manifest недоступен", str(exc), parent=self.root)
            return
        if disk_matrix.get("matrix_signature") != self.matrix.get("matrix_signature"):
            messagebox.showerror("Manifest изменился", "Файл manifest изменился после загрузки. Загрузите его заново.", parent=self.root)
            return
        self.matrix = disk_matrix
        task = self._selected_task()
        if task is None:
            messagebox.showwarning("Задача изменилась", "Выбранная задача больше не является pending.", parent=self.root)
            self._refresh_tasks()
            return
        prior_attempt = self.output_dir / "attempts" / f"{task['task_id']}.json"
        if prior_attempt.exists():
            messagebox.showwarning(
                "Задача уже имеет попытку",
                "Для выбранной задачи уже существует журнал запуска. Повторная установка кисти и исполнение заблокированы.",
                parent=self.root,
            )
            return
        if not callable(self.on_transfer_plan) or not callable(self.on_start):
            messagebox.showerror("FILL-001 не подключён", "Callback передачи в Stage 6 отсутствует.", parent=self.root)
            return
        self.diagnostic_active = (
            self.matrix.get("experiment_protocol") in (FILL001_AB_PROTOCOL, FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL)
            or bool(self.diagnostic_var.get())
        )
        self.diagnostic_readiness = None
        self.diagnostic_screens = {}
        self.diagnostic_capture_timestamps = {}
        if self.diagnostic_active:
            try:
                self.diagnostic_readiness = inspect_diagnostic_preflight(
                    self.output_dir.parent / "game_monitor_bridge", task
                )
            except (ValueError, OSError, TypeError, KeyError) as exc:
                self.diagnostic_active = False
                self.status_var.set(f"Диагностический preflight заблокирован: {exc}")
                messagebox.showwarning("FILL-001 Monitor 0.2.4 не готов", str(exc), parent=self.root)
                return
        if not self.brush_tab._validate_automation_preflight():
            return
        canvas_size = self.brush_tab.get_canvas_size()
        if not canvas_size:
            messagebox.showwarning("Не выбрана область доски", "Сначала задайте область доски в AutoDraw.", parent=self.root)
            return
        if tuple(map(int, canvas_size)) != (460, 240):
            messagebox.showwarning(
                "Размер logical canvas не совпадает",
                "FILL-001 frozen canvas — 460×240 logical pixels. Изменять или масштабировать frozen mask нельзя.",
                parent=self.root,
            )
            return
        capture_error = None
        try:
            # The board ROI must be visible, not covered by the AutoDraw window.
            self.root.iconify()
            self.root.update_idletasks()
            self.root.update()
            time.sleep(0.5)
            self.before_png_path = self._capture_board_png(task, phase="before")
        except Exception as exc:
            capture_error = exc
            self.before_png_path = None
        finally:
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
        if capture_error is not None:
            messagebox.showwarning(
                "FILL-001 preflight не пройден",
                f"Не удалось подтвердить пустую доску и сохранить before PNG. Рисование не запущено.\\n\\n{capture_error}",
                parent=self.root,
            )
            return
        diagnostic_warning = (
            "\n\nВКЛЮЧЕНА ДИАГНОСТИКА: программа сохранит PNG ВСЕГО ЭКРАНА до и после "
            "рисования, включая другие окна и возможные личные данные. "
            "Не публикуйте эти PNG в открытом репозитории без проверки. "
            "Выполнится только выбранная задача, расход CHALK реален."
            if getattr(self, "diagnostic_active", False) else ""
        )
        if not messagebox.askyesno(
            "Разрешить один экспериментальный запуск?",
            (
                f"Будет запущена только задача {task['task_id']} с радиусом {task['requested_radius']}.\n\n"
                "Проверьте, что это отдельная тестовая доска, она очищена, запас краски достаточен, "
                "Game Monitor Bridge подключён, а calibrated ROI точно охватывает игровую доску. "
                "Пакетное выполнение других задач останется запрещено. Продолжить?"
                + diagnostic_warning
                + (
                    "\n\nРЕЖИМ ИГРЫ: установите в интерфейсе игры smooth="
                    + ("ON" if task["expected_smooth"] else "OFF")
                    + ". AutoDraw не переключает этот параметр. Фактический режим "
                      "всех 27 штрихов будет проверен по ENGINE_FRAME_SAMPLE."
                    if task.get("experiment_protocol") in (FILL001_AB_PROTOCOL, FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL) else ""
                )
            ),
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            current_region = self.brush_tab.get_canvas_area()
            if not isinstance(current_region, dict):
                raise ValueError("Calibrated screen ROI стал недоступен после before capture.")
            current_region = {
                key: int(current_region[key]) for key in ("x", "y", "width", "height")
            }
            if current_region != self.capture_region:
                raise ValueError(
                    "Calibrated screen ROI изменился после before capture; "
                    "переснимите before PNG и повторите подготовку задачи."
                )
            plan, selected = prepare_fill001_single_task_plan(
                self.matrix,
                task["task_id"],
                operator_approved_single_task_preflight=True,
            )
            if task.get("experiment_protocol") == FILL001_AB_V3_PROTOCOL:
                plan["generation"]["screen_mapping_policy"] = COORDINATE_PREFLIGHT
                plan["generation"]["screen_mapping_expected_roi"] = dict(self.capture_region)
            plan_path = self.output_dir / "plans" / f"{task['task_id']}.json"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if not self.on_transfer_plan(plan, plan_path):
                raise RuntimeError("AutoDraw отклонил передачу FILL-001 плана в Stage 6.")
            generation = plan.get("generation")
            screen_transform = generation.get("screen_transform") if isinstance(generation, dict) else None
            if task.get("experiment_protocol") == FILL001_AB_V3_PROTOCOL:
                if (screen_transform is not None
                        or plan["generation"].get("screen_mapping_expected_roi") != self.capture_region):
                    raise RuntimeError("V3 must remain LOGICAL until fresh BoardPane preflight.")
            elif (
                not isinstance(screen_transform, dict)
                or screen_transform.get("screen_roi") != self.capture_region
            ):
                raise RuntimeError(
                    "Logical→screen transform DrawingPlan не совпадает с ROI, "
                    "с которого снят before PNG."
                )
            self.active_task = selected
            self.active_plan_path = plan_path
            self.status_var.set(
                f"План {task['task_id']} передан в Stage 6. Устанавливаю радиус {task['requested_radius']} "
                "перетаскиванием и ожидаю точного подтверждения Game Monitor."
            )
            if not self.brush_tab.set_brush_size_for_workflow(
                int(task["requested_radius"]),
                lambda brush: self._start_after_brush_verified(brush),
            ):
                self.active_task = None
                self.active_plan_path = None
                raise RuntimeError("Не удалось начать установку/проверку радиуса кисти.")
        except Exception as exc:
            self.status_var.set(f"FILL-001 остановлен до запуска: {exc}")
            messagebox.showerror("Не удалось подготовить FILL-001", str(exc), parent=self.root)

    def _start_after_brush_verified(self, brush: int) -> None:
        if self.active_task is None or self.active_plan_path is None:
            self.status_var.set("FILL-001 handoff отменён: активная задача отсутствует.")
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            return
        if brush != self.active_task.get("requested_radius"):
            self.status_var.set("FILL-001 заблокирован: подтверждённый радиус не совпадает с задачей.")
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            return
        if getattr(self, "diagnostic_active", False):
            try:
                fresh = inspect_diagnostic_preflight(
                    self.output_dir.parent / "game_monitor_bridge", self.active_task
                )
                if (not isinstance(self.diagnostic_readiness, dict)
                        or fresh["session_id"] != self.diagnostic_readiness["session_id"]
                        or fresh["renderer_geometry_sha256"] !=
                           self.diagnostic_readiness["renderer_geometry_sha256"]):
                    raise ValueError("Bridge session или native renderer geometry изменились после before PNG.")
            except (ValueError, OSError, TypeError, KeyError) as exc:
                self.status_var.set(f"Диагностический FILL-001 остановлен до game input: {exc}")
                messagebox.showerror("Monitor/Bridge сменился", str(exc), parent=self.root)
                self.active_task = None
                self.active_plan_path = None
                return
        attempt_path = self.output_dir / "attempts" / f"{self.active_task['task_id']}.json"
        attempt_path.parent.mkdir(parents=True, exist_ok=True)
        if attempt_path.exists():
            messagebox.showwarning(
                "Задача уже запускалась",
                "Для этой задачи уже существует запись попытки. Повторный запуск запрещён без отдельного разбора.",
                parent=self.root,
            )
            return
        record = {
            "schema_version": 1,
            "phase_id": "FILL001",
            "task": self.active_task,
            "manifest_path": str(self.manifest_path),
            "plan_path": str(self.active_plan_path),
            "status": "start_requested",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "execution_report_path": None,
            "before_png": str(self.before_png_path) if self.before_png_path else None,
            "screen_roi": dict(self.capture_region) if self.capture_region else None,
            "after_png": None,
            "capture_path": None,
            "diagnostic": ({
                "protocol": self.diagnostic_readiness["protocol"],
                "readiness": dict(self.diagnostic_readiness),
                "before_full_screen": self.diagnostic_screens.get("before"),
                "before_captured_at_utc": self.diagnostic_capture_timestamps.get("before"),
                "after_full_screen": None,
                "after_captured_at_utc": None,
                "audit_report": None,
            } if getattr(self, "diagnostic_active", False) else None),
        }
        attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.active_run_record = attempt_path
        try:
            started = bool(self.on_start(brush, self.active_task, self.active_plan_path))
        except Exception as exc:
            started = False
            self.status_var.set(f"Ошибка запуска FILL-001: {exc}")
        if not started:
            record["status"] = "start_rejected"
            attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status_var.set("Stage 6 не принял FILL-001. Попытка зафиксирована; задача не будет запущена повторно автоматически.")
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            return
        record["status"] = "running"
        attempt_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.status_var.set(f"FILL-001 запущен: {self.active_task['task_id']}. Остальные задачи серии не запускаются.")

    def handle_executor_finished(self, summary: dict[str, Any], report_path: str | Path | None) -> bool:
        if self.active_task is None or self.active_run_record is None:
            return False
        record = json.loads(self.active_run_record.read_text(encoding="utf-8"))
        record["execution_report_path"] = str(report_path) if report_path is not None else None
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        record["executor_status"] = summary.get("status")
        record["status"] = "execution_completed_pending_runtime_and_png_audit" if summary.get("status") == "completed" else "execution_failed"
        self.active_run_record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if summary.get("status") == "completed":
            self.root.after(1000, self._capture_after_png)
        else:
            self.status_var.set(
                f"FILL-001 {self.active_task['task_id']}: Executor {summary.get('status')}. "
                f"Отчёт: {report_path or 'не сохранён'}. Task не принят."
            )
        return True

    def _capture_board_png(self, task: dict[str, Any], *, phase: str) -> Path:
        """Capture the actual calibrated client ROI; logical 460x240 is handled separately."""
        config = self.brush_tab.get_calibration_profile() if callable(self.brush_tab.get_calibration_profile) else None
        if not isinstance(config, dict):
            raise ValueError("Профиль калибровки доски отсутствует.")
        region = self.brush_tab.get_canvas_area()
        if not isinstance(region, dict):
            raise ValueError("Screen ROI доски отсутствует.")
        region = {key: int(region[key]) for key in ("x", "y", "width", "height")}
        if region["width"] < 2 or region["height"] < 2:
            raise ValueError("Calibrated screen ROI должен быть не меньше 2×2 px.")
        if phase == "after" and self.capture_region is None:
            raise ValueError("Before capture ROI отсутствует; after PNG не может быть принят без пары.")
        if phase == "after" and region != self.capture_region:
            raise ValueError("ROI доски изменился между before/after capture.")
        if phase == "before":
            self.capture_region = dict(region)
        screen = ImageGrab.grab()
        expected_screen = config.get("screen_size", {})
        if isinstance(expected_screen, dict) and (
            expected_screen.get("width") != screen.width or expected_screen.get("height") != screen.height
        ):
            raise ValueError("Разрешение экрана изменилось после калибровки.")
        if (
            region["x"] < 0 or region["y"] < 0
            or region["x"] + region["width"] > screen.width
            or region["y"] + region["height"] > screen.height
        ):
            raise ValueError("Calibrated screen ROI выходит за границы текущего снимка экрана.")
        configured_regions = config.get("regions", {})
        avoid = tuple(
            value for name, value in configured_regions.items()
            if name != "board_area" and isinstance(value, dict)
        ) if isinstance(configured_regions, dict) else ()
        safe_point = _cursor_safe_point_outside_region(
            region, (screen.width, screen.height), avoid_regions=avoid
        )
        if phase == "after":
            pyautogui.mouseUp()
        pyautogui.moveTo(*safe_point)
        time.sleep(0.25)
        screen = ImageGrab.grab()
        crop = screen.crop((
            region["x"], region["y"],
            region["x"] + region["width"], region["y"] + region["height"],
        )).convert("RGB")
        if crop.size != (region["width"], region["height"]):
            raise ValueError("Размер PNG crop не совпадает с фактическим calibrated screen ROI.")
        directory = self.output_dir / "captures"
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f"{task['task_id']}-{phase}.png"
        if phase == "before":
            reference_path, metadata_path = self.brush_tab._blank_board_reference_paths()
            if not reference_path.is_file() or not metadata_path.is_file():
                raise ValueError("Не найден подтверждённый эталон пустой доски.")
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if (
                metadata.get("reference_type") != "user_confirmed_blank_board_roi"
                or metadata.get("user_confirmed_blank") is not True
                or metadata.get("board_region") != region
                or metadata.get("screen_size") != {"width": screen.width, "height": screen.height}
                or metadata.get("image_file") != reference_path.name
            ):
                raise ValueError("Эталон пустой доски не совпадает с текущими ROI/разрешением.")
            from brush_experiment_capture import evaluate_board_clear

            with Image.open(reference_path) as reference:
                if reference.size != crop.size:
                    raise ValueError("Размер эталона пустой доски не совпадает с FILL-001 crop.")
                clear_result = evaluate_board_clear(reference.copy(), crop)
            if clear_result.get("status") not in {"restored", "restored_within_pixel_tolerance"}:
                raise ValueError(
                    f"Пустая доска не подтверждена эталоном: {clear_result.get('status')}."
                )
        if getattr(self, "diagnostic_active", False):
            full_screen = directory / f"{task['task_id']}-{phase}-full-screen.png"
            if destination.exists() or full_screen.exists():
                raise FileExistsError("Диагностические PNG этого task уже существуют; перезапись запрещена.")
            # A single ImageGrab frame supplies both PNGs, so cropping cannot
            # silently mix a newer screenshot with the earlier calibrated ROI.
            screen.save(full_screen)
            self.diagnostic_screens[phase] = str(full_screen)
            self.diagnostic_capture_timestamps[phase] = datetime.now(timezone.utc).isoformat()
        crop.save(destination)
        return destination

    def _capture_after_png(self) -> None:
        if self.active_task is None or self.active_run_record is None:
            return
        try:
            self.after_png_path = self._capture_board_png(self.active_task, phase="after")
            record = json.loads(self.active_run_record.read_text(encoding="utf-8"))
            record["after_png"] = str(self.after_png_path)
            record["after_png_captured_at_utc"] = datetime.now(timezone.utc).isoformat()
            if isinstance(record.get("diagnostic"), dict):
                record["diagnostic"]["after_full_screen"] = self.diagnostic_screens.get("after")
                record["diagnostic"]["after_captured_at_utc"] = self.diagnostic_capture_timestamps.get("after")
            self.active_run_record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status_var.set(
                f"After PNG сохранён: {self.after_png_path}. Нажмите «Проверить runtime + PNG и принять capture» "
                "после завершения runtime binding."
            )
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
        except Exception as exc:
            self.status_var.set(f"Не удалось сохранить after PNG: {exc}. Capture не принят.")
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass


    def analyze_smooth_ab(self) -> None:
        """Analyze only a complete new A/B pair, never archival captures."""
        try:
            if (not isinstance(self.matrix, dict)
                    or self.matrix.get("experiment_protocol") not in (FILL001_AB_PROTOCOL, FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL)):
                raise FillMatrixError("Откройте двухзадачный FILL-001 Smooth A/B manifest.")
            if self.manifest_path is None:
                raise FillMatrixError("A/B manifest не загружен.")
            current = load_fill001_matrix(self.manifest_path)
            if current["matrix_signature"] != self.matrix["matrix_signature"]:
                raise FillMatrixError("Manifest изменился; перезагрузите его.")
            reports = []
            for task in current["tasks"]:
                path = task.get("capture_path")
                if task.get("capture_status") != "completed" or not path:
                    raise FillMatrixError("Оба режима должны иметь завершённый raw audit и PNG.")
                reports.append(json.loads(Path(path).read_text(encoding="utf-8")))
            protocol = current["experiment_protocol"]
            analysis = (
                analyze_smooth_ab_v3_pair(current, reports)
                if protocol == FILL001_AB_V3_PROTOCOL else
                analyze_smooth_ab_v2_pair(current, reports)
                if protocol == FILL001_AB_V2_PROTOCOL
                else analyze_smooth_ab_pair(current, reports)
            )
            path = self.output_dir / "captures" / (
                f"{current['series_id']}-{protocol}-comparison.json"
            )
            if path.exists():
                previous = json.loads(path.read_text(encoding="utf-8"))
                if previous != analysis:
                    raise FileExistsError("A/B comparison exists with other contents.")
            else:
                path.write_text(
                    json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            self.status_var.set(
                f"A/B comparison: {analysis['status']}. "
                f"Результат: {path}. PNG quality каждого прогона показано отдельно."
            )
        except Exception as exc:
            self.status_var.set(f"A/B comparison заблокирован: {exc}")
            messagebox.showerror("FILL-001 Smooth A/B", str(exc), parent=self.root)

    def finalize_capture(self) -> None:
        if self.active_task is None or self.active_run_record is None:
            messagebox.showwarning("Нет активной FILL-001 задачи", "Сначала выполните одну задачу FILL-001.", parent=self.root)
            return
        try:
            record = json.loads(self.active_run_record.read_text(encoding="utf-8"))
            disk_matrix = load_fill001_matrix(self.manifest_path)
            if disk_matrix.get("matrix_signature") != self.matrix.get("matrix_signature"):
                raise FillMatrixError("Manifest изменился после запуска; capture не будет перезаписывать внешние изменения.")
            report_path = Path(record["execution_report_path"])
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("runtime_binding_status") != "passed":
                context = report.get("experiment_context")
                if not isinstance(context, dict) or context.get("phase_id") != "FILL001":
                    raise FillMatrixError(
                        "Executor report не содержит корректный FILL-001 experiment context."
                    )
                from chalk_fill_runtime_binding import (
                    build_fill001_runtime_binding_summary,
                    find_fill001_runtime_binding,
                )
                from drawing.execution_diagnostics import update_execution_report

                bridge_root = self.output_dir.parent / "game_monitor_bridge"
                runtime_binding = find_fill001_runtime_binding(context, bridge_root, report_path)
                if runtime_binding is None:
                    update_execution_report(
                        report_path,
                        {
                            "runtime_binding_status": "not_ready",
                            "runtime_binding_error": (
                                "Bridge session/run ещё не содержит полный набор runtime evidence."
                            ),
                        },
                    )
                    raise FillMatrixError(
                        "Runtime binding пока не готов: Bridge session/run ещё обновляется "
                        "или не найден в окне этого исполнения. Повторите проверку после завершения записи Bridge."
                    )
                update_execution_report(
                    report_path,
                    {
                        "runtime_binding_status": "passed",
                        "runtime_binding": build_fill001_runtime_binding_summary(runtime_binding),
                        "runtime_binding_error": None,
                    },
                )
                report = json.loads(report_path.read_text(encoding="utf-8"))
            binding = report.get("runtime_binding")
            session_path = binding.get("session_file") if isinstance(binding, dict) else None
            before_png, after_png = record.get("before_png"), record.get("after_png")
            if not session_path or not before_png or not after_png:
                raise FillMatrixError("Не хватает session.json, before PNG или after PNG.")
            if not isinstance(record.get("screen_roi"), dict):
                raise FillMatrixError("В attempt record отсутствует calibrated screen ROI.")
            if isinstance(record.get("diagnostic"), dict):
                diagnostic = record["diagnostic"]
                run_file = binding.get("bridge_run_file") if isinstance(binding, dict) else None
                if not run_file:
                    raise FillMatrixError("Диагностический FILL-001: runtime binding не содержит raw run file.")
                audit = audit_diagnostic_capture(
                    task=self.active_task,
                    readiness=diagnostic["readiness"],
                    monitor_run_path=Path(run_file),
                    before_full=Path(diagnostic["before_full_screen"]),
                    before_roi=Path(before_png),
                    after_full=Path(diagnostic["after_full_screen"]),
                    after_roi=Path(after_png),
                    screen_roi=record["screen_roi"],
                )
                audit_file = self.output_dir / "captures" / (
                    f"{self.active_task['task_id']}-{audit['protocol']}.json"
                )
                if audit_file.exists():
                    previous = json.loads(audit_file.read_text(encoding="utf-8"))
                    if previous != audit:
                        raise FileExistsError(
                            "Диагностический raw audit уже существует с другим содержимым; перезапись запрещена."
                        )
                else:
                    audit_file.write_text(
                        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                    )
                diagnostic["audit_report"] = str(audit_file)
                diagnostic["raw_e4_status"] = audit["status"]
                record["diagnostic"] = diagnostic
                self.active_run_record.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                if audit["status"] != "PASS_E4_RAW_CAPTURE":
                    raise FillMatrixError(
                        "FILL-001 raw E4 diagnostic PARTIAL: " + ", ".join(audit["reasons"])
                        + ". Report сохранён, capture не принят."
                    )
            if self.matrix.get("experiment_protocol") in (FILL001_AB_PROTOCOL, FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL):
                # Preserve a failed PNG as evidence. This is NOT the legacy
                # accepted FILL-001 capture path and never weakens its gates.
                ab_protocol = self.matrix["experiment_protocol"]
                if audit.get("protocol") != ab_protocol:
                    raise FillMatrixError("Expected the same versioned Smooth A/B raw audit.")
                png = audit_fill001_png_pair(
                    "rectangle", before_png, after_png, screen_roi=record["screen_roi"]
                )
                evidence = {
                    "schema_version": (3 if ab_protocol == FILL001_AB_V3_PROTOCOL else
                                       2 if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL) else 1),
                    "protocol": ab_protocol,
                    "task_id": self.active_task["task_id"],
                    "expected_smooth": self.active_task["expected_smooth"],
                    "raw_e4_status": audit["status"],
                    "run_id": audit["run_id"], "session_id": audit["session_id"],
                    "exact_chalk": audit["exact_chalk"],
                    "plan_signature": self.active_task["plan_signature"],
                    "target_mask_sha256": self.active_task["target_mask_sha256"],
                    "raw_run_sha256": audit["raw_run_sha256"],
                    "renderer_geometry_sha256": audit["geometry_at_start_sha256"],
                    "screen_roi": record["screen_roi"],
                    "before_png": str(before_png), "after_png": str(after_png),
                    "before_png_sha256": png["before_png_sha256"],
                    "after_png_sha256": png["after_png_sha256"],
                    "png_audit": png,
                }
                if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL):
                    # This is run-bound and derived from the CURRENT raw run;
                    # no old series, fitted offsets, or screenshot-derived calibration.
                    v2_binding = bind_from_monitor_run(Path(run_file), audit_file)
                    if v2_binding["screen_roi"] != record["screen_roi"]:
                        raise FillMatrixError("V2 run-bound ROI differs from the captured PNG ROI.")
                    v2 = audit_screen_mask_v2(
                        "rectangle", before_png, after_png,
                        run_id=audit["run_id"], screen_roi=record["screen_roi"],
                        geometry=v2_binding["geometry"],
                    )
                    if (v2["frozen_target_mask_sha256"] !=
                            self.active_task["target_mask_sha256"]):
                        raise FillMatrixError("V2 frozen logical target mismatch.")
                    evidence["screen_mask_version"] = FILL001_V2_MASK
                    evidence["v2_audit"] = v2
                    evidence["v2_binding_provenance"] = v2_binding["provenance"]
                    if ab_protocol == FILL001_AB_V3_PROTOCOL:
                        frozen_source = json.loads(Path(self.active_plan_path).read_text(encoding="utf-8"))
                        generation = frozen_source.get("generation")
                        preflight = generation.get("screen_transform") if isinstance(generation, dict) else None
                        if (not isinstance(preflight, dict)
                                or preflight.get("schema") != COORDINATE_PREFLIGHT
                                or preflight.get("session_id") != audit["session_id"]
                                or preflight.get("renderer_geometry_sha256") != audit["geometry_at_start_sha256"]
                                or preflight.get("screen_roi") != record["screen_roi"]
                                or preflight.get("no_fallback") is not True):
                            raise FillMatrixError("V3 fresh BoardPane preflight evidence is absent or mismatched.")
                        evidence["boardpane_preflight"] = preflight
                evidence_file = self.output_dir / "captures" / (
                    f"{self.active_task['task_id']}-{ab_protocol}-result.json"
                )
                if evidence_file.exists():
                    previous = json.loads(evidence_file.read_text(encoding="utf-8"))
                    if previous != evidence:
                        raise FileExistsError("A/B evidence already exists with different content.")
                else:
                    evidence_file.write_text(
                        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8",
                    )
                matching = [
                    item for item in self.matrix["tasks"]
                    if item["task_id"] == self.active_task["task_id"]
                ]
                if len(matching) != 1:
                    raise FillMatrixError("A/B task identity changed.")
                matching[0]["capture_status"] = "completed"
                matching[0]["capture_path"] = str(evidence_file)
                self.matrix["status"] = "in_progress"
                identity_fields = (
                    V3_IDENTITY_FIELDS if ab_protocol == FILL001_AB_V3_PROTOCOL
                    else V2_IDENTITY_FIELDS if ab_protocol == FILL001_AB_V2_PROTOCOL
                    else (
                        "schema_version", "phase_id", "series_id", "shapes",
                        "radii", "repeats", "tasks", "plan_variant",
                        "candidate_selection_policy", "experiment_protocol",
                    )
                )
                identity = {key: self.matrix[key] for key in identity_fields}
                self.matrix["matrix_signature"] = hashlib.sha256(
                    json.dumps(identity, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                write_fill001_matrix(self.matrix, self.manifest_path)
                measured = (
                    evidence["v2_audit"] if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL)
                    else png
                )
                quality = (
                    measured["v2_diagnostic_gate"] if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL)
                    else png["png_audit_status"]
                )
                record["status"] = (
                    "ab_raw_complete_png_pass" if quality in ("passed", "PASS")
                    else "ab_raw_complete_png_failed"
                )
                record["capture_path"] = str(evidence_file)
                record["capture_summary"] = {
                    "run_id": audit["run_id"], "exact_chalk": audit["exact_chalk"],
                    "coverage_fraction": png["coverage_fraction"],
                    "leakage_pixels": png["leakage_pixels"],
                    "png_audit_status": png["png_audit_status"],
                    "raw_e4_status": audit["status"],
                    **({"v2_coverage_fraction": evidence["v2_audit"]["coverage_fraction"],
                        "v2_leakage_pixels": evidence["v2_audit"]["leakage_pixels"],
                        "v2_diagnostic_gate": evidence["v2_audit"]["v2_diagnostic_gate"]}
                       if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL) else {}),
                }
                self.active_run_record.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                self.status_var.set(
                    f"Smooth A/B: raw E4={audit['status']}, "
                    f"PNG quality={png['png_audit_status']} "
                    f"(coverage={png['coverage_fraction']:.6%}, "
                    f"leakage={png['leakage_pixels']}). "
                    + (f" V2 coverage={evidence['v2_audit']['coverage_fraction']:.6%}, "
                       f"V2 leakage={evidence['v2_audit']['leakage_pixels']}, "
                       f"V2={evidence['v2_audit']['v2_diagnostic_gate']}."
                       if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL) else "")
                    + " Результат сохранён; перед следующим запуском очистите доску."
                )
                self.active_task = None
                self.active_plan_path = None
                self.active_run_record = None
                self.before_png_path = None
                self.after_png_path = None
                self.capture_region = None
                self.diagnostic_active = False
                self.diagnostic_readiness = None
                self.diagnostic_screens = {}
                self.diagnostic_capture_timestamps = {}
                self._refresh_tasks()
                return
            from chalk_fill_capture_adapter import build_fill001_capture_from_runtime

            capture = build_fill001_capture_from_runtime(
                self.active_task,
                session_path=session_path,
                executor_report_path=report_path,
                before_png=before_png,
                after_png=after_png,
                screen_roi=record.get("screen_roi"),
            )
            capture_path = self.output_dir / "captures" / f"{self.active_task['task_id']}-capture.json"
            capture_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            task_id = self.active_task["task_id"]
            matching = [task for task in self.matrix["tasks"] if task.get("task_id") == task_id]
            if len(matching) != 1:
                raise FillMatrixError("Task отсутствует или неоднозначен в текущем manifest.")
            matching[0]["capture_status"] = "completed"
            matching[0]["capture_path"] = str(capture_path)
            self.matrix["status"] = "in_progress"
            identity = {
                key: self.matrix[key]
                for key in ("schema_version", "phase_id", "series_id", "shapes", "radii", "repeats", "tasks")
            }
            self.matrix["matrix_signature"] = hashlib.sha256(
                json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            write_fill001_matrix(self.matrix, self.manifest_path)
            record["status"] = "capture_accepted"
            record["capture_path"] = str(capture_path)
            record["capture_summary"] = {
                "run_id": capture["run_id"],
                "exact_chalk": capture["exact_chalk"],
                "coverage_fraction": capture["coverage_fraction"],
                "leakage_pixels": capture["leakage_pixels"],
                "png_audit_status": capture["png_audit_status"],
                "runtime_binding_status": capture["runtime_binding_status"],
            }
            self.active_run_record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status_var.set(
                f"FILL-001 capture принят: exact CHALK={capture['exact_chalk']}, "
                f"coverage={capture['coverage_fraction']:.3%}, leakage={capture['leakage_pixels']}. "
                "Результат записан в manifest."
            )
            self.active_task = None
            self.active_plan_path = None
            self.active_run_record = None
            self.before_png_path = None
            self.after_png_path = None
            self.capture_region = None
            self.diagnostic_active = False
            self.diagnostic_readiness = None
            self.diagnostic_screens = {}
            self.diagnostic_capture_timestamps = {}
            self._refresh_tasks()
        except Exception as exc:
            messagebox.showerror("FILL-001 capture не принят", str(exc), parent=self.root)
