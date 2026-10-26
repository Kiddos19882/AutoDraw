from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from color_scanline import build_color_scanline_plan, validate_color_scanline_plan
from palette_profiles import PaletteProfileError, validate_palette_profile
from palette_quantization import normalize_palette


class PaintLimitTestError(ValueError):
    """Invalid configuration or observations for the paint-limit experiment."""


# Legacy A/B presets are kept for backwards compatibility with earlier projects.
SCENARIOS = {
    "few_long": {"stroke_count": 10, "label": "A — меньше длинных штрихов"},
    "many_short": {"stroke_count": 80, "label": "B — больше коротких штрихов"},
}

# The game drawing area is limited to 660 x 340 px. Controlled series use
# 26,000 px total path, divisible by every current stroke length.
MAX_TEST_CANVAS_WIDTH = 660
MAX_TEST_CANVAS_HEIGHT = 340
STROKE_LENGTH_SCENARIOS = {
    "length_650": {"stroke_length_px": 650, "label": "650 px — длинные штрихи"},
    "length_200": {"stroke_length_px": 200, "label": "200 px — средние штрихи"},
    "length_50": {"stroke_length_px": 50, "label": "50 px — короткие штрихи"},
    "length_10": {"stroke_length_px": 10, "label": "10 px — очень короткие штрихи"},
}
# Existing observation logs from version 1.8.1 may still contain length_800.
# It is accepted for analysis only; the 660 px board cannot fit an 800 px stroke.
LEGACY_STROKE_LENGTH_SCENARIOS = {
    "length_800": {"stroke_length_px": 800, "label": "800 px — старый вариант (история)"},
}
ALL_STROKE_LENGTH_SCENARIOS = {**STROKE_LENGTH_SCENARIOS, **LEGACY_STROKE_LENGTH_SCENARIOS}
OBSERVATION_STATES = {"all_visible", "partial", "none_visible"}
TEST_STROKE_GAP_PX = 2


def build_paint_limit_test_plan(
    profile_document: dict[str, Any],
    *,
    canvas_width: int,
    canvas_height: int,
    color_hex: str,
    scenario_id: str,
    target_total_drawing_length_px: int = 800,
    row_spacing_px: int = 3,
    experiment_id: str = "",
    margin_px: int = 3,
) -> dict[str, Any]:
    """Build one controlled single-color pattern.

    New ``length_*`` scenarios place multiple separated strokes on each row,
    preserving exact summed path length while changing stroke length and count.
    Legacy ``few_long``/``many_short`` scenarios are kept for older callers.
    """
    try:
        profile = validate_palette_profile(profile_document)
    except (PaletteProfileError, TypeError, ValueError) as exc:
        raise PaintLimitTestError(f"Некорректный профиль палитры: {exc}") from exc

    is_length_scenario = scenario_id in ALL_STROKE_LENGTH_SCENARIOS
    if scenario_id not in SCENARIOS and not is_length_scenario:
        raise PaintLimitTestError("Неизвестный вариант теста.")
    for field, value in (("Ширина холста", canvas_width), ("Высота холста", canvas_height),
                         ("Суммарная длина", target_total_drawing_length_px),
                         ("Расстояние между строками", row_spacing_px), ("Отступ", margin_px)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise PaintLimitTestError(f"{field} должен быть целым числом.")
    if canvas_width < 20 or canvas_height < 20:
        raise PaintLimitTestError("Область теста слишком мала; требуется холст не меньше 20 × 20 px.")
    if canvas_width > MAX_TEST_CANVAS_WIDTH or canvas_height > MAX_TEST_CANVAS_HEIGHT:
        raise PaintLimitTestError(
            f"Размер тестовой области не может превышать {MAX_TEST_CANVAS_WIDTH} × {MAX_TEST_CANVAS_HEIGHT} px "
            "(ограничение игровой доски). Выберите фактическую область рисования."
        )
    if target_total_drawing_length_px < 800 or target_total_drawing_length_px > 10_000_000:
        raise PaintLimitTestError("Суммарная длина должна быть в диапазоне 800…10 000 000 px.")
    if row_spacing_px < 2 or row_spacing_px > 50:
        raise PaintLimitTestError("Расстояние между тестовыми строками должно быть от 2 до 50 px.")
    if margin_px < 1 or margin_px * 2 >= min(canvas_width, canvas_height):
        raise PaintLimitTestError("Недопустимый отступ тестового рисунка.")

    if is_length_scenario:
        stroke_length_px = int(ALL_STROKE_LENGTH_SCENARIOS[scenario_id]["stroke_length_px"])
        if target_total_drawing_length_px % stroke_length_px != 0:
            raise PaintLimitTestError(
                f"Для штрихов длиной {stroke_length_px} px суммарная длина должна делиться на неё без остатка. "
                "Для текущей доски сравните 650/200/50/10 px при суммарной длине 26 000 px."
            )
        requested_strokes = target_total_drawing_length_px // stroke_length_px
        scenario_label = ALL_STROKE_LENGTH_SCENARIOS[scenario_id]["label"]
        # New scenarios are packed in rows with a transparent gap between strokes.
        gap_px = TEST_STROKE_GAP_PX
        legacy_one_stroke_per_row = False
    else:
        requested_strokes = int(SCENARIOS[scenario_id]["stroke_count"])
        if target_total_drawing_length_px % 80 != 0:
            raise PaintLimitTestError(
                "Для старого A/B-варианта суммарная длина должна быть кратна 80 px. "
                "Для нового сравнения выбирайте длину штриха 650/200/50/10 px."
            )
        stroke_length_px = target_total_drawing_length_px // requested_strokes
        scenario_label = SCENARIOS[scenario_id]["label"]
        gap_px = 0
        legacy_one_stroke_per_row = True

    max_stroke_length = canvas_width - 2 * margin_px - 1
    if stroke_length_px > max_stroke_length:
        raise PaintLimitTestError(
            f"Для варианта {scenario_id} требуется штрих длиной {stroke_length_px} px, "
            f"но при ширине {canvas_width} px доступно не более {max_stroke_length} px. "
            "Выберите более короткий штрих или более широкую область."
        )

    if legacy_one_stroke_per_row:
        strokes_per_row = 1
    else:
        strokes_per_row = max(1, (max_stroke_length + gap_px) // (stroke_length_px + gap_px))
    required_rows = (requested_strokes + strokes_per_row - 1) // strokes_per_row
    max_rows_by_height = ((canvas_height - margin_px - 1 - margin_px) // row_spacing_px) + 1
    if required_rows > max_rows_by_height:
        raise PaintLimitTestError(
            f"Тест требует {required_rows} строк, но в выбранной области помещается {max_rows_by_height}. "
            "Увеличьте высоту области или шаг строк либо выберите более короткие штрихи."
        )

    palette = normalize_palette(profile["colors"])
    wanted_hex = str(color_hex).strip().upper()
    if not wanted_hex.startswith("#"):
        wanted_hex = "#" + wanted_hex
    selected_index = next((int(color["index"]) for color in palette if color["hex"] == wanted_hex), None)
    if selected_index is None:
        raise PaintLimitTestError(f"Цвет {wanted_hex} отсутствует в выбранном профиле палитры.")
    selected_profile_color = profile["colors"][selected_index]
    if selected_profile_color.get("status") not in {"confirmed", "corrected"}:
        raise PaintLimitTestError(
            f"Цвет {wanted_hex} ещё не подтверждён. Подтвердите его во вкладке 3 перед тестовым рисованием."
        )

    index_map = np.full((canvas_height, canvas_width), -1, dtype=np.int32)
    x_start_base = margin_px
    stroke_positions: list[dict[str, int]] = []
    unique_rows: list[int] = []
    for index in range(requested_strokes):
        if legacy_one_stroke_per_row:
            row_index, column_index = index, 0
        else:
            row_index, column_index = divmod(index, strokes_per_row)
        y = margin_px + row_index * row_spacing_px
        x_start = x_start_base + column_index * (stroke_length_px + gap_px)
        x_end = x_start + stroke_length_px
        if y >= canvas_height - margin_px:
            raise PaintLimitTestError("Тестовые строки выходят за пределы холста; увеличьте высоту или шаг строк.")
        if x_end >= canvas_width - margin_px:
            raise PaintLimitTestError("Штрихи выходят за пределы ширины холста; уменьшите длину или отступ.")
        # Endpoints differ by stroke_length_px. The inclusive array fill merely
        # supplies raster coverage for the scanline planner's endpoint convention.
        index_map[y, x_start:x_end + 1] = selected_index
        stroke_positions.append({"x_start": x_start, "x_end": x_end, "y": y})
        if y not in unique_rows:
            unique_rows.append(y)

    plan = build_color_scanline_plan(
        index_map,
        profile,
        source_name=f"Тест лимита краски — {scenario_label}",
        plan_name=f"Тест лимита краски — {scenario_label} — {wanted_hex}",
        row_step_px=1,
    )
    if len(plan["strokes"]) != requested_strokes:
        raise PaintLimitTestError(
            f"Тест сформировал {len(plan['strokes'])} штрихов вместо {requested_strokes}. "
            "Проверьте выбранную область и шаг между штрихами."
        )
    actual_total_length = int(sum(
        int(round(float(stroke["points"][-1]["x"] - stroke["points"][0]["x"])))
        for stroke in plan["strokes"]
    ))
    if actual_total_length != target_total_drawing_length_px:
        raise PaintLimitTestError(
            f"Фактическая длина созданного плана {actual_total_length} px не совпала с заданной "
            f"{target_total_drawing_length_px} px. План не сохранён."
        )

    plan["source"]["paint_limit_test"] = {
        "experiment_id": str(experiment_id).strip(),
        "scenario_id": scenario_id,
        "scenario_label": scenario_label,
        "profile_name": profile["profile_name"],
        "color_hex": wanted_hex,
        "requested_total_drawing_length_px": target_total_drawing_length_px,
        "stroke_count": requested_strokes,
        "stroke_length_px": stroke_length_px,
        "planned_total_drawing_length_px": actual_total_length,
        "row_spacing_px": row_spacing_px,
        "stroke_gap_px": gap_px,
        "strokes_per_row": strokes_per_row,
        "row_count": len(unique_rows),
        "row_y_positions": unique_rows,
        "stroke_positions": stroke_positions,
        "first_stroke_y": stroke_positions[0]["y"],
        "last_stroke_y": stroke_positions[-1]["y"],
        "comparison_note": (
            "Контролируемая серия: все варианты имеют одинаковую суммарную длину пути, "
            "но разное количество штрихов. Запускайте каждый вариант с полным/сопоставимым запасом краски."
            if is_length_scenario else
            "Старый A/B-вариант для совместимости. Используйте варианты длины 650/200/50/10 px "
            "для анализа при одинаковой суммарной длине и ограничении доски 660 × 340 px."
        ),
    }
    validate_color_scanline_plan(plan)
    return plan


def make_paint_limit_observation(
    plan: dict[str, Any],
    *,
    outcome: str,
    last_visible_strokes: int | None = None,
    notes: str = "",
    fresh_supply_confirmed: bool = False,
) -> dict[str, Any]:
    """Create a normalized manual observation from a completed browser test run."""
    validate_color_scanline_plan(plan)
    test = plan.get("source", {}).get("paint_limit_test")
    if not isinstance(test, dict):
        raise PaintLimitTestError("Выбранный план не является планом теста лимита краски.")
    if outcome not in OBSERVATION_STATES:
        raise PaintLimitTestError("Неизвестный результат наблюдения.")
    if not fresh_supply_confirmed:
        raise PaintLimitTestError(
            "Для достоверного замера подтвердите, что этот запуск начинался с полного/сопоставимого запаса краски."
        )
    total = int(test["stroke_count"])
    if outcome == "all_visible":
        last_visible = total
    elif outcome == "none_visible":
        last_visible = 0
    else:
        if isinstance(last_visible_strokes, bool) or not isinstance(last_visible_strokes, int):
            raise PaintLimitTestError("Для частичного результата укажите число полностью видимых штрихов.")
        if not 0 <= last_visible_strokes < total:
            raise PaintLimitTestError(f"Для частичного результата число штрихов должно быть от 0 до {total - 1}.")
        last_visible = last_visible_strokes

    stroke_length = int(test["stroke_length_px"])
    measured_length = last_visible * stroke_length
    if outcome == "all_visible":
        interpretation = "Лимит не достигнут; ресурс не меньше протестированного объёма."
    elif outcome == "none_visible":
        interpretation = "Цвет не появился на всём тесте; проверьте палитру/координаты и запас краски."
    else:
        interpretation = "Краска закончилась или стала незаметной внутри тестового шаблона; граница приблизительная."
    return {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "experiment_id": test.get("experiment_id", ""),
        "scenario_id": test["scenario_id"],
        "scenario_label": test["scenario_label"],
        "profile_name": test["profile_name"],
        "color_hex": test["color_hex"],
        "outcome": outcome,
        "planned_strokes": total,
        "last_visible_strokes": last_visible,
        "first_missing_stroke": (last_visible + 1) if outcome == "partial" else None,
        "stroke_length_px": stroke_length,
        "estimated_visible_path_length_px": measured_length,
        "planned_path_length_px": int(test["planned_total_drawing_length_px"]),
        "target_total_drawing_length_px": int(test["requested_total_drawing_length_px"]),
        "row_spacing_px": int(test["row_spacing_px"]),
        "fresh_supply_confirmed": bool(fresh_supply_confirmed),
        "notes": str(notes).strip(),
        "interpretation": interpretation,
    }


def append_paint_limit_observation(path: str | Path, record: dict[str, Any]) -> Path:
    """Append a test observation to a JSON log using an atomic replacement."""
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("records"), list):
                raise PaintLimitTestError("Журнал тестов краски повреждён или имеет неизвестную версию.")
            records = list(data["records"])
        except json.JSONDecodeError as exc:
            raise PaintLimitTestError(f"Не удалось прочитать журнал тестов: {exc}") from exc
    records.append(dict(record))
    document = {"schema_version": 1, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "records": records}
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temp_name).replace(target)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target



def analyze_paint_limit_series(records: list[dict[str, Any]], experiment_id: str) -> str:
    """Compare latest observations for fixed-length scenarios sharing one total path."""
    matching = [r for r in records if r.get("experiment_id") == experiment_id and r.get("scenario_id") in ALL_STROKE_LENGTH_SCENARIOS]
    latest_by_scenario: dict[str, dict[str, Any]] = {}
    for record in matching:
        scenario_id = str(record.get("scenario_id"))
        latest_by_scenario[scenario_id] = record
    if len(latest_by_scenario) < 2:
        return (
            "Для сравнения нужны хотя бы два варианта одной серии. Рекомендуется выполнить все четыре: "
            "650, 200, 50 и 10 px. Каждый вариант помещается в область до 660 × 340 px. "
            "После каждого запуска нужен сопоставимый полный запас краски."
        )
    items = list(latest_by_scenario.items())
    records_only = [record for _, record in items]
    colors = {r.get("color_hex") for r in records_only}
    profiles = {r.get("profile_name") for r in records_only}
    targets = {r.get("target_total_drawing_length_px") for r in records_only}
    planned = {r.get("planned_path_length_px") for r in records_only}
    if len(colors) != 1 or len(profiles) != 1:
        return "В серии различаются цвет или профиль палитры. Повторите её с одним профилем и одним подтверждённым цветом."
    if len(targets) != 1 or len(planned) != 1:
        return "В серии различается суммарная длина пути. Установите одну длину (например, 26 000 px) для всех вариантов."
    if any(not r.get("fresh_supply_confirmed") for r in records_only):
        return "Не для всех вариантов подтверждён полный/сопоставимый запас краски; вывод пока недостоверен."
    if any(r.get("outcome") == "none_visible" for r in records_only):
        return "В одном из вариантов цвет не появился вообще. Проверьте палитру, координаты и пополнение краски до оценки лимита."

    ordered = sorted(
        ((int(record.get("stroke_length_px", 0)), record) for record in records_only),
        key=lambda item: item[0], reverse=True,
    )
    result_lines: list[str] = []
    for stroke_length, record in ordered:
        outcome = record.get("outcome")
        planned_path = int(record.get("planned_path_length_px", 0) or 0)
        visible_path = int(record.get("estimated_visible_path_length_px", 0) or 0)
        count = int(record.get("planned_strokes", 0) or 0)
        visible_count = int(record.get("last_visible_strokes", 0) or 0)
        if outcome == "all_visible":
            result_lines.append(f"{stroke_length}px: все {count} штрихов видны ({planned_path:,} px — лимит не достигнут)")
        else:
            result_lines.append(f"{stroke_length}px: примерно {visible_count}/{count} штрихов, путь {visible_path:,}/{planned_path:,} px до пропуска")

    failed = [(length, r) for length, r in ordered if r.get("outcome") == "partial"]
    complete = [(length, r) for length, r in ordered if r.get("outcome") == "all_visible"]
    prefix = "Результаты серии:\n" + "\n".join(result_lines) + "\n"
    if not failed:
        return prefix + "Лимит не достигнут ни в одном варианте на выбранной суммарной длине. Увеличьте длину теста."
    if complete and any(length <= 50 for length, _ in failed) and any(length >= 200 for length, _ in complete):
        return prefix + (
            "Предварительно виден дополнительный расход на большое количество коротких штрихов: длинные варианты прошли, "
            "а короткие начали пропадать при одинаковом суммарном пути. Повторите серию минимум дважды."
        )
    thresholds = [int(r.get("estimated_visible_path_length_px", 0) or 0) for _, r in failed]
    if len(thresholds) >= 2:
        positive = [v for v in thresholds if v > 0]
        if positive and (max(positive) - min(positive)) / max(positive) <= 0.15:
            return prefix + (
                "Границы отказа у вариантов близки по суммарному пути (разброс до 15%): вероятно, доминирует расход на длину. "
                "Нужен повтор для подтверждения."
            )
        if len(positive) >= 2 and max(positive) >= min(positive) * 1.3:
            shortest_failure = min((length for length, record in failed if int(record.get("estimated_visible_path_length_px", 0) or 0) == min(positive)), default=0)
            longest_failure = max((length for length, record in failed if int(record.get("estimated_visible_path_length_px", 0) or 0) == max(positive)), default=0)
            if shortest_failure < longest_failure:
                return prefix + (
                    "Короткие штрихи достигают границы раньше по суммарному пути, чем длинные. Это согласуется с дополнительной "
                    "стоимостью каждого штриха, но нужно повторить серию с тем же запасом краски."
                )
    return prefix + (
        "Результат пока не отделяет расход на длину пути от стоимости отдельных штрихов. Повторите варианты с полным запасом "
        "краски; учитывайте, что последний видимый штрих может быть частично нарисован."
    )

def analyze_paint_limit_pair(records: list[dict[str, Any]], experiment_id: str) -> str:
    """Offer cautious evidence-based guidance for legacy matched-length A/B tests."""
    matching = [r for r in records if r.get("experiment_id") == experiment_id]
    by_scenario: dict[str, dict[str, Any]] = {}
    for record in matching:
        if record.get("scenario_id") in SCENARIOS:
            by_scenario[record["scenario_id"]] = record
    if "few_long" not in by_scenario or "many_short" not in by_scenario:
        return "Для вывода нужны оба результата одной серии: A (10 длинных штрихов) и B (80 коротких)."
    a, b = by_scenario["few_long"], by_scenario["many_short"]
    if a.get("color_hex") != b.get("color_hex") or a.get("profile_name") != b.get("profile_name"):
        return "Пары A/B используют разные цвета или профили. Создайте новую серию и выберите один подтверждённый цвет."
    if a.get("target_total_drawing_length_px") != b.get("target_total_drawing_length_px"):
        return "У вариантов A/B разная заданная суммарная длина. Повторите пару с одинаковой настройкой длины."
    if a.get("row_spacing_px") != b.get("row_spacing_px"):
        return "У вариантов A/B разный интервал строк. Повторите пару с одинаковым интервалом."
    a_planned = a.get("planned_path_length_px")
    b_planned = b.get("planned_path_length_px")
    if a_planned is not None and b_planned is not None and int(a_planned) != int(b_planned):
        return "Фактическая плановая длина A/B различается. Повторите пару с одинаковой суммарной длиной пути."
    if not a.get("fresh_supply_confirmed") or not b.get("fresh_supply_confirmed"):
        return "Запас краски подтверждён не для обоих запусков; сравнение нельзя считать достоверным."
    if a.get("outcome") == "none_visible" or b.get("outcome") == "none_visible":
        return (
            "Хотя бы в одном сценарии цвет не появился вообще. Это нельзя уверенно считать лимитом краски: "
            "сначала проверьте правильность профиля, выбор цвета, область рисования и пополнение краски, затем повторите."
        )
    a_complete = a.get("outcome") == "all_visible"
    b_complete = b.get("outcome") == "all_visible"
    a_failed = a.get("outcome") == "partial"
    b_failed = b.get("outcome") == "partial"
    a_strokes, b_strokes = int(a.get("last_visible_strokes", 0)), int(b.get("last_visible_strokes", 0))
    a_length, b_length = int(a.get("estimated_visible_path_length_px", 0)), int(b.get("estimated_visible_path_length_px", 0))
    if a_complete and b_complete:
        tested_length = min(int(a.get("planned_path_length_px", 0)), int(b.get("planned_path_length_px", 0)))
        return (
            f"Лимит не обнаружен в обоих сценариях до примерно {tested_length:,} px пути. "
            "Повторите пару с большей суммарной длиной."
        )
    if a_complete and b_failed:
        return (
            "Вероятнее ограничение числом штрихов или стоимостью каждого отдельного штриха: "
            "A с 10 длинными штрихами завершился, а B с 80 короткими — нет, при близкой суммарной длине. "
            "Повторите пару для подтверждения."
        )
    if b_complete and a_failed:
        return (
            "Вероятнее ограничение общей длиной пути или отдельными длинными движениями: "
            "B с 80 короткими штрихами завершился, а A с 10 длинными — нет. Повторите пару для подтверждения."
        )
    if a_failed and b_failed:
        max_length = max(a_length, b_length, 1)
        length_difference = abs(a_length - b_length) / max_length
        max_count = max(a_strokes, b_strokes, 1)
        count_difference = abs(a_strokes - b_strokes) / max_count
        if length_difference <= 0.2 and count_difference >= 0.4:
            return "Граница расхода ближе по суммарной длине, чем по числу штрихов: это указывает на лимит длины пути. Нужен повтор."
        if count_difference <= 0.2 and length_difference >= 0.4:
            return "Граница расхода ближе по числу штрихов, чем по длине пути: это указывает на лимит количества/стоимости штрихов. Нужен повтор."
    return (
        "Пара пока не отделяет длину пути от числа штрихов. Проверьте, что оба запуска начались с одинакового запаса "
        "краски, и повторите тест. На результат могут влиять минимальная длина распознаваемого штриха и задержки игры."
    )
