#!/usr/bin/env python3
"""Run the run-bound Stage A-D Egret compositor in the source browser family (Firefox)."""
from __future__ import annotations

import argparse
import base64
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--workspace", default=".", type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    expected_manifest = json.loads((workspace / EXPECTED_BROWSER_MANIFEST).read_text(encoding="utf-8-sig"))
    expected_ua = str(expected_manifest.get("browser", {}).get("userAgent", ""))
    match = re.search(r"Firefox/([0-9.]+)", expected_ua)
    if not match:
        raise RuntimeError("The committed source renderer manifest does not identify a Firefox version.")
    expected_major = match.group(1).split(".", 1)[0]

    options = Options()
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
        for case in CASES:
            monitor_path = workspace / case["monitor"]
            monitor = json.loads(monitor_path.read_text(encoding="utf-8-sig"))
            if monitor.get("run_id") != case["run_id"]:
                raise ValueError(f"Monitor report run ID mismatch for {case['name']}.")
            query = f"/{case['monitor'].replace(os.sep, '/')}"
            from urllib.parse import quote
            url = f"{args.base_url}/AutoDraw_Stage20/tests/game_renderer_reference.html?monitor={quote(query, safe='')}"
            case_output = output_root / f"stage-level-{case['name']}"
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
            for link in links:
                name = Path(str(link["name"])).name
                if not name.startswith("stage-level-") or not name.endswith(".png"):
                    continue
                data_url = str(link["href"])
                if not data_url.startswith("data:image/png;base64,"):
                    raise ValueError(f"Unexpected PNG URL for {name}.")
                payload = base64.b64decode(data_url.split(",", 1)[1], validate=True)
                (case_output / name).write_bytes(payload)
                stage_count += 1
            if stage_count != 4:
                raise RuntimeError(f"Firefox Stage probe expected four A-D PNGs, saved {stage_count}.")
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
