from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPARATION_ROOT = PROJECT_ROOT / "source" / "preparation"
sys.path.insert(0, str(PREPARATION_ROOT))

from board_resource_model import BOARD_ITEM_POINT_LIMITS  # noqa: E402


STROKE_LENGTHS = (650, 200, 50, 10)
TOTAL_PATH_PX = 26000


def _ask_int(prompt: str, *, minimum: int, maximum: int | None = None) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Введите целое число.")
            continue
        if value < minimum or (maximum is not None and value > maximum):
            upper = f" и не больше {maximum}" if maximum is not None else ""
            print(f"Значение должно быть не меньше {minimum}{upper}.")
            continue
        return value


def _ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt + " [y/n]: ").strip().lower()
        if answer in {"y", "yes", "д", "да"}:
            return True
        if answer in {"n", "no", "н", "нет"}:
            return False
        print("Введите y или n.")


def _ask_outcome() -> tuple[str, int]:
    while True:
        outcome = input("Исход (partial/all_visible/none_visible): ").strip().lower()
        if outcome == "partial":
            visible = _ask_int(
                "Количество полностью видимых штрихов: ",
                minimum=1,
            )
            return outcome, visible
        if outcome == "all_visible":
            return outcome, 0
        if outcome == "none_visible":
            return outcome, 0
        print("Допустимые значения: partial, all_visible, none_visible.")


def _read_frame_probe(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict) and "AUTODRAW_FRAME_PROBE_JSON=" in raw:
        raise ValueError("Укажите JSON-объект frame probe, не обёртку с префиксом.")
    if not isinstance(raw, dict):
        raise ValueError("Frame probe должен быть JSON-объектом.")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Интерактивная запись результатов реальных испытаний краски. "
            "Не запускает игру и не определяет видимость штрихов автоматически."
        )
    )
    parser.add_argument("--frame-probe", required=True, help="Путь к JSON, полученному из browser_frame_probe.js.")
    parser.add_argument("--output", required=True, help="Путь выходного game_point_observations.json.")
    parser.add_argument("--board", choices=tuple(BOARD_ITEM_POINT_LIMITS), default="BoardItem2")
    parser.add_argument("--step", type=float, default=2.0, help="Фактический point_step_px для всех запусков.")
    parser.add_argument("--delay-ms", type=float, default=10.0, help="Фактический point_delay_ms для всех запусков.")
    parser.add_argument("--repeats", type=int, default=2, choices=(1, 2, 3, 4, 5))
    parser.add_argument("--browser-label", required=True, help="Браузер и версия, например Firefox 159.")
    args = parser.parse_args()

    if args.step <= 0 or args.delay_ms <= 0:
        parser.error("--step и --delay-ms должны быть положительными.")
    if args.step > 100 or args.delay_ms > 1000:
        parser.error("--step или --delay-ms выходят за пределы допустимых значений.")

    frame_path = Path(args.frame_probe).resolve()
    output_path = Path(args.output).resolve()
    try:
        frame_probe = _read_frame_probe(frame_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(f"Не удалось прочитать frame probe: {exc}")

    board_type = args.board
    point_limit = BOARD_ITEM_POINT_LIMITS[board_type]
    runs: list[dict[str, Any]] = []

    print("\nЗапись браузерных испытаний AutoDraw")
    print(f"Доска: {board_type}; лимит: {point_limit}")
    print(f"Шаг: {args.step:g}px; задержка: {args.delay_ms:g}ms")
    print(f"Запусков: {len(STROKE_LENGTHS) * args.repeats}")
    print("Вводите только результаты, которые вы лично проверили на доске.\n")

    for repeat_index in range(1, args.repeats + 1):
        for stroke_length in STROKE_LENGTHS:
            planned_strokes = TOTAL_PATH_PX // stroke_length
            run_id = f"{board_type}-length{stroke_length}-repeat{repeat_index}"
            print(f"\n--- {run_id} ---")
            print(
                f"Перед вводом: план {planned_strokes} штрихов × "
                f"{stroke_length}px = {planned_strokes * stroke_length}px."
            )
            fresh_supply = _ask_yes_no(
                "Подтверждаете полный/сопоставимый начальный запас краски?"
            )
            outcome, visible_count = _ask_outcome()

            if outcome == "all_visible":
                visible_count = planned_strokes
            visible_path = visible_count * stroke_length
            notes = input("Примечания (Enter, если нет): ").strip()

            runs.append({
                "run_id": run_id,
                "board_item_type": board_type,
                "board_point_limit": point_limit,
                "point_step_px": args.step,
                "point_delay_ms": args.delay_ms,
                "scenario_id": f"length_{stroke_length}",
                "stroke_length_px": stroke_length,
                "planned_strokes": planned_strokes,
                "planned_path_length_px": planned_strokes * stroke_length,
                "outcome": outcome,
                "last_visible_strokes": visible_count,
                "visible_path_length_px": visible_path,
                "fresh_supply_confirmed": fresh_supply,
                "repeat_index": repeat_index,
                "notes": notes,
            })

    document = {
        "schema_version": 1,
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "browser": {
            "label": args.browser_label,
            "frame_probe": frame_probe,
        },
        "runs": runs,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    output_path.write_text(serialized, encoding="utf-8")
    print(f"\nЗаписано запусков: {len(runs)}")
    print(f"JSON сохранён: {output_path}")
    print(
        "Следующий шаг: запустите analyze_game_point_calibration.py с этим JSON. "
        "Если анализатор отклонит frame probe или запись, сначала проверьте исходные данные."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
