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


@pytest.mark.parametrize("shape", FILL001_SHAPES)
def test_contour_edge_trim_preserves_every_row_and_frozen_mask(shape):
    from chalk_fill_strategy_comparison import compare_contour_edge_trims
    report, raster = compare_contour_edge_trims(shape)
    assert report["protocol"] == "FILL001_CONTOUR_EDGE_TRIMS_V2"
    assert report["frozen_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256[shape]
    assert report["measurement_scope"]["measured_chalk"] is None
    assert report["measurement_scope"]["executor_ready"] is False
    original, _ = compare_fill001_strategies(shape)
    control = report["strategies"]["E_contour_first_same_geometry"]
    assert control["coverage_fraction"] == (
        original["strategies"]["C_sparse_plus_contour"]["coverage_fraction"]
    )
    assert report["tested_endpoint_trims"] == [1, 2, 3, 4]
    for trim in report["tested_endpoint_trims"]:
        candidate = report["strategies"][f"G_contour_first_endpoints_trim_{trim}"]
        assert candidate["rows_preserved"]
        assert candidate["interior_scanline_count"] == control["interior_scanline_count"]
        assert candidate["contour_first"]
        assert candidate["contour_interior_overlap_logical_pixels"] > 0
        assert candidate["sampling_points_proxy_not_chalk"] <= (
            control["sampling_points_proxy_not_chalk"]
        )
        assert candidate["leakage_logical_pixels"] >= 0
        assert candidate["offline_quality_gate_passed"] == (
            candidate["coverage_fraction"] >= 0.99
            and candidate["leakage_logical_pixels"] == 0
        )
    assert all(image.shape == (240, 460) for image in raster.values())


def test_contour_edge_trim_invalid_inputs_and_immutable_reports(tmp_path):
    from chalk_fill_strategy_comparison import (
        compare_contour_edge_trims, save_contour_edge_trim_report,
    )
    for kwargs in ({"endpoint_trims": (0,)}, {"endpoint_trims": (5,)},
                   {"endpoint_trims": (2, 2)}, {"endpoint_trims": (True,)},
                   {"endpoint_trims": [1]}, {"brush_value": 30}):
        with pytest.raises(ValueError):
            compare_contour_edge_trims("rectangle", **kwargs)
    out = tmp_path / "edge-trim-v2"
    path = save_contour_edge_trim_report(out, ["rectangle"])
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["analysis_type"] == "fill001_contour_edge_trims_v2"
    assert len(list(out.glob("*.png"))) == 6
    with pytest.raises(FileExistsError):
        save_contour_edge_trim_report(out, ["rectangle"])



def test_contour_native_fixture_pins_frozen_rectangle_and_non_executable(tmp_path):
    from chalk_fill_strategy_comparison import export_contour_first_native_fixture
    path = tmp_path / "fixture.json"
    data = export_contour_first_native_fixture(path)
    assert data["schema"] == "FILL001_NATIVE_CONTOUR_FIRST_V1"
    assert data["frozen_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256["rectangle"]
    assert data["measured_chalk"] is None
    assert data["executor_ready"] is False
    cases = data["cases"]
    assert list(cases) == ["B_sparse_only", "C_contour_last", "E_contour_first"]
    assert [len(cases[name]) for name in cases] == [27, 28, 28]
    assert cases["C_contour_last"][-1] == cases["E_contour_first"][0]
    assert cases["C_contour_last"][:-1] == cases["E_contour_first"][1:]
    assert len(cases["E_contour_first"][0]["points"]) > 3
    contour = cases["E_contour_first"][0]["points"]
    assert contour[0] == contour[-1]
    assert all(stroke["mode"] == "normal" and stroke["width"] == 10
               for strokes in cases.values() for stroke in strokes)
    assert json.loads(path.read_text(encoding="utf-8")) == data
    with pytest.raises(FileExistsError):
        export_contour_first_native_fixture(path)


def test_native_contour_alpha_read_only_audit(tmp_path):
    import cv2
    import hashlib
    from chalk_fill_strategy_comparison import analyze_contour_native_pngs
    render = tmp_path / "native"
    render.mkdir()
    cases = {}
    for name in ("B_sparse_only", "C_contour_last", "E_contour_first"):
        rgba = np.zeros((720, 1380, 4), dtype=np.uint8)
        rgba[200:210, 200:210, 3] = 255
        if name != "B_sparse_only":
            rgba[200:210, 210:215, 3] = 255
        pngname = f"fill001-native-{name}.png"
        assert cv2.imwrite(str(render / pngname), rgba)
        cases[name] = {
            "pngName": pngname,
            "strokeCount": 27 if name == "B_sparse_only" else 28,
            "acceptedSyntheticPoints": 54 if name == "B_sparse_only" else 119,
        }
    manifest = {
        "schema": "FILL001_NATIVE_CONTOUR_FIRST_V1",
        "status": "OFFLINE_NATIVE_EGRET_RENDERED",
        "sourceMaskSha256": FILL001_EXPECTED_MASK_SHA256["rectangle"],
        "cases": cases,
        "comparisons": {"contourFirstVsLast": {"differingPixels": 0}},
        "measuredChalk": None, "executorReady": False,
    }
    (render / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    out = tmp_path / "audit.json"
    report = analyze_contour_native_pngs(render, out)
    assert report["status"] == "OFFLINE_NATIVE_DIAGNOSTIC_ONLY"
    assert report["native_to_live_stage_mapping"] == "NOT_EVALUATED"
    assert report["game_png_quality_gate"] == "NOT_EVALUATED"
    assert report["projected_target_backing_pixels"] > 0
    assert report["measured_chalk"] is None
    assert set(report["cases"]) == set(cases)
    assert report["order_parity_exact_rgba"] is True
    for row in report["cases"].values():
        assert set(row["alpha_threshold_diagnostics"]) == {"1", "64", "128", "254"}
        assert len(row["native_png_sha256"]) == 64
    with pytest.raises(FileExistsError):
        analyze_contour_native_pngs(render, out)
    out.unlink()
    manifest["sourceMaskSha256"] = "0" * 64
    (render / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="identity"):
        analyze_contour_native_pngs(render, out)


def test_native_v2_contour_trim_fixture_preserves_contour_rows_and_sha(tmp_path):
    from chalk_fill_strategy_comparison import export_contour_trim_native_fixture
    path = tmp_path / "native-v2.json"
    fixture = export_contour_trim_native_fixture(path)
    assert fixture["schema"] == "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2"
    assert fixture["tested_trim_px"] == [1,2,3,4]
    assert fixture["frozen_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256["rectangle"]
    assert fixture["measured_chalk"] is None and fixture["executor_ready"] is False
    cases = fixture["cases"]
    assert len(cases) == 7
    assert len(cases["B_sparse_only"]) == 27
    assert len(cases["E_contour_first"]) == 28
    for trim in fixture["tested_trim_px"]:
        case = cases[f"G_trim_{trim}"]
        assert len(case) == 28
        assert case[0] == cases["E_contour_first"][0]
        for original, updated in zip(cases["E_contour_first"][1:], case[1:]):
            first, last = original["points"]
            left, right = updated["points"]
            assert left == {"x": first["x"] + trim, "y": first["y"]}
            assert right == {"x": last["x"] - trim, "y": last["y"]}
    assert json.loads(path.read_text(encoding="utf-8")) == fixture
    with pytest.raises(FileExistsError):
        export_contour_trim_native_fixture(path)


def test_mixed_contour_native_v3_fixture_uses_exact_two_brush_widths(tmp_path):
    from chalk_fill_strategy_comparison import export_mixed_contour_native_fixture
    output = tmp_path / "mixed-v3.json"
    fixture = export_mixed_contour_native_fixture(output)
    assert fixture["schema"] == "FILL001_NATIVE_MIXED_CONTOUR_V3"
    assert fixture["frozen_mask_sha256"] == FILL001_EXPECTED_MASK_SHA256["rectangle"]
    assert fixture["tested_trim_px"] == [0,1,2,3,4]
    assert fixture["contour_width"] == 5 and fixture["contour_inset"] == 3
    assert fixture["interior_width"] == 10 and fixture["row_step"] == 5
    assert fixture["measured_chalk"] is None
    assert fixture["executor_ready"] is False
    cases = fixture["cases"]
    assert len(cases) == 6
    assert len(cases["E_contour_10"]) == 28
    for trim in range(5):
        strokes = cases[f"H_mixed_trim_{trim}"]
        assert len(strokes) == 28
        assert strokes[0]["width"] == 5
        assert strokes[0]["points"][0] == strokes[0]["points"][-1]
        assert all(st["width"] == 10 and st["mode"] == "normal" for st in strokes[1:])
        for old, amended in zip(cases["E_contour_10"][1:], strokes[1:]):
            p,q=old["points"]
            a,b=amended["points"]
            assert a == {"x": p["x"] + trim, "y": p["y"]}
            assert b == {"x": q["x"] - trim, "y": q["y"]}
    assert json.loads(output.read_text(encoding="utf-8")) == fixture
    with pytest.raises(FileExistsError):
        export_mixed_contour_native_fixture(output)


def test_native_footprint_phase_a_contract_and_tampering(tmp_path):
    import hashlib
    import cv2
    from chalk_fill_strategy_comparison import analyze_native_brush_footprints
    source = tmp_path / "native"
    source.mkdir()
    coordinates = {
        "horizontal": [(130,120),(330,120)],
        "vertical": [(230,40),(230,200)],
        "diagonal": [(130,60),(330,180)],
        "corner": [(150,70),(300,70),(300,180)],
    }
    cases, png_hashes = [], {}
    for width in (5,10):
        for shape in ("horizontal","vertical","diagonal","corner","smooth_horizontal"):
            mode = "smooth" if shape.startswith("smooth") else "normal"
            orientation = "horizontal" if mode == "smooth" else shape
            points = coordinates[orientation]
            name = f"{mode}_{orientation}_w{width}"
            png = f"fill001-footprint-{name}.png"
            image = np.zeros((720,1380,4), dtype=np.uint8)
            pixels = np.array(points, dtype=np.int32)*3
            for a,b in zip(pixels[:-1],pixels[1:]):
                cv2.line(image, tuple(a), tuple(b), (0,0,0,255),
                         thickness=width*3)
            assert cv2.imwrite(str(source/png), image)
            png_hashes[png] = hashlib.sha256((source/png).read_bytes()).hexdigest()
            cases.append({
                "id":name, "mode":mode, "width":width,
                "points":[{"x":x,"y":y} for x,y in points],
                "pngName":png,
                "acceptedSyntheticVerticesNotChalk":len(points),
                "sceneDiagnostics":{"boardRenderMode":3},
            })
    manifest = {
        "schema":"FILL001_NATIVE_FOOTPRINT_A_V1",
        "status":"OFFLINE_NATIVE_EGRET_RENDERED",
        "engineVersion":"5.4.1",
        "canvasSize":{"width":1380,"height":720},
        "logicalBoard":{"width":460,"height":240},
        "scale":3,
        "alphaThresholds":[1,64,128,254],
        "measuredChalk":None,"originalGameCapture":None,
        "executorReady":False,
        "gameQualityGate":"NOT_EVALUATED",
        "liveStageMapping":"NOT_EVALUATED",
        "cases":cases,
    }
    (source/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    provenance = {
        "schema":"FILL001_NATIVE_FOOTPRINT_CAPTURE_A_V1",
        "liveRunId":None,"exactChalk":None,"pngSha256":png_hashes,
    }
    (source/"capture-provenance.json").write_text(
        json.dumps(provenance),encoding="utf-8")
    out = tmp_path/"footprint-analysis.json"
    report = analyze_native_brush_footprints(source,out)
    assert report["status"] == "OFFLINE_NATIVE_DIAGNOSTIC_ONLY"
    assert report["case_count"] == 10
    assert report["measured_chalk"] is None
    assert report["game_quality_gate"] == "NOT_EVALUATED"
    assert report["native_to_game_screen_equivalence"] == "NOT_EVALUATED"
    assert report["executor_ready"] is False
    assert set(report["cases"]) == {case["id"] for case in cases}
    for case in report["cases"].values():
        assert set(case["thresholds"]) == {"1","64","128","254"}
        assert case["thresholds"]["128"]["painted_backing_pixels"] > 0
        assert len(case["png_sha256"]) == 64
    assert (report["cases"]["normal_horizontal_w10"]["thresholds"]["128"]
            ["midpoint_cross_section_backing_px"] > 0)
    assert (report["cases"]["normal_vertical_w5"]["thresholds"]["128"]
            ["midpoint_cross_section_backing_px"] > 0)
    assert (report["cases"]["normal_corner_w10"]["thresholds"]["128"]
            ["corner_joint_13x13_painted_pixels"] > 0)
    assert json.loads(out.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        analyze_native_brush_footprints(source,out)
    out.unlink()
    path=source/"fill001-footprint-normal_horizontal_w5.png"
    path.write_bytes(path.read_bytes()+b"tamper")
    with pytest.raises(ValueError,match="SHA-256"):
        analyze_native_brush_footprints(source,out)
    path.write_bytes(path.read_bytes()[:-6])
    manifest["cases"][0]["points"][0]["x"]+=1
    (source/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(ValueError,match="coordinates"):
        analyze_native_brush_footprints(source,out)


def test_contour_spatial_partition_disjoint_and_native_wrapper(tmp_path):
    import cv2
    import hashlib
    from chalk_fill_strategy_comparison import (
        _spatial_partition_contour_residual,
        analyze_native_contour_spatial_residual,
    )
    from chalk_fill_experiment import build_fill_target_mask
    mask = build_fill_target_mask("rectangle")
    target = np.repeat(np.repeat(mask, 3, axis=0), 3, axis=1)
    painted = target.copy()
    # Last three backing rows: 819 pixels each; width1 leakage at left,
    # top and far below are disjoint from missing zones.
    painted[570:573, :] = False
    painted[0, 0] = True
    painted[200, 0] = True
    painted[710, 0] = True
    result = _spatial_partition_contour_residual(target, painted)
    assert result["uncovered_backing_pixels"] == 2457
    assert result["uncovered_regions"]["bottom"] == 2457
    assert result["leakage_backing_pixels"] == 3
    assert result["leakage_regions"]["above"] == 1
    assert result["leakage_regions"]["below"] == 1
    assert result["leakage_regions"]["left"] == 1
    assert sum(result["uncovered_regions"].values()) == 2457
    assert sum(result["leakage_regions"].values()) == 3
    assert result["worst_uncovered_rows"][0]["backing_y"] == 570
    assert result["worst_uncovered_rows"][0]["uncovered"] == 819
    assert len(result["row_residuals"]) >= 3
    with pytest.raises(ValueError):
        _spatial_partition_contour_residual(target, target.astype(np.uint8))
    with pytest.raises(ValueError):
        _spatial_partition_contour_residual(target, painted, edge_band=0)

    root = tmp_path / "native-v3"
    root.mkdir()
    names = ["E_contour_10"] + [f"H_mixed_trim_{i}" for i in range(5)]
    cases, summaries = {}, {}
    for name in names:
        png = f"fill001-native-{name}.png"
        rgba = np.zeros((720, 1380, 4), dtype=np.uint8)
        rgba[:, :, 3] = painted.astype(np.uint8) * 255
        assert cv2.imwrite(str(root / png), rgba)
        cases[name] = {"pngName": png}
        summaries[name] = {
            "native_png_sha256": hashlib.sha256((root/png).read_bytes()).hexdigest(),
            "alpha_threshold_diagnostics": {
                str(cutoff): {
                    "uncovered_target_backing_pixels": 2457,
                    "leakage_backing_pixels": 3,
                } for cutoff in (1, 64, 128, 254)
            },
        }
    manifest = {
        "schema": "FILL001_NATIVE_MIXED_CONTOUR_V3",
        "status": "OFFLINE_NATIVE_EGRET_RENDERED",
        "sourceMaskSha256": FILL001_EXPECTED_MASK_SHA256["rectangle"],
        "measuredChalk": None, "executorReady": False,
        "cases": cases,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    previous = {
        "source_native_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "frozen_mask_sha256": FILL001_EXPECTED_MASK_SHA256["rectangle"],
        "status": "OFFLINE_NATIVE_DIAGNOSTIC_ONLY",
        "game_png_quality_gate": "NOT_EVALUATED",
        "measured_chalk": None,
        "cases": summaries,
    }
    audit = root / "native-alpha-audit-v3.json"
    audit.write_text(json.dumps(previous), encoding="utf-8")
    output = root / "native-spatial-audit-v1.json"
    report = analyze_native_contour_spatial_residual(root, output)
    assert report["schema"] == "FILL001_NATIVE_CONTOUR_SPATIAL_AUDIT_V1"
    assert report["source_native_variant"] == "v3"
    assert report["repair_plan"] == "NOT_GENERATED"
    assert report["game_png_quality_gate"] == "NOT_EVALUATED"
    assert report["executor_ready"] is False
    assert set(report["cases"]) == set(names)
    assert report["cases"][names[0]]["128"]["uncovered_regions"]["bottom"] == 2457
    assert json.loads(output.read_text(encoding="utf-8")) == report
    with pytest.raises(FileExistsError):
        analyze_native_contour_spatial_residual(root, output)
    output.unlink()
    previous["cases"][names[0]]["native_png_sha256"] = "0"*64
    audit.write_text(json.dumps(previous), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA"):
        analyze_native_contour_spatial_residual(root, output)
