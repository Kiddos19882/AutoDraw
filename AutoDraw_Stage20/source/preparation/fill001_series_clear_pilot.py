"""FILL001-SERIES-001 one-time offline Clear E4 evidence evaluator.

This tool intentionally never clicks Clear or drives Firefox. The operator
must acquire genuine same-session game screenshots and exact Monitor snapshots.
It writes immutable PASS/BLOCKED evidence, including negative results.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from fill001_series_blank_verification import verify_blank_screen_after_clear

SCHEMA = "FILL001_SERIES_CLEAR_PILOT_REPORT_V1"


def evaluate_clear_pilot(source: dict) -> dict:
    if not isinstance(source, dict):
        raise ValueError("Clear pilot evidence must be a JSON object")
    report = {
        "schema": SCHEMA,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED",
        "session_id": source.get("session_id"),
        "mapping_sha256": source.get("mapping_sha256"),
        "blank_screen_proof": None,
        "reason": None,
        "game_clear_click_executed_by_tool": False,
        "e4_live_clear_action_verified": False,
        "actual_chalk": None,
    }
    try:
        proof = verify_blank_screen_after_clear(
            session_id=source["session_id"],
            mapping_sha256=source["mapping_sha256"],
            reference_blank_png=Path(source["reference_blank_png"]),
            after_clear_png=Path(source["after_clear_png"]),
            reference_blank_snapshot=source["reference_blank_snapshot"],
            pre_clear_snapshot=source["pre_clear_snapshot"],
            settled_snapshots=source["settled_snapshots"],
            cursor_parked_off_roi=source["cursor_parked_off_roi"],
            mouse_released=source["mouse_released"],
        )
        report["status"] = "SCREEN_AND_COUNTER_PASS"
        report["blank_screen_proof"] = proof
        report["reason"] = (
            "Game UI Clear control was not independently observed by this offline tool; "
            "live control selection and automatic click remain NOT_VALIDATED."
        )
    except (KeyError, TypeError, OSError, ValueError) as exc:
        report["reason"] = f"{type(exc).__name__}: {exc}"
    return report


def write_clear_pilot(source: dict, output_dir: Path) -> Path:
    record = evaluate_clear_pilot(source)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / ("clear-pilot-" + uuid.uuid4().hex + ".json")
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Check captured game Clear proof (no game control)")
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    saved = write_clear_pilot(evidence, args.output_dir)
    report = json.loads(saved.read_text(encoding="utf-8"))
    print(f"Clear pilot: {report['status']}; evidence {saved}")
    return 0 if report["status"] == "SCREEN_AND_COUNTER_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
