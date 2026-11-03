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
    load_fill001_matrix,
    write_fill001_matrix,
)
from brush_behavior_test_ui import _cursor_safe_point_outside_region


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
        self.series_var = tk.StringVar(
            value=f"fill001-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        self.task_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Создайте новую серию или откройте существующий manifest.")
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
        ttk.Button(series, text="Открыть manifest…", command=self.load_series_dialog).pack(side="left", padx=4)
        self.manifest_label = ttk.Label(series, text="Manifest не загружен")
        self.manifest_label.pack(side="left", padx=10)

        task = ttk.LabelFrame(outer, text="Одиночная задача", padding=8)
        task.pack(fill="x", pady=(0, 8))
        ttk.Label(task, text="Pending task").pack(side="left")
        self.task_combo = ttk.Combobox(task, textvariable=self.task_var, state="readonly", width=62)
        self.task_combo.pack(side="left", padx=6)
        self.task_combo.bind("<<ComboboxSelected>>", lambda _event: self._show_selected_task())
        ttk.Button(task, text="Обновить список", command=self._refresh_tasks).pack(side="left", padx=4)
        ttk.Button(task, text="Подготовить и запустить одну задачу", command=self.prepare_and_run).pack(side="left", padx=4)
        ttk.Button(task, text="Проверить runtime + PNG и принять capture", command=self.finalize_capture).pack(side="left", padx=4)

        self.task_details = tk.Text(outer, height=10, wrap="word", state="disabled")
        self.task_details.pack(fill="both", expand=True, pady=(0, 8))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1120).pack(anchor="w")

    def create_series(self) -> None:
        raw_id = self.series_var.get().strip()
        if not raw_id or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", raw_id) is None:
            messagebox.showwarning(
                "Некорректный ID серии",
                "Используйте 1–64 символа: латинские буквы, цифры, точка, дефис или подчёркивание.",
                parent=self.root,
            )
            return
        try:
            matrix = build_fill001_matrix(raw_id)
            path = self.output_dir / f"{raw_id}.json"
            if path.exists():
                raise FileExistsError(f"Серия уже существует: {path}. Откройте её вместо перезаписи.")
            write_fill001_matrix(matrix, path)
            self.matrix, self.manifest_path = matrix, path
            self.manifest_label.configure(text=path.name)
            self._refresh_tasks()
            self.status_var.set(f"Создан manifest из 45 задач: {path}")
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
            self.task_var.set(pending[0] if pending else "")
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
                f"Repeat: {task['repeat_index']}/3\n"
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
        try:
            # The board ROI must be visible, not covered by the AutoDraw window.
            self.root.iconify()
            time.sleep(0.5)
            self.before_png_path = self._capture_board_png(task, phase="before")
        except Exception as exc:
            messagebox.showwarning(
                "FILL-001 preflight не пройден",
                f"Не удалось подтвердить пустую доску и сохранить before PNG. Рисование не запущено.\\n\\n{exc}",
                parent=self.root,
            )
            self.before_png_path = None
            return
        finally:
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
        if not messagebox.askyesno(
            "Разрешить один экспериментальный запуск?",
            (
                f"Будет запущена только задача {task['task_id']} с радиусом {task['requested_radius']}.\n\n"
                "Проверьте, что это отдельная тестовая доска, она очищена, запас краски достаточен, "
                "Game Monitor Bridge подключён, а область доски совпадает с frozen canvas. "
                "Пакетное выполнение остальных 44 задач останется запрещено. Продолжить?"
            ),
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            plan, selected = prepare_fill001_single_task_plan(
                self.matrix,
                task["task_id"],
                operator_approved_single_task_preflight=True,
            )
            plan_path = self.output_dir / "plans" / f"{task['task_id']}.json"
            plan_path.parent.mkdir(parents=True, exist_ok=True)
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            if not self.on_transfer_plan(plan, plan_path):
                raise RuntimeError("AutoDraw отклонил передачу FILL-001 плана в Stage 6.")
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
            "after_png": None,
            "capture_path": None,
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
        self.active_run_record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        if summary.get("status") == "completed":
            self.root.after(1000, self._capture_after_png)
        else:
            self.status_var.set(
                f"FILL-001 {self.active_task['task_id']}: Executor {summary.get('status')}. "
                f"Отчёт: {report_path or 'не сохранён'}. Task не принят."
            )
        return True

    def _capture_board_png(self, task: dict[str, Any], *, phase: str) -> Path:
        """Capture exact 460x240 board ROI with cursor moved outside calibrated regions."""
        config = self.brush_tab.get_calibration_profile() if callable(self.brush_tab.get_calibration_profile) else None
        if not isinstance(config, dict):
            raise ValueError("Профиль калибровки доски отсутствует.")
        region = self.brush_tab.get_canvas_area()
        if not isinstance(region, dict):
            raise ValueError("Screen ROI доски отсутствует.")
        region = {key: int(region[key]) for key in ("x", "y", "width", "height")}
        if (region["width"], region["height"]) != (460, 240):
            raise ValueError(
                "Для FILL-001 pixel audit требуется screen ROI ровно 460×240 px; "
                "масштабированный ROI пока не поддерживается."
            )
        if phase == "after" and self.capture_region is not None and region != self.capture_region:
            raise ValueError("ROI доски изменился между before/after capture.")
        if phase == "before":
            self.capture_region = dict(region)
        screen = ImageGrab.grab()
        expected_screen = config.get("screen_size", {})
        if isinstance(expected_screen, dict) and (
            expected_screen.get("width") != screen.width or expected_screen.get("height") != screen.height
        ):
            raise ValueError("Разрешение экрана изменилось после калибровки.")
        configured_regions = config.get("regions", {})
        avoid = tuple(
            value for name, value in configured_regions.items()
            if name != "board_area" and isinstance(value, dict)
        ) if isinstance(configured_regions, dict) else ()
        safe_point = _cursor_safe_point_outside_region(
            region, (screen.width, screen.height), avoid_regions=avoid
        )
        pyautogui.moveTo(*safe_point)
        time.sleep(0.25)
        screen = ImageGrab.grab()
        crop = screen.crop((
            region["x"], region["y"],
            region["x"] + region["width"], region["y"] + region["height"],
        )).convert("RGB")
        if crop.size != (460, 240):
            raise ValueError("Сохранённый board crop не равен 460×240 px.")
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
            self.active_run_record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
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
                raise FillMatrixError(
                    "Runtime binding ещё не прошёл. Дождитесь обновления executor report и повторите проверку."
                )
            binding = report.get("runtime_binding")
            session_path = binding.get("session_file") if isinstance(binding, dict) else None
            before_png, after_png = record.get("before_png"), record.get("after_png")
            if not session_path or not before_png or not after_png:
                raise FillMatrixError("Не хватает session.json, before PNG или after PNG.")
            from chalk_fill_capture_adapter import build_fill001_capture_from_runtime

            capture = build_fill001_capture_from_runtime(
                self.active_task,
                session_path=session_path,
                executor_report_path=report_path,
                before_png=before_png,
                after_png=after_png,
            )
            capture_path = self.output_dir / "captures" / f"{self.active_task['task_id']}-capture.json"
            capture_path.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
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
            self.active_run_record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
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
            self._refresh_tasks()
        except Exception as exc:
            messagebox.showerror("FILL-001 capture не принят", str(exc), parent=self.root)
