from __future__ import annotations

"""Offline structural inventory for generated candidate DrawingPlans.

Not a predictor validation, CHALK estimator, or production eligibility gate.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any

from autodraw_project import open_project
from chalk_int006_validation import SHORT_LOOKUP, _normalize_manifest_strokes

AUDIT_VERSION = 1


def _within_root(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Путь выходит за каталог корпуса: {relative}")
    return path


def audit_corpus(manifest_path: str | Path) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("protocol_eligibility") != "candidate_only_not_assessed":
        raise ValueError("Ожидается только candidate-only corpus; этот аудит не является approval.")
    records = manifest.get("records")
    if not isinstance(records, list):
        raise ValueError("Manifest records должны быть массивом.")
    # Manifest is written to <output_root>/results/generated_validation_corpus_manifest.json.
    data_root = manifest_path.parent.parent
    accepted_lengths = {int(value) for value in SHORT_LOOKUP}
    summaries: list[dict[str, Any]] = []

    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Повреждённая запись manifest.")
        project_path = _within_root(data_root, record["project_path"])
        bundle = open_project(project_path)
        plan = bundle.json_file("drawing_plan")
        strokes = plan.get("strokes")
        if not isinstance(strokes, list):
            raise ValueError(f"Нет stroke list: {record['source']}")
        if len(strokes) != record["drawing_plan_stroke_count"]:
            raise ValueError(f"Несовпадение N manifest и DrawingPlan: {record['source']}")
        try:
            normalized = _normalize_manifest_strokes(strokes)
        except ValueError as exc:
            summaries.append({
                "source": record["source"],
                "monochrome_N": len(strokes),
                "schema_valid": False,
                "schema_error": str(exc),
                "predictor_domain_eligibility": "not_assessed",
                "protocol_eligibility": "candidate_only_not_assessed",
            })
            continue

        lengths = [
            math.hypot(float(s["points"][1][0]) - float(s["points"][0][0]),
                       float(s["points"][1][1]) - float(s["points"][0][1]))
            for s in normalized
        ]
        zero = sum(value <= 1e-9 for value in lengths)
        unknown_short = sum(
            1 for value in lengths
            if value > 1e-9 and value <= 10
            and not (abs(value - round(value)) < 1e-9
                     and round(value) in accepted_lengths)
        )
        horizontal = sum(
            s["points"][0][1] == s["points"][1][1] for s in normalized
        )
        summaries.append({
            "source": record["source"],
            "source_sha256": record["source_sha256"],
            "family_label": record["family_label"],
            "monochrome_N": len(strokes),
            "color_N": record.get("color_plan_stroke_count"),
            "schema_valid": True,
            "two_point_strokes": len(normalized),
            "horizontal_strokes": horizontal,
            "zero_length_strokes": zero,
            "short_lengths_outside_frozen_lookup": unknown_short,
            "min_length_px": min(lengths) if lengths else None,
            "max_length_px": max(lengths) if lengths else None,
            "predictor_domain_eligibility": "not_assessed",
            "protocol_eligibility": "candidate_only_not_assessed",
        })

    return {
        "schema_version": AUDIT_VERSION,
        "audit_type": "offline_candidate_geometry_inventory",
        "not_a_CHALK_measurement": True,
        "predictor_domain_eligibility": "not_assessed",
        "production_eligibility": "not_validated",
        "schema_valid_records": sum(bool(item["schema_valid"]) for item in summaries),
        "schema_invalid_records": sum(not item["schema_valid"] for item in summaries),
        "source_count": len(summaries),
        "records": summaries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline-аудит схемы кандидатного корпуса.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = audit_corpus(args.manifest)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "source_count": report["source_count"],
        "schema_valid_records": report["schema_valid_records"],
        "schema_invalid_records": report["schema_invalid_records"],
        "predictor_domain_eligibility": report["predictor_domain_eligibility"],
        "output": str(output),
    }, ensure_ascii=False))
    return 1 if report["schema_invalid_records"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
