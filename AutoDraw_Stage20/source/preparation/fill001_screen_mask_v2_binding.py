from __future__ import annotations

"""FILL-001 V2 binding derived from the original same-run Monitor telemetry.

No estimated screenshot alignment, hand-entered desktop offsets, or fallback
to the browser window screenX is allowed. This only provides a diagnostic
binding; native Egret-vs-live comparison remains an independent E5 gate.
"""

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from chalk_fill_matrix import FillMatrixError
from fill001_screen_mask_v2 import project_screen_mask_v2


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _geometry_sha(geometry: dict) -> str:
    raw = json.dumps(
        geometry, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return _sha(raw)


def _load(path: str | Path) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise FillMatrixError("V2 provenance must be a JSON object.")
    return obj, _sha(raw)


def _number(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise FillMatrixError("V2 requires finite numeric coordinate samples.")
    return float(value)


def bind_from_monitor_run(
    run_path: str | Path,
    evidence_path: str | Path,
) -> dict[str, Any]:
    """Produce a verified V2 binding from one raw run and its E4 audit report.

    The offset is established from actual paired DOM mouse client/screen
    samples, not inferred from painted pixels or the frozen target shape.
    """
    run, run_sha = _load(run_path)
    evidence, evidence_sha = _load(evidence_path)
    run_id = run.get("run_id")
    checks = {
        "run_id_missing": not isinstance(run_id, str) or not run_id,
        "run_id_mismatch": run_id != evidence.get("run_id"),
        "raw_run_sha256_mismatch": run_sha != evidence.get("raw_run_sha256"),
        "e4_status_not_pass": evidence.get("status") != "PASS_E4_RAW_CAPTURE",
        "monitor_version_mismatch": evidence.get("monitor_version") != "0.2.4",
        "session_id_mismatch": run.get("session_id") != evidence.get("session_id"),
    }
    failed = [name for name, invalid in checks.items() if invalid]
    if failed:
        raise FillMatrixError("V2 run/evidence provenance failure: " + ", ".join(failed))
    g0, g1 = run.get("renderer_geometry_at_start"), run.get("renderer_geometry_at_end")
    if (not isinstance(g0, dict) or g0 != g1
            or run.get("renderer_geometry_updates") != []
            or _geometry_sha(g0) != evidence.get("geometry_at_start_sha256")
            or g0.get("boardLogicalSize") != {"width": 460, "height": 240}
            or g0.get("renderMode") != "webgl"):
        raise FillMatrixError("V2 same-run BoardPane geometry missing, changed, or unbound.")
    players = g0.get("players")
    if not isinstance(players, list) or len(players) != 1:
        raise FillMatrixError("V2 requires exactly one BoardPane player.")
    player = players[0]
    if player.get("boardClientMappingMethod") not in (
        "getBoxQuads_content", "validated_axis_aligned_rect"
    ):
        raise FillMatrixError("V2 client mapping has not been validated.")
    corners = player.get("boardClientCorners")
    if not isinstance(corners, dict):
        raise FillMatrixError("V2 requires actual same-run BoardPane client corners.")
    try:
        tl, tr, br, bl = (corners[k] for k in (
            "topLeft", "topRight", "bottomRight", "bottomLeft"))
        left, top = _number(tl["x"]), _number(tl["y"])
        right, bottom = _number(br["x"]), _number(br["y"])
        if any(abs(_number(p["y"]) - top) > 1e-5 for p in (tr,)) or any(
            abs(_number(p["x"]) - right) > 1e-5 for p in (tr,)
        ) or abs(_number(bl["x"]) - left) > 1e-5 or abs(
            _number(bl["y"]) - bottom
        ) > 1e-5 or right <= left or bottom <= top:
            raise FillMatrixError("V2 requires axis-aligned positive BoardPane bounds.")
    except (KeyError, TypeError) as exc:
        raise FillMatrixError("V2 invalid BoardPane corner coordinates.") from exc

    events = run.get("events")
    if not isinstance(events, list):
        raise FillMatrixError("V2 requires complete raw Monitor event list.")
    samples = [e for e in events if isinstance(e, dict) and
               e.get("type") == "MOUSE_MOVE_SAMPLE"]
    if len(samples) < 30 or len(samples) != evidence.get("mouse_move_count"):
        raise FillMatrixError("V2 lacks complete E4 mouse-move evidence.")
    offsets = []
    for e in samples:
        if e.get("source") != "window-bubble-after-egret-canvas":
            raise FillMatrixError("V2 mouse sample has an unsupported source.")
        offsets.append((
            _number(e.get("screenX")) - _number(e.get("clientX")),
            _number(e.get("screenY")) - _number(e.get("clientY")),
        ))
    offsets = np.asarray(offsets, dtype=np.float64)
    center = np.median(offsets, axis=0)
    max_residual = float(np.max(np.abs(offsets - center)))
    if max_residual > 1e-6:
        raise FillMatrixError("V2 desktop/client offset is not constant within the run.")

    roi = evidence.get("screen_roi")
    if not isinstance(roi, dict):
        raise FillMatrixError("V2 missing original same-run screen ROI.")
    geometry = {
        "run_id": run_id,
        "same_run": True,
        "coordinate_system": "desktop_screen_css_pixels",
        "validation_status": "valid",
        "independent_screen_mapping": True,
        "board_screen_corners": {
            "left": left + float(center[0]),
            "top": top + float(center[1]),
            "right": right + float(center[0]),
            "bottom": bottom + float(center[1]),
        },
        "evidence_sha256": run_sha,
    }
    # Check that the calculated mask is usable without adapting its shape.
    project_screen_mask_v2(
        "rectangle", run_id=run_id, screen_roi=roi, geometry=geometry
    )
    return {
        "screen_roi": roi,
        "geometry": geometry,
        "provenance": {
            "schema": "FILL001_SCREEN_MASK_V2_MONITOR_BINDING",
            "run_id": run_id,
            "raw_run_sha256": run_sha,
            "e4_evidence_sha256": evidence_sha,
            "native_geometry_sha256": _geometry_sha(g0),
            "mouse_sample_count": len(samples),
            "client_screen_offset_x": float(center[0]),
            "client_screen_offset_y": float(center[1]),
            "max_offset_residual_px": max_residual,
            "method": "same_run_board_client_corners_plus_DOM_screen_minus_client",
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Verified FILL-001 V2 run binding")
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--e4-audit", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FillMatrixError("V2 refuses to overwrite existing binding evidence.")
    binding = bind_from_monitor_run(args.run, args.e4_audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(binding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
