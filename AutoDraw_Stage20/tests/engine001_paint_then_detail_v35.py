#!/usr/bin/env python3
"""ENGINE-001/V35 experimental layer plan validation, NOT gameplay/brush acceptance.

Allows reusing the V34R stroke dictionaries unchanged while recording explicit
paint/detail ownership and sequence. No Stage6/production imports or side effects.
"""
from __future__ import annotations

from copy import deepcopy
import math

WIDTH_LIMITS = (1, 2, 3, 4, 8, 10, 15, 20, 30)
BOARD_SIZE = (460, 240)
PROBE_MAX_STROKES = 3000
PROBE_MAX_VERTICES = 5900
LAYER_ORDER = ("paint", "detail")


def _check_stroke(s: dict) -> None:
    if not isinstance(s, dict):
        raise ValueError("V35 stroke must be a dictionary")
    if not isinstance(s.get("strokeId"), str) or not s["strokeId"]:
        raise ValueError("V35 strokeId missing")
    w = s.get("width")
    if type(w) is not int or w not in WIDTH_LIMITS:
        raise ValueError("V35 stroke width is not in explicit native-probe set")
    rgb = s.get("colorRgb")
    if type(rgb) is not int or not 0 <= rgb <= 0xFFFFFF:
        raise ValueError("V35 stroke RGB invalid")
    points = s.get("points")
    if not isinstance(points, list) or not 2 <= len(points) <= 128:
        raise ValueError("V35 invalid accepted-point sequence length")
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("V35 invalid point")
        x, y = point.get("x"), point.get("y")
        if any(type(z) not in (int, float) or not math.isfinite(z) for z in (x, y)):
            raise ValueError("V35 non-finite or non-numeric logical coordinate")
        if not (0 <= x < BOARD_SIZE[0] and 0 <= y < BOARD_SIZE[1]):
            raise ValueError("V35 point outside logical board")
    if all(point["x"] == points[0]["x"] and point["y"] == points[0]["y"]
           for point in points[1:]):
        raise ValueError("V35 zero-length stroke not accepted by BoardPane")
    if "colorIndex" not in s or type(s["colorIndex"]) is not int:
        raise ValueError("V35 source color ownership missing")


def build_layered_native_plan(paint: list[dict], detail: list[dict],
                              max_strokes: int = PROBE_MAX_STROKES,
                              max_vertices: int = PROBE_MAX_VERTICES) -> dict:
    """Return immutable-by-copy ordered probe plan; no native quality claim.

    Both layers must contain actual executable-style stroke dictionaries.
    Candidates cannot be silently clipped at the resource cap.
    """
    if not isinstance(paint, list) or not isinstance(detail, list):
        raise ValueError("V35 layers must be lists")
    if not paint:
        raise ValueError("V35 paint layer cannot be empty")
    if type(max_strokes) is not int or type(max_vertices) is not int or min(
            max_strokes, max_vertices) <= 0:
        raise ValueError("V35 invalid resource caps")
    count = len(paint) + len(detail)
    vertices = sum(len(s.get("points", [])) if isinstance(s, dict) else 0
                   for s in paint + detail)
    if count > max_strokes or vertices > max_vertices:
        raise ValueError("V35 OVER_BUDGET; no silent truncation")
    seen = set()
    ordered = []
    for layer, strokes in (("paint", paint), ("detail", detail)):
        for s in strokes:
            _check_stroke(s)
            if s["strokeId"] in seen:
                raise ValueError("V35 duplicate strokeId across layers")
            seen.add(s["strokeId"])
            ordered.append({"layer": layer, "stroke": deepcopy(s)})
    assert len(ordered) == count
    if [entry["layer"] for entry in ordered] != (
            ["paint"] * len(paint) + ["detail"] * len(detail)):
        raise AssertionError("V35 layer ordering bug")
    return {
        "experiment": "ENGINE001_PAINT_THEN_DETAIL_V35",
        "sequence": list(LAYER_ORDER),
        "paint_strokes": len(paint),
        "detail_strokes": len(detail),
        "synthetic_vertices_NOT_CHALK": vertices,
        "strokes": ordered,
        "native_quality_status": "NOT_RUN",
        "exact_CHALK": None,
    }


def native_strokes(plan: dict) -> list[dict]:
    """Unwrap layer metadata in deterministic paint-first order."""
    entries = plan.get("strokes")
    if not isinstance(entries, list):
        raise ValueError("V35 missing layered strokes")
    layers = [entry.get("layer") for entry in entries]
    if layers != sorted(layers, key=LAYER_ORDER.index):
        raise ValueError("V35 paint/detail layer order reversed")
    return [deepcopy(entry["stroke"]) for entry in entries]
