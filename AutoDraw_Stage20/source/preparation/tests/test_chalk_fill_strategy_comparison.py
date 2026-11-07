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
