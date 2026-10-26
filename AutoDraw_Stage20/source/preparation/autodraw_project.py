from __future__ import annotations

"""Portable .autodraw project format for the AutoDraw pipeline.

A project is a ZIP archive. It never extracts arbitrary archive paths when opening;
all members and integrity hashes are validated before their contents are exposed.
"""

import hashlib
import io
import json
import os
import re
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from PIL import Image, ImageOps

import stage9_quality

FORMAT_ID = "autodraw-project"
FORMAT_VERSION = 1
MAX_IMAGE_PIXELS = 40_000_000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
MAX_PLAN_JSON_BYTES = 100 * 1024 * 1024

REQUIRED_LOGICAL_FILES = {
    "source_image",
    "binary_mask",
    "processing_settings",
    "drawing_plan",
    "quality_report",
}
OPTIONAL_LOGICAL_FILES = {
    "prepared_color",
    "grayscale",
    "imported_quality_report",
}
ALLOWED_LOGICAL_FILES = REQUIRED_LOGICAL_FILES | OPTIONAL_LOGICAL_FILES

DEFAULT_EXECUTION_PROFILE: dict[str, float] = {
    "point_step_px": 2.0,
    "point_delay_ms": 10.0,
    "before_mouse_down_ms": 20.0,
    "after_mouse_up_ms": 20.0,
    "after_mouse_down_ms": 40.0,
    "before_mouse_up_ms": 50.0,
}


class ProjectFormatError(ValueError):
    """Raised when a project or one of its required assets is invalid."""


@dataclass(frozen=True)
class ProjectBundle:
    path: Path
    manifest: dict[str, Any]
    files: dict[str, bytes]

    @property
    def name(self) -> str:
        return str(self.manifest.get("project", {}).get("name", self.path.stem))

    @property
    def canvas(self) -> tuple[int, int]:
        canvas = self.manifest.get("canvas", {})
        return int(canvas.get("width", 0)), int(canvas.get("height", 0))

    def file_bytes(self, logical_name: str) -> bytes:
        member = self.manifest.get("files", {}).get(logical_name)
        if not member or member not in self.files:
            raise ProjectFormatError(f"В проекте отсутствует файл '{logical_name}'.")
        return self.files[member]

    def json_file(self, logical_name: str) -> dict[str, Any]:
        try:
            value = json.loads(self.file_bytes(logical_name).decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProjectFormatError(f"Файл проекта '{logical_name}' содержит некорректный JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ProjectFormatError(f"Файл проекта '{logical_name}' должен содержать JSON-объект.")
        return value


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_limited(path: str | Path, *, limit: int = MAX_MEMBER_BYTES) -> bytes:
    source = Path(path)
    try:
        size = source.stat().st_size
        if size > limit:
            raise ProjectFormatError(f"Файл '{source.name}' превышает лимит {limit // (1024 * 1024)} MiB.")
        data = source.read_bytes()
    except OSError as exc:
        raise ProjectFormatError(f"Не удалось прочитать '{source}': {exc}") from exc
    if len(data) > limit:
        raise ProjectFormatError(f"Файл '{source.name}' превышает допустимый размер.")
    return data


def _read_json_file(path: str | Path, label: str) -> dict[str, Any]:
    raw = _read_limited(path, limit=MAX_PLAN_JSON_BYTES)
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectFormatError(f"'{Path(path).name}' не является корректным JSON ({label}): {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectFormatError(f"'{Path(path).name}' должен содержать JSON-объект ({label}).")
    return value


def _image_info(data: bytes, label: str) -> tuple[int, int, str]:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            width, height = opened.size
            fmt = str(opened.format or "unknown").upper()
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise ProjectFormatError(
                    f"Изображение '{label}' имеет недопустимый размер {width}×{height}; "
                    f"лимит — {MAX_IMAGE_PIXELS:,} пикселей."
                )
            opened.verify()
        return width, height, fmt
    except ProjectFormatError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ProjectFormatError(f"Не удалось открыть изображение '{label}': {exc}") from exc


def _normalized_mask_png(data: bytes, label: str) -> tuple[bytes, int, int]:
    try:
        with Image.open(io.BytesIO(data)) as opened:
            image = ImageOps.exif_transpose(opened).convert("L")
            width, height = image.size
            if width < 1 or height < 1 or width * height > MAX_IMAGE_PIXELS:
                raise ProjectFormatError(
                    f"Маска '{label}' имеет недопустимый размер {width}×{height}; "
                    f"лимит — {MAX_IMAGE_PIXELS:,} пикселей."
                )
            output = io.BytesIO()
            image.save(output, format="PNG", optimize=False)
            return output.getvalue(), width, height
    except ProjectFormatError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ProjectFormatError(f"Не удалось открыть маску '{label}': {exc}") from exc


def _validate_plan(plan: dict[str, Any]) -> tuple[int, int]:
    # Deliberately enforce the shape consumed by Stage 6 DrawingPlan.from_dict,
    # rather than accepting the looser formats supported by the Stage 9 renderer.
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict) or "width" not in canvas or "height" not in canvas:
        raise ProjectFormatError("DrawingPlan должен содержать canvas.width и canvas.height для этапа 6.")
    try:
        raw_width, raw_height = canvas["width"], canvas["height"]
        width, height = int(raw_width), int(raw_height)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProjectFormatError("В DrawingPlan должны быть целые размеры canvas.width и canvas.height.") from exc
    if isinstance(raw_width, bool) or isinstance(raw_height, bool) or width != raw_width or height != raw_height:
        raise ProjectFormatError("Размеры DrawingPlan должны быть целыми числами.")
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise ProjectFormatError("Размеры DrawingPlan недопустимы.")
    if not isinstance(plan.get("strokes"), list):
        raise ProjectFormatError("В DrawingPlan отсутствует массив 'strokes'.")
    # Stage 6 DrawingPlan requires at least one Stroke, and each Stroke needs two points.
    if not plan["strokes"]:
        raise ProjectFormatError("DrawingPlan пуст: Stage 6 требует хотя бы один штрих.")
    for stroke_index, stroke in enumerate(plan["strokes"], start=1):
        if not isinstance(stroke, dict) or not isinstance(stroke.get("points"), list):
            raise ProjectFormatError(f"Штрих №{stroke_index} должен содержать массив points.")
        if not str(stroke.get("name", "")).strip():
            raise ProjectFormatError(f"У штриха №{stroke_index} отсутствует непустое имя, требуемое этапом 6.")
        if "closed" in stroke and not isinstance(stroke["closed"], bool):
            raise ProjectFormatError(f"Поле closed штриха №{stroke_index} должно быть логическим.")
        if "metadata" in stroke and not isinstance(stroke["metadata"], dict):
            raise ProjectFormatError(f"Поле metadata штриха №{stroke_index} должно быть объектом.")
        if len(stroke["points"]) < 2:
            raise ProjectFormatError(f"Штрих №{stroke_index} содержит меньше двух точек и не совместим со Stage 6.")
        if stroke.get("closed", False) and len(stroke["points"]) < 3:
            raise ProjectFormatError(f"Замкнутый штрих №{stroke_index} должен содержать не менее трёх точек.")
        for point_index, point in enumerate(stroke["points"], start=1):
            # Stage 6 Point.from_dict expects mapping objects with x and y keys.
            try:
                if not isinstance(point, dict):
                    raise ValueError
                x, y = float(point["x"]), float(point["y"])
            except (KeyError, TypeError, ValueError, OverflowError) as exc:
                raise ProjectFormatError(f"Некорректная точка {point_index} штриха №{stroke_index}; ожидаются x и y.") from exc
            import math
            if not math.isfinite(x) or not math.isfinite(y):
                raise ProjectFormatError(f"Точка {point_index} штриха №{stroke_index} содержит не конечные координаты.")
            # Stage 6 allows coordinates on the max edge (x == width, y == height).
            if x < 0 or y < 0 or x > width or y > height:
                raise ProjectFormatError(
                    f"Точка {point_index} штриха №{stroke_index} выходит за границы холста: ({x}, {y})."
                )
    try:
        int(plan.get("schema_version", 1))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProjectFormatError("schema_version DrawingPlan должен быть целым числом.") from exc
    return width, height


def _read_optional_json(path: str | Path | None, label: str) -> tuple[dict[str, Any] | None, bytes | None]:
    if path is None or not str(path).strip():
        return None, None
    parsed = _read_json_file(path, label)
    return parsed, json.dumps(parsed, ensure_ascii=False, indent=2).encode("utf-8")


def _build_processing_settings(
    stage3_metadata: dict[str, Any] | None,
    plan: dict[str, Any],
    quality_threshold: int,
    quality_foreground: str,
) -> dict[str, Any]:
    metadata = stage3_metadata or {}
    stage3_settings = metadata.get("settings") if isinstance(metadata.get("settings"), dict) else {}
    generation = plan.get("generation") if isinstance(plan.get("generation"), dict) else {}
    try:
        threshold_used = int(stage3_settings.get("threshold_used", stage3_settings.get("requested_threshold", 128)))
    except (TypeError, ValueError):
        threshold_used = 128
    image_processing = {
        "fit_mode": metadata.get("fit_mode", "unknown"),
        "crop_box_original_pixels": metadata.get("crop_box_original_pixels"),
        "brightness": stage3_settings.get("brightness", 0),
        "contrast": stage3_settings.get("contrast", 1.0),
        "denoise_level": stage3_settings.get("denoise_level", 0),
        "threshold_mode": stage3_settings.get("threshold_mode", "unknown"),
        "requested_threshold": stage3_settings.get("requested_threshold", stage3_settings.get("threshold", 128)),
        "threshold_used": threshold_used,
        "binary_mask_convention": metadata.get(
            "binary_mask_convention", "preserved grayscale mask; threshold/foreground are stored below"
        ),
    }
    return {
        "schema_version": 1,
        "created_at": _now_iso(),
        "image_processing": image_processing,
        "scanline": {
            "method": generation.get("method", "unknown"),
            "row_step_px": generation.get("row_step_px"),
            "threshold": generation.get("threshold", quality_threshold),
            "foreground": generation.get("foreground", quality_foreground),
            "max_strokes": generation.get("max_strokes"),
        },
        "quality_check": {
            "source_mask_threshold": quality_threshold,
            "source_mask_foreground": quality_foreground,
            "report_method": "recomputed from the bundled mask and drawing plan",
        },
        "execution_profile_defaults": dict(DEFAULT_EXECUTION_PROFILE),
        "source_stage3_processing_result": metadata or None,
        "notes": [
            "Сохранённые параметры описывают фактически выбранные настройки там, где они были доступны.",
            "execution_profile_defaults — справочные значения, а не доказательство настроек конкретного запуска.",
        ],
    }


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_basename(path: str | Path) -> str:
    name = Path(path).name
    return name if name not in ("", ".", "..") else "unnamed"


def create_project(
    output_path: str | Path,
    source_image_path: str | Path,
    mask_path: str | Path,
    drawing_plan_path: str | Path,
    *,
    project_name: str | None = None,
    processing_metadata_path: str | Path | None = None,
    imported_quality_report_path: str | Path | None = None,
    prepared_color_path: str | Path | None = None,
    grayscale_path: str | Path | None = None,
    quality_threshold: int | None = None,
    quality_foreground: str | None = None,
) -> Path:
    """Builds a single .autodraw archive and atomically replaces the destination."""
    output = Path(output_path)
    if output.suffix.lower() != ".autodraw":
        output = output.with_suffix(".autodraw")
    if source_image_path is None or mask_path is None or drawing_plan_path is None:
        raise ProjectFormatError("Нужны исходное изображение, бинарная маска и DrawingPlan JSON.")

    source_path = Path(source_image_path)
    mask_source = Path(mask_path)
    plan_source = Path(drawing_plan_path)
    source_bytes = _read_limited(source_path)
    source_width, source_height, source_format = _image_info(source_bytes, source_path.name)
    mask_raw = _read_limited(mask_source)
    mask_bytes, mask_width, mask_height = _normalized_mask_png(mask_raw, mask_source.name)
    plan = _read_json_file(plan_source, "DrawingPlan")
    canvas_width, canvas_height = _validate_plan(plan)
    if (canvas_width, canvas_height) != (mask_width, mask_height):
        raise ProjectFormatError(
            f"Размеры не совпадают: маска {mask_width}×{mask_height}, DrawingPlan {canvas_width}×{canvas_height}."
        )

    generation = plan.get("generation") if isinstance(plan.get("generation"), dict) else {}
    if quality_threshold is None:
        candidate = generation.get("threshold", 127)
        try:
            quality_threshold = int(candidate)
        except (TypeError, ValueError):
            quality_threshold = 127
    if not 0 <= quality_threshold <= 255:
        raise ProjectFormatError("Порог проверки качества должен быть в диапазоне 0–255.")
    if quality_foreground is None:
        candidate = generation.get("foreground", "dark")
        quality_foreground = candidate if candidate in ("dark", "light") else "dark"
    if quality_foreground not in ("dark", "light"):
        raise ProjectFormatError("foreground должен быть 'dark' или 'light'.")

    stage3_metadata, _ = _read_optional_json(processing_metadata_path, "Stage 3 processing metadata")
    imported_report, imported_report_bytes = _read_optional_json(imported_quality_report_path, "Stage 9 quality report")
    settings = _build_processing_settings(stage3_metadata, plan, quality_threshold, quality_foreground)

    # The canonical report is always recomputed from the files that will actually live in the project.
    try:
        with Image.open(io.BytesIO(mask_bytes)) as image:
            mask_image = image.convert("L")
            report, _, _, _ = stage9_quality.analyze_quality(
                mask_image, plan, threshold=quality_threshold, foreground=quality_foreground
            )
        quality_data = report.to_dict()
    except Exception as exc:
        raise ProjectFormatError(f"Не удалось пересчитать отчёт Stage 9 для этой маски и плана: {exc}") from exc

    entries: dict[str, bytes] = {}
    suffix = source_path.suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix or ""):
        suffix = ".img"
    entries[f"assets/source_image{suffix}"] = source_bytes
    entries["assets/binary_mask.png"] = mask_bytes
    entries["config/processing_settings.json"] = json.dumps(settings, ensure_ascii=False, indent=2).encode("utf-8")
    entries["plans/drawing_plan.json"] = json.dumps(plan, ensure_ascii=False, indent=2).encode("utf-8")
    entries["reports/quality_report.json"] = json.dumps(quality_data, ensure_ascii=False, indent=2).encode("utf-8")

    if prepared_color_path:
        prepared_bytes = _read_limited(prepared_color_path)
        prepared_w, prepared_h, _ = _image_info(prepared_bytes, Path(prepared_color_path).name)
        if (prepared_w, prepared_h) != (canvas_width, canvas_height):
            raise ProjectFormatError("Размер prepared_color не совпадает с размером холста.")
        with Image.open(io.BytesIO(prepared_bytes)) as image:
            rgb = image.convert("RGB")
            stream = io.BytesIO()
            rgb.save(stream, format="PNG")
            entries["assets/prepared_color.png"] = stream.getvalue()
    if grayscale_path:
        gray_bytes = _read_limited(grayscale_path)
        gray_w, gray_h, _ = _image_info(gray_bytes, Path(grayscale_path).name)
        if (gray_w, gray_h) != (canvas_width, canvas_height):
            raise ProjectFormatError("Размер grayscale не совпадает с размером холста.")
        with Image.open(io.BytesIO(gray_bytes)) as image:
            gray = image.convert("L")
            stream = io.BytesIO()
            gray.save(stream, format="PNG")
            entries["assets/grayscale.png"] = stream.getvalue()
    if imported_report_bytes is not None:
        entries["reports/imported_quality_report.json"] = imported_report_bytes

    files = {
        "source_image": next(name for name in entries if name.startswith("assets/source_image")),
        "binary_mask": "assets/binary_mask.png",
        "processing_settings": "config/processing_settings.json",
        "drawing_plan": "plans/drawing_plan.json",
        "quality_report": "reports/quality_report.json",
    }
    if "assets/prepared_color.png" in entries:
        files["prepared_color"] = "assets/prepared_color.png"
    if "assets/grayscale.png" in entries:
        files["grayscale"] = "assets/grayscale.png"
    if "reports/imported_quality_report.json" in entries:
        files["imported_quality_report"] = "reports/imported_quality_report.json"

    hashes = {name: _sha256(data) for name, data in entries.items()}
    sizes = {name: len(data) for name, data in entries.items()}
    total_size = sum(sizes.values())
    if total_size > MAX_TOTAL_UNCOMPRESSED_BYTES:
        raise ProjectFormatError(
            f"Суммарный размер файлов проекта превышает {MAX_TOTAL_UNCOMPRESSED_BYTES // (1024 * 1024)} MiB."
        )

    project = {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "project": {
            "name": (project_name or source_path.stem or "AutoDraw project").strip() or "AutoDraw project",
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        },
        "canvas": {"width": canvas_width, "height": canvas_height},
        "source": {
            "source_image_filename": _safe_basename(source_path),
            "source_image_format": source_format,
            "source_image_size": {"width": source_width, "height": source_height},
            "mask_source_filename": _safe_basename(mask_source),
            "drawing_plan_source_filename": _safe_basename(plan_source),
            "processing_metadata_source_filename": _safe_basename(processing_metadata_path) if processing_metadata_path else None,
            "imported_quality_report_source_filename": _safe_basename(imported_quality_report_path) if imported_quality_report_path else None,
        },
        "files": files,
        "sha256": hashes,
        "byte_sizes": sizes,
        "quality_report_provenance": "recomputed from the bundled binary mask and DrawingPlan",
        "compatibility": {"stage6_drawing_plan_json": True},
    }
    manifest_bytes = json.dumps(project, ensure_ascii=False, indent=2).encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as temporary:
            temp_path = Path(temporary.name)
        with zipfile.ZipFile(temp_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("project.json", manifest_bytes)
            for member, data in entries.items():
                archive.writestr(member, data)
        # Validate the archive before replacing any existing project.
        open_project(temp_path)
        os.replace(temp_path, output)
        temp_path = None
    except Exception:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return output


def _safe_archive_member(name: str) -> bool:
    if not name or "\\" in name or name.startswith("/"):
        return False
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return False
    return str(path) == name and not name.endswith("/")


def open_project(path: str | Path) -> ProjectBundle:
    source = Path(path)
    try:
        archive = zipfile.ZipFile(source, "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ProjectFormatError(f"Не удалось открыть проект '{source}': это не корректный ZIP-архив. {exc}") from exc

    with archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        if len(names) != len(set(names)):
            raise ProjectFormatError("Архив содержит повторяющиеся имена файлов.")
        if any(not _safe_archive_member(name) for name in names):
            raise ProjectFormatError("Архив содержит небезопасный путь к файлу.")
        if "project.json" not in names:
            raise ProjectFormatError("В архиве отсутствует project.json — это не проект AutoDraw.")
        total_uncompressed = 0
        for info in infos:
            if info.file_size > MAX_MEMBER_BYTES:
                raise ProjectFormatError(f"Файл '{info.filename}' превышает допустимый размер.")
            total_uncompressed += info.file_size
        if total_uncompressed > MAX_TOTAL_UNCOMPRESSED_BYTES:
            raise ProjectFormatError("Распакованный размер проекта превышает безопасный лимит.")
        try:
            manifest = json.loads(archive.read("project.json").decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
            raise ProjectFormatError(f"Некорректный project.json или повреждённый архив: {exc}") from exc
        if not isinstance(manifest, dict):
            raise ProjectFormatError("Корень project.json должен быть объектом.")
        if manifest.get("format") != FORMAT_ID:
            raise ProjectFormatError(f"Неизвестный формат проекта: {manifest.get('format')!r}.")
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ProjectFormatError(
                f"Версия формата {manifest.get('format_version')!r} не поддерживается; ожидается {FORMAT_VERSION}."
            )
        project_record = manifest.get("project")
        if not isinstance(project_record, dict) or not isinstance(project_record.get("name"), str):
            raise ProjectFormatError("В project.json отсутствует объект project с названием проекта.")
        if not isinstance(manifest.get("canvas"), dict):
            raise ProjectFormatError("В project.json отсутствует объект canvas.")
        files = manifest.get("files")
        hashes = manifest.get("sha256")
        sizes = manifest.get("byte_sizes")
        if not isinstance(files, dict) or not isinstance(hashes, dict) or not isinstance(sizes, dict):
            raise ProjectFormatError("В project.json отсутствуют files, sha256 или byte_sizes.")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in files.items()):
            raise ProjectFormatError("Все ключи и пути в files должны быть строками.")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in hashes.items()):
            raise ProjectFormatError("SHA-256 должны быть строками с именами файлов в качестве ключей.")
        if any(not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0
               for key, value in sizes.items()):
            raise ProjectFormatError("Размеры файлов в byte_sizes должны быть неотрицательными целыми числами.")
        if not REQUIRED_LOGICAL_FILES.issubset(files):
            missing = sorted(REQUIRED_LOGICAL_FILES - set(files))
            raise ProjectFormatError(f"В проекте отсутствуют обязательные записи файлов: {', '.join(missing)}.")
        if not set(files).issubset(ALLOWED_LOGICAL_FILES):
            raise ProjectFormatError("В project.json обнаружены неизвестные логические типы файлов.")
        member_names = set(names) - {"project.json"}
        if set(files.values()) != member_names:
            raise ProjectFormatError("Список files не совпадает с содержимым архива.")
        if set(hashes) != member_names or set(sizes) != member_names:
            raise ProjectFormatError("Контрольные суммы/размеры не совпадают со списком файлов.")
        if len(set(files.values())) != len(files):
            raise ProjectFormatError("Один файл архива привязан к нескольким логическим типам.")
        expected_members = {
            "binary_mask": "assets/binary_mask.png",
            "processing_settings": "config/processing_settings.json",
            "drawing_plan": "plans/drawing_plan.json",
            "quality_report": "reports/quality_report.json",
            "prepared_color": "assets/prepared_color.png",
            "grayscale": "assets/grayscale.png",
            "imported_quality_report": "reports/imported_quality_report.json",
        }
        for logical, member in files.items():
            if not _safe_archive_member(member):
                raise ProjectFormatError(f"Небезопасный путь в files['{logical}'].")
            if logical == "source_image":
                if not re.fullmatch(r"assets/source_image\.[a-z0-9]{1,10}", member):
                    raise ProjectFormatError("Недопустимый путь исходного изображения в project.json.")
            elif expected_members.get(logical) != member:
                raise ProjectFormatError(f"Недопустимый путь файла '{logical}' в project.json.")
        contents: dict[str, bytes] = {}
        for member in sorted(member_names):
            try:
                data = archive.read(member)
            except (OSError, zipfile.BadZipFile, KeyError, RuntimeError) as exc:
                raise ProjectFormatError(f"Не удалось прочитать '{member}': {exc}") from exc
            if len(data) != sizes.get(member):
                raise ProjectFormatError(f"Размер файла '{member}' не совпадает с project.json.")
            if not isinstance(hashes.get(member), str) or _sha256(data) != hashes[member]:
                raise ProjectFormatError(f"Контрольная сумма файла '{member}' не совпадает; файл повреждён или изменён.")
            contents[member] = data

    # Validate required content semantically after archive integrity has been established.
    by_logical = {logical: contents[member] for logical, member in files.items()}
    try:
        mask_bytes, mask_w, mask_h = _normalized_mask_png(by_logical["binary_mask"], "binary_mask.png")
        if mask_bytes != by_logical["binary_mask"]:
            # The archive should already carry canonical L-mode PNG data created by this module.
            # Decoding is enough for older valid archives; bytes are not silently modified here.
            pass
        plan = json.loads(by_logical["drawing_plan"].decode("utf-8-sig"))
        if not isinstance(plan, dict):
            raise ProjectFormatError("drawing_plan.json должен содержать JSON-объект.")
        plan_w, plan_h = _validate_plan(plan)
        if (plan_w, plan_h) != (mask_w, mask_h):
            raise ProjectFormatError("Размеры маски и DrawingPlan в проекте не совпадают.")
        settings = json.loads(by_logical["processing_settings"].decode("utf-8-sig"))
        report = json.loads(by_logical["quality_report"].decode("utf-8-sig"))
        if not isinstance(settings, dict) or not isinstance(report, dict):
            raise ProjectFormatError("processing_settings.json и quality_report.json должны быть JSON-объектами.")
        canvas = manifest.get("canvas")
        if not isinstance(canvas, dict) or int(canvas.get("width", 0)) != mask_w or int(canvas.get("height", 0)) != mask_h:
            raise ProjectFormatError("Размер холста в project.json не совпадает с маской.")
        for optional_name in ("prepared_color", "grayscale"):
            if optional_name in by_logical:
                optional_w, optional_h, _ = _image_info(by_logical[optional_name], files[optional_name])
                if (optional_w, optional_h) != (mask_w, mask_h):
                    raise ProjectFormatError(f"Размер {optional_name} не совпадает с холстом.")
        if "imported_quality_report" in by_logical:
            imported = json.loads(by_logical["imported_quality_report"].decode("utf-8-sig"))
            if not isinstance(imported, dict):
                raise ProjectFormatError("imported_quality_report.json должен содержать JSON-объект.")
    except ProjectFormatError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        raise ProjectFormatError(f"Содержимое проекта не прошло проверку: {exc}") from exc
    _image_info(by_logical["source_image"], files["source_image"])
    return ProjectBundle(source, manifest, contents)


def export_drawing_plan(project_path: str | Path, destination_path: str | Path) -> Path:
    """Exports the plan as standalone Stage 6-compatible JSON without rewriting it."""
    bundle = open_project(project_path)
    destination = Path(destination_path)
    if destination.suffix.lower() != ".json":
        destination = destination.with_suffix(".json")
    data = bundle.file_bytes("drawing_plan")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    # Confirm that the exported file is still readable by the project format validator.
    _validate_plan(_read_json_file(destination, "DrawingPlan export"))
    return destination


def extract_project(project_path: str | Path, destination_dir: str | Path, *, overwrite: bool = False) -> Path:
    """Extracts the project into a new folder using only validated relative member paths."""
    bundle = open_project(project_path)
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)
    for member, data in bundle.files.items():
        target = destination.joinpath(*PurePosixPath(member).parts)
        # Defense in depth in case this function changes in the future.
        if not _safe_archive_member(member) or not target.resolve().is_relative_to(destination.resolve()):
            raise ProjectFormatError(f"Небезопасный путь извлечения: {member}")
        if target.exists() and not overwrite:
            raise ProjectFormatError(f"Файл уже существует и не будет перезаписан: {target}")
    manifest_target = destination / "project.json"
    if manifest_target.exists() and not overwrite:
        raise ProjectFormatError(f"Файл уже существует и не будет перезаписан: {manifest_target}")
    for member, data in bundle.files.items():
        target = destination.joinpath(*PurePosixPath(member).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    manifest_target.write_text(json.dumps(bundle.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


def project_summary(bundle: ProjectBundle) -> str:
    manifest = bundle.manifest
    width, height = bundle.canvas
    lines = [
        f"Проект: {bundle.name}",
        f"Файл: {bundle.path}",
        f"Холст: {width} × {height} px",
        f"Версия формата: {manifest.get('format_version')}",
        f"Создан: {manifest.get('project', {}).get('created_at', 'не указано')}",
        "",
        "Содержимое:",
    ]
    for logical, member in manifest.get("files", {}).items():
        lines.append(f"  ✓ {logical}: {member}")
    plan = bundle.json_file("drawing_plan")
    lines.append(f"Штрихов: {len(plan.get('strokes', []))}")
    report = bundle.json_file("quality_report")
    if "f1_percent" in report:
        lines.append(f"F1 по пикселям: {float(report['f1_percent']):.2f}%")
        lines.append(f"Пропущено пикселей: {int(report.get('missing_pixels', 0))}")
        lines.append(f"Лишних пикселей: {int(report.get('extra_pixels', 0))}")
    return "\n".join(lines)
