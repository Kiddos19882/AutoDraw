from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREPARATION_ROOT = PROJECT_ROOT / "source" / "preparation"
sys.path.insert(0, str(PREPARATION_ROOT))

from engine_point_calibration import build_engine_point_calibration_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Показывает калибровку игровых точек и ограничения её достоверности."
    )
    parser.add_argument("--point-step", type=float, default=2.0, help="Шаг мыши в экранных пикселях.")
    parser.add_argument("--point-delay-ms", type=float, default=10.0, help="Задержка между перемещениями мыши.")
    parser.add_argument("--fps", type=float, default=48.0, help="Фактическая/ожидаемая частота кадров игры.")
    parser.add_argument(
        "--calibration-point-limit",
        type=int,
        choices=(3000, 6000, 12000),
        default=None,
        help="Известный лимит доски, на которой проводились четыре контрольных замера.",
    )
    args = parser.parse_args()

    report = build_engine_point_calibration_report(
        point_step_px=args.point_step,
        point_delay_ms=args.point_delay_ms,
        frame_rate_fps=args.fps,
        calibration_point_limit=args.calibration_point_limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
