"""Independent read-only FILL-001 W2/W3 E5 audit on committed raw evidence.

Separate from fill001_screen_mask_v2 and fill001_v5_finalization: independently
recomputes PNG RGB differences, screen projection, perimeter distance and
closed-run event accounting. Reuses ONLY the immutable logical frozen mask
constructor (as an input, not the screen/policy auditor).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "data/results/brush_behavior_tests"
POLICY = "FILL001_CHALK_FIRST_PERIMETER_V2"
EXPECTED = (
    ("W2", "K_trim_0_y190_w2", "51480631-902c-47b1-b782-5fc74596246d",
     "d0999212-c9d0-437e-90a9-26d03a5ffaa3",
     "c36be38c-98c5-4654-b598-3ec3f07bf4c3", 1709, 2, 5),
    ("W3", "K_trim_0_y189_w3", "8f770c4a-43a6-478f-b581-8af006cde6ec",
     "6f68db86-c831-42ec-a632-f62c8fba85b1",
     "ca3bfa8b-a339-4c11-9f98-ed3881a16ad7", 1706, 3, 4),
)


def require(test: bool, message: str) -> None:
    if not test:
        raise AssertionError(message)


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_png(path: Path, expected_hash: str) -> np.ndarray:
    require(path.is_file(), f"Missing original PNG: {path}")
    require(hash_file(path) == expected_hash, f"PNG SHA256 mismatch: {path}")
    with Image.open(path) as image:
        require(image.format == "PNG", f"Not a PNG: {path}")
        return np.asarray(image.convert("RGB"), dtype=np.int16)


def inspect_case(label: str, candidate: str, attempt: str, session: str,
                 run_id: str, expected_chalk: int, final_radius: int,
                 expected_sliders: int) -> dict:
    from chalk_fill_experiment import build_fill_target_mask, fill_target_mask_sha256

    base = EVIDENCE / "fill001/v5_stage6_runs" / ("v5-" + attempt)
    report_path = base / "report.json"
    require(report_path.is_file(), f"Missing report: {label}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    request = report["request"]
    original = report["finalization"]["screen_mask_v2"]
    binding = report["finalization"]["binding"]
    active = original["active_quality_metrics"]
    require(request["attempt_id"] == attempt and request["candidate_id"] == candidate
            and request["session_id"] == session, f"{label}: wrong attempt or session")
    require(request["initial_snapshot"]["pointCount"] == 1, f"{label}: not blank")
    require(original["active_quality_policy_id"] == POLICY, f"{label}: wrong policy")
    frozen = build_fill_target_mask("rectangle")
    frozen_sha = fill_target_mask_sha256("rectangle", frozen)
    require(original["frozen_target_mask_sha256"] == frozen_sha,
            f"{label}: wrong frozen mask")
    roi = request["screen_roi"]
    corners = request["mapping"]["board_screen_corners"]
    require(request["mapping"]["session_id"] == session
            and request["mapping"]["status"] == "validated_preflight_input_transform_not_live_draw"
            and request["mapping"]["no_fallback"] is True
            and request["mapping"]["passive_sample_count"] >= 3,
            f"{label}: unvalidated mapping")
    require(original["geometry_evidence_sha256"] == request["mapping"]["passive_samples_sha256"],
            f"{label}: geometry provenance mismatch")

    before = load_png(base / "before.png", report["before_png"]["sha256"])
    after = load_png(base / "after_settled.png", report["after_settled_png"]["sha256"])
    require(before.shape == after.shape == (roi["height"], roi["width"], 3),
            f"{label}: ROI/PNG dimensions mismatch")
    left, right = float(corners["left"]), float(corners["right"])
    top, bottom = float(corners["top"]), float(corners["bottom"])
    sx, sy = (right - left) / 460, (bottom - top) / 240
    require(sx > 0 and sy > 0 and abs(sx-sy) / max(sx, sy) <= 0.01,
            f"{label}: nonuniform geometry")
    # Independent screen-center -> logical pixel projection; no fitted offsets.
    xx = (roi["x"] + np.arange(roi["width"]) - left) / sx
    yy = (roi["y"] + np.arange(roi["height"]) - top) / sy
    ix = np.clip(np.rint(xx).astype(int), 0, 459)
    iy = np.clip(np.rint(yy).astype(int), 0, 239)
    target = frozen[iy[:, None], ix[None, :]] & (
        ((yy >= 0) & (yy <= 240))[:, None]
        & ((xx >= 0) & (xx <= 460))[None, :]
    )
    painted = (np.max(np.abs(after - before), axis=2) > 8)
    area = int(target.sum())
    covered = int((target & painted).sum())
    outside = painted & ~target
    leak = int(outside.sum())
    # scipy exact Euclidean distance to the nearest true target pixel:
    # independent of production cv2.distanceTransform.
    distance = distance_transform_edt(~target)
    outs = distance[outside] / min(sx, sy)
    far = int(np.count_nonzero(outs > 3.0 + 1e-6))
    max_out = round(float(outs.max()) if leak else 0.0, 6)
    coverage = covered / area
    gate = "PASS" if coverage >= 0.99 and far == 0 else "FAIL"
    require((area, covered, leak, far) == (
        original["target_pixels"], original["covered_pixels"],
        original["leakage_pixels"], active["leakage_pixels_beyond_allowed_halo"]
    ), f"{label}: independent RGB pixel metrics disagree with report")
    require(abs(coverage - original["coverage_fraction"]) <= 1e-12,
            f"{label}: coverage disagreement")
    require(abs(max_out - active["max_perimeter_overshoot_logical_px"]) <= 1e-6,
            f"{label}: perimeter distance disagreement")
    require(gate == original["active_quality_gate"] == "PASS",
            f"{label}: active quality gate disagreement")

    monitor_dir = EVIDENCE / "game_monitor_bridge" / session
    found = sorted(monitor_dir.glob("game-monitor-run-*.json"))
    require(len(found) == 1, f"{label}: expected one closed Bridge run, got {len(found)}")
    run = json.loads(found[0].read_text(encoding="utf-8"))
    require(run["run_id"] == run_id and run["session_id"] == session
            and run["record_type"] == "autodraw_game_monitor_run"
            and run["execution_status"] == "completed", f"{label}: mismatched closed run")
    require(all(run.get(k) == 0 for k in (
        "monitor_dropped_events", "monitor_error_count",
        "collector_sequence_gap_count", "bridge_send_failures_delta"
    )) and run["point_delta_matches_chalk"] is True, f"{label}: telemetry not clean")
    first, last = run["pre_test_snapshot"], run["post_test_snapshot"]
    require(first["isExact"] is True and last["isExact"] is True,
            f"{label}: resource counter not exact")
    pre, post = first["pointCount"], last["pointCount"]
    require(pre == binding["pre_pointCount"] == 1
            and post == binding["post_pointCount"]
            and post - pre == expected_chalk == report["actual_chalk"]
            == binding["exact_chalk"] == run["chalk"]["consumed_points"],
            f"{label}: independent exact CHALK mismatch")
    require(run["chalk"]["pre_point_count"] == pre
            and run["chalk"]["post_point_count"] == post
            and run["chalk"]["status"] == "exact",
            f"{label}: closed chalk provenance invalid")
    events = run["events"]
    down = [e for e in events if e.get("type") == "POINTER_DOWN_CANDIDATE"]
    metrics = run["per_stroke_metrics"]
    planned = request["expected_pointer_down_client"]
    require(len(events) == run["event_count"]
            and len(down) == len(metrics) == 29 + expected_sliders
            and run["stroke_count"] == 29
            and run["non_consuming_stroke_candidate_count"] == expected_sliders,
            f"{label}: input counts not independently consistent")
    slider = request["slider_client_corridor"]
    selected, extras = 0, 0
    for e, m in zip(down, metrics):
        require(e["strokeId"] == m["stroke_id"]
                and m["lifecycle_status"] == "complete",
                f"{label}: broken stroke lifecycle")
        x, y = e["clientX"], e["clientY"]
        matched = (selected < 29
                   and abs(x - planned[selected][0]) <= 3
                   and abs(y - planned[selected][1]) <= 3)
        if matched:
            expected_radius = 10 if selected < 28 else final_radius
            require(e["board"]["currentRadius"] == expected_radius
                    and m["point_count_delta"] > 0
                    and m["point_count_delta_matches_updates"] is True,
                    f"{label}: drawn stroke wrong radius or point updates")
            selected += 1
        else:
            require(slider["left"] <= x <= slider["right"]
                    and slider["top"] <= y <= slider["bottom"]
                    and m["point_count_delta"] == 0
                    and m["point_update_event_count"] == 0,
                    f"{label}: unexplained off-plan input")
            extras += 1
    require(selected == 29 and extras == expected_sliders, f"{label}: wrong event split")
    require(report["stage6_summary"]["completed_strokes"] == 29
            and report["stage6_summary"]["mouse_release"]["succeeded"] is True,
            f"{label}: executor incomplete")
    return {
        "candidate": candidate, "attempt": attempt, "session": session,
        "closed_run": run_id, "frozen_mask_sha256": frozen_sha,
        "before_png_sha256": hash_file(base / "before.png"),
        "settled_png_sha256": hash_file(base / "after_settled.png"),
        "target_pixels": area, "covered_pixels": covered,
        "leakage_pixels": leak, "coverage_fraction": coverage,
        "max_overshoot_logical_px": max_out, "leakage_beyond_halo": far,
        "quality_gate": gate, "pre_pointCount": pre,
        "post_pointCount": post, "exact_chalk": post-pre,
        "planned_strokes": selected, "excluded_slider_moves": extras,
        "monitor_event_count": len(events), "audit_status": "PASS",
    }


def main() -> int:
    results, failures = {}, {}
    for row in EXPECTED:
        try:
            results[row[0]] = inspect_case(*row)
        except Exception as exc:
            failures[row[0]] = f"{type(exc).__name__}: {exc}"
    comparison = {}
    if not failures and len(results) == 2:
        comparison = {
            "w2_minus_w3_chalk": results["W2"]["exact_chalk"] -
                                 results["W3"]["exact_chalk"],
            "provisional_winner": "W3",
            "independent_runtime_replay": "NOT_RUN",
            "repeatability": "NOT_RUN",
            "multi_color_holdout": "NOT_RUN",
            "production_eligible": False,
        }
        require(comparison["w2_minus_w3_chalk"] == 3,
                "Unexpected exact CHALK difference")
    report = {
        "schema": "FILL001_V5_INDEPENDENT_E5_W2_W3_V1",
        "scope": "committed PNG pixel audit plus raw closed Bridge run accounting",
        "status": "PASS" if not failures else "FAIL",
        "accepted": len(results), "rejected": len(failures), "missing": 2 - len(results) - len(failures),
        "runs": results, "failures": failures, "comparison": comparison,
        "frozen_criteria": {"threshold_rgb_gt": 8, "minimum_coverage": 0.99,
                            "maximum_perimeter_overshoot_logical_px": 3.0},
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
