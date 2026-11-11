"""FILL-001-SERIES-001: fail-closed multi-figure schedule and run journal.

This is an experimental orchestration contract, NOT a game-clear implementation
or a bypass for FILL-001's single-task execution gate. The runner requires
injected, independently validated live callbacks before any game interaction.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable
import uuid

SCHEMA = "FILL001_SERIES_MANIFEST_V1"
RUN_SCHEMA = "FILL001_SERIES_RUN_V1"
SHAPES = ("rectangle", "wide_irregular", "narrow_irregular")
METHODS = ("dense_scanlines", "spaced_scanlines")
RADII = (1, 5, 10, 20, 30)
MAX_TASKS = 250
MAX_CYCLES = 100
MAX_FIGURES = 100


class SeriesBlocked(ValueError):
    pass


def _positive(value: Any, limit: int, label: str) -> int:
    if type(value) is not int or not 1 <= value <= limit:
        raise SeriesBlocked(f"{label} must be an integer in 1..{limit}")
    return value


def _selection(values: Any, allowed: tuple, label: str) -> list:
    if not isinstance(values, (list, tuple)) or not values or len(values) != len(set(values)):
        raise SeriesBlocked(f"{label} must be a nonempty list with no duplicates")
    if any(type(value) is not type(allowed[0]) or value not in allowed for value in values):
        raise SeriesBlocked(f"{label} contains unknown values")
    return list(values)


def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def build_manifest(*, cycles: int, figures_per_cycle: int,
                   shapes: list[str], methods: list[str],
                   radii: list[int], series_id: str | None = None) -> dict:
    """Deterministic rotation through shape/method/brush combinations per cycle.

    Tasks are offline-only. They neither request Clear nor grant execution.
    """
    cycles = _positive(cycles, MAX_CYCLES, "cycles")
    figures_per_cycle = _positive(figures_per_cycle, MAX_FIGURES, "figures_per_cycle")
    if cycles * figures_per_cycle > MAX_TASKS:
        raise SeriesBlocked(f"Total figure runs cannot exceed {MAX_TASKS}")
    shapes = _selection(shapes, SHAPES, "shapes")
    methods = _selection(methods, METHODS, "methods")
    radii = _selection(radii, RADII, "radii")
    if series_id is None:
        series_id = "fill001-series-" + uuid.uuid4().hex[:12]
    if (not isinstance(series_id, str) or not 1 <= len(series_id) <= 64
            or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in series_id)):
        raise SeriesBlocked("Invalid series_id")

    # Balanced diagonal factorial: adjacent tasks vary shape, method and brush;
    # each full rotation still visits every shape/method/radius combination once.
    variants = []
    for index in range(len(shapes) * len(methods) * len(radii)):
        shape_index = index % len(shapes)
        shape_block = index // len(shapes)
        method_index = (shape_block + shape_index) % len(methods)
        radius_index = (shape_block // len(methods) + shape_index) % len(radii)
        variants.append((shapes[shape_index], methods[method_index], radii[radius_index]))
    tasks = []
    for cycle in range(1, cycles + 1):
        for figure in range(1, figures_per_cycle + 1):
            number = (cycle - 1) * figures_per_cycle + figure
            shape, method, radius = variants[(number - 1) % len(variants)]
            tasks.append({
                "task_id": f"{series_id}-c{cycle:03}-f{figure:03}",
                "cycle": cycle, "figure_in_cycle": figure,
                "order": number, "shape_id": shape,
                "fill_method": method, "brush_radius": radius,
                "state": "pending",
                "execution_allowed": False,
                "clear_allowed": False,
            })
    identity = {
        "schema": SCHEMA, "series_id": series_id,
        "cycles": cycles, "figures_per_cycle": figures_per_cycle,
        "shapes": shapes, "methods": methods, "radii": radii,
        "tasks": tasks,
    }
    return {**identity,
            "manifest_sha256": hashlib.sha256(_canonical(identity)).hexdigest(),
            "execution_allowed": False, "automatic_clear_allowed": False,
            "mode": "offline_preparation_only",
            "statistics": {
                "exact_chalk": "post.pointCount-pre.pointCount, only run-bound",
                "offline_estimate_is_not_exact_chalk": True,
                "png_quality": "must be run-bound against corresponding frozen mask",
            }}


def validate_manifest(manifest: Any) -> None:
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        raise SeriesBlocked("Invalid series manifest")
    expected = build_manifest(
        cycles=manifest["cycles"], figures_per_cycle=manifest["figures_per_cycle"],
        shapes=manifest["shapes"], methods=manifest["methods"], radii=manifest["radii"],
        series_id=manifest["series_id"])
    if manifest != expected:
        raise SeriesBlocked("Series manifest identity was modified or auto-execution enabled")


def write_manifest(manifest: dict, destination: Path) -> Path:
    validate_manifest(manifest)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return destination


def _clear_proof_valid(proof: Any, session_id: str) -> bool:
    """Accept preserved strict screen proof OR the established ENGINE-001 comparator.

    The ENGINE-001 tolerance is reused without raising its threshold.
    This validates the callback's evidence object, not hidden game state.
    """
    if (not isinstance(proof, dict)
            or proof.get("status") != "PASS"
            or proof.get("session_id") != session_id
            or proof.get("post_clear_pointCount") != 1
            or not isinstance(proof.get("mapping_sha256"), str)
            or len(proof["mapping_sha256"]) != 64
            or not all(isinstance(proof.get(k), str) and len(proof[k]) == 64
                       for k in ("reference_png_sha256", "post_clear_png_sha256"))
            or not isinstance(proof.get("last_settled_at_utc"), str)):
        return False
    if proof.get("schema") == "FILL001_SERIES_BLANK_SCREEN_VERIFICATION_V1":
        return (proof.get("changed_screen_pixels") == 0
                and proof.get("clear_ui_action_proven") is False)
    if proof.get("schema") == "FILL001_SERIES_ENGINE001_CLEAR_REUSE_V1":
        return (proof.get("engine001_visual_status") in
                ("restored", "restored_within_pixel_tolerance")
                and type(proof.get("engine001_tolerance_percent")) in (int, float)
                and float(proof["engine001_tolerance_percent"]) == 0.15
                and type(proof.get("engine001_changed_percent")) in (int, float)
                and 0 <= proof["engine001_changed_percent"] <= 0.15
                and proof.get("clear_ui_action_proven") is True
                and proof.get("screen_evidence_status")
                    == "ENGINE001_EXISTING_COMPARATOR_PASS")
    return False


def run_with_validated_callbacks(
    manifest: dict, *, results_dir: Path,
    observe_blank: Callable[[dict], dict],
    run_one: Callable[[dict], dict],
    clear_and_verify: Callable[[dict], dict],
    stop_requested: Callable[[], bool] | None = None,
) -> dict:
    """Experimental runner; injected callbacks MUST implement verified live gates.

    No call is made after an invalid/ambiguous Clear, run identity, PNG or
    exact counter. Caller must supply a genuinely validated game adapter.
    No restart-overwrite, no skip-on-error, no bulk preauthorization.
    """
    validate_manifest(manifest)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    summary_path = results_dir / (manifest["series_id"] + ".summary.json")
    if summary_path.exists():
        raise SeriesBlocked("An immutable series summary already exists; use a new series ID")
    accepted = []
    quality_failed = []
    quota_limited = []
    seen_sessions: set[str] = set()
    seen_run_ids: set[str] = set()
    previous_clear_proof: dict | None = None
    stop_requested = stop_requested or (lambda: False)
    status = "completed"
    issue = None
    for task in manifest["tasks"]:
        if stop_requested():
            status, issue = "stopped", "Operator stop requested"
            break
        record = {"schema": RUN_SCHEMA, "series_id": manifest["series_id"],
                  "manifest_sha256": manifest["manifest_sha256"],
                  "task_id": task["task_id"], "cycle": task["cycle"],
                  "shape_id": task["shape_id"], "fill_method": task["fill_method"],
                  "brush_radius": task["brush_radius"], "status": "BLOCKED",
                  "actual_chalk": None, "quality_gate": "NOT_EVALUATED"}
        path = results_dir / (task["task_id"] + ".json")
        if path.exists() or (results_dir / (task["task_id"] + ".clear.json")).exists():
            status, issue = "blocked", "Existing run or Clear evidence: never overwrite or rerun"
            break
        try:
            pre = observe_blank(task)
            if (not isinstance(pre, dict) or pre.get("valid") is not True
                    or type(pre.get("pointCount")) is not int
                    or pre["pointCount"] != 1
                    or pre.get("calibration_valid") is not True
                    or pre.get("fresh_board") is not True
                    or not isinstance(pre.get("session_id"), str)
                    or not pre["session_id"]):
                raise SeriesBlocked("No fresh blank board / valid mapping / unique session")
            if pre["session_id"] in seen_sessions:
                proof = pre.get("blank_screen_verification")
                try:
                    latest_clear = datetime.fromisoformat(
                        proof["last_settled_at_utc"].replace("Z", "+00:00")
                    )
                    latest_pre = datetime.fromisoformat(
                        pre["observed_at_utc"].replace("Z", "+00:00")
                    )
                    timestamps_fresh = (
                        latest_clear.tzinfo is not None
                        and latest_pre.tzinfo is not None
                        and latest_pre > latest_clear
                    )
                except (KeyError, TypeError, ValueError, AttributeError):
                    timestamps_fresh = False
                if (previous_clear_proof is None
                        or not isinstance(proof, dict)
                        or proof != previous_clear_proof
                        or proof.get("session_id") != pre["session_id"]
                        or not _clear_proof_valid(proof, pre["session_id"])
                        or proof.get("post_clear_pointCount") != pre["pointCount"]
                        or not isinstance(pre.get("mapping_sha256"), str)
                        or pre["mapping_sha256"] != proof.get("mapping_sha256")
                        or not timestamps_fresh):
                    raise SeriesBlocked(
                        "Reused session requires fresh exact observation after previous Clear"
                    )
            seen_sessions.add(pre["session_id"])
            result = run_one(task)
            limited = (isinstance(result, dict)
                       and result.get("execution_status") == "quota_limited")
            proof = result.get("quota_stop") if limited else None
            limited_valid = (
                limited and isinstance(proof, dict)
                and proof.get("reason") == "EXACT_REMAINING_BELOW_SAFETY_MARGIN"
                and type(proof.get("safety_margin_points")) is int
                and proof["safety_margin_points"] == 300
                and type(proof.get("remainingPoints")) is int
                and 0 <= proof["remainingPoints"] < 300
                and type(proof.get("completed_strokes")) is int
                and type(proof.get("planned_strokes")) is int
                and 0 < proof["completed_strokes"] < proof["planned_strokes"]
                and isinstance(result.get("stage6_summary"), dict)
                and result["stage6_summary"].get("completed_strokes") == proof["completed_strokes"]
                and result["stage6_summary"].get("planned_strokes") == proof["planned_strokes"]
                and type(proof.get("pointCount")) is int
                and type(proof.get("maxPoints")) is int
                and proof["pointCount"] == result.get("post_pointCount")
                and proof["maxPoints"]-proof["pointCount"] == proof["remainingPoints"]
                and result.get("quality_gate") == "NOT_EVALUATED"
            )
            if (not isinstance(result, dict)
                    or result.get("session_id") != pre["session_id"]
                    or result.get("task_id") != task["task_id"]
                    or (limited and not limited_valid)
                    or (not limited and result.get("execution_status") != "completed")
                    or result.get("monitor_binding") != "EXACT_RUN_BOUND"
                    or (not limited and result.get("quality_gate") not in ("PASS", "FAIL"))
                    or result.get("mouse_release_succeeded") is not True
                    or type(result.get("pre_pointCount")) is not int
                    or result["pre_pointCount"] != pre["pointCount"]
                    or type(result.get("post_pointCount")) is not int
                    or result["post_pointCount"] < pre["pointCount"]
                    or type(result.get("actual_chalk")) is not int
                    or result["actual_chalk"] != result["post_pointCount"]-result["pre_pointCount"]
                    or not result.get("before_png_sha256")
                    or not result.get("after_settled_png_sha256")
                    or not isinstance(result.get("run_id"), str)
                    or not result["run_id"]
                    or result["run_id"] in seen_run_ids):
                raise SeriesBlocked("Run lacks validated exact CHALK and quality evidence")
            seen_run_ids.add(result["run_id"])
            quality = result["quality_gate"]
            record.update(status=("QUOTA_LIMITED" if limited else
                                  "PASS" if quality == "PASS" else "QUALITY_FAIL"),
                          actual_chalk=result["actual_chalk"],
                          quality_gate=quality, runtime=result)
        except Exception as exc:
            record["status"] = "BLOCKED"
            record["error"] = f"{type(exc).__name__}: {exc}"
            status, issue = "blocked", record["error"]
        # Original result always preserved, including a negative result.
        with path.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        if record["status"] not in ("PASS", "QUALITY_FAIL", "QUOTA_LIMITED"):
            break
        if record["status"] == "PASS":
            accepted.append(record)
        elif record["status"] == "QUALITY_FAIL":
            quality_failed.append(record)
        else:
            quota_limited.append(record)
        # Never clear after last job; never continue if Clear is uncertain.
        if task["order"] < len(manifest["tasks"]):
            clear_record = results_dir / (task["task_id"] + ".clear.json")
            clear_evidence = {"schema": "FILL001_SERIES_CLEAR_V1",
                              "task_id": task["task_id"], "status": "BLOCKED"}
            try:
                cleared = clear_and_verify(task)
                clear_evidence["proof"] = cleared
                proof = cleared.get("blank_screen_verification") if isinstance(cleared, dict) else None
                if (not isinstance(cleared, dict) or cleared.get("valid") is not True
                        or type(cleared.get("pointCount")) is not int
                        or cleared["pointCount"] != 1
                        or cleared.get("mouse_released") is not True
                        or cleared.get("fresh_board") is not True
                        or not _clear_proof_valid(proof, pre["session_id"])):
                    raise SeriesBlocked("Clear lacks independent blank-screen verification")
                clear_evidence["status"] = "PASS"
                previous_clear_proof = dict(proof)
            except Exception as exc:
                clear_evidence["error"] = f"{type(exc).__name__}: {exc}"
                status, issue = "blocked", f"Clear failed: {type(exc).__name__}: {exc}"
            finally:
                with clear_record.open("x", encoding="utf-8") as stream:
                    json.dump(clear_evidence, stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
            if status == "blocked":
                break
    groups: dict[str, dict[str, dict]] = {"shape": {}, "method": {}, "brush": {}}
    for item in accepted:
        fields = {
            "shape": item["shape_id"],
            "method": item["fill_method"],
            "brush": str(item["brush_radius"]),
        }
        for dimension, value in fields.items():
            row = groups[dimension].setdefault(
                value, {"accepted": 0, "total_exact_chalk": 0, "min_exact_chalk": None,
                        "max_exact_chalk": None, "mean_exact_chalk": None}
            )
            chalk = item["actual_chalk"]
            row["accepted"] += 1
            row["total_exact_chalk"] += chalk
            row["min_exact_chalk"] = chalk if row["min_exact_chalk"] is None else min(row["min_exact_chalk"], chalk)
            row["max_exact_chalk"] = chalk if row["max_exact_chalk"] is None else max(row["max_exact_chalk"], chalk)
            row["mean_exact_chalk"] = row["total_exact_chalk"] / row["accepted"]
    if status == "completed" and quota_limited:
        status = "completed_with_quota_limited"
    summary = {"schema": "FILL001_SERIES_SUMMARY_V1", "series_id": manifest["series_id"],
               "manifest_sha256": manifest["manifest_sha256"],
               "status": status, "issue": issue, "scheduled": len(manifest["tasks"]),
               "accepted": len(accepted), "quality_failed": len(quality_failed),
               "quota_limited": len(quota_limited),
               "completed_with_bound_chalk": len(accepted) + len(quality_failed) + len(quota_limited),
               "exact_chalk_sum_of_accepted_runs": sum(r["actual_chalk"] for r in accepted),
               "exact_chalk_sum_of_quality_failed_runs": sum(r["actual_chalk"] for r in quality_failed),
               "exact_chalk_sum_of_quota_limited_runs": sum(r["actual_chalk"] for r in quota_limited),
               "exact_chalk_is_per_run_only": True,
               "grouped_exact_chalk_statistics": groups,
               "next_task_requires_fresh_session": True}
    with summary_path.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return summary


def run_with_series_owner_lock(
    manifest: dict, *, results_dir: Path,
    observe_blank: Callable[[dict], dict],
    run_one: Callable[[dict], dict],
    clear_and_verify: Callable[[dict], dict],
    stop_requested: Callable[[], bool] | None = None,
) -> dict:
    """Reuse ENGINE-001's cross-process owner lock for a whole series.

    The lock lives in the shared series directory, not a single task folder.
    It is held through drawing, evidence capture and game Clear. This prevents
    two AutoDraw processes from driving the same game in parallel.
    """
    from chalk_test_blocks import (
        acquire_chalk_block_owner_lock, release_chalk_block_owner_lock,
    )
    validate_manifest(manifest)
    destination = Path(results_dir)
    lock = acquire_chalk_block_owner_lock(destination.parent / "series-owner.json")
    if lock is None:
        raise SeriesBlocked("Another AutoDraw series already owns the game-control lock")
    try:
        return run_with_validated_callbacks(
            manifest, results_dir=destination,
            observe_blank=observe_blank, run_one=run_one,
            clear_and_verify=clear_and_verify,
            stop_requested=stop_requested,
        )
    finally:
        release_chalk_block_owner_lock(lock)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a SAFE offline multi-figure FILL-001 schedule")
    parser.add_argument("--cycles", type=int, required=True)
    parser.add_argument("--figures-per-cycle", type=int, required=True)
    parser.add_argument("--shapes", nargs="+", choices=SHAPES, default=list(SHAPES))
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--radii", nargs="+", type=int, choices=RADII, default=list(RADII))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(cycles=args.cycles, figures_per_cycle=args.figures_per_cycle,
                              shapes=args.shapes, methods=args.methods, radii=args.radii)
    write_manifest(manifest, args.output)
    print(f"Offline manifest: {args.output} ({len(manifest['tasks'])} tasks).")
    print("Live game execution and automatic Clear remain BLOCKED until validated adapter.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
