#!/usr/bin/env python3
"""Run the run-bound Stage A-D Egret compositor in the source browser family (Firefox)."""
from __future__ import annotations

import argparse
import base64
import hashlib
from pathlib import PureWindowsPath
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from run_paired_renderer_acceptance import discover_paired_renderer_runs  # noqa: E402


CASES = (
    {
        "name": "vertical",
        "monitor": "AutoDraw_Stage20/data/results/brush_behavior_tests/experiment-20261105-192426-b10-paired_renderer_vertical_single_stroke-6f2227c7/monitor_report.json",
        "run_id": "c860234f-995a-4789-9ac2-e05b322fe742",
    },
    {
        "name": "diagonal",
        "monitor": "AutoDraw_Stage20/data/results/brush_behavior_tests/experiment-20261105-192602-b10-paired_renderer_diagonal_single_stroke-0e61bc40/monitor_report.json",
        "run_id": "f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f",
    },
)
EXPECTED_BROWSER_MANIFEST = Path(
    "AutoDraw_Stage20/data/results/renderer_compare/vertical/"
    "egret-5.4.1-renderer-reference-manifest.json"
)
ORIGINAL_RUN_IDS = {item["run_id"] for item in CASES}


def discover_additional_cases(experiment_root: Path, workspace: Path) -> list[dict[str, str]]:
    """Create one offline renderer replay input for each non-baseline saved live run."""
    candidates, _rejected = discover_paired_renderer_runs(experiment_root)
    cases: list[dict[str, str]] = []
    for candidate in candidates:
        run_id = str(candidate["run_id"])
        if run_id in ORIGINAL_RUN_IDS:
            continue
        orientation = str(candidate["orientation"])
        monitor_path = (Path(candidate["experiment_dir"]) / "monitor_report.json").resolve()
        relative_monitor = monitor_path.relative_to(workspace).as_posix()
        cases.append({
            "name": f"{orientation}-{run_id}",
            "monitor": relative_monitor,
            "run_id": run_id,
            "output_subdir": f"paired-renderer/{orientation}/{run_id}",
        })
    return cases


def find_firefox() -> Path:
    candidates = [
        shutil.which("firefox"),
        Path(os.environ.get("ProgramFiles", "")) / "Mozilla Firefox/firefox.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Mozilla Firefox/firefox.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError("Firefox executable was not found on the GitHub Actions runner.")


def validate_manifest(
    manifest: dict[str, Any],
    monitor: dict[str, Any],
    run_id: str,
    expected_browser_major: str,
    actual_browser_version: str,
    actual_user_agent: str,
) -> None:
    profile = manifest.get("runtimeProfile", {})
    fixtures = manifest.get("fixtures", [])
    compositor = manifest.get("stageLevelCompositor", {})
    if profile.get("sourceRunId") != run_id or len(fixtures) != 1:
        raise ValueError("Firefox Stage probe is not bound to the expected single Monitor run.")
    fixture = fixtures[0]
    if fixture.get("sourceRunId") != run_id:
        raise ValueError("Firefox Stage fixture run ID differs from its Monitor report.")
    if compositor.get("status") != "generated_four_offline_variants" or compositor.get("variantCount") != 4:
        raise ValueError("Firefox Stage probe did not generate all four A-D variants.")
    variants = {item.get("id"): item for item in fixture.get("stageLevelCompositor", [])}
    if set(variants) != {"A", "B", "C", "D"}:
        raise ValueError("Firefox Stage manifest does not contain exactly A-D.")
    for key, backend in (("A", "WebGL"), ("B", "WebGL"), ("C", "Canvas2D"), ("D", "Canvas2D")):
        if variants[key].get("backend") != backend:
            raise ValueError(f"Variant {key} backend is not {backend}.")
    if "Egret WebGLRenderer" not in str(variants["A"].get("rendererBackend", "")):
        raise ValueError("Variant A did not use the actual Egret WebGLRenderer.")

    geometry = monitor.get("renderer_geometry_at_start", {})
    players = geometry.get("players", [])
    if len(players) != 1:
        raise ValueError(f"Expected exactly one monitored game player, found {len(players)}.")
    corners = geometry.get("boardStageCorners") or players[0].get("boardStageCorners") or {}
    top_left = corners.get("topLeft", {})
    scale_x = float(geometry.get("canvasScaleX", 0))
    scale_y = float(geometry.get("canvasScaleY", 0))
    expected_x = float(top_left.get("x", float("nan"))) * scale_x
    expected_y = float(top_left.get("y", float("nan"))) * scale_y
    placement = variants["A"].get("placement", {})
    rounded = variants["B"].get("placement", {})
    if abs(float(placement.get("x", float("inf"))) - expected_x) > 1e-4:
        raise ValueError("Variant A does not use the exact run-bound fractional X origin.")
    if abs(float(placement.get("y", float("inf"))) - expected_y) > 1e-4:
        raise ValueError("Variant A does not use the exact run-bound Y origin.")
    if float(rounded.get("x", float("inf"))) != round(expected_x):
        raise ValueError("Variant B does not use the rounded run-bound X origin.")
    if float(rounded.get("y", float("inf"))) != round(expected_y):
        raise ValueError("Variant B does not use the rounded run-bound Y origin.")
    if int(variants["A"].get("comparisonToA", {}).get("differingPixels", -1)) != 0:
        raise ValueError("Variant A self-comparison is not exact.")

    browser = manifest.get("browser", {})
    manifest_ua = str(browser.get("userAgent", ""))
    actual_major = actual_browser_version.split(".", 1)[0]
    if "Firefox/" not in manifest_ua or actual_major != expected_browser_major:
        raise ValueError(
            f"Firefox browser mismatch: expected major {expected_browser_major}, "
            f"actual {actual_browser_version}, manifest UA={manifest_ua!r}."
        )
    if actual_user_agent != manifest_ua:
        raise ValueError("Manifest userAgent differs from the live Firefox navigator.userAgent.")

    gl_info = manifest.get("webglProbe", {}).get("glInfo", {})
    if manifest.get("webglProbe", {}).get("status") != "complete":
        raise ValueError("Firefox WebGL probe did not complete.")
    if not gl_info.get("version") or not (gl_info.get("renderer") or gl_info.get("unmaskedRenderer")):
        raise ValueError("Firefox WebGL renderer diagnostics are incomplete.")



def discover_engine001_cases(journal_path: Path, workspace: Path) -> list[dict[str, str]]:
    """Use the immutable nine-task journal, not a guessed directory glob."""
    journal = json.loads(journal_path.read_text(encoding="utf-8-sig"))
    expected = {(s, n) for s in (
        "engine001_horizontal_endpoint", "engine001_vertical_axis", "engine001_diagonal_axis"
    ) for n in (1, 2, 3)}
    if journal.get("phase_id") != "ENGINE001" or journal.get("status") != "completed" or len(journal.get("tasks", [])) != 9:
        raise ValueError("ENGINE-001 E4 journal is not an immutable completed nine-cell matrix.")
    root = workspace / "AutoDraw_Stage20/data/results/brush_behavior_tests"
    seen_cells, seen_runs, seen_experiments, sessions = set(), set(), set(), set()
    cases = []
    for task in journal["tasks"]:
        cell = (task.get("scenario_id"), task.get("repeat_index"))
        if cell not in expected or cell in seen_cells or task.get("status") != "completed":
            raise ValueError("ENGINE-001 journal contains a duplicate, unknown or unfinished cell.")
        seen_cells.add(cell)
        attempts = task.get("attempts") or []
        if len(attempts) != 1 or attempts[0].get("status") != "completed":
            raise ValueError("ENGINE-001 journal contains a retry or incomplete attempt.")
        attempt = attempts[0]
        dirname = PureWindowsPath(str(attempt.get("experiment_dir", ""))).name
        if not dirname.startswith("experiment-20261108-") or "/" in dirname or "\\\\" in dirname:
            raise ValueError("ENGINE-001 journal contains an invalid experiment directory.")
        directory = root / dirname
        exp_path, monitor_path = directory / "experiment.json", directory / "monitor_report.json"
        audit_path = directory / "engine001-lab-audit.json"
        experiment = json.loads(exp_path.read_text(encoding="utf-8-sig"))
        monitor = json.loads(monitor_path.read_text(encoding="utf-8-sig"))
        audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
        exp_id, run_id, session_id = experiment.get("experiment_id"), monitor.get("run_id"), monitor.get("session_id")
        if (exp_id != attempt.get("experiment_id") or exp_id in seen_experiments
                or not run_id or run_id in seen_runs or not session_id):
            raise ValueError("ENGINE-001 experiment/run IDs are invalid or repeated.")
        seen_experiments.add(exp_id); seen_runs.add(run_id); sessions.add(session_id)
        if (audit.get("status") != "PASS_E4_RAW_CAPTURE"
                or audit.get("source_experiment_id") != exp_id
                or audit.get("run_id") != run_id or audit.get("session_id") != session_id
                or audit.get("scenario_id") != cell[0] or audit.get("repeat_index") != cell[1]
                or monitor.get("autodraw_experiment_id") != exp_id
                or monitor.get("execution_status") != "completed"
                or monitor.get("renderer_geometry_at_start") != monitor.get("renderer_geometry_at_end")
                or monitor.get("point_delta_matches_chalk") is not True):
            raise ValueError("ENGINE-001 audit or monitor binding disagrees with the completed journal.")
        if experiment.get("chalk_experiment_matrix", {}).get("series_id") != journal.get("series_id"):
            raise ValueError("ENGINE-001 series ID differs from the immutable journal.")
        points = monitor.get("accepted_points") or []
        pre, post = monitor.get("pre_test_snapshot") or {}, monitor.get("post_test_snapshot") or {}
        if (len(points) != audit.get("exact_chalk")
                or len(points) != post.get("pointCount", -1) - pre.get("pointCount", -1)
                or len(monitor.get("observed_stroke_modes") or []) != 1
                or monitor["observed_stroke_modes"][0].get("stroke_option_raw") is not True):
            raise ValueError("ENGINE-001 accepted points, CHALK or observed stroke mode disagree.")
        for filename in ("monitor_report.json", "experiment.json", "before_clear-screen.png", "after_draw-screen.png",
                         "before_clear-board.png", "after_draw-board.png"):
            path = directory / filename
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != audit.get("raw_sha256", {}).get(filename):
                raise ValueError(f"ENGINE-001 immutable raw hash mismatch: {path}")
        rel = monitor_path.relative_to(workspace).as_posix()
        cases.append({"name": f"engine001-{cell[0]}-r{cell[1]}", "monitor": rel,
                      "run_id": run_id, "output_subdir": f"engine001/{cell[0]}-r{cell[1]}-{run_id[:8]}"})
    if seen_cells != expected or len(seen_runs) != 9 or len(sessions) != 1:
        raise ValueError("ENGINE-001 E4 journal is missing cells or contains multiple Bridge sessions.")
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--workspace", default=".", type=Path)
    parser.add_argument(
        "--paired-renderer-experiment-root", type=Path, default=None,
        help="Generate additional run-bound offline WebGL references for saved paired-renderer captures.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run Firefox with a visible window so local hardware acceleration can be used.",
    )
    parser.add_argument("--engine001-journal", type=Path, default=None,
                        help="Replay exactly the nine immutable ENGINE-001 E4 runs.")
    parser.add_argument("--fill001-chalk-first-v5-only", action="store_true",
                        help="Isolated native V5 DEC-030 perimeter candidate sweep.")
    parser.add_argument("--fill001-bottom-only", action="store_true",
                        help="Replay the isolated native V4 thin bottom repair candidates.")
    parser.add_argument("--fill001-footprint-only", action="store_true",
                        help="Measure 10 isolated actual Egret WebGL brush footprints, no live run.")
    parser.add_argument("--fill001-contour-mixed-only", action="store_true",
                        help="Replay native V3 thin contour and wide interior candidates.")
    parser.add_argument("--fill001-contour-trim-only", action="store_true",
                        help="Replay isolated V2 contour-first endpoint trims on native BoardPane.")
    parser.add_argument("--fill001-contour-only", action="store_true",
                        help="Run frozen synthetic contour-first multi-stroke native BoardPane probe.")
    parser.add_argument("--engine001-only", action="store_true",
                        help="Do not repeat historical paired-renderer fixtures.")
    args = parser.parse_args()
    if args.engine001_only and args.engine001_journal is None:
        parser.error("--engine001-only requires --engine001-journal.")
    workspace = args.workspace.resolve()
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    cases = [] if args.engine001_only else list(CASES)
    if args.engine001_journal is not None:
        path = args.engine001_journal if args.engine001_journal.is_absolute() else workspace / args.engine001_journal
        cases.extend(discover_engine001_cases(path.resolve(), workspace))
    if args.paired_renderer_experiment_root is not None:
        experiment_root = args.paired_renderer_experiment_root
        if not experiment_root.is_absolute():
            experiment_root = workspace / experiment_root
        cases.extend(discover_additional_cases(experiment_root.resolve(), workspace))

    expected_manifest = json.loads((workspace / EXPECTED_BROWSER_MANIFEST).read_text(encoding="utf-8-sig"))
    expected_ua = str(expected_manifest.get("browser", {}).get("userAgent", ""))
    match = re.search(r"Firefox/([0-9.]+)", expected_ua)
    if not match:
        raise RuntimeError("The committed source renderer manifest does not identify a Firefox version.")
    expected_major = match.group(1).split(".", 1)[0]

    options = Options()
    if not args.headed:
        options.add_argument("-headless")
    options.binary_location = str(find_firefox())
    options.set_preference("webgl.disabled", False)
    options.set_preference("webgl.force-enabled", True)
    options.set_preference("webgl.disable-fail-if-major-performance-caveat", True)
    options.set_preference("webgl.min_capability_mode", False)
    options.set_preference("webgl.enable-webgl2", True)
    options.set_preference("webgl.msaa-force", True)
    driver = webdriver.Firefox(options=options)
    try:
        actual_version = str(driver.capabilities.get("browserVersion", ""))
        actual_user_agent = str(driver.execute_script("return navigator.userAgent"))
        if not actual_version or actual_version.split(".", 1)[0] != expected_major:
            raise RuntimeError(
                f"Firefox version mismatch: source renderer manifest expects {expected_major}.x, "
                f"runner Firefox is {actual_version!r}."
            )
        driver.set_page_load_timeout(90)
        if args.fill001_chalk_first_v5_only:
            if (args.engine001_journal or args.paired_renderer_experiment_root
                    or args.engine001_only or args.fill001_bottom_only
                    or args.fill001_footprint_only or args.fill001_contour_only
                    or args.fill001_contour_trim_only or args.fill001_contour_mixed_only):
                parser.error("--fill001-chalk-first-v5-only must be isolated.")
            fixture_path=workspace/"AutoDraw_Stage20/tests/fill001-chalk-first-v5-native-input.json"
            fixture_raw=fixture_path.read_bytes()
            fixture=json.loads(fixture_raw)
            names=["V4_y190_w2_control"]+[
                f"K_trim_{t}_y{y}_w{w}"
                for t in (0,1,2,3) for y,w in ((190,2),(189,3))
            ]
            frozen="ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b"
            if (fixture.get("schema")!="FILL001_CHALK_FIRST_NATIVE_V5"
                    or fixture.get("status")!="OFFLINE_SYNTHETIC_INPUT_ONLY"
                    or fixture.get("quality_policy_id")!="FILL001_CHALK_FIRST_PERIMETER_V2"
                    or fixture.get("frozen_mask_sha256")!=frozen
                    or fixture.get("baseline_variant")!="FILL001_NATIVE_BOTTOM_REPAIR_V4/J_bottom_y190_w2"
                    or fixture.get("lateral_trim_values")!=[0,1,2,3]
                    or fixture.get("bottom_variants")!=[{"y":190,"width":2},{"y":189,"width":3}]
                    or fixture.get("bottom_line_endpoints")!=[97,363]
                    or list(fixture.get("cases") or {})!=names
                    or fixture.get("measured_chalk") is not None
                    or fixture.get("executor_ready") is not False):
                raise ValueError("Native V5 protocol input identity mismatch")
            driver.get(f"{args.base_url}/AutoDraw_Stage20/tests/game_renderer_reference.html?contour=fill001v5")
            def complete_v5(browser: webdriver.Firefox) -> bool:
                return browser.execute_script(
                    "return document.body.dataset.chalkFirstV5Status"
                ) in ("complete","error")
            WebDriverWait(driver,120,poll_frequency=0.25).until(complete_v5)
            if driver.execute_script("return document.body.dataset.chalkFirstV5Status")!="complete":
                raise RuntimeError(driver.find_element("id","renderer-status").text)
            manifest=json.loads(
                driver.find_element("id","renderer-manifest-json").get_property("textContent")
            )
            items=manifest.get("cases") or {}
            if (manifest.get("schema")!=fixture["schema"]
                    or manifest.get("status")!="OFFLINE_NATIVE_EGRET_RENDERED"
                    or manifest.get("qualityPolicyId")!=fixture["quality_policy_id"]
                    or manifest.get("sourceMaskSha256")!=frozen
                    or manifest.get("lateralTrimValues")!=[0,1,2,3]
                    or manifest.get("bottomVariants")!=[{"y":190,"width":2},{"y":189,"width":3}]
                    or list(items)!=names
                    or manifest.get("measuredChalk") is not None
                    or manifest.get("executorReady") is not False
                    or manifest.get("gamePngQualityGate")!="NOT_EVALUATED"
                    or any(items[n].get("strokeCount")!=29 for n in names)):
                raise ValueError("Native V5 renderer manifest drift")
            links=driver.execute_script(
                "return Array.from(document.querySelectorAll('a[download]'))"
                ".filter(a=>a.href.startsWith('data:image/png;base64,'))"
                ".map(a=>({name:a.download,href:a.href}));"
            )
            if ({z["name"] for z in links}!=
                    {f"fill001-native-{n}.png" for n in names}
                    or len(links)!=len(names)):
                raise ValueError("V5 must preserve all nine pinned PNGs")
            dest=output_root/"fill001-chalk-first-native-v5"
            dest.mkdir(parents=True,exist_ok=False)
            (dest/"fixture-input.json").write_bytes(fixture_raw)
            for item in links:
                (dest/item["name"]).write_bytes(
                    base64.b64decode(item["href"].split(",",1)[1],validate=True)
                )
            (dest/"manifest.json").write_text(
                json.dumps(manifest,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8"
            )
            (dest/"fixture-provenance.json").write_text(
                json.dumps({
                    "schema":"FILL001_CHALK_FIRST_NATIVE_CAPTURE_V5",
                    "fixtureSha256":hashlib.sha256(fixture_raw).hexdigest(),
                    "frozenMaskSha256":frozen,
                    "browser":actual_version,"userAgent":actual_user_agent,
                    "pngSha256":{
                        z["name"]:hashlib.sha256((dest/z["name"]).read_bytes()).hexdigest()
                        for z in links
                    },
                    "gameRunId":None,"measuredChalk":None,
                    "source":"offline native BoardPane synthetic points, not game input",
                },ensure_ascii=False,indent=2)+"\\n",encoding="utf-8"
            )
            print("DEC-030 V5 native: 9 RGBA PNG + exact source fixture SHA. Game CHALK NOT_RUN.")
            return 0
        if args.fill001_bottom_only:
            if (args.engine001_journal or args.paired_renderer_experiment_root or args.engine001_only
                    or args.fill001_footprint_only or args.fill001_contour_only
                    or args.fill001_contour_trim_only or args.fill001_contour_mixed_only):
                parser.error("--fill001-bottom-only requires an isolated native replay.")
            fixture_path=workspace/"AutoDraw_Stage20/tests/fill001-bottom-repair-native-input.json"
            fixture_raw=fixture_path.read_bytes()
            fixture=json.loads(fixture_raw)
            expected_names=["G_trim_3_control"]+[
                f"J_bottom_y{y}_w{w}" for w in (1,2,3) for y in (189,190)
            ]
            expected_sha="ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b"
            if (fixture.get("schema")!="FILL001_NATIVE_BOTTOM_REPAIR_V4"
                    or fixture.get("status")!="OFFLINE_SYNTHETIC_INPUT_ONLY"
                    or fixture.get("frozen_mask_sha256")!=expected_sha
                    or fixture.get("baseline_variant")!="FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2/G_trim_3"
                    or fixture.get("candidate_widths")!=[1,2,3]
                    or fixture.get("candidate_y")!=[189,190]
                    or fixture.get("bottom_line_endpoints")!=[97,363]
                    or list(fixture.get("cases") or {})!=expected_names
                    or fixture.get("measured_chalk") is not None
                    or fixture.get("executor_ready") is not False):
                raise ValueError("V4 native bottom fixture identity mismatch")
            driver.get(f"{args.base_url}/AutoDraw_Stage20/tests/game_renderer_reference.html?contour=fill001v4")
            def bottom_completed(browser: webdriver.Firefox) -> bool:
                status=browser.execute_script("return document.body.dataset.bottomRepairStatus")
                return status in ("complete","error")
            WebDriverWait(driver,120,poll_frequency=0.25).until(bottom_completed)
            if driver.execute_script("return document.body.dataset.bottomRepairStatus")!="complete":
                raise RuntimeError(driver.find_element("id","renderer-status").text)
            manifest=json.loads(
                driver.find_element("id","renderer-manifest-json").get_property("textContent")
            )
            cases=manifest.get("cases") or {}
            if (manifest.get("schema")!=fixture["schema"]
                    or manifest.get("status")!="OFFLINE_NATIVE_EGRET_RENDERED"
                    or manifest.get("sourceMaskSha256")!=expected_sha
                    or manifest.get("bottomLineEndpoints")!=[97,363]
                    or manifest.get("testedWidths")!=[1,2,3]
                    or manifest.get("testedYs")!=[189,190]
                    or list(cases)!=expected_names
                    or manifest.get("measuredChalk") is not None
                    or manifest.get("executorReady") is not False
                    or any(cases[n].get("strokeCount")!=(28 if n==expected_names[0] else 29)
                           for n in expected_names)
                    or any(not isinstance(manifest.get("comparisons",{}).get(n,{}).get("differingPixels"),int)
                           for n in expected_names[1:])):
                raise ValueError("V4 native manifest and changed geometry mismatch")
            links=driver.execute_script(
                "return Array.from(document.querySelectorAll('a[download]'))"
                ".filter(a=>a.href.startsWith('data:image/png;base64,'))"
                ".map(a=>({name:a.download,href:a.href}));"
            )
            if ({z["name"] for z in links}!=
                    {f"fill001-native-{n}.png" for n in expected_names}
                    or len(links)!=len(expected_names)):
                raise ValueError("Expected seven pinned native V4 PNGs")
            dest=output_root/"fill001-bottom-native-v4"
            dest.mkdir(parents=True,exist_ok=False)
            (dest/"fixture-input.json").write_bytes(fixture_raw)
            for item in links:
                (dest/item["name"]).write_bytes(
                    base64.b64decode(item["href"].split(",",1)[1],validate=True)
                )
            (dest/"manifest.json").write_text(
                json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
            )
            (dest/"fixture-provenance.json").write_text(
                json.dumps({
                    "schema":"FILL001_NATIVE_BOTTOM_CAPTURE_V4",
                    "fixtureSha256":hashlib.sha256(fixture_raw).hexdigest(),
                    "maskSha256":expected_sha,
                    "browser":actual_version,"userAgent":actual_user_agent,
                    "pngSha256":{
                        n:hashlib.sha256((dest/n).read_bytes()).hexdigest()
                        for n in (z["name"] for z in links)
                    },
                    "liveRunId":None,"measuredChalk":None,
                    "source":"native synthetic BoardPane, no game execution",
                },ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
            )
            print("FILL001 V4 native bottom repair: seven renders + SHA provenance; no game CHALK")
            return 0
        if args.fill001_footprint_only:
            if (args.engine001_journal or args.paired_renderer_experiment_root or args.engine001_only
                    or args.fill001_contour_only or args.fill001_contour_trim_only
                    or args.fill001_contour_mixed_only or args.fill001_bottom_only):
                parser.error("--fill001-footprint-only requires an isolated native-probe invocation.")
            driver.get(f"{args.base_url}/AutoDraw_Stage20/tests/game_renderer_reference.html?footprint=fill001a")
            def footprint_completed(browser: webdriver.Firefox) -> bool:
                state = browser.execute_script("return document.body.dataset.fill001FootprintStatus")
                return state in ("complete", "error")
            WebDriverWait(driver, 120, poll_frequency=0.25).until(footprint_completed)
            if driver.execute_script("return document.body.dataset.fill001FootprintStatus") != "complete":
                raise RuntimeError(driver.find_element("id", "renderer-status").text)
            manifest = json.loads(
                driver.find_element("id", "renderer-manifest-json").get_property("textContent")
            )
            points = {
                "horizontal": [{"x":130,"y":120},{"x":330,"y":120}],
                "vertical": [{"x":230,"y":40},{"x":230,"y":200}],
                "diagonal": [{"x":130,"y":60},{"x":330,"y":180}],
                "corner": [{"x":150,"y":70},{"x":300,"y":70},{"x":300,"y":180}],
            }
            expected = {}
            for width in (5, 10):
                for orientation in ("horizontal", "vertical", "diagonal", "corner"):
                    expected[f"normal_{orientation}_w{width}"] = ("normal", width, points[orientation])
                expected[f"smooth_horizontal_w{width}"] = ("smooth", width, points["horizontal"])
            cases = manifest.get("cases")
            if (manifest.get("schema") != "FILL001_NATIVE_FOOTPRINT_A_V1"
                    or manifest.get("status") != "OFFLINE_NATIVE_EGRET_RENDERED"
                    or manifest.get("engineVersion") != "5.4.1"
                    or manifest.get("canvasSize") != {"width":1380, "height":720}
                    or manifest.get("scale") != 3
                    or manifest.get("alphaThresholds") != [1,64,128,254]
                    or manifest.get("measuredChalk") is not None
                    or manifest.get("originalGameCapture") is not None
                    or manifest.get("executorReady") is not False
                    or manifest.get("gameQualityGate") != "NOT_EVALUATED"
                    or not isinstance(cases, list) or len(cases) != 10
                    or {case.get("id") for case in cases} != set(expected)):
                raise ValueError("Footprint native manifest schema, isolation or count changed.")
            for case in cases:
                mode, width, path_points = expected[case["id"]]
                if (case.get("mode") != mode or case.get("width") != width
                        or case.get("points") != path_points
                        or case.get("acceptedSyntheticVerticesNotChalk") != len(path_points)
                        or case.get("pngName") != "fill001-footprint-" + case["id"] + ".png"
                        or case.get("sceneDiagnostics", {}).get("boardRenderMode") != 3):
                    raise ValueError("Native brush footprint probe coordinates were changed.")
            links = driver.execute_script(
                "return Array.from(document.querySelectorAll('a[download]'))"
                ".filter(a=>a.href.startsWith('data:image/png;base64,'))"
                ".map(a=>({name:a.download,href:a.href}));"
            )
            if {item["name"] for item in links} != {
                "fill001-footprint-" + key + ".png" for key in expected
            } or len(links) != len(expected):
                raise ValueError("Footprint native PNG inventory incomplete.")
            destination = output_root / "fill001-footprint-a-v1"
            destination.mkdir(parents=True, exist_ok=False)
            for item in links:
                data = base64.b64decode(item["href"].split(",", 1)[1], validate=True)
                (destination / item["name"]).write_bytes(data)
            (destination / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            (destination / "capture-provenance.json").write_text(
                json.dumps({
                    "schema": "FILL001_NATIVE_FOOTPRINT_CAPTURE_A_V1",
                    "browser": actual_version,
                    "userAgent": actual_user_agent,
                    "nativeRenderer": manifest["nativeRenderer"],
                    "source": "native Egret WebGL BoardPane synthetic probes",
                    "liveRunId": None, "exactChalk": None,
                    "pngSha256": {
                        item["name"]: hashlib.sha256(
                            (destination / item["name"]).read_bytes()
                        ).hexdigest() for item in links
                    },
                }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print("FILL001 phase A: 10 pinned native brush cases and PNGs verified; "
                  "no live screen/CHALK claims.")
            return 0
        if args.fill001_contour_only or args.fill001_contour_trim_only or args.fill001_contour_mixed_only:
            if sum((args.fill001_contour_only, args.fill001_contour_trim_only,
                    args.fill001_contour_mixed_only)) != 1:
                parser.error("Choose only one native contour version.")
            trim_v2 = args.fill001_contour_trim_only
            mixed_v3 = args.fill001_contour_mixed_only
            if args.engine001_journal or args.paired_renderer_experiment_root or args.engine001_only:
                parser.error("--fill001-contour-only is incompatible with other live-reference options.")
            fixture_path = workspace / ("AutoDraw_Stage20/tests/fill001-contour-mixed-native-input.json"
                                       if mixed_v3 else "AutoDraw_Stage20/tests/fill001-contour-trims-native-input.json"
                                       if trim_v2 else "AutoDraw_Stage20/tests/fill001-contour-first-native-input.json")
            if not fixture_path.is_file():
                raise FileNotFoundError("Native contour fixture must be generated in this checkout.")
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            if (fixture.get("schema") != ("FILL001_NATIVE_MIXED_CONTOUR_V3" if mixed_v3
                                                 else "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2" if trim_v2
                                                 else "FILL001_NATIVE_CONTOUR_FIRST_V1")
                    or fixture.get("status") != "OFFLINE_SYNTHETIC_INPUT_ONLY"):
                raise ValueError("Unexpected native contour fixture.")
            driver.get(f"{args.base_url}/AutoDraw_Stage20/tests/game_renderer_reference.html?contour="
                       f"{'fill001v3' if mixed_v3 else 'fill001v2' if trim_v2 else 'fill001'}")
            state_script = ("return document.body.dataset.contourMixedStatus" if mixed_v3
                            else "return document.body.dataset.contourTrimStatus" if trim_v2
                            else "return document.body.dataset.contourNativeStatus")
            def contour_completed(browser: webdriver.Firefox) -> bool:
                status = browser.execute_script(state_script)
                return status in ("complete", "error")
            WebDriverWait(driver, 120, poll_frequency=0.25).until(contour_completed)
            if driver.execute_script(state_script) != "complete":
                raise RuntimeError(driver.find_element("id", "renderer-status").text)
            manifest = json.loads(driver.find_element("id", "renderer-manifest-json").get_property("textContent"))
            expected_names = {"B_sparse_only", "C_contour_last", "E_contour_first"}
            if mixed_v3:
                expected_names = {"E_contour_10"} | {f"H_mixed_trim_{i}" for i in range(5)}
            elif trim_v2:
                expected_names |= {f"G_trim_{i}" for i in range(1,5)}
            if (manifest.get("status") != "OFFLINE_NATIVE_EGRET_RENDERED"
                    or manifest.get("schema") != fixture.get("schema")
                    or manifest.get("sourceMaskSha256") != fixture.get("frozen_mask_sha256")
                    or set(manifest.get("cases", {})) != expected_names
                    or any(manifest["cases"][name]["strokeCount"] != (27 if name == "B_sparse_only" else 28)
                           for name in expected_names)
                    or manifest.get("measuredChalk") is not None
                    or manifest.get("executorReady") is not False):
                raise ValueError("Native contour manifest did not verify frozen identity and output.")
            comparisons = manifest.get("comparisons", {})
            if not mixed_v3:
                order = comparisons.get("contourFirstVsLast", {})
                added = comparisons.get("sparseVsContourFirst", {})
                if (order.get("differingPixels") != 0 or order.get("equal") is not True
                        or not isinstance(added.get("differingPixels"), int)
                        or added["differingPixels"] <= 0):
                    raise ValueError("Native contour order parity or added geometry failed.")
            if trim_v2 or mixed_v3:
                for trim in (0,1,2,3,4) if mixed_v3 else (1,2,3,4):
                    delta = comparisons.get(f"contourFirstVsTrim{trim}", {})
                    if not isinstance(delta.get("differingPixels"), int) or delta["differingPixels"] <= 0:
                        raise ValueError(f"Native trim{trim} did not change the baseline render.")
            links = driver.execute_script(
                "return Array.from(document.querySelectorAll('a[download]'))"
                ".filter(a=>a.href.startsWith('data:image/png;base64,'))"
                ".map(a=>({name:a.download,href:a.href}));"
            )
            pngs = {f"fill001-native-{name}.png" for name in expected_names}
            if {Path(item["name"]).name for item in links} != pngs:
                raise ValueError(f"Expected {len(pngs)} native FILL001 PNGs.")
            case_output = output_root / ("fill001-contour-native-v3" if mixed_v3
                                         else "fill001-contour-native-v2" if trim_v2
                                         else "fill001-contour-native-v1")
            case_output.mkdir(parents=True, exist_ok=False)
            for item in links:
                payload = base64.b64decode(item["href"].split(",", 1)[1], validate=True)
                (case_output / Path(item["name"]).name).write_bytes(payload)
            (case_output / "manifest.json").write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            (case_output / "fixture-provenance.json").write_text(
                json.dumps({
                    "fixtureSha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
                    "maskSha256": fixture["frozen_mask_sha256"],
                    "baselinePlanSignature": fixture["baseline_plan_signature"],
                    "browser": actual_version,
                    "userAgent": actual_user_agent,
                    "source": "frozen synthetic contour-first, not a live Game Monitor run"
                }, indent=2) + "\n", encoding="utf-8"
            )
            comparison_label = ("mixed contour-vs-baseline differingPixels="
                                f"{manifest['comparisons']['contourFirstVsTrim0']['differingPixels']}"
                                if mixed_v3 else
                                "first-vs-last differingPixels="
                                f"{manifest['comparisons']['contourFirstVsLast']['differingPixels']}")
            print("FILL001 native BoardPane contour " +
                  ("V3" if mixed_v3 else "V2" if trim_v2 else "V1") +
                  " PASS; " + comparison_label + "; no live/game quality inference.")
            return 0
        for case in cases:
            monitor_path = workspace / case["monitor"]
            monitor = json.loads(monitor_path.read_text(encoding="utf-8-sig"))
            if monitor.get("run_id") != case["run_id"]:
                raise ValueError(f"Monitor report run ID mismatch for {case['name']}.")
            query = f"/{case['monitor'].replace(os.sep, '/')}"
            from urllib.parse import quote
            url = f"{args.base_url}/AutoDraw_Stage20/tests/game_renderer_reference.html?monitor={quote(query, safe='')}"
            output_subdir = case.get("output_subdir", f"stage-level-{case['name']}")
            case_output = output_root / Path(output_subdir)
            case_output.mkdir(parents=True, exist_ok=True)
            driver.get(url)

            def completed(browser: webdriver.Firefox) -> bool:
                state = browser.execute_script(
                    "return {reference:document.body.dataset.referenceStatus,"
                    "fixtures:document.body.dataset.fixtureCount,"
                    "webgl:document.body.dataset.webglStatus,"
                    "comparisons:document.body.dataset.webglComparisonCount};"
                )
                if state.get("reference") == "error":
                    return True
                return (
                    state.get("reference") == "complete"
                    and state.get("fixtures") == "1"
                    and state.get("webgl") == "complete"
                    and state.get("comparisons") == "1"
                )

            WebDriverWait(driver, 120, poll_frequency=0.25).until(completed)
            state = driver.execute_script(
                "return {reference:document.body.dataset.referenceStatus,"
                "fixtures:document.body.dataset.fixtureCount,"
                "webgl:document.body.dataset.webglStatus,"
                "comparisons:document.body.dataset.webglComparisonCount};"
            )
            (case_output / "page-source.html").write_text(driver.page_source, encoding="utf-8")
            if state.get("reference") != "complete" or state.get("webgl") != "complete":
                status = driver.find_element("id", "renderer-status").text
                raise RuntimeError(f"Firefox Stage probe failed for {case['name']}: {status}; state={state}")

            manifest_text = driver.find_element("id", "renderer-manifest-json").get_property("textContent")
            manifest = json.loads(manifest_text)
            validate_manifest(manifest, monitor, case["run_id"], expected_major, actual_version, actual_user_agent)
            (case_output / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )

            links = driver.execute_script(
                "return Array.from(document.querySelectorAll('a[download]'))"
                ".filter(a=>a.href.startsWith('data:image/png;base64,'))"
                ".map(a=>({name:a.download,href:a.href}));"
            )
            if len(links) != 7:
                raise RuntimeError(f"Firefox Stage probe expected 7 PNG links for {case['name']}, got {len(links)}.")
            stage_count = 0
            fixture_png_count = 0
            for link in links:
                name = Path(str(link["name"])).name
                if not name.endswith(".png"):
                    continue
                data_url = str(link["href"])
                if not data_url.startswith("data:image/png;base64,"):
                    raise ValueError(f"Unexpected PNG URL for {name}.")
                payload = base64.b64decode(data_url.split(",", 1)[1], validate=True)
                (case_output / name).write_bytes(payload)
                if name.startswith("stage-level-"):
                    stage_count += 1
                if name == "live-accepted-points-width-10-webgl-board-reference.png":
                    fixture_png_count += 1
            if stage_count != 4:
                raise RuntimeError(f"Firefox Stage probe expected four A-D PNGs, saved {stage_count}.")
            if fixture_png_count != 1:
                raise RuntimeError(f"Firefox paired replay expected one WebGL board PNG, saved {fixture_png_count}.")
            driver.save_screenshot(str(case_output / "firefox-page.png"))
            actual_context = manifest.get("webglProbe", {}).get("contextAttributes", {})
            expected_context = expected_manifest.get("webglProbe", {}).get("contextAttributes", {})
            context_differences = {
                key: {"expected": expected_context.get(key), "actual": actual_context.get(key)}
                for key in sorted(set(expected_context) | set(actual_context))
                if expected_context.get(key) != actual_context.get(key)
            }
            (case_output / "browser-session.json").write_text(
                json.dumps(
                    {
                        "browser": "Firefox",
                        "version": actual_version,
                        "userAgent": actual_user_agent,
                        "expectedMajor": expected_major,
                        "headless": not args.headed,
                        "webgl": manifest.get("webglProbe", {}).get("glInfo", {}),
                        "contextAttributes": actual_context,
                        "expectedContextAttributes": expected_context,
                        "contextAttributeDifferences": context_differences,
                        "expectedWebGLRenderer": expected_manifest.get("webglProbe", {}).get("glInfo", {}),
                    },
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            print(
                f"Firefox Stage {case['name']}: run {case['run_id']}, "
                f"WebGL={manifest['webglProbe']['glInfo'].get('renderer')}, A-D saved."
            )
    finally:
        driver.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
