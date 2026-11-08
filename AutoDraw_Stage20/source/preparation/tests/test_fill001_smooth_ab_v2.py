from __future__ import annotations

import copy

import pytest

from chalk_fill_matrix import (
    FillMatrixError, load_fill001_matrix, write_fill001_matrix,
)
from chalk_fill_execution import prepare_fill001_single_task_plan
from fill001_smooth_ab import build_fill001_smooth_ab_matrix
from fill001_smooth_ab_v2 import (
    PROTOCOL, SCREEN_MASK, V2_IDENTITY_FIELDS,
    build_fill001_smooth_ab_v2_matrix, validate_smooth_ab_v2_matrix,
    analyze_smooth_ab_v2_pair,
)
from chalk_fill_matrix import _hash
from fill001_monitor_diagnostic import _expected_mode


def test_fresh_v2_matrix_and_same_frozen_plan(tmp_path):
    matrix = build_fill001_smooth_ab_v2_matrix("fresh-mask-v2-20261108")
    old = build_fill001_smooth_ab_matrix("legacy-separate")
    assert matrix["experiment_protocol"] == PROTOCOL
    assert matrix["screen_mask_version"] == SCREEN_MASK
    assert matrix["execution_allowed"] is False
    assert matrix["expected_task_count"] == 2
    assert [t["expected_smooth"] for t in matrix["tasks"]] == [True, False]
    assert set(t["screen_mask_version"] for t in matrix["tasks"]) == {SCREEN_MASK}
    assert all("-v2-smooth-" in t["task_id"] for t in matrix["tasks"])
    assert len({t["plan_signature"] for t in matrix["tasks"]}) == 1
    assert all(t["expected_strokes"] == 27 for t in matrix["tasks"])
    assert {t["plan_signature"] for t in matrix["tasks"]} == {
        old["tasks"][0]["plan_signature"]
    }
    for task in matrix["tasks"]:
        assert _expected_mode(task) == (PROTOCOL, task["expected_smooth"])
    out = write_fill001_matrix(matrix, tmp_path / "fresh.json")
    assert load_fill001_matrix(out) == matrix
    docs = [prepare_fill001_single_task_plan(
        matrix, task["task_id"], operator_approved_single_task_preflight=True
    )[0] for task in matrix["tasks"]]
    assert [s["points"] for s in docs[0]["strokes"]] == [
        s["points"] for s in docs[1]["strokes"]
    ]
    assert len(docs[0]["strokes"]) == 27
    assert old["experiment_protocol"] != matrix["experiment_protocol"]


def test_v2_rejects_legacy_id_and_mask_even_after_signature_rehash():
    base = build_fill001_smooth_ab_v2_matrix("v2-guard")
    for mutation in (
        lambda m: m["tasks"][0].update(expected_smooth=False),
        lambda m: m["tasks"][0].update(screen_mask_version="V1"),
        lambda m: m["tasks"][0].update(task_id="old-series-task"),
        lambda m: m.update(screen_mask_version="V1"),
        lambda m: m["tasks"][1].update(plan_signature="f" * 64),
        lambda m: m.update(execution_allowed=True),
        lambda m: m["tasks"].append(copy.deepcopy(m["tasks"][0])),
    ):
        matrix = copy.deepcopy(base)
        mutation(matrix)
        matrix["matrix_signature"] = _hash({
            key: matrix[key] for key in V2_IDENTITY_FIELDS
        })
        with pytest.raises(FillMatrixError):
            validate_smooth_ab_v2_matrix(matrix)


def _evidence(task, run_id, sha="a" * 64):
    v1 = {"coverage_fraction": .987, "leakage_pixels": 3,
          "png_audit_status": "failed"}
    v2 = {"schema": SCREEN_MASK, "run_id": run_id,
          "acceptance_override": False, "before_png_sha256": sha,
          "after_png_sha256": "b" * 64,
          "frozen_target_mask_sha256": task["target_mask_sha256"],
          "v1_original": v1, "coverage_fraction": .988,
          "leakage_pixels": 4}
    return {
        "protocol": PROTOCOL, "screen_mask_version": SCREEN_MASK,
        "task_id": task["task_id"],
        "expected_smooth": task["expected_smooth"],
        "raw_e4_status": "PASS_E4_RAW_CAPTURE",
        "run_id": run_id, "plan_signature": task["plan_signature"],
        "target_mask_sha256": task["target_mask_sha256"],
        "before_png_sha256": sha, "after_png_sha256": "b" * 64,
        "renderer_geometry_sha256": "c" * 64,
        "screen_roi": {"x": 50, "y": 100, "width": 674, "height": 355},
        "png_audit": v1, "v2_audit": v2, "exact_chalk": 1300,
    }


def test_v2_pair_does_not_mix_run_ids_versions_or_baselines():
    matrix = build_fill001_smooth_ab_v2_matrix("fresh-pair")
    rows = [_evidence(task, f"run-{i}") for i, task in enumerate(matrix["tasks"])]
    good = analyze_smooth_ab_v2_pair(matrix, rows)
    assert good["status"] == "ANALYZED_COMPARABLE"
    assert good["acceptance_override"] is False
    assert good["off_minus_on"]["v2_leakage_pixels"] == 0
    cases = [
        lambda e: e[1].update(run_id="run-0"),
        lambda e: e[1].update(protocol="FILL001_SMOOTH_AB_V1"),
        lambda e: e[1].update(screen_mask_version="V1"),
        lambda e: e[0]["v2_audit"].update(acceptance_override=True),
        lambda e: e[0].update(before_png_sha256="f" * 64),
    ]
    for mutation in cases:
        broken = copy.deepcopy(rows)
        mutation(broken)
        with pytest.raises(FillMatrixError):
            analyze_smooth_ab_v2_pair(matrix, broken)
    different = copy.deepcopy(rows)
    different[1]["before_png_sha256"] = "d" * 64
    different[1]["v2_audit"]["before_png_sha256"] = "d" * 64
    assert analyze_smooth_ab_v2_pair(matrix, different)["status"].startswith("PARTIAL")
