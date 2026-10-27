from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PREPARATION_ROOT = Path(__file__).resolve().parents[1] / "source" / "preparation"
if str(PREPARATION_ROOT) not in sys.path:
    sys.path.insert(0, str(PREPARATION_ROOT))

from game_point_calibration import analyze_game_point_calibration  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Оценить расход игровых точек по результатам контролируемых браузерных запусков."
    )
    parser.add_argument("--input", required=True, help="JSON с измерением кадров и результатами запусков.")
    parser.add_argument("--output", help="Необязательный путь сохранения JSON-отчёта.")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    try:
        document = json.loads(input_path.read_text(encoding="utf-8-sig"))
        report = analyze_game_point_calibration(document)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(serialized, encoding="utf-8")
        print(f"Отчёт сохранён: {output_path}")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
