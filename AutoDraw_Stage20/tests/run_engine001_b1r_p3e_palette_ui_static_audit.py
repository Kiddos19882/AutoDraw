#!/usr/bin/env python3
"""ENGINE-001 B1-R-P3E: bounded static engine128 UI color routing audit.

All conclusions are E1/E2/E3. Never treats Javascript button presence,
old screenshot calibration, or screenshot palette subset as live E4 proof.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from run_engine001_b1r_p3b_engine128_adaptive32 import (
    ENGINE_GIT_BLOB_SHA1, ENGINE_WHITE_INDEX, read_engine_palette,
    git_blob_sha,
)
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT = "ENGINE001_B1R_P3E_ENGINE128_COLOR_UI_AUDIT_V1"
SCREENSHOT_PALETTE_BLOB = "461b5f3725b9b79888ad36e807b3cf4c9e445e98"
TOKENS = {
    "popup_new_palette": "createElaborateEasterEggs",
    "popup_old_palette": "oldCreateElaborateEasterEggs",
    "extended_palette_gate": "_isPainterExtend",
    "egg_color_icon": "EggColorIcon",
    "egg_color_event_handler": "eggColorChangedHandler",
    "board_set_color": ".setColor(",
    "rgb_sliders": "rgbSlider",
}
MAX_MATCHES_PER_TOKEN = 3
CONTEXT_BEFORE = 170
CONTEXT_AFTER = 330


def validate_screenshot_palette(raw: bytes, engine_rgb: np.ndarray):
    if (not isinstance(raw, bytes) or
            git_blob_sha(raw) != SCREENSHOT_PALETTE_BLOB):
        raise ValueError("BLOCKED_P3E_BROWSER_PALETTE_BLOB_DRIFT")
    return validate_palette_object(json.loads(raw.decode("utf-8")), engine_rgb)


def validate_palette_object(data: dict, engine_rgb: np.ndarray):
    if (not isinstance(data, dict) or not isinstance(data.get("colors"), list) or
            len(data["colors"]) != 32 or engine_rgb.shape != (128, 3) or
            engine_rgb.dtype != np.uint8):
        raise ValueError("BLOCKED_P3E_SCREENSHOT_OR_ENGINE_SHAPE")
    engine_map = {
        "#%02X%02X%02X" % tuple(int(n) for n in v): i
        for i, v in enumerate(engine_rgb)
    }
    seen = set()
    entries = []
    for item in data["colors"]:
        if (not isinstance(item, dict) or
                not isinstance(item.get("rgb"), list) or
                len(item["rgb"]) != 3 or
                any(type(k) is not int or not 0 <= k <= 255
                    for k in item["rgb"])):
            raise ValueError("BLOCKED_P3E_INVALID_RGB_ENTRY")
        expect = "#%02X%02X%02X" % tuple(item["rgb"])
        if (str(item.get("hex", "")).upper() != expect or
                expect in seen or expect not in engine_map):
            raise ValueError("BLOCKED_P3E_SCREENSHOT_RGB_INVALID_OR_OUTSIDE_ENGINE")
        seen.add(expect)
        entries.append({
            "screenshot_rgb": expect,
            "engine128_index": int(engine_map[expect]),
            "old_screenshot_screen_xy": [
                item.get("screen_x"), item.get("screen_y")
            ],
            "screen_position_executor_validated": False,
        })
    if len(seen) != 32:
        raise AssertionError("BLOCKED_P3E_NOT32_UNIQUE_SCREENSHOT_COLORS")
    return entries


def token_contexts(js: str):
    """Deterministic bounded snippets; NO full 4.8MB JS in result."""
    if not isinstance(js, str):
        raise ValueError("BLOCKED_P3E_JS_NOT_TEXT")
    contexts = {}
    for label, token in TOKENS.items():
        occurrences = [m.start() for m in re.finditer(re.escape(token), js)]
        contexts[label] = {
            "keyword": token,
            "occurrence_count": len(occurrences),
            "bounded_examples": [
                {
                    "byte_or_char_offset": int(loc),
                    "context": js[max(0, loc-CONTEXT_BEFORE):
                                  min(len(js), loc+len(token)+CONTEXT_AFTER)],
                } for loc in occurrences[:MAX_MATCHES_PER_TOKEN]
            ],
        }
    return contexts


def event_handler_evidence(js: str):
    """Look only for plausible handler definitions, never infer an executed UI."""
    matches = list(re.finditer(
        r"[A-Za-z_$][A-Za-z_$0-9]*\.prototype\.eggColorChangedHandler=function\(",
        js,
    ))
    entries = []
    for m in matches[:4]:
        excerpt = js[m.start():min(len(js), m.start()+2800)]
        first_set = excerpt.find(".setColor(")
        entries.append({
            "method_definition_offset": m.start(),
            "has_setColor_within_2800_chars": first_set >= 0,
            "distance_to_setColor_chars": first_set if first_set >= 0 else None,
            "bounded_method_excerpt": excerpt[:1100],
        })
    return {
        "definition_count": len(matches),
        "bounded_definitions": entries,
        "setColor_within_handler_E1_possible": any(
            e["has_setColor_within_2800_chars"] for e in entries
        ),
        "runtime_callback_invocation_observed": False,
    }


def palette_sheet(engine: np.ndarray, captured: set, path: Path):
    columns, cell_w, cell_h = 16, 82, 67
    rows = 8
    image = Image.new("RGB", (columns*cell_w, rows*cell_h+32),
                      (244, 244, 244))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((12, 8), "STATIC ENGINE128 - * in screenshot32; NOT live UI proof",
              fill=(20, 20, 20), font=font)
    for i, rgb in enumerate(engine):
        col, row = i % columns, i // columns
        x, y = col*cell_w, row*cell_h+32
        v = tuple(int(a) for a in rgb)
        hexstr = "#%02X%02X%02X" % v
        draw.rectangle([x+2, y+2, x+cell_w-3, y+cell_h-3],
                       fill=v, outline=(70, 70, 70), width=1)
        bright = float(sum(v))/3.0 > 138
        text_color = (0, 0, 0) if bright else (255, 255, 255)
        draw.text((x+7, y+6), "%03d%s" % (i, "*" if hexstr in captured else ""),
                  fill=text_color, font=font)
        draw.text((x+7, y+46), hexstr, fill=text_color, font=font)
    image.save(path)


def run(engine_js: Path, screenshot_palette: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P3E_OUTPUT_EXISTS")
    engine, provenance = read_engine_palette(engine_js)  # P3B pinned parser.
    raw = screenshot_palette.read_bytes()
    screenshot = validate_screenshot_palette(raw, engine)
    raw_js = engine_js.read_bytes()
    if git_blob_sha(raw_js) != ENGINE_GIT_BLOB_SHA1:
        raise ValueError("BLOCKED_P3E_ENGINE_HASH_DRIFT")
    js = raw_js.decode("utf-8")
    contexts = token_contexts(js)
    event = event_handler_evidence(js)
    all_hex = ["#%02X%02X%02X" % tuple(int(v) for v in row) for row in engine]
    screenshot_set = {item["screenshot_rgb"] for item in screenshot}
    # Verify screenshot indexed subset is EXACT; do not equate it to all reachable colors.
    snapshot_indices = {e["engine128_index"] for e in screenshot}
    if (len(snapshot_indices) != 32 or
            not all(all_hex[k] in screenshot_set for k in snapshot_indices)
            or len(all_hex) != len(set(all_hex)) or
            all_hex[ENGINE_WHITE_INDEX] != "#FFFFFF"):
        raise AssertionError("BLOCKED_P3E_ENGINE128_SCREENSHOT32_INCONSISTENT")
    output.mkdir(parents=True)
    palette_sheet(engine, screenshot_set, output / "STATIC_ENGINE128_vs_SCREENSHOT32.png")
    (output / "STATIC_ENGINE128_SWATCHES.json").write_text(
        json.dumps([{"engine128_index": i, "rgb_hex": v,
                     "in_old_screenshot32": v in screenshot_set,
                     "runtime_selectable_E4": "UNKNOWN"}
                    for i, v in enumerate(all_hex)],
                   indent=2) + "\n", encoding="utf-8"
    )
    (output / "SCREENSHOT32_ENGINE128_INDEX_MAPPING.json").write_text(
        json.dumps(screenshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    (output / "BOUNDED_ENGINE_UI_ROUTING_EXCERPTS.json").write_text(
        json.dumps({"context_search": contexts, "event_handler": event},
                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "README_REVIEW_RU.txt").write_text(
        "ENGINE-001 B1-R-P3E: СТАТИЧЕСКАЯ проверка UI маршрутов и свотчей.\n"
        "STATIC_ENGINE128_vs_SCREENSHOT32.png — все 128 исходных RGB движка.\n"
        "* означает: RGB найден среди 32 старых скриншотных образцов, "
        "НЕ что он гарантированно выбирается в запущенной игре.\n"
        "BOUNDED_ENGINE_UI_ROUTING_EXCERPTS.json — короткие фрагменты JS "
        "без экспорта всего исходного минифицированного движка.\n"
        "SCREENSHOT32_ENGINE128_INDEX_MAPPING.json — старые координаты, "
        "НЕ использовать их в executor без нового live calibration.\n"
        "Игровая доступность 128 цветов и точный CHALK всё ещё UNKNOWN/NOT_RUN.\n",
        encoding="utf-8"
    )
    checks = {
        "pinned_engine_blob_provenance": True,
        "engine128_exact_unique_rgb": len(all_hex) == 128,
        "WHITE_engine_index_6": all_hex[6] == "#FFFFFF",
        "pinned_browser_palette_blob": git_blob_sha(raw) == SCREENSHOT_PALETTE_BLOB,
        "all_screenshot32_match_engine128_exact_rgb": len(screenshot) == 32,
        "extended_gate_token_present": contexts["extended_palette_gate"]["occurrence_count"] > 0,
        "old_new_palette_method_tokens_present": (
            contexts["popup_new_palette"]["occurrence_count"] > 0 and
            contexts["popup_old_palette"]["occurrence_count"] > 0),
        "color_icon_token_present": contexts["egg_color_icon"]["occurrence_count"] > 0,
        "color_handler_token_present": contexts["egg_color_event_handler"]["occurrence_count"] > 0,
        "board_setColor_token_present": contexts["board_set_color"]["occurrence_count"] > 0,
    }
    report = {
        "experiment": EXPERIMENT,
        "source_engine_git_blob_sha1": ENGINE_GIT_BLOB_SHA1,
        "source_engine_bytes": len(raw_js),
        "source_screenshot_json_git_blob_sha1": SCREENSHOT_PALETTE_BLOB,
        "source_screenshot_json_sha256": digest(raw),
        "source_screenshot_declared_capture_date": "2026-10-26",
        "source_screenshot_coordinates_current_executor_calibration": False,
        "all_engine_colors_static": 128,
        "screenshot32_source_matches": len(snapshot_indices),
        "engine_colors_not_in_screenshot32": 128-len(snapshot_indices),
        "original_method_128_same_as_old_P3B_pin": True,
        "checks": {k: bool(v) for k, v in checks.items()},
        "UI_js_token_occurrence_counts": {
            k: v["occurrence_count"] for k, v in contexts.items()
        },
        "UI_event_handler_definition_count": event["definition_count"],
        "UI_event_handler_setColor_E1_possible": event[
            "setColor_within_handler_E1_possible"],
        "condition_extended_eggs": "P3B regex confirms _isPainterExtend conditional",
        "all_128_colors_currently_clickable_in_live_game": "UNKNOWN_E4_NOT_RUN",
        "P3D_27_of_selected32_outside_screenshot32": "EARLIER_READONLY_ZIP_E1_DIAGNOSTIC_NOT_P3E_INPUT",
        "existing_128_to_actual_ui_position_mapping": None,
        "live_board_color_echo_and_calibration": "NOT_RUN",
        "native_game_egret_coverage_leakage": "NOT_RUN",
        "exact_game_CHALK": None,
        "production_promotion": False,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "file_sha256": {
            p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
            if p.is_file()
        },
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--engine-js", type=Path, required=True)
    p.add_argument("--screenshot-json", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    r = run(args.engine_js, args.screenshot_json, args.output)
    print("P3E_E1_ENGINE128_COLOR_COUNT", r["all_engine_colors_static"])
    print("P3E_E1_SCREENSHOT32_MATCHES", r["screenshot32_source_matches"])
    print("P3E_E1_HANDLER_DEFINITIONS",r["UI_event_handler_definition_count"])
    print("P3E_E1_POSSIBLE_SET_COLOR",r["UI_event_handler_setColor_E1_possible"])
    print("P3E_E1_STATIC_CHECKS",r["checks"])
    print("P3E_E1_TOKEN_COUNTS",r["UI_js_token_occurrence_counts"])
    print("RUNTIME_UI_CALIBRATION_E4_E5_CHALK_NOT_RUN")
