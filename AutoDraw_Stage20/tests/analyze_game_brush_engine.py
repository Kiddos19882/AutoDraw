from __future__ import annotations

"""Collect small, reproducible evidence snippets from the game's minified JS bundle.

This is a discovery tool, not a JavaScript parser. It never executes the game
bundle and does not claim that every textual match is part of brush rendering.
The report is used to locate real canvas/brush geometry code for manual review.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_ENGINE_PATH = "AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js"

PATTERNS: dict[str, str] = {
    "canvas_context": r"\.getContext\s*\(",
    "canvas_line_width": r"\.lineWidth\b",
    "canvas_line_cap": r"\.lineCap\b",
    "canvas_line_join": r"\.lineJoin\b",
    "canvas_begin_path": r"\.beginPath\s*\(",
    "canvas_move_to": r"\.moveTo\s*\(",
    "canvas_line_to": r"\.lineTo\s*\(",
    "canvas_arc": r"\.arc\s*\(",
    "canvas_ellipse": r"\.ellipse\s*\(",
    "canvas_stroke": r"\.stroke\s*\(",
    "canvas_scale": r"\.scale\s*\(",
    "canvas_transform": r"\.(?:setTransform|resetTransform|transform)\s*\(",
    "canvas_draw_image": r"\.drawImage\s*\(",
    "canvas_composite": r"\.globalCompositeOperation\b",
    "egret_line_style": r"\.lineStyle\s*\(",
    "egret_draw_circle": r"\.drawCircle\s*\(",
    "egret_draw_ellipse": r"\.drawEllipse\s*\(",
    "egret_curve_to": r"\.curveTo\s*\(",
    "egret_begin_fill": r"\.beginFill\s*\(",
    "egret_end_fill": r"\.endFill\s*\(",
    "egret_draw_rect": r"\.drawRect\s*\(",
    "brush_terms": r"brush|Brush|radius|thickness|lineWidth|lineCap|lineJoin|painterExtend|isPainterExtend",
    "board_terms": r"BoardPane|BoardItem|BoardCanvas|DrawingBoard|CanvasRenderingContext2D|BLACK_BOARD_WIDTH|BLACK_BOARD_HEIGHT|isPainterExtend|maxPoint",
    "board_dimensions": r"BLACK_BOARD_WIDTH|BLACK_BOARD_HEIGHT",
    "board_draw_input": r"BoardPane\.prototype\.(?:start|move|draw|paint|clear|add|finish|end|begin)|BoardPane\.BLACK_BOARD_(?:WIDTH|HEIGHT)",
    "point_quota_terms": r"maxPoints|max_points|pointCount|point_count|pointsLimit|pointLimit|maxPoint",
    "pointer_terms": r"pointerdown|pointermove|pointerup|mousedown|mousemove|mouseup|PointerEvent|TOUCH_BEGIN|TOUCH_MOVE|TOUCH_END",
}

MAX_SNIPPETS_PER_PATTERN = 12
CONTEXT_CHARS = 260


def read_git_file(git_ref: str, git_path: str) -> tuple[str, str]:
    command = ["git", "show", f"{git_ref}:{git_path}"]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Не удалось прочитать {git_ref}:{git_path}: {detail}")
    raw = result.stdout
    return raw.decode("utf-8", errors="replace"), hashlib.sha256(raw).hexdigest()


def collect_report(source: str, source_sha256: str, git_ref: str, git_path: str) -> dict[str, Any]:
    snippets: dict[str, list[dict[str, Any]]] = {}
    counts: dict[str, int] = {}
    for name, expression in PATTERNS.items():
        pattern = re.compile(expression)
        matches = list(pattern.finditer(source))
        counts[name] = len(matches)
        first_half = MAX_SNIPPETS_PER_PATTERN // 2
        selected_matches = matches[:first_half] + matches[-(MAX_SNIPPETS_PER_PATTERN - first_half):]
        selected = list({match.start(): match for match in selected_matches}.values())
        snippets[name] = [
            {
                "offset": match.start(),
                "excerpt": re.sub(
                    r"\s+",
                    " ",
                    source[max(0, match.start() - CONTEXT_CHARS):min(len(source), match.end() + CONTEXT_CHARS)],
                ),
            }
            for match in selected
        ]
    return {
        "schema_version": 1,
        "report_type": "autodraw_game_brush_engine_source_scan",
        "source": {
            "git_ref": git_ref,
            "git_path": git_path,
            "sha256": source_sha256,
            "bytes": len(source.encode("utf-8")),
        },
        "method": (
            "Text-only search in minified JavaScript; no code execution. Counts and snippets "
            "are discovery evidence, not a semantic proof that each match controls brush geometry."
        ),
        "pattern_counts": counts,
        "snippets": snippets,
        "next_review_questions": [
            "Where is the selected brush value converted into a Canvas width or geometric radius?",
            "Is the width expressed in logical board units, canvas backing-store pixels, or CSS pixels?",
            "Which scale/transform maps pointer coordinates into drawing coordinates?",
            "Are round caps/joins used, and does a click create a disk or only a zero-length path?",
            "Which exact operation records a point versus paints a pixel?",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan minified game JS for brush and canvas geometry evidence.")
    parser.add_argument("--git-ref", default="origin/master")
    parser.add_argument("--git-path", default=DEFAULT_ENGINE_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        source, source_sha256 = read_git_file(args.git_ref, args.git_path)
        report = collect_report(source, source_sha256, args.git_ref, args.git_path)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    print(f"Analyzed {report['source']['bytes']:,} bytes from {args.git_ref}:{args.git_path}")
    print(f"SHA-256: {source_sha256}")
    for name, count in report["pattern_counts"].items():
        print(f"{name}: {count}")
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
