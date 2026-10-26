from __future__ import annotations

import json
import uuid
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from PIL import Image, ImageTk

from color_scanline import render_color_scanline_preview, save_color_scanline_plan
from paint_limit_test import (
    PaintLimitTestError,
    analyze_paint_limit_series,
    append_paint_limit_observation,
    build_paint_limit_test_plan,
    make_paint_limit_observation,
)
from palette_profiles import load_palette_profile, validate_palette_profile


class PaintLimitTestTab:
    """Controlled equal-path series for estimating in-game paint cost."""

    def __init__(
        self,
        root: tk.Misc,
        parent: tk.Widget,
        output_dir: str | Path,
        profile_dir: str | Path,
        *,
        get_canvas_size: Callable[[], tuple[int, int] | None],
        on_transfer_plan: Callable[[dict[str, Any], dict[str, Any], Path], bool],
    ):
        self.root = root
        self.output_dir = Path(output_dir).resolve()
        self.profile_dir = Path(profile_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.get_canvas_size = get_canvas_size
        self.on_transfer_plan = on_transfer_plan
        self.profile: dict[str, Any] | None = None
        self.profile_path: Path | None = None
        self.plan: dict[str, Any] | None = None
        self.plan_path: Path | None = None
        self.color_by_display: dict[str, dict[str, Any]] = {}
        self.experiment_id_var = tk.StringVar(value=uuid.uuid4().hex[:8].upper())
        self.profile_info_var = tk.StringVar(value="Профиль палитры не загружен.")
        self.color_var = tk.StringVar()
        self.scenario_display_to_id = {
            "650 px — длинные": "length_650",
            "200 px — средние": "length_200",
            "50 px — короткие": "length_50",
            "10 px — очень короткие": "length_10",
        }
        self.scenario_var = tk.StringVar(value="650 px — длинные")
        self.total_length_var = tk.StringVar(value="26000")
        self.spacing_var = tk.StringVar(value="3")
        self.plan_info_var = tk.StringVar(value="Сначала выберите область рисования и загрузите подтверждённый профиль палитры.")
        self.status_var = tk.StringVar(value="Тесты необходимо выполнять на отдельной тестовой области, а не поверх важного рисунка.")
        self.outcome_var = tk.StringVar(value="all_visible")
        self.last_visible_var = tk.StringVar(value="0")
        self.notes_var = tk.StringVar()
        self.fresh_supply_var = tk.BooleanVar(value=False)
        self.analysis_var = tk.StringVar(value="Запишите результаты вариантов 650/200/50/10 px одной серии, чтобы сравнить расход при равной суммарной длине.")
        self.preview_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None

        scroll_host = ttk.Frame(parent)
        scroll_host.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(scroll_host, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(scroll_host, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        outer = ttk.Frame(self.scroll_canvas, padding=10)
        self.scroll_window_id = self.scroll_canvas.create_window((0, 0), window=outer, anchor="nw")
        outer.bind("<Configure>", lambda _event: self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all")))
        self.scroll_canvas.bind(
            "<Configure>",
            lambda event: self.scroll_canvas.itemconfigure(self.scroll_window_id, width=event.width),
        )
        ttk.Label(outer, text="Эксперимент — ограничение краски кисти", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "AutoDraw не может напрямую прочитать остаток краски из игры. Этот тест рисует контролируемый шаблон, "
                "а ты отмечаешь, где штрихи перестали отображаться. Максимальная область доски — 660 × 340 px. "
                "Серия использует одинаковый суммарный путь, но четыре длины отдельного штриха — 650, 200, 50 и 10 px. "
                "Для сравнения каждый вариант нужно запускать с полным и сопоставимым запасом краски."
            ),
            wraplength=1100,
        ).pack(anchor="w", pady=(4, 8))

        profile_frame = ttk.LabelFrame(outer, text="Профиль и цвет теста", padding=7)
        profile_frame.pack(fill="x", pady=(0, 7))
        ttk.Button(profile_frame, text="Загрузить профиль палитры…", command=self.load_profile_dialog).grid(row=0, column=0, sticky="w")
        ttk.Label(profile_frame, textvariable=self.profile_info_var, wraplength=960).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Label(profile_frame, text="Цвет").grid(row=1, column=0, sticky="w", pady=(7, 0))
        self.color_combo = ttk.Combobox(profile_frame, textvariable=self.color_var, state="readonly", width=55)
        self.color_combo.grid(row=1, column=1, sticky="ew", padx=8, pady=(7, 0))
        profile_frame.columnconfigure(1, weight=1)

        settings = ttk.LabelFrame(outer, text="Контролируемый шаблон", padding=7)
        settings.pack(fill="x", pady=(0, 7))
        controls = ttk.Frame(settings)
        controls.pack(fill="x")
        primary_row = ttk.Frame(controls)
        primary_row.pack(fill="x")
        ttk.Label(primary_row, text="Вариант").pack(side="left")
        self.scenario_combo = ttk.Combobox(
            primary_row,
            textvariable=self.scenario_var,
            values=tuple(self.scenario_display_to_id.keys()),
            state="readonly",
            width=27,
        )
        self.scenario_combo.pack(side="left", padx=(6, 14))
        ttk.Label(primary_row, text="Суммарный путь, px").pack(side="left")
        ttk.Entry(primary_row, textvariable=self.total_length_var, width=9).pack(side="left", padx=(6, 14))

        secondary_row = ttk.Frame(controls)
        secondary_row.pack(fill="x", pady=(6, 0))
        ttk.Label(secondary_row, text="Интервал строк, px").pack(side="left")
        ttk.Combobox(
            secondary_row,
            textvariable=self.spacing_var,
            values=("3", "4", "5", "6"),
            state="readonly",
            width=5,
        ).pack(side="left", padx=(6, 14))
        self.generate_button = ttk.Button(secondary_row, text="Создать тестовый план", command=self.generate_plan)
        self.generate_button.pack(side="left")
        ttk.Label(
            settings,
            text=(
                "Рекомендуемая серия: 26 000 px суммарного пути для каждого варианта: 40×650 px, 130×200 px, "
                "520×50 px и 2600×10 px. Все варианты помещаются в область до 660 × 340 px и рисуются одним подтверждённым цветом, с одинаковым "
                "запасом краски и одинаковой областью. Короткие штрихи размещаются отдельными сегментами с зазором, "
                "строки идут сверху вниз, сегменты внутри строки — слева направо. Суммарная длина должна делиться "
                "на выбранную длину штриха без остатка."
            ),
            wraplength=1050,
            justify="left",
        ).pack(fill="x", pady=(6, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 7))
        ttk.Button(actions, text="Передать тест в исполнение →", command=self.transfer_plan).pack(side="left")
        ttk.Button(actions, text="Новая серия", command=self.new_experiment).pack(side="left", padx=(7, 0))
        ttk.Label(actions, text="ID серии:").pack(side="left", padx=(14, 4))
        ttk.Label(actions, textvariable=self.experiment_id_var, font=("Segoe UI", 10, "bold")).pack(side="left")

        preview_frame = ttk.LabelFrame(outer, text="Предпросмотр тестового шаблона", padding=5)
        preview_frame.pack(fill="both", expand=True, pady=(0, 7))
        self.preview_canvas = tk.Canvas(preview_frame, background="#eeeeee", highlightthickness=0, height=150)
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda _event: self._render_preview())
        ttk.Label(outer, textvariable=self.plan_info_var, wraplength=1300).pack(anchor="w", pady=(0, 5))

        result_frame = ttk.LabelFrame(outer, text="Записать наблюдение после завершения исполнения", padding=7)
        result_frame.pack(fill="x", pady=(0, 7))
        ttk.Radiobutton(result_frame, text="Все штрихи видны", variable=self.outcome_var, value="all_visible", command=self._on_outcome_changed).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(result_frame, text="Краска пропала/часть штрихов отсутствует", variable=self.outcome_var, value="partial", command=self._on_outcome_changed).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Radiobutton(result_frame, text="Цвет не появился вообще", variable=self.outcome_var, value="none_visible", command=self._on_outcome_changed).grid(row=0, column=2, sticky="w")
        ttk.Label(result_frame, text="Последний полностью видимый штрих (номер)").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.last_visible_entry = ttk.Entry(result_frame, textvariable=self.last_visible_var, width=8)
        self.last_visible_entry.grid(row=1, column=1, sticky="w", pady=(6, 0))
        ttk.Label(result_frame, text="Заметки").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(result_frame, textvariable=self.notes_var).grid(row=2, column=1, columnspan=2, sticky="ew", padx=8, pady=(6, 0))
        ttk.Checkbutton(
            result_frame,
            text="Подтверждаю: перед этим запуском запас краски был полным/сопоставимым",
            variable=self.fresh_supply_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(7, 0))
        ttk.Button(result_frame, text="Сохранить результат наблюдения", command=self.record_observation).grid(row=4, column=0, sticky="w", pady=(7, 0))
        ttk.Label(result_frame, textvariable=self.analysis_var, wraplength=1300).grid(row=5, column=0, columnspan=3, sticky="ew", pady=(7, 0))
        result_frame.columnconfigure(1, weight=1)
        ttk.Label(outer, textvariable=self.status_var, wraplength=1300).pack(anchor="w")
        # Bind wheel events to this tab's descendants so lower controls remain
        # reachable even when the current window is shorter than the content.
        self._bind_scroll_events(self.scroll_canvas)
        self._on_outcome_changed()

    def _bind_scroll_events(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
        widget.bind("<Button-4>", self._on_mousewheel, add="+")
        widget.bind("<Button-5>", self._on_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_scroll_events(child)

    def _on_mousewheel(self, event: tk.Event) -> str:
        if getattr(event, "num", None) == 4:
            self.scroll_canvas.yview_scroll(-1, "units")
        elif getattr(event, "num", None) == 5:
            self.scroll_canvas.yview_scroll(1, "units")
        else:
            delta = int(-1 * (getattr(event, "delta", 0) / 120))
            if delta == 0:
                delta = -1 if getattr(event, "delta", 0) > 0 else 1
            self.scroll_canvas.yview_scroll(delta, "units")
        return "break"

    def load_profile_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Выберите сохранённый профиль палитры",
            initialdir=str(self.profile_dir if self.profile_dir.is_dir() else self.output_dir),
            filetypes=(("Профиль палитры AutoDraw", "*.json"), ("JSON", "*.json"), ("Все файлы", "*.*")),
        )
        if not selected:
            return
        try:
            profile = load_palette_profile(selected)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Не удалось открыть профиль", str(exc), parent=self.root)
            return
        self.set_profile(profile, Path(selected))

    def set_profile(self, profile: dict[str, Any], path: Path | None = None) -> None:
        self.profile = validate_palette_profile(profile)
        self.profile_path = path.resolve() if path else None
        self.color_by_display.clear()
        values: list[str] = []
        for color in self.profile["colors"]:
            display = f"{color['hex']} — {color['name']} [{color['status']}]"
            values.append(display)
            self.color_by_display[display] = color
        self.color_combo.configure(values=values)
        if values:
            confirmed = next((value for value in values if self.color_by_display[value]["status"] in {"confirmed", "corrected"}), values[0])
            self.color_var.set(confirmed)
        else:
            self.color_var.set("")
        self.profile_info_var.set(
            f"{self.profile['profile_name']} · цветов: {len(values)} · "
            f"масштаб Windows: {self.profile['calibration']['dpi_scale_percent']}%"
        )
        self.plan = None
        self.plan_path = None
        self.plan_info_var.set("Профиль загружен. Создайте новый тестовый план.")
        self._render_preview()

    def _get_scenario_id(self) -> str:
        try:
            return self.scenario_display_to_id[self.scenario_var.get()]
        except KeyError as exc:
            raise ValueError("Выберите один из режимов длины штриха: 650, 200, 50 или 10 px.") from exc

    def generate_plan(self) -> None:
        if self.profile is None:
            messagebox.showinfo("Нет профиля", "Сначала загрузите сохранённый профиль палитры.", parent=self.root)
            return
        size = self.get_canvas_size()
        if size is None:
            messagebox.showwarning("Не выбрана область рисования", "Выберите область рисования на вкладке 1 или 2.", parent=self.root)
            return
        color = self.color_by_display.get(self.color_var.get())
        if color is None:
            messagebox.showwarning("Не выбран цвет", "Выберите подтверждённый цвет палитры для теста.", parent=self.root)
            return
        try:
            total_length = int(self.total_length_var.get())
            spacing = int(self.spacing_var.get())
            plan = build_paint_limit_test_plan(
                self.profile,
                canvas_width=int(size[0]),
                canvas_height=int(size[1]),
                color_hex=color["hex"],
                scenario_id=self._get_scenario_id(),
                target_total_drawing_length_px=total_length,
                row_spacing_px=spacing,
                experiment_id=self.experiment_id_var.get(),
            )
            path = save_color_scanline_plan(
                self.output_dir / f"paint_limit_{self.experiment_id_var.get()}_{self._get_scenario_id()}.json",
                plan,
            )
        except (ValueError, TypeError, OSError, MemoryError) as exc:
            messagebox.showerror("Не удалось создать тест", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка создания теста: {exc}")
            return
        self.plan = plan
        self.plan_path = path
        # Each newly generated pattern must be explicitly confirmed against a fresh,
        # comparable paint supply before transfer; don't carry confirmation forward.
        self.fresh_supply_var.set(False)
        self.outcome_var.set("all_visible")
        self.last_visible_var.set("0")
        self._on_outcome_changed()
        test = plan["source"]["paint_limit_test"]
        self.plan_info_var.set(
            f"План: {path.name} · {test['scenario_label']} · цвет {test['color_hex']} · "
            f"штрихов: {test['stroke_count']} · длина одного штриха: {test['stroke_length_px']} px · "
            f"суммарный путь: {test['planned_total_drawing_length_px']} px · "
            f"область: {plan['canvas']['width']} × {plan['canvas']['height']} px"
        )
        self.status_var.set("План готов. Перед запуском переключитесь в браузер и убедитесь, что область теста пуста.")
        self._render_preview()

    def transfer_plan(self) -> None:
        if self.plan is None or self.profile is None or self.plan_path is None:
            messagebox.showinfo("Нет тестового плана", "Сначала создайте тестовый план.", parent=self.root)
            return
        if not self.fresh_supply_var.get():
            messagebox.showwarning(
                "Подтвердите запас краски",
                "Для сравнения лимита нужно начать с полного/сопоставимого запаса краски. "
                "Если игра не позволяет это обеспечить, результаты серии могут быть недостоверны.",
                parent=self.root,
            )
            return
        success = self.on_transfer_plan(self.plan, self.profile, self.plan_path)
        if success:
            self.status_var.set("Тестовый план передан исполнителю. После рисования вернитесь сюда и запишите, где цвет пропал.")

    def new_experiment(self) -> None:
        self.experiment_id_var.set(uuid.uuid4().hex[:8].upper())
        self.plan = None
        self.plan_path = None
        self.plan_info_var.set("Создана новая серия. Выполните варианты A и B с сопоставимым запасом краски.")
        self.analysis_var.set("Для сравнения выполните варианты 650, 200, 50 и 10 px в одной новой серии.")
        self._render_preview()

    def _on_outcome_changed(self) -> None:
        self.last_visible_entry.configure(state="normal" if self.outcome_var.get() == "partial" else "disabled")

    def record_observation(self) -> None:
        if self.plan is None:
            messagebox.showinfo("Нет теста", "Сначала создайте и выполните тестовый план.", parent=self.root)
            return
        outcome = self.outcome_var.get()
        try:
            last_visible = int(self.last_visible_var.get()) if outcome == "partial" else None
            record = make_paint_limit_observation(
                self.plan,
                outcome=outcome,
                last_visible_strokes=last_visible,
                notes=self.notes_var.get(),
                fresh_supply_confirmed=self.fresh_supply_var.get(),
            )
            log_path = append_paint_limit_observation(self.output_dir / "observations.json", record)
            records = json.loads(log_path.read_text(encoding="utf-8"))["records"]
            analysis = analyze_paint_limit_series(records, self.experiment_id_var.get())
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            messagebox.showerror("Не удалось сохранить наблюдение", str(exc), parent=self.root)
            return
        self.analysis_var.set(analysis)
        self.status_var.set(f"Результат сохранён: {log_path}. Для надёжного вывода выполните все четыре длины и повторите серию.")

    def _render_preview(self) -> None:
        self.preview_canvas.delete("all")
        self.preview_photo = None
        width = max(1, self.preview_canvas.winfo_width())
        height = max(1, self.preview_canvas.winfo_height())
        if self.plan is None:
            self.preview_canvas.create_text(width / 2, height / 2, text="Тестовый шаблон ещё не построен", fill="#444444")
            return
        image = render_color_scanline_preview(self.plan).convert("RGBA")
        scale = min((width - 12) / image.width, (height - 12) / image.height)
        if scale <= 0:
            return
        display = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale)),), Image.Resampling.NEAREST)
        background = Image.new("RGB", display.size, "#eeeeee")
        background.paste(display.convert("RGB"), mask=display.getchannel("A"))
        self.preview_photo = ImageTk.PhotoImage(background)
        self.preview_canvas.create_image(width / 2, height / 2, image=self.preview_photo, anchor="center")
