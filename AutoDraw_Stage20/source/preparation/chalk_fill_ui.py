from __future__ import annotations

"""Tkinter single-task FILL-001 preflight UI."""

import hashlib
import queue
import threading
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from PIL import Image, ImageGrab
import pyautogui
from typing import Any, Callable

from chalk_fill_execution import prepare_fill001_single_task_plan
from fill001_series_runner import build_manifest as build_fill001_series_manifest, write_manifest as write_fill001_series_manifest, SeriesBlocked
from fill001_series_offline_plans import prepare_offline_variants as prepare_fill001_series_geometry
from fill001_series_statistics import write_analysis as write_fill001_series_analysis
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
        on_v5_run: Callable[..., bool] | None = None,
        on_series_run: Callable[..., bool] | None = None,
        on_v5_cancel: Callable[[], None] | None = None,
    ) -> None:
        self.root = root
        self.output_dir = Path(output_dir).resolve() / "fill001"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.brush_tab = brush_tab
        self.on_transfer_plan = on_transfer_plan
        self.on_start = on_start
        self.on_v5_run = on_v5_run
        self.on_series_run = on_series_run
        self.on_v5_cancel = on_v5_cancel
        self.v5_run_after_probe_var = tk.BooleanVar(value=True)
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
        self.v5_candidate_var = tk.StringVar(value="K_trim_0_y190_w2")
        self.series_cycles_var = tk.StringVar(value="2")
        self.series_figures_var = tk.StringVar(value="3")
        self.series_shapes_var = tk.StringVar(value="rectangle,wide_irregular,narrow_irregular")
        self.series_methods_var = tk.StringVar(value="dense_scanlines,spaced_scanlines")
        self.series_radii_var = tk.StringVar(value="1,5,10")
        self.status_var = tk.StringVar(value="Создайте новую серию или откройте существующий manifest.")
        self.bridge_status_var = tk.StringVar(value="Monitor/Bridge: подключение ещё не проверено.")
        self._firefox_driver = None
        self._firefox_messages = queue.Queue()
        self._firefox_confirm = threading.Event()
        self._firefox_stop = threading.Event()
        self._v5_stage6_completed = threading.Event()
        self._v5_stage6_completed.set()
        self._firefox_thread = None
        self._series_manifest_path: Path | None = None
        self._series_pending_manifest: dict[str, Any] | None = None
        self._firefox_execute_series = False
        self._build(parent)
        self.root.after(300, self._poll_firefox_messages)

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
        firefox = ttk.Frame(bridge_controls)
        firefox.pack(fill="x", pady=(6, 0))
        ttk.Button(
            firefox, text="Firefox: открыть игру + Bridge автоматически",
            command=self.start_firefox_monitor,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            firefox, text="Подтвердить доску и разрешить ожидание Firefox",
            command=self.confirm_firefox_board,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            firefox, text="Остановить Firefox-сессию",
            command=self.stop_firefox_monitor,
        ).pack(side="left")
        ttk.Checkbutton(
            bridge_controls,
            text="После ROI выполнить один V5 через Stage6 (только при pointCount=1 и проверенной кисти)",
            variable=self.v5_run_after_probe_var,
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(
            bridge_controls,
            text=("Firefox: откройте доску, подтвердите её здесь, затем нажмите на "
                  "верхнюю панель Firefox вне холста; ожидается native Win32 PID. "
                  "Selenium только подключает Monitor/Bridge к iframe; "
                  "рисование остаётся за штатным Stage6 и fail-closed preflight."),
            wraplength=1080, justify="left",
        ).pack(anchor="w", pady=(3, 2))
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

        v5_group = ttk.LabelFrame(outer, text="FILL-001 DEC-030 V5 — frozen-plan export (без запуска)", padding=6)
        v5_group.pack(fill="x", pady=(0, 6))
        ttk.Combobox(
            v5_group, textvariable=self.v5_candidate_var, state="readonly", width=29,
            values=("K_trim_0_y190_w2", "K_trim_0_y189_w3"),
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            v5_group, text="Сохранить диагностический DrawingPlan V5",
            command=self.export_v5_source_plan,
        ).pack(side="left")
        ttk.Label(
            v5_group, text="Только файл плана. Штатный Stage6 блокирует mixed-width до runtime gate.",
        ).pack(side="left", padx=(8, 0))

        series_batch = ttk.LabelFrame(
            outer, text="FILL001-SERIES-001 — последовательные эксперименты", padding=6
        )
        series_batch.pack(fill="x", pady=(0, 6))
        count_row = ttk.Frame(series_batch)
        count_row.pack(fill="x", pady=2)
        ttk.Label(count_row, text="Циклов").pack(side="left")
        ttk.Entry(count_row, textvariable=self.series_cycles_var, width=6).pack(side="left", padx=(4, 12))
        ttk.Label(count_row, text="Фигур за цикл").pack(side="left")
        ttk.Entry(count_row, textvariable=self.series_figures_var, width=6).pack(side="left", padx=(4, 12))
        ttk.Button(count_row, text="Создать план серии (без запуска)",
                   command=self.create_fill001_series_schedule).pack(side="left")
        ttk.Button(count_row, text="Запустить серию (тестовая доска)",
                   command=self.start_fill001_series_live).pack(side="left", padx=(8, 0))
        ttk.Button(count_row, text="Проанализировать результаты",
                   command=self.analyze_fill001_series_schedule).pack(side="left", padx=(8, 0))
        for description, state in (
            ("Фигуры (через запятую)", self.series_shapes_var),
            ("Способы (dense_scanlines, spaced_scanlines)", self.series_methods_var),
            ("Радиусы кистей (1,5,10,20,30)", self.series_radii_var),
        ):
            entry_row = ttk.Frame(series_batch)
            entry_row.pack(fill="x", pady=2)
            ttk.Label(entry_row, text=description, width=43).pack(side="left")
            ttk.Entry(entry_row, textvariable=state, width=55).pack(side="left", fill="x", expand=True)
        ttk.Label(series_batch, text=(
            "Создание плана ничего не рисует. «Запустить серию» — отдельный "
            "подтверждаемый опыт на тестовой доске: существующий Stage6, Monitor, "
            "ENGINE-001 Clear; на любой ошибке — блокировка следующей фигуры. "
            "Калибровка и исходный эталон чистой доски обязательны."
        ), wraplength=1080, justify="left").pack(anchor="w", pady=(3, 0))

        self.task_details = tk.Text(outer, height=10, wrap="word", state="disabled")
        self.task_details.pack(fill="both", expand=True, pady=(0, 8))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1120).pack(anchor="w")

    def create_fill001_series_schedule(self) -> None:
        """Create only a durable offline manifest, never execute or Clear."""
        try:
            def values(value: str) -> list[str]:
                return [part.strip() for part in value.split(",") if part.strip()]

            manifest = build_fill001_series_manifest(
                cycles=int(self.series_cycles_var.get()),
                figures_per_cycle=int(self.series_figures_var.get()),
                shapes=values(self.series_shapes_var.get()),
                methods=values(self.series_methods_var.get()),
                radii=[int(value) for value in values(self.series_radii_var.get())],
            )
            # Prepare all geometry before writing either artifact. Preview is
            # NOT executor-ready, never an estimate of exact game CHALK.
            geometry = prepare_fill001_series_geometry(manifest)
            destination = self.output_dir / "series" / (manifest["series_id"] + ".json")
            preview_path = destination.with_suffix(".geometry.json")
            if destination.exists() or preview_path.exists():
                raise SeriesBlocked("Серия уже существует, перезапись запрещена.")
            write_fill001_series_manifest(manifest, destination)
            self._series_manifest_path = destination
            with preview_path.open("x", encoding="utf-8") as stream:
                json.dump(geometry, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
            count = len(manifest["tasks"])
            self.status_var.set(
                f"Подготовлена серия {manifest['series_id']}: {count} рисунков, "
                f"{geometry['unique_variants']} геометрических вариантов. "
                f"Manifest: {destination}; offline preview: {preview_path}. "
                "Для реального теста используйте отдельную кнопку «Запустить серию» "
                "после подтверждения Bridge, Firefox и калибровки."
            )
        except (SeriesBlocked, ValueError, OSError) as exc:
            messagebox.showerror("FILL001-SERIES: подготовка заблокирована", str(exc))

    def start_fill001_series_live(self) -> None:
        """One explicit opt-in for a bounded series, reusing ENGINE-001 Clear."""
        try:
            from fill001_series_runner import validate_manifest
            if (self._firefox_thread is not None
                    and self._firefox_thread.is_alive()):
                raise SeriesBlocked("Firefox/Stage6 is already owned by a test")
            if not callable(self.on_series_run):
                raise SeriesBlocked("The shared Stage6 series callback is unavailable")
            selected = self._series_manifest_path
            if selected is None or not selected.is_file():
                filename = filedialog.askopenfilename(
                    parent=self.root, title="Выберите новый FILL001 series manifest",
                    initialdir=str(self.output_dir / "series"),
                    filetypes=(("JSON", "*.json"),),
                )
                if not filename:
                    return
                selected = Path(filename)
            manifest = json.loads(selected.read_text(encoding="utf-8"))
            validate_manifest(manifest)
            result_dir = self.output_dir / "series" / (manifest["series_id"] + "-runs")
            if result_dir.exists() and any(result_dir.iterdir()):
                raise SeriesBlocked("Series evidence already exists: overwriting or resuming is forbidden")
            profile = self.brush_tab.get_calibration_profile() if callable(
                self.brush_tab.get_calibration_profile) else None
            if not isinstance(profile, dict):
                raise SeriesBlocked("Verified Brush Lab Clear button calibration is required")
            from calibrated_game_clear import click_calibrated_board_clear
            screen = profile.get("screen_size", {})
            point = profile.get("points", {}).get("clear_board")
            if (not isinstance(point,dict) or profile.get("needs_review") is True
                    or profile.get("status",{}).get("points",{}).get("clear_board")
                       not in ("set","confirmed")
                    or not isinstance(screen,dict)):
                raise SeriesBlocked("Existing ENGINE-001 Clear calibration needs review")
            if not messagebox.askyesno(
                "Запустить FILL001-SERIES-001",
                f"Будут нарисованы {len(manifest['tasks'])} фигур: одна полностью, "
                "затем точный CHALK/PNG/Monitor, затем штатный Clear и следующая. "
                "Подтверди, что игровая доска СЕЙЧАС визуально пуста: "
                "первый эталон будет снят автоматически по проверенному BoardPane ROI. "
                "Текущий рисунок может быть удалён. Только тестовая доска. "
                "Остановить можно через Stop/Alt. Подтверждаешь пустую доску и запуск?",
                icon="warning", parent=self.root,
            ):
                return
            self._series_pending_manifest = manifest
            self._series_manifest_path = selected
            self._series_profile = profile
            self._firefox_execute_series = True
            self.v5_run_after_probe_var.set(False)
            self.start_firefox_monitor()
        except (ValueError,OSError,TypeError,AttributeError,KeyError) as exc:
            messagebox.showerror("FILL001-SERIES BLOCKED", str(exc), parent=self.root)

    def analyze_fill001_series_schedule(self) -> None:
        """Analyze immutable run records; no Firefox or executor calls."""
        try:
            selected = filedialog.askopenfilename(
                parent=self.root, title="Выберите manifest серии",
                filetypes=(("JSON", "*.json"),),
                initialdir=str(self.output_dir / "series"),
            )
            if not selected:
                return
            manifest_path = Path(selected)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            results_folder = filedialog.askdirectory(
                parent=self.root, title="Выберите каталог JSON результатов",
                initialdir=str(self.output_dir / "series"),
            )
            if not results_folder:
                return
            output_path = Path(results_folder) / (manifest["series_id"] + ".analytics.json")
            write_fill001_series_analysis(manifest, Path(results_folder), output_path)
            data = json.loads(output_path.read_text(encoding="utf-8"))
            self.status_var.set(
                f"Статистика серии {data['series_id']} сохранена: {output_path}; "
                f"измерено {data['observed']}/{data['scheduled']}; "
                f"quality PASS={data['quality_pass']}, FAIL={data['quality_fail']}, "
                f"missing={len(data['missing'])}, rejected={len(data['rejected'])}. "
                "Это анализ отдельных run-bound evidence, не E5/production validation."
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("FILL001-SERIES: анализ", str(exc), parent=self.root)

    def _poll_firefox_messages(self) -> None:
        try:
            while True:
                state, message = self._firefox_messages.get_nowait()
                self.bridge_status_var.set(f"Firefox {state}: {message}")
        except queue.Empty:
            pass
        try:
            self.root.after(300, self._poll_firefox_messages)
        except tk.TclError:
            pass

    def start_firefox_monitor(self) -> None:
        """Opt-in browser telemetry; never bypass FILL-001 Stage6 preflight."""
        if self._firefox_thread is not None and self._firefox_thread.is_alive():
            self.bridge_status_var.set("Firefox уже запущен. Откройте доску и подтвердите.")
            return
        try:
            # Reuse the only shared Bridge, bound to the actual game iframe origin.
            accepted = self.brush_tab.start_game_monitor_bridge(
                require_input_telemetry=True,
                origin_override="https://eufbpet.hust.me/",
            )
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
            self.bridge_status_var.set(f"BLOCKED: {exc}")
            self._firefox_execute_series = False
            self._series_pending_manifest = None
            return
        if not accepted:
            self.bridge_status_var.set("BLOCKED: Bridge не запущен с Input Telemetry ON.")
            self._firefox_execute_series = False
            self._series_pending_manifest = None
            return
        # Read Tk state on UI thread, never from the Firefox worker.
        self._firefox_selected_candidate = self.v5_candidate_var.get()
        self._firefox_execute_v5 = bool(self.v5_run_after_probe_var.get()) and not self._firefox_execute_series
        self._firefox_confirm.clear()
        self._firefox_stop.clear()
        self._v5_stage6_completed.set()
        self._firefox_thread = threading.Thread(
            target=self._firefox_worker, name="fill001-firefox-monitor", daemon=True,
        )
        self._firefox_thread.start()

    def confirm_firefox_board(self) -> None:
        if self._firefox_thread is None or not self._firefox_thread.is_alive():
            self.bridge_status_var.set("BLOCKED: Firefox ещё не запущен.")
            return
        self._firefox_confirm.set()

    def stop_firefox_monitor(self) -> None:
        self._firefox_stop.set()
        self._firefox_confirm.set()
        if callable(self.on_v5_cancel):
            # Stop Stage6 first: guarantees MouseExecutor releases mouseDown.
            self.on_v5_cancel()

    def _firefox_worker(self) -> None:
        driver = None
        try:
            from firefox_monitor_session import (
                FirefoxMonitorError, open_firefox, attach_monitor_after_confirmation,
            )
            driver = open_firefox()
            self._firefox_messages.put(("READY", "Откройте доску в Firefox, подтвердите её в AutoDraw, затем активируйте Firefox щелчком по верхней панели браузера."))
            # No game input and no Monitor injection until the operator confirms.
            if not self._firefox_confirm.wait(timeout=600) or self._firefox_stop.is_set():
                raise FirefoxMonitorError("Доска не подтверждена; действие отменено.")
            if getattr(sys, "frozen", False):
                monitor_dir = Path(sys.executable).resolve().parent / "game_monitor"
            else:
                monitor_dir = Path(__file__).resolve().parents[1] / "game_monitor"
            snippet_path = getattr(self.brush_tab, "bridge_snippet_path", None)
            if not isinstance(snippet_path, Path):
                raise FirefoxMonitorError("Нет одноразового Bridge snippet.")
            deadline = time.monotonic() + 30
            while not snippet_path.is_file() and time.monotonic() < deadline:
                if self._firefox_stop.wait(0.5):
                    raise FirefoxMonitorError("Оператор остановил сессию.")
            from brush_radius_feedback import read_active_bridge_geometry
            bridge_root = self.brush_tab.output_dir / "game_monitor_bridge"
            previous = read_active_bridge_geometry(bridge_root)
            previous_sid = previous.get("session_id") if isinstance(previous, dict) else None
            attached = attach_monitor_after_confirmation(
                driver, monitor_dir / "game_monitor.js", snippet_path,
                operator_confirmed=True,
            )
            ready = None
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline and not self._firefox_stop.is_set():
                ready = read_active_bridge_geometry(bridge_root)
                if isinstance(ready, dict) and ready.get("board_detected") \
                        and not ready.get("board_ambiguous") \
                        and ready.get("session_id") \
                        and ready.get("session_id") != previous_sid:
                    session_file = bridge_root / ready["session_id"] / "session.json"
                    try:
                        session = json.loads(session_file.read_text(encoding="utf-8"))
                        telemetry = session["bridge_configuration"]["inputTelemetry"]
                        status = session["bridge_diagnostics"]["last_monitor_status"]
                        if (telemetry.get("requested") is True
                                and telemetry.get("enabled") is True
                                and status.get("version") == "0.2.4"
                                and status.get("inputTelemetryEnabled") is True):
                            break
                    except (OSError, ValueError, KeyError, TypeError):
                        pass
                self._firefox_stop.wait(0.5)
            else:
                raise FirefoxMonitorError(
                    "BLOCKED: Monitor внедрён, но Bridge не подтвердил свежую "
                    "однозначную сессию игровой доски."
                )
            self._firefox_messages.put((
                "WAITING_FOR_USER_FOCUS",
                f"Monitor {attached['monitor_version']}; session={ready['session_id']}. "
                "Нажмите мышью на верхнюю панель Firefox (НЕ на игровую доску). "
                "AutoDraw автоматически проверит, что Firefox активен.",
            ))
            # The automatic probe is diagnostic only.  It does not clear the
            # board, set a brush, transfer plans or authorize Stage6 input.
            from fill001_firefox_auto_probe import collect_verified_v5_firefox_roi
            minimized = threading.Event()
            def hide_ui() -> None:
                try:
                    self.root.iconify()
                finally:
                    minimized.set()
            self.root.after(0, hide_ui)
            if not minimized.wait(timeout=5):
                raise RuntimeError("BLOCKED: AutoDraw не подтвердил сворачивание окна.")
            try:
                if self._firefox_stop.is_set():
                    raise RuntimeError("BLOCKED: Firefox probe был остановлен.")
                from firefox_foreground_witness import (
                    wait_for_operator_firefox_foreground,
                )
                # This is intentionally a user gesture. Switching a Selenium
                # window or calling Win32 SetForegroundWindow does not prove
                # foreground ownership and must never replace this check.
                wait_for_operator_firefox_foreground(
                    driver, cancel_event=self._firefox_stop,
                    timeout_seconds=90.0,
                )
                self._firefox_messages.put((
                    "FOREGROUND_CONFIRMED",
                    "Активное окно Firefox подтверждено через Win32 PID. "
                    "Начинается пассивная ROI-проверка без кликов.",
                ))
                if self._firefox_execute_series:
                    self._run_fill001_series_in_firefox(
                        driver, bridge_root, ready["session_id"]
                    )
                    self._firefox_stop.wait()
                    return
                # Series uses its own signed DrawingPlan; the optional V5 trim
                # candidate is only required by the isolated V5 probe/run.
                from fill001_v5_handoff import build_fill001_v5_source_plan
                candidate = getattr(self, "_firefox_selected_candidate", "")
                plan = build_fill001_v5_source_plan(candidate)
                mapped, witness, roi = collect_verified_v5_firefox_roi(
                    driver, bridge_root, ready["session_id"], plan,
                    native_mouse=pyautogui,
                    now_utc=lambda: datetime.now(timezone.utc),
                )
            finally:
                if not getattr(self, "_firefox_execute_v5", False):
                    self.root.after(0, self.root.deiconify)
            # Independent passive evidence, never an executable Stage6 gate.
            from fill001_firefox_auto_probe import write_v5_probe_result
            report_path = write_v5_probe_result(
                self.output_dir / "v5_passive_roi",
                candidate_id=candidate,
                session_id=ready["session_id"],
                status="PASSIVE_MAPPING_ONLY_NOT_EXECUTOR_READY",
                source_strokes_sha256=plan["generation"]["source_strokes_sha256"],
                roi=roi,
                mapping=witness,
            )
            self._firefox_messages.put((
                "V5_PROBE_ONLY",
                f"Пассивный ROI подтверждён для session={ready['session_id']}. "
                f"Отчёт: {report_path}. Рисование Stage6 всё ещё заблокировано.",
            ))
            if getattr(self, "_firefox_execute_v5", False):
                if not callable(self.on_v5_run):
                    raise RuntimeError("BLOCKED: Stage6 V5 callback is not connected.")
                started = threading.Event()
                outcome = {}
                def start_v5_on_ui_thread() -> None:
                    try:
                        outcome["accepted"] = bool(self.on_v5_run(
                            source=plan, mapped=mapped, mapping=witness,
                            roi=roi, bridge_root=bridge_root,
                            session_id=ready["session_id"], driver=driver,
                            output_dir=self.output_dir / "v5_stage6_runs",
                            finished_callback=self._on_v5_stage6_finished,
                        ))
                    except Exception as exc:
                        outcome["error"] = f"{type(exc).__name__}: {exc}"
                    finally:
                        started.set()
                self.root.after(0, start_v5_on_ui_thread)
                if not started.wait(timeout=15):
                    raise RuntimeError("BLOCKED: Stage6 V5 launch callback timed out.")
                if not outcome.get("accepted"):
                    raise RuntimeError(
                        f"BLOCKED: Stage6 refused V5: {outcome.get('error','preflight not accepted')}"
                    )
                self._v5_stage6_completed.clear()
                self._firefox_messages.put((
                    "V5_STAGE6_RUNNING",
                    "Stage6: pointCount=1, кисть 10→2/3, 29 штрихов; "
                    "PNG/Bridge отчёты сохраняются в v5_stage6_runs.",
                ))
            # Keep the browser alive for inspection until explicit stop.
            self._firefox_stop.wait()
            # Never terminate the browser while the Stage6 stop handler is
            # still releasing mouseDown from an in-progress stroke.
            self._v5_stage6_completed.wait(timeout=30)
        except Exception as exc:
            details = str(exc)
            sid = None
            ready_state = locals().get("ready")
            if isinstance(ready_state, dict):
                sid = ready_state.get("session_id")
            # Store run-scoped failure reason without cookies, auth tokens or
            # browser profile. Diagnostics cannot grant Stage6 execution.
            if driver is not None:
                try:
                    from fill001_firefox_auto_probe import write_v5_probe_result
                    report_path = write_v5_probe_result(
                        self.output_dir / "v5_passive_roi",
                        candidate_id=getattr(self, "_firefox_selected_candidate", "") or "UNKNOWN",
                        session_id=sid,
                        status="BLOCKED",
                        reason=details,
                    )
                    details = f"{details}. Диагностика: {report_path}"
                except (OSError, ValueError, TypeError):
                    pass
            self._firefox_messages.put(("BLOCKED", details))
            self.root.after(0, self.root.deiconify)
            if driver is not None:
                self._firefox_stop.wait()
        finally:
            # A failed/closed opt-in must not leak a live series request into
            # the next ordinary Firefox/V5 launch.
            self._firefox_execute_series = False
            self._series_pending_manifest = None
            if driver is not None:
                try:
                    driver.quit()
                except Exception:
                    pass
            self._firefox_messages.put(("STOPPED", "Firefox-сессия завершена."))

    def _run_fill001_series_in_firefox(
        self, driver: Any, bridge_root: Path, session_id: str,
    ) -> None:
        """One bounded opt-in sequence on the existing Firefox, Stage6, Bridge.

        No duplicate Clear executor: call the established ENGINE-001 calibrated
        click+blank comparator. Each next task gets a new authenticated passive
        BoardPane preflight, closed Monitor run, PNG and exact CHALK.
        """
        from fill001_series_runner import (
            run_with_series_owner_lock, validate_manifest, SeriesBlocked,
        )
        from fill001_series_handoff import build_series_source_plan
        from fill001_firefox_auto_probe import collect_verified_series_firefox_roi
        from fill001_series_stage6_execution import normalized_series_run
        from fill001_series_engine001_clear import (
            clear_with_existing_engine001, capture_verified_series_boardpane_blank,
            require_same_series_boardpane_roi,
        )
        from fill001_v5_live_gate import verify_v5_live_gate
        from firefox_foreground_witness import firefox_foreground_witness
        from fill001_series_statistics import write_analysis as write_series_analysis

        manifest = self._series_pending_manifest
        if not isinstance(manifest, dict):
            raise SeriesBlocked("No operator-approved FILL001 series manifest")
        validate_manifest(manifest)
        if not callable(self.on_series_run):
            raise SeriesBlocked("Stage6 series callback disconnected")
        profile = getattr(self, "_series_profile", None)
        if not isinstance(profile, dict):
            raise SeriesBlocked("Existing ENGINE-001 Clear button profile missing")
        root_dir = self.output_dir / "series" / (manifest["series_id"] + "-runs")
        state: dict[str, Any] = {"last_clear": None, "last_run": None,
                                 "reference_png": None, "reference_meta": None}

        def bridge_gate(*, blank: bool=False) -> dict:
            if self._firefox_stop.is_set():
                raise SeriesBlocked("Operator stopped the FILL001 series")
            if firefox_foreground_witness(driver) is not True:
                raise SeriesBlocked("Native Firefox foreground lost during series")
            return verify_v5_live_gate(
                bridge_root,session_id=session_id,
                expected_mapping_sha256=state["mapping"]["boardpane_mapping_sha256"],
                require_blank=blank,
            )

        def observe_blank(task: dict) -> dict:
            if self._firefox_stop.is_set():
                raise SeriesBlocked("Series stopped before new passive preflight")
            source = build_series_source_plan(manifest,task["task_id"])
            mapped,mapping,roi = collect_verified_series_firefox_roi(
                manifest,driver,bridge_root,session_id,source,
                native_mouse=pyautogui,
                now_utc=lambda:datetime.now(timezone.utc),
            )
            state.update(source=source,mapped=mapped,mapping=mapping,roi=roi)
            gate=bridge_gate(blank=True)
            if state["reference_meta"] is None:
                # New per-series blank baseline: same native BoardPane probe
                # as Stage6, not a stale manual brush_calibration board_area.
                blank_png = root_dir / "boardpane-blank" / "blank-board-reference.png"
                blank_meta_path = blank_png.with_suffix(".json")
                blank_meta = capture_verified_series_boardpane_blank(
                    roi=roi, screen_size=profile["screen_size"],
                    session_id=session_id,
                    mapping_sha256=mapping["boardpane_mapping_sha256"],
                    point_count=gate["pointCount"], operator_confirmed=True,
                    grab_screen=ImageGrab.grab,
                    reference_png=blank_png, metadata_path=blank_meta_path,
                )
                state["reference_png"] = blank_png
                state["reference_meta"] = blank_meta
            else:
                require_same_series_boardpane_roi(
                    roi, state["reference_meta"], session_id=session_id,
                    mapping_sha256=mapping["boardpane_mapping_sha256"],
                )
            record={
                "valid":True,"fresh_board":True,
                "calibration_valid":True,
                "session_id":session_id,
                "mapping_sha256":mapping["boardpane_mapping_sha256"],
                "observed_at_utc":gate["heartbeat_at_utc"],
                "pointCount":gate["pointCount"],
            }
            if state["last_clear"] is not None:
                record["blank_screen_verification"]=state["last_clear"]
            self._firefox_messages.put((
                "SERIES_PREFLIGHT",
                f"Фигура {task['order']}/{len(manifest['tasks'])}: "
                f"{task['shape_id']}, {task['fill_method']}, кисть {task['brush_radius']}. "
                "Свежий Monitor и BoardPane подтверждены.",
            ))
            return record

        def run_one(task: dict) -> dict:
            if self._firefox_stop.is_set():
                raise SeriesBlocked("Operator stopped before Stage6")
            started=threading.Event()
            done=threading.Event()
            outcome: dict[str, Any]={}
            self._v5_stage6_completed.clear()
            def stage6_finished(result: dict) -> None:
                outcome["report"]=result
                self._v5_stage6_completed.set()
                done.set()
            def start_on_ui_thread() -> None:
                try:
                    outcome["accepted"]=bool(self.on_series_run(
                        manifest=manifest,task_id=task["task_id"],
                        source=state["source"],mapped=state["mapped"],
                        mapping=state["mapping"],roi=state["roi"],
                        bridge_root=bridge_root,session_id=session_id,driver=driver,
                        output_dir=root_dir / "stage6",
                        finished_callback=stage6_finished,
                    ))
                except Exception as exc:
                    outcome["error"]=f"{type(exc).__name__}: {exc}"
                finally:
                    started.set()
            self.root.after(0,start_on_ui_thread)
            if not started.wait(timeout=20) or outcome.get("accepted") is not True:
                self._v5_stage6_completed.set()
                raise SeriesBlocked(
                    "Stage6 refused the next series figure: " +
                    str(outcome.get("error","callback timed out or refused"))
                )
            limit=time.monotonic()+3600
            stopped=False
            while not done.wait(timeout=.2):
                if self._firefox_stop.is_set():
                    # Existing Stop invokes Stage6 stop_event, which must finish
                    # its own mouse-release finally before browser teardown.
                    stopped=True
                if time.monotonic() > limit:
                    self._firefox_messages.put((
                        "SERIES_BLOCKED",
                        "Stage6 timeout: use Stop; Firefox is retained until "
                        "the executor reports mouse-release completion.",
                    ))
                    self._firefox_stop.wait()
                    stopped=True
                # Do not return while Stage6 still owns mouseDown.
            if stopped:
                raise SeriesBlocked("Operator stopped Stage6 after its safe release")
            report=outcome.get("report")
            if not isinstance(report,dict):
                raise SeriesBlocked("No Stage6 figure report")
            state["last_run"]=report
            return normalized_series_run(task,report)

        def clear_and_verify(task: dict) -> dict:
            previous=state.get("last_run")
            if not isinstance(previous,dict) or not isinstance(previous.get("binding"),dict):
                raise SeriesBlocked("Cannot clear before exact Stage6 run binding")
            if self._firefox_stop.is_set():
                raise SeriesBlocked("Operator stopped before Clear")
            binding=previous["binding"]
            gate=bridge_gate()
            if gate["pointCount"] != binding["post_pointCount"]:
                raise SeriesBlocked("Game counter moved between Stage6 and Clear")
            def snapshot_from_bridge() -> dict:
                deadline=time.monotonic()+8
                last=state.get("snapshot_stamp", "")
                while time.monotonic()<deadline:
                    g=bridge_gate()
                    stamp=g["heartbeat_at_utc"]
                    if stamp>last:
                        state["snapshot_stamp"]=stamp
                        return {
                            "session_id":session_id,
                            "mapping_sha256":state["mapping"]["boardpane_mapping_sha256"],
                            "pointCount":g["pointCount"],
                            "maxPoints":g["maxPoints"],
                            "remainingPoints":g["remainingPoints"],
                            "isExact":g["exact"],
                            "captured_at_utc":stamp,
                        }
                    if self._firefox_stop.wait(.2):
                        raise SeriesBlocked("Operator stopped during Clear settle")
                raise SeriesBlocked("No fresh exact Bridge heartbeat after Clear")
            # Immediately bind the pre-Clear counter to the completed run.
            state["snapshot_stamp"]=""
            before=snapshot_from_bridge()
            if before["pointCount"] != binding["post_pointCount"]:
                raise SeriesBlocked("Pre-Clear snapshot does not match closed run")
            # Re-probe after Stage6 release: a moved Firefox window must not
            # reuse desktop screen coordinates frozen at the initial preflight.
            _, current_mapping, current_roi = collect_verified_series_firefox_roi(
                manifest, driver, bridge_root, session_id, state["source"],
                native_mouse=pyautogui,
                now_utc=lambda:datetime.now(timezone.utc),
            )
            if current_mapping["boardpane_mapping_sha256"] != (
                    state["mapping"]["boardpane_mapping_sha256"]):
                raise SeriesBlocked("BoardPane mapping changed before Clear")
            region=require_same_series_boardpane_roi(
                current_roi, state["reference_meta"], session_id=session_id,
                mapping_sha256=current_mapping["boardpane_mapping_sha256"],
            )
            if bridge_gate()["pointCount"] != binding["post_pointCount"]:
                raise SeriesBlocked("Game counter moved during Clear ROI revalidation")
            profile_for_clear = {
                **profile, "regions": {**profile.get("regions", {}), "board_area": region},
            }
            def capture_board_roi() -> Image.Image:
                screen=ImageGrab.grab()
                size=profile["screen_size"]
                if screen.size!=(size["width"],size["height"]):
                    raise SeriesBlocked("Calibrated screen dimensions changed")
                box=(region["x"],region["y"],
                     region["x"]+region["width"],region["y"]+region["height"])
                return screen.crop(box)
            target=root_dir/"clear-png"/(task["task_id"]+"-after-clear.png")
            clear=clear_with_existing_engine001(
                profile=profile_for_clear,
                reference_png=state["reference_png"],
                reference_metadata=state["reference_meta"],
                session_id=session_id,
                mapping_sha256=state["mapping"]["boardpane_mapping_sha256"],
                pre_clear_snapshot=before,
                live_snapshot=snapshot_from_bridge,
                grab_board_roi=capture_board_roi,
                click=lambda x,y:pyautogui.click(x,y),
                foreground_verified=lambda:firefox_foreground_witness(driver),
                stop_requested=self._firefox_stop.is_set,
                wait_settle=lambda:time.sleep(1.5),
                after_clear_png=target,
                mouse_released=previous.get("stage6_summary",{})
                    .get("mouse_release",{}).get("succeeded") is True,
            )
            state["last_clear"]=clear["blank_screen_verification"]
            state["last_run"]=None
            self._firefox_messages.put((
                "SERIES_CLEAR",
                f"Штатный Clear после фигуры {task['order']} подтверждён "
                "эталоном ENGINE-001 и exact game counter.",
            ))
            return clear

        report=run_with_series_owner_lock(
            manifest,results_dir=root_dir,
            observe_blank=observe_blank,run_one=run_one,
            clear_and_verify=clear_and_verify,
            stop_requested=self._firefox_stop.is_set,
        )
        try:
            analysis=root_dir/(manifest["series_id"]+".analytics.json")
            write_series_analysis(manifest,root_dir,analysis)
            report["analysis_path"]=str(analysis)
        except (ValueError,TypeError,OSError) as exc:
            report["analysis_error"]=f"{type(exc).__name__}: {exc}"
        self._firefox_messages.put((
            "SERIES_FINISHED",
            f"Серия {manifest['series_id']}: статус={report['status']}, "
            f"полных quality PASS={report['accepted']}, "
            f"quality FAIL={report['quality_failed']}, "
            f"quota-limited={report['quota_limited']} (не quality PASS), "
            f"подробности: {root_dir}",
        ))
        self._series_pending_manifest=None
        self._firefox_execute_series=False
        self.root.after(0,self.root.deiconify)

    def _on_v5_stage6_finished(self, result: dict) -> None:
        self._v5_stage6_completed.set()
        if result.get("failure_stage") == "BRUSH_SLIDER_NO_RESPONSE":
            # Never auto-retry an unverified game control on the next Firefox
            # session. The operator must recalibrate and opt in again.
            self.v5_run_after_probe_var.set(False)
            self._firefox_messages.put((
                "V5_SLIDER_BLOCKED",
                "Кисть не изменилась при первом перетаскивании. "
                "Автозапуск V5 выключен; требуется новая проверка ползунка.",
            ))
        status = result.get("status", "FAILED")
        attempt = result.get("request", {}).get("attempt_id")
        self._firefox_messages.put((
            "V5_STAGE6_FINISHED",
            f"Stage6 {status}, attempt={attempt}; "
            "actual CHALK и E5 подтверждаются отдельно по run binding.",
        ))
        try:
            self.root.deiconify()
        except tk.TclError:
            pass

    def export_v5_source_plan(self) -> None:
        """Expose the pinned two-candidate source preview; never start Stage6."""
        from fill001_v5_handoff import (
            CANDIDATES, Fill001V5Error, build_fill001_v5_source_plan,
        )
        candidate = self.v5_candidate_var.get()
        if candidate not in CANDIDATES:
            self.status_var.set("V5 BLOCKED: кандидат не из frozen DEC-030 allowlist.")
            return
        destination = self.output_dir / "v5_source_plans" / f"{candidate}.json"
        try:
            plan = build_fill001_v5_source_plan(candidate)
            if destination.exists():
                raise FileExistsError(
                    "Этот frozen V5 source plan уже сохранён. Перезапись запрещена."
                )
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(plan, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
        except (OSError, ValueError, TypeError, Fill001V5Error) as exc:
            self.status_var.set(f"V5 BLOCKED: {exc}")
            return
        self.status_var.set(
            f"V5 frozen source plan сохранён: {destination}. "
            "Не исполнять до verified mixed-width Stage6 handoff."
        )

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
        """Copy only the one-time token from a live, V3-capable Bridge."""
        process = getattr(self.brush_tab, "bridge_process", None)
        if (process is None or process.poll() is not None
                or getattr(self.brush_tab, "bridge_input_telemetry_requested", None)
                   is not True):
            self.bridge_status_var.set(
                "BLOCKED: сначала запустите текущий Bridge с Input Telemetry ON "
                "через кнопку 1. Старый или остановленный snippet копировать нельзя."
            )
            return
        self.brush_tab.copy_game_monitor_bridge_snippet()

    def check_fill001_bridge(self) -> None:
        """Read actual same-session Bridge diagnostics, never assume connected."""
        bridge_root = self.output_dir.parent / "game_monitor_bridge"
        task = self._selected_task()
        if task is None:
            # Allow checking the connection before creating any experiment.
            # This is not permission to execute: task-specific E4 preflight
            # remains mandatory when "Подготовить и запустить" is pressed.
            from brush_radius_feedback import read_active_bridge_geometry
            geometry = read_active_bridge_geometry(bridge_root)
            if not isinstance(geometry, dict) or not geometry.get("board_detected"):
                self.bridge_status_var.set(
                    "НЕ ГОТОВО: нет свежей подключённой Monitor/Bridge сессии "
                    "и одной обнаруженной игровой доской."
                )
                return
            sid = geometry.get("session_id")
            if not isinstance(sid, str) or not sid:
                self.bridge_status_var.set("НЕ ГОТОВО: отсутствует ID Bridge-сессии.")
                return
            try:
                session = json.loads(
                    (bridge_root / sid / "session.json").read_text(encoding="utf-8")
                )
                telemetry = session.get("bridge_configuration", {}).get("inputTelemetry", {})
                status = session.get("bridge_diagnostics", {}).get("last_monitor_status", {})
                if (not isinstance(telemetry, dict)
                        or telemetry.get("requested") is not True
                        or telemetry.get("enabled") is not True
                        or status.get("version") != "0.2.4"
                        or status.get("inputTelemetryEnabled") is not True):
                    raise ValueError("Monitor 0.2.4 + Input Telemetry ON не подтверждены.")
            except (OSError, ValueError, TypeError, AttributeError) as exc:
                self.bridge_status_var.set(f"НЕ ГОТОВО: {exc}")
                return
            self.bridge_status_var.set(
                f"СОЕДИНЕНИЕ ЕСТЬ: session={sid}. "
                "Теперь создайте/выберите FILL-001 V3 задачу для полной "
                "проверки preflight перед рисованием."
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
                if not isinstance(self.diagnostic_readiness, dict):
                    raise ValueError("Отсутствует исходная проверка Monitor перед before PNG.")
                expected_key = (
                    "boardpane_mapping_sha256"
                    if self.active_task.get("experiment_protocol") == FILL001_AB_V3_PROTOCOL
                    else "renderer_geometry_sha256"
                )
                if (fresh["session_id"] != self.diagnostic_readiness["session_id"]
                        or not isinstance(fresh.get(expected_key), str)
                        or fresh[expected_key] != self.diagnostic_readiness.get(expected_key)):
                    raise ValueError(
                        "Bridge session или координатная геометрия BoardPane "
                        "изменились после before PNG; ввод заблокирован."
                    )
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
                    "boardpane_mapping_sha256": audit.get("boardpane_mapping_at_start_sha256"),
                    "screen_roi": record["screen_roi"],
                    "before_png": str(before_png), "after_png": str(after_png),
                    "before_png_sha256": png["before_png_sha256"],
                    "after_png_sha256": png["after_png_sha256"],
                    "png_audit": png,
                }
                if ab_protocol in (FILL001_AB_V2_PROTOCOL, FILL001_AB_V3_PROTOCOL):
                    # This is run-bound and derived from the CURRENT raw run;
                    # no old series, fitted offsets, or screenshot-derived calibration.
                    v2_binding = bind_from_monitor_run(
                        Path(run_file), audit_file,
                        allow_v3_boardpane_only=(ab_protocol == FILL001_AB_V3_PROTOCOL),
                    )
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
                                or preflight.get("boardpane_mapping_sha256") != audit["boardpane_mapping_at_start_sha256"]
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
