"""Offline series geometry: frozen masks, method parameter provenance, no game input."""
import json
from pathlib import Path

import pytest

from fill001_series_runner import build_manifest
from fill001_series_offline_plans import prepare_offline_variants, write_offline_geometry
from fill001_series_handoff import build_series_source_plan
from chalk_fill_matrix import FILL001_RS_SCANLINE_CONFIGS
from chalk_fill_experiment import FILL001_EXPECTED_MASK_SHA256


def schedule():
    return build_manifest(
        cycles=3, figures_per_cycle=10,
        shapes=["rectangle", "wide_irregular", "narrow_irregular"],
        methods=["dense_scanlines", "spaced_scanlines"],
        radii=[1, 5, 10, 20, 30], series_id="series-all-30")


def test_30_factorial_variants_and_frozen_rs_parameters():
    report = prepare_offline_variants(schedule())
    assert report["unique_variants"] == 30
    assert report["task_count"] == 30
    assert not report["execution_allowed"]
    assert not report["automatic_clear_allowed"]
    keys = set(report["variants"])
    assert len(keys) == 30
    for key, variant in report["variants"].items():
        assert variant["target_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256[variant["shape_id"]]
        assert variant["stroke_count"] > 0
        assert variant["estimated_sampling_points_are_exact_chalk"] is False
        assert variant["engine_chalk_status"] == "NOT_EVALUATED"
        assert variant["execution_allowed"] is False
        if variant["fill_method"] == "dense_scanlines":
            assert (variant["scanline_row_step"], variant["scanline_offset"]) == (1, 0)
        else:
            assert (variant["scanline_row_step"], variant["scanline_offset"]) == (
                FILL001_RS_SCANLINE_CONFIGS[(variant["shape_id"], variant["radius"])]
            )


def test_reuse_variant_cache_without_chalk_claims(tmp_path):
    manifest = build_manifest(
        cycles=4, figures_per_cycle=2,
        shapes=["rectangle"], methods=["spaced_scanlines"], radii=[10],
        series_id="repeated-same")
    report = prepare_offline_variants(manifest)
    assert report["task_count"] == 8
    assert report["unique_variants"] == 1
    target = tmp_path / "report.json"
    write_offline_geometry(manifest, target)
    assert json.loads(target.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        write_offline_geometry(manifest, target)


def test_manifest_tamper_rejected():
    manifest = schedule()
    manifest["tasks"][0]["brush_radius"] = 30
    with pytest.raises(Exception):
        prepare_offline_variants(manifest)

def test_offline_preview_and_signed_source_keep_identical_frozen_signatures():
    m = schedule()
    preview = prepare_offline_variants(m)
    for task in m["tasks"]:
        key = f'{task["shape_id"]}:{task["fill_method"]}:r{task["brush_radius"]}'
        variant = preview["variants"][key]
        source = build_series_source_plan(m, task["task_id"])
        generation = source["generation"]
        assert variant["plan_signature"] == generation["plan_signature"]
        assert variant["target_mask_sha256"] == generation["frozen_target_mask_sha256"]
        assert (variant["scanline_row_step"], variant["scanline_offset"]) == (
            generation["scanline_row_step"], generation["scanline_offset"]
        )
        assert variant["stroke_count"] == generation["expected_strokes"]
        assert variant["execution_allowed"] is False
        assert generation["automatic_execution_allowed"] is False
