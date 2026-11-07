from __future__ import annotations

"""Build a provenance-tracked candidate corpus from source images.

This tool reuses AutoDraw's Stage 12 image pipeline, Stage 8 monochrome
scanline planner, portable .autodraw project writer, palette quantizer and
color scanline planner. It never executes a drawing or contacts the game.
"""

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

_PREPARATION_ROOT = Path(__file__).resolve().parent
_SOURCE_ROOT = _PREPARATION_ROOT.parent
sys.path[:0] = [str(_PREPARATION_ROOT), str(_SOURCE_ROOT)]

from autodraw_project import create_project, open_project
from color_scanline import build_color_scanline_plan, save_color_scanline_plan
from image_processing import ProcessingSettings, load_rgb_image, process_image
from palette_quantization import quantize_image_to_palette
from stage8_optimizer import build_scanline_plan, save_plan

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
GENERATOR_VERSION = "1.0.0"


class CorpusGenerationError(ValueError):
    """Raised when an input cannot be converted into valid AutoDraw artifacts."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_name(value: str, fallback: str = "image") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return (cleaned or fallback)[:80]


def _load_palette(path: str | Path) -> tuple[list[dict[str, Any]], str]:
    palette_path = Path(path)
    try:
        document = json.loads(palette_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CorpusGenerationError(f"Не удалось прочитать JSON палитры '{palette_path}': {exc}") from exc
    colors = document.get("colors") if isinstance(document, dict) else document
    if not isinstance(colors, list) or not colors:
        raise CorpusGenerationError("Файл палитры должен содержать непустой массив colors.")
    # Both quantizer and color-plan builder validate RGB/HEX consistency.
    palette_hash = _sha256_json(colors)
    return colors, palette_hash


def _discover_images(input_dir: Path) -> list[Path]:
    if not input_dir.is_dir():
        raise CorpusGenerationError(f"Каталог исходных изображений не найден: {input_dir}")
    return sorted(
        (path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda path: path.relative_to(input_dir).as_posix().casefold(),
    )


def _family_for(path: Path, input_dir: Path, explicit_family: str | None) -> tuple[str, str]:
    if explicit_family and explicit_family.strip():
        return explicit_family.strip(), "cli_argument"
    relative_parent = path.relative_to(input_dir).parent
    if str(relative_parent) not in ("", "."):
        return relative_parent.as_posix(), "input_subdirectory"
    return "unclassified", "not_provided"


def generate_corpus(
    input_dir: str | Path,
    output_root: str | Path,
    *,
    palette_path: str | Path | None,
    canvas_width: int = 646,
    canvas_height: int = 323,
    fit_mode: str = "contain",
    row_step_px: int = 1,
    color_row_step_px: int = 1,
    threshold_mode: str = "otsu",
    threshold: int = 128,
    denoise_level: int = 0,
    brightness: int = 0,
    contrast: float = 1.0,
    family: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Generate one .autodraw project and optionally one color plan per unique image."""
    source_root = Path(input_dir).resolve()
    data_root = Path(output_root).resolve()
    if canvas_width < 1 or canvas_height < 1 or canvas_width * canvas_height > 40_000_000:
        raise CorpusGenerationError("Размер холста должен быть положительным и не превышать 40 млн пикселей.")
    if fit_mode not in {"contain", "cover", "stretch"}:
        raise CorpusGenerationError("fit_mode должен быть contain, cover или stretch.")
    if row_step_px < 1 or color_row_step_px < 1:
        raise CorpusGenerationError("Шаг строк должен быть не меньше 1.")
    if threshold_mode not in {"otsu", "manual"}:
        raise CorpusGenerationError("threshold_mode должен быть otsu или manual.")
    if not 0 <= threshold <= 255:
        raise CorpusGenerationError("Порог должен быть от 0 до 255.")
    if not -100 <= brightness <= 100:
        raise CorpusGenerationError("Яркость должна быть от -100 до 100.")
    if not 0.5 <= contrast <= 2.5:
        raise CorpusGenerationError("Контраст должен быть от 0.5 до 2.5.")
    if not 0 <= denoise_level <= 4:
        raise CorpusGenerationError("Denoise level должен быть от 0 до 4.")

    images = _discover_images(source_root)
    if not images:
        raise CorpusGenerationError(f"В каталоге нет поддерживаемых изображений: {source_root}")

    palette: list[dict[str, Any]] | None = None
    palette_hash: str | None = None
    if palette_path is not None:
        palette, palette_hash = _load_palette(palette_path)

    projects_dir = data_root / "projects" / "generated_validation_corpus"
    plans_dir = data_root / "results" / "color_scanline_plans" / "generated_validation_corpus"
    projects_dir.mkdir(parents=True, exist_ok=True)
    if palette is not None:
        plans_dir.mkdir(parents=True, exist_ok=True)

    settings = ProcessingSettings(
        brightness=brightness,
        contrast=contrast,
        denoise_level=denoise_level,
        threshold_mode=threshold_mode,  # type: ignore[arg-type]
        threshold=threshold,
    )
    records: list[dict[str, Any]] = []
    duplicates: list[dict[str, str]] = []
    seen_hashes: dict[str, str] = {}

    for source_path in images:
        relative_source = source_path.relative_to(source_root).as_posix()
        source_hash = _sha256_file(source_path)
        if source_hash in seen_hashes:
            duplicates.append({
                "source": relative_source,
                "duplicate_of": seen_hashes[source_hash],
                "source_sha256": source_hash,
            })
            continue
        seen_hashes[source_hash] = relative_source
        source_id = source_hash[:16]
        stem = _safe_name(source_path.stem)
        artifact_stem = f"{stem}-{source_id}"
        project_path = projects_dir / f"{artifact_stem}.autodraw"
        color_plan_path = plans_dir / f"{artifact_stem}.json"
        if not overwrite and (project_path.exists() or (palette is not None and color_plan_path.exists())):
            raise CorpusGenerationError(
                f"Артефакт уже существует для {relative_source}. Используйте --overwrite после проверки данных."
            )

        try:
            source_image = load_rgb_image(source_path)
            result = process_image(
                source_image,
                canvas_width,
                canvas_height,
                fit_mode,  # type: ignore[arg-type]
                None,
                settings,
            )
            # Stage 8 consumes a grayscale mask with dark foreground. The
            # thresholded result is already binary; 127 is the canonical split.
            drawing_plan = build_scanline_plan(
                result.binary_mask,
                row_step_px=row_step_px,
                threshold=127,
                foreground="dark",
            )
        except Exception as exc:
            raise CorpusGenerationError(f"Не удалось подготовить '{relative_source}': {exc}") from exc

        with tempfile.TemporaryDirectory(prefix="autodraw-corpus-") as temp_dir:
            temp = Path(temp_dir)
            mask_path = temp / "binary_mask.png"
            prepared_path = temp / "prepared_color.png"
            grayscale_path = temp / "grayscale.png"
            drawing_plan_path = temp / "drawing_plan.json"
            metadata_path = temp / "processing_metadata.json"
            result.binary_mask.save(mask_path, format="PNG")
            result.prepared_color.save(prepared_path, format="PNG")
            result.grayscale.save(grayscale_path, format="PNG")
            save_plan(drawing_plan_path, drawing_plan)
            metadata = {
                "schema_version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source_file": relative_source,
                "source_sha256": source_hash,
                "canvas": {"width": canvas_width, "height": canvas_height},
                "coordinate_system": "local_canvas_pixels",
                "fit_mode": fit_mode,
                "crop_box_original_pixels": None,
                "settings": {
                    "brightness": brightness,
                    "contrast": contrast,
                    "denoise_level": denoise_level,
                    "threshold_mode": threshold_mode,
                    "requested_threshold": threshold,
                    "threshold_used": result.threshold_used,
                },
                "binary_mask_convention": "black=dark_foreground_white=background",
                "outputs": {
                    "prepared_color": "prepared_color.png",
                    "grayscale": "grayscale.png",
                    "binary_mask": "binary_mask.png",
                },
                "generator": {
                    "name": "generate_validation_corpus",
                    "version": GENERATOR_VERSION,
                    "row_step_px": row_step_px,
                    "family": _family_for(source_path, source_root, family)[0],
                },
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
            try:
                create_project(
                    project_path,
                    source_path,
                    mask_path,
                    drawing_plan_path,
                    project_name=source_path.stem,
                    processing_metadata_path=metadata_path,
                    prepared_color_path=prepared_path,
                    grayscale_path=grayscale_path,
                    quality_threshold=127,
                    quality_foreground="dark",
                )
                # Re-open with the production reader: successful ZIP creation alone is insufficient.
                project_bundle = open_project(project_path)
                if project_bundle.canvas != (canvas_width, canvas_height):
                    raise CorpusGenerationError("Проверка созданного .autodraw вернула неожиданный размер холста.")
            except Exception as exc:
                project_path.unlink(missing_ok=True)
                raise CorpusGenerationError(f"Не удалось создать/проверить '{project_path.name}': {exc}") from exc

        color_stroke_count: int | None = None
        color_plan_hash: str | None = None
        if palette is not None:
            try:
                quantized = quantize_image_to_palette(result.prepared_color, palette)
                source_report = dict(quantized.report)
                source_report["palette_profile"] = {
                    "name": Path(palette_path).stem if palette_path else "provided_palette",
                    "file": Path(palette_path).name if palette_path else None,
                }
                color_plan = build_color_scanline_plan(
                    quantized.index_map,
                    palette,
                    source_report=source_report,
                    source_name=relative_source,
                    plan_name=f"{source_path.stem} — color scanline",
                    row_step_px=color_row_step_px,
                )
                save_color_scanline_plan(color_plan_path, color_plan)
                color_stroke_count = int(color_plan["summary"]["stroke_count"])
                color_plan_hash = _sha256_json(color_plan)
            except Exception as exc:
                project_path.unlink(missing_ok=True)
                color_plan_path.unlink(missing_ok=True)
                raise CorpusGenerationError(
                    f"Не удалось создать цветной scanline-план для '{relative_source}': {exc}"
                ) from exc

        family_label, family_source = _family_for(source_path, source_root, family)
        records.append({
            "plan_id": source_id,
            "independence_group_id": source_hash,
            "source": relative_source,
            "source_sha256": source_hash,
            "family_label": family_label,
            "family_label_source": family_source,
            "project_path": project_path.relative_to(data_root).as_posix(),
            "drawing_plan_stroke_count": int(len(drawing_plan["strokes"])),
            "drawing_plan_sha256": _sha256_json(drawing_plan),
            "color_plan_path": color_plan_path.relative_to(data_root).as_posix() if palette is not None else None,
            "color_plan_stroke_count": color_stroke_count,
            "color_plan_sha256": color_plan_hash,
            "canvas": {"width": canvas_width, "height": canvas_height},
            "fit_mode": fit_mode,
            "monochrome_row_step_px": row_step_px,
            "color_row_step_px": color_row_step_px if palette is not None else None,
            "palette_sha256": palette_hash,
            "protocol_eligibility": "candidate_only_not_assessed",
        })

    manifest = {
        "schema_version": 1,
        "generator": {"name": "generate_validation_corpus", "version": GENERATOR_VERSION},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_kind": "generated_candidate_corpus_from_source_images",
        "protocol_eligibility": "candidate_only_not_assessed",
        "warning": (
            "Эти артефакты являются кандидатами. Наличие генератора не доказывает "
            "репрезентативность production-популяции, независимость геометрий или пригодность "
            "для calibration/holdout. Проверить происхождение, семейства и дубликаты до split."
        ),
        "configuration": {
            "canvas": {"width": canvas_width, "height": canvas_height},
            "fit_mode": fit_mode,
            "row_step_px": row_step_px,
            "color_row_step_px": color_row_step_px if palette is not None else None,
            "threshold_mode": threshold_mode,
            "threshold": threshold,
            "brightness": brightness,
            "contrast": contrast,
            "denoise_level": denoise_level,
            "palette_sha256": palette_hash,
        },
        "unique_source_count": len(records),
        "duplicate_source_count": len(duplicates),
        "records": records,
        "duplicates": duplicates,
    }
    manifest_path = data_root / "results" / "generated_validation_corpus_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_manifest = manifest_path.with_suffix(".json.tmp")
    temp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_manifest.replace(manifest_path)
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Создать .autodraw и color_scanline_plans из каталога исходных изображений."
    )
    parser.add_argument("--input", required=True, help="Каталог с исходными PNG/JPG/BMP/WEBP/TIFF.")
    parser.add_argument("--output-root", default=str(_SOURCE_ROOT.parent / "data"), help="Корень data/ AutoDraw.")
    parser.add_argument("--palette", help="JSON палитры/профиля с массивом colors; обязателен для цветных планов.")
    parser.add_argument("--skip-color-plans", action="store_true", help="Создавать только .autodraw и DrawingPlan.")
    parser.add_argument("--canvas-width", type=int, default=646)
    parser.add_argument("--canvas-height", type=int, default=323)
    parser.add_argument("--fit-mode", choices=("contain", "cover", "stretch"), default="contain")
    parser.add_argument("--row-step", type=int, default=1, help="Шаг строк для Stage 8 DrawingPlan.")
    parser.add_argument("--color-row-step", type=int, default=1, help="Шаг строк для цветного scanline-плана.")
    parser.add_argument("--threshold-mode", choices=("otsu", "manual"), default="otsu")
    parser.add_argument("--threshold", type=int, default=128)
    parser.add_argument("--brightness", type=int, default=0)
    parser.add_argument("--contrast", type=float, default=1.0)
    parser.add_argument("--denoise-level", type=int, choices=range(5), default=0)
    parser.add_argument("--family", help="Общая метка семейства; иначе берётся имя подпапки или unclassified.")
    parser.add_argument("--overwrite", action="store_true", help="Разрешить замену совпадающих выходных артефактов.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.skip_color_plans and not args.palette:
        parser.error("Укажите --palette для создания color_scanline_plans или используйте --skip-color-plans.")
    try:
        manifest = generate_corpus(
            args.input,
            args.output_root,
            palette_path=None if args.skip_color_plans else args.palette,
            canvas_width=args.canvas_width,
            canvas_height=args.canvas_height,
            fit_mode=args.fit_mode,
            row_step_px=args.row_step,
            color_row_step_px=args.color_row_step,
            threshold_mode=args.threshold_mode,
            threshold=args.threshold,
            brightness=args.brightness,
            contrast=args.contrast,
            denoise_level=args.denoise_level,
            family=args.family,
            overwrite=args.overwrite,
        )
    except (CorpusGenerationError, OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Ошибка генерации корпуса: {exc}\n")
    print(json.dumps({
        "manifest": str(Path(args.output_root) / "results" / "generated_validation_corpus_manifest.json"),
        "unique_source_count": manifest["unique_source_count"],
        "duplicate_source_count": manifest["duplicate_source_count"],
        "projects": "data/projects/generated_validation_corpus/",
        "color_plans": (
            "data/results/color_scanline_plans/generated_validation_corpus/"
            if not args.skip_color_plans else None
        ),
        "protocol_eligibility": manifest["protocol_eligibility"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
