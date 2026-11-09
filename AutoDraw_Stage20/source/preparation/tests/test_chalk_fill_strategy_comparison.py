from __future__ import annotations

import json

import numpy as np
import pytest

from chalk_fill_experiment import FILL001_EXPECTED_MASK_SHA256, FILL001_SHAPES
from chalk_fill_strategy_comparison import (
    compare_fill001_strategies,
    save_exploratory_report,
)


@pytest.mark.parametrize("shape", FILL001_SHAPES)
def test_frozen_fill_strategy_screen_keeps_provenance_and_reports_all_four(shape):
    report, rasters = compare_fill001_strategies(shape)
    assert report["frozen_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256[shape]
    assert list(report["strategies"]) == [
        "A_dense_scanline",
        "B_sparse_scanline",
        "C_sparse_plus_contour",
        "D_plus_oracle_local_correction",
    ]
    assert all(mask.shape == (240, 460) for mask in rasters.values())
    assert report["strategies"]["A_dense_scanline"]["stroke_count"] > (
        report["strategies"]["B_sparse_scanline"]["stroke_count"]
    )
    assert report["strategies"]["B_sparse_scanline"]["leakage_logical_pixels"] == 0
    assert np.all(
        rasters["B_sparse_scanline"] <= rasters["C_sparse_plus_contour"]
    )
    assert np.all(
        rasters["C_sparse_plus_contour"] <= rasters["D_plus_oracle_local_correction"]
    )
    assert report["strategies"]["D_plus_oracle_local_correction"]["uncovered_logical_pixels"] == 0
    assert report["measurement_scope"]["measured_chalk"] is None
    assert report["measurement_scope"]["runtime_validated"] is False
    assert report["measurement_scope"]["executor_ready"] is False


def test_strategy_screen_is_deterministic_and_non_executor():
    first, images_first = compare_fill001_strategies("rectangle")
    second, images_second = compare_fill001_strategies("rectangle")
    assert first == second
    assert all(np.array_equal(images_first[name], images_second[name]) for name in images_first)
    assert first["strategies"]["A_dense_scanline"]["stroke_count"] == 131
    assert first["strategies"]["B_sparse_scanline"]["stroke_count"] == 27
    assert first["measurement_scope"]["D_oracle_warning"]


@pytest.mark.parametrize(
    ("kwargs", "error_fragment"),
    [
        ({"brush_value": 30}, "radius-10 only"),
        ({"sparse_row_step": 0}, "sparse_row_step"),
        ({"sparse_row_step": True}, "sparse_row_step"),
        ({"sampling_step": 0}, "sampling_step"),
        ({"contour_inset": -1}, "contour inset"),
        ({"contour_inset": 200}, "single connected"),
    ],
)
def test_strategy_screen_rejects_invalid_parameters(kwargs, error_fragment):
    with pytest.raises(ValueError, match=error_fragment):
        compare_fill001_strategies("rectangle", **kwargs)


def test_strategy_screen_writes_versioned_diagnostics_without_overwrite(tmp_path):
    out = tmp_path / "fill001-ad-v1"
    report_file = save_exploratory_report(out, ["rectangle"])
    payload = json.loads(report_file.read_text(encoding="utf-8"))
    assert payload["analysis_type"] == "fill001_frozen_A_D_offline_comparison"
    assert len(payload["reports"]) == 1
    assert len(list(out.glob("*.png"))) == 5
    with pytest.raises(FileExistsError, match="prior experimental"):
        save_exploratory_report(out, ["rectangle"])


@pytest.mark.parametrize("shape", FILL001_SHAPES)
def test_contour_first_order_only_control_and_overlap_screen(shape):
    from chalk_fill_strategy_comparison import compare_contour_first_overlap
    report, rasters = compare_contour_first_overlap(shape)
    assert report["protocol"] == "FILL001_CONTOUR_FIRST_OVERLAP_V1"
    assert report["frozen_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256[shape]
    assert report["measurement_scope"]["measured_chalk"] is None
    assert report["measurement_scope"]["executor_ready"] is False
    assert report["measurement_scope"]["runtime_validated"] is False
    assert report["tested_interior_insets"] == [7, 8, 9]
    assert np.array_equal(
        rasters["C_contour_last_control"],
        rasters["E_contour_first_same_geometry"],
    )
    a = report["strategies"]["C_contour_last_control"]
    b = report["strategies"]["E_contour_first_same_geometry"]
    assert a["coverage_fraction"] == b["coverage_fraction"]
    assert a["leakage_logical_pixels"] == b["leakage_logical_pixels"]
    assert a["sampling_points_proxy_not_chalk"] == b["sampling_points_proxy_not_chalk"]
    assert not a["contour_first"] and b["contour_first"]
    assert a["contour_interior_overlap_logical_pixels"] > 0
    for inset in (7, 8, 9):
        row = report["strategies"][f"F_contour_first_interior_inset_{inset}"]
        assert row["contour_first"]
        assert row["contour_interior_overlap_logical_pixels"] > 0
        assert row["stroke_count"] >= 2
        assert row["leakage_logical_pixels"] >= 0
        assert row["offline_quality_gate_passed"] == (
            row["coverage_fraction"] >= 0.99 and row["leakage_logical_pixels"] == 0
        )


@pytest.mark.parametrize("kwargs", [
    {"brush_value": 30}, {"scanline_row_step": 0},
    {"contour_inset": 0}, {"interior_insets": (6,)},
    {"interior_insets": (8, 8)}, {"interior_insets": (True,)},
    {"sampling_step": 0},
])
def test_contour_first_rejects_unsupported_inputs(kwargs):
    from chalk_fill_strategy_comparison import compare_contour_first_overlap
    with pytest.raises(ValueError):
        compare_contour_first_overlap("rectangle", **kwargs)


def test_contour_first_is_deterministic_and_preserves_old_comparison(tmp_path):
    from chalk_fill_strategy_comparison import (
        compare_contour_first_overlap, save_contour_first_report,
    )
    first, rasters = compare_contour_first_overlap("rectangle")
    second, again = compare_contour_first_overlap("rectangle")
    assert first == second
    assert all(np.array_equal(rasters[k], again[k]) for k in rasters)
    original, _ = compare_fill001_strategies("rectangle")
    assert first["strategies"]["C_contour_last_control"]["coverage_fraction"] == (
        original["strategies"]["C_sparse_plus_contour"]["coverage_fraction"]
    )
    out = tmp_path / "contour-first-v1"
    path = save_contour_first_report(out, ["rectangle"])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["analysis_type"] == "fill001_contour_first_overlap_v1"
    assert len(list(out.glob("*.png"))) == 7  # target + six strategies
    with pytest.raises(FileExistsError):
        save_contour_first_report(out, ["rectangle"])
