from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from PIL import Image

from palette_detection import (
    PaletteFormatError,
    create_palette_document,
    parse_hex_color,
    rgb_to_hex,
    sample_color_at,
    validate_palette_document,
)

PROFILE_SCHEMA_VERSION = 1
PROFILE_STATUSES = {"detected", "confirmed", "corrected"}


class PaletteProfileError(ValueError):
    """A saved browser palette profile is malformed or unsupported."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _status_for_source(source: str) -> str:
    source = str(source).strip().lower()
    if source in {"manual-edit", "corrected"}:
        return "corrected"
    if source == "confirmed":
        return "confirmed"
    # A manually sampled swatch has better provenance than an auto candidate,
    # but it is not marked confirmed until the user explicitly confirms it.
    return "detected"


def _to_int(value: Any, field: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool):
        raise PaletteProfileError(f"{field} должен быть целым числом.")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise PaletteProfileError(f"{field} должен быть целым числом.") from exc
    if result < minimum or (maximum is not None and result > maximum):
        if maximum is None:
            expected = f"не меньше {minimum}"
        else:
            expected = f"от {minimum} до {maximum}"
        raise PaletteProfileError(f"{field} должен быть {expected}.")
    return result


def get_windows_scale_percent(default: int = 100) -> int:
    """Read Windows display scaling when available; otherwise use the supplied default."""
    if os.name != "nt":
        return int(default)
    try:
        import ctypes
        # SHCore is available on supported Windows versions and reports the
        # configured display scale independently of current window geometry.
        scale = int(ctypes.windll.shcore.GetScaleFactorForDevice(0))
        if 50 <= scale <= 300:
            return scale
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    try:
        import ctypes
        dpi = int(ctypes.windll.user32.GetDpiForSystem())
        scale = round(dpi * 100 / 96)
        if 50 <= scale <= 300:
            return scale
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return int(default)


def create_palette_profile(
    palette_document: dict[str, Any],
    profile_name: str,
    *,
    browser_label: str = "",
    dpi_scale_percent: int = 100,
    notes: str = "",
    previous_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a named, versioned profile using a Stage 16 palette document."""
    palette = validate_palette_document(palette_document)
    name = str(profile_name).strip()
    if not name:
        raise PaletteProfileError("Укажите имя профиля палитры.")
    scale = _to_int(dpi_scale_percent, "Масштаб Windows", minimum=50, maximum=300)
    previous = validate_palette_profile(previous_profile) if previous_profile else None
    now = _now()
    colors: list[dict[str, Any]] = []
    previous_by_hex = {item["hex"]: item for item in previous["colors"]} if previous else {}
    for item in palette["colors"]:
        old = previous_by_hex.get(item["hex"])
        # Keep identity/status when the user saves changes to the same named profile.
        color_id = old["id"] if old else str(uuid.uuid4())
        status = old["status"] if old else _status_for_source(item.get("source", "auto"))
        source = str(item.get("source", "manual"))
        if source == "manual-edit":
            status = "corrected"
        colors.append({
            "id": color_id,
            "name": str(item.get("name") or f"Цвет {len(colors) + 1}"),
            "hex": item["hex"],
            "rgb": list(item["rgb"]),
            "screen_x": item["screen_x"],
            "screen_y": item["screen_y"],
            "local_x": item["local_x"],
            "local_y": item["local_y"],
            "source": source,
            "status": status,
        })
    palette_metadata = palette.get("metadata") if isinstance(palette.get("metadata"), dict) else {}
    calibration = {
        "dpi_scale_percent": scale,
        "browser_label": str(browser_label).strip(),
        "notes": str(notes).strip(),
        "captured_at": str(palette_metadata.get("captured_at") or palette.get("created_at", now)),
        "capture_method": str(palette_metadata.get("method", "screenshot-assisted")),
    }
    return validate_palette_profile({
        "profile_schema_version": PROFILE_SCHEMA_VERSION,
        "profile_name": name,
        "created_at": previous["created_at"] if previous else now,
        "updated_at": now,
        "screen": palette["screen"],
        "region": palette["region"],
        "colors": colors,
        "calibration": calibration,
        "metadata": palette.get("metadata", {}),
    })


def validate_palette_profile(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise PaletteProfileError("Корневой элемент профиля должен быть объектом JSON.")
    # Read a Stage 16 palette JSON as an importable legacy profile.
    if "profile_schema_version" not in document and document.get("schema_version") == 1:
        legacy_metadata = document.get("metadata")
        if not isinstance(legacy_metadata, dict):
            legacy_metadata = {}
        try:
            return create_palette_profile(
                document,
                str(legacy_metadata.get("profile_name") or "Импортированный профиль"),
                browser_label=str(legacy_metadata.get("browser_label") or ""),
                dpi_scale_percent=int(legacy_metadata.get("dpi_scale_percent", 100)),
                notes="Импортировано из формата палитры этапа 16.",
            )
        except (ValueError, TypeError, AttributeError) as exc:
            raise PaletteProfileError(f"Не удалось импортировать палитру этапа 16: {exc}") from exc

    if document.get("profile_schema_version") != PROFILE_SCHEMA_VERSION:
        raise PaletteProfileError(
            f"Неподдерживаемая версия профиля палитры: {document.get('profile_schema_version')!r}."
        )
    profile_name = str(document.get("profile_name") or "").strip()
    if not profile_name:
        raise PaletteProfileError("Имя профиля не может быть пустым.")
    calibration = document.get("calibration")
    if not isinstance(calibration, dict):
        raise PaletteProfileError("calibration должен быть объектом JSON.")
    try:
        scale = _to_int(calibration.get("dpi_scale_percent", 100), "Масштаб Windows", minimum=50, maximum=300)
        base_palette = validate_palette_document({
            "schema_version": 1,
            "created_at": document.get("created_at") or _now(),
            "screen": document.get("screen"),
            "region": document.get("region"),
            "colors": [
                {key: value for key, value in item.items() if key not in {"id", "status"}}
                for item in document.get("colors", [])
            ],
            "metadata": document.get("metadata") or {},
        })
    except (PaletteFormatError, AttributeError, TypeError, ValueError) as exc:
        raise PaletteProfileError(f"Некорректные данные палитры в профиле: {exc}") from exc

    raw_colors = document.get("colors")
    if not isinstance(raw_colors, list) or len(raw_colors) != len(base_palette["colors"]):
        raise PaletteProfileError("colors должен быть массивом корректных цветов.")
    colors: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, (raw, base) in enumerate(zip(raw_colors, base_palette["colors"]), start=1):
        color_id = str(raw.get("id") or uuid.uuid4())
        if color_id in seen_ids:
            raise PaletteProfileError(f"Идентификатор цвета №{index} повторяется.")
        seen_ids.add(color_id)
        status = str(raw.get("status") or _status_for_source(base["source"]))
        if status not in PROFILE_STATUSES:
            raise PaletteProfileError(f"Недопустимый статус цвета №{index}: {status!r}.")
        colors.append({**base, "id": color_id, "status": status})

    updated_at = str(document.get("updated_at") or document.get("created_at") or _now())
    created_at = str(document.get("created_at") or updated_at)
    return {
        "profile_schema_version": PROFILE_SCHEMA_VERSION,
        "profile_name": profile_name,
        "created_at": created_at,
        "updated_at": updated_at,
        "screen": base_palette["screen"],
        "region": base_palette["region"],
        "colors": colors,
        "calibration": {
            "dpi_scale_percent": scale,
            "browser_label": str(calibration.get("browser_label") or "").strip(),
            "notes": str(calibration.get("notes") or "").strip(),
            "captured_at": str(calibration.get("captured_at") or created_at),
            "capture_method": str(calibration.get("capture_method") or "screenshot-assisted"),
        },
        "metadata": dict(document.get("metadata") or {}),
    }


def palette_document_from_profile(document: dict[str, Any]) -> dict[str, Any]:
    """Export the profile's colors/coordinates back to the Stage 16 JSON shape."""
    profile = validate_palette_profile(document)
    return create_palette_document(
        [{key: value for key, value in item.items() if key not in {"id", "status"}}
         for item in profile["colors"]],
        screen_size=(profile["screen"]["width"], profile["screen"]["height"]),
        region=profile["region"],
        metadata={
            **profile["metadata"],
            "profile_name": profile["profile_name"],
            "browser_label": profile["calibration"]["browser_label"],
            "dpi_scale_percent": profile["calibration"]["dpi_scale_percent"],
        },
    )


def save_palette_profile(path: str | Path, document: dict[str, Any]) -> Path:
    """Validate and atomically save a named palette profile."""
    target = Path(path).resolve()
    normalized = validate_palette_profile(document)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(normalized, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(tmp).replace(target)
    except Exception:
        try:
            Path(tmp).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def load_palette_profile(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            raw = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise PaletteProfileError(f"Не удалось прочитать профиль палитры: {exc}") from exc
    return validate_palette_profile(raw)


def check_profile_freshness(
    document: dict[str, Any],
    *,
    current_screen_size: tuple[int, int] | None,
    current_region: dict[str, int] | None = None,
    current_dpi_scale_percent: int | None = None,
    observed_colors: dict[str, Iterable[int]] | None = None,
    rgb_tolerance: int = 16,
) -> dict[str, Any]:
    """Compare a profile with current capture conditions; never changes coordinates silently."""
    profile = validate_palette_profile(document)
    issues: list[str] = []
    warnings: list[str] = []
    if current_screen_size is None:
        warnings.append("Разрешение экрана не проверено.")
    else:
        try:
            actual_size = tuple(int(v) for v in current_screen_size)
        except (TypeError, ValueError) as exc:
            raise PaletteProfileError("Текущее разрешение экрана задано некорректно.") from exc
        if len(actual_size) != 2 or any(value <= 0 for value in actual_size):
            raise PaletteProfileError("Текущее разрешение экрана должно содержать ширину и высоту больше нуля.")
        if actual_size != (profile["screen"]["width"], profile["screen"]["height"]):
            issues.append(
                f"Разрешение изменилось: сохранено {profile['screen']['width']}×{profile['screen']['height']}, "
                f"сейчас {actual_size[0]}×{actual_size[1]}."
            )
    if current_region is None:
        warnings.append("Положение и размеры палитры в браузере не проверены.")
    else:
        expected = profile["region"]
        normalized_region = {key: int(current_region[key]) for key in ("x", "y", "width", "height")}
        if normalized_region != expected:
            issues.append(
                "Область палитры переместилась или изменила размер: "
                f"сохранено ({expected['x']}, {expected['y']}, {expected['width']}×{expected['height']}), "
                f"сейчас ({normalized_region['x']}, {normalized_region['y']}, "
                f"{normalized_region['width']}×{normalized_region['height']})."
            )
    saved_scale = profile["calibration"]["dpi_scale_percent"]
    if current_dpi_scale_percent is None:
        warnings.append(f"Масштаб Windows не перепроверен (в профиле {saved_scale}%).")
    elif _to_int(current_dpi_scale_percent, "Текущий масштаб Windows", minimum=50, maximum=300) != saved_scale:
        issues.append(f"Масштаб Windows изменился: сохранено {saved_scale}%, сейчас {current_dpi_scale_percent}%.")
    if observed_colors is None:
        warnings.append("Фактические цвета образцов на новом снимке не проверены.")
    else:
        for color in profile["colors"]:
            observed = observed_colors.get(color["id"])
            if observed is None:
                warnings.append(f"Не удалось повторно считать образец {color['name']} ({color['hex']}).")
                continue
            values = tuple(int(v) for v in observed)
            if len(values) != 3 or any(v < 0 or v > 255 for v in values):
                issues.append(f"Для образца {color['name']} получены некорректные RGB-данные.")
                continue
            deltas = [abs(values[i] - color["rgb"][i]) for i in range(3)]
            if max(deltas) > rgb_tolerance:
                issues.append(
                    f"Цвет образца {color['name']} изменился: сохранено {color['hex']}, "
                    f"на снимке {rgb_to_hex(values)}."
                )
    status = "stale" if issues else ("unverified" if warnings else "current")
    return {"status": status, "issues": issues, "warnings": warnings}


def sample_profile_colors(
    document: dict[str, Any],
    region_image: Image.Image,
    *,
    rgb_tolerance: int = 16,
) -> dict[str, Any]:
    """Sample saved local positions in a freshly captured, selected palette region."""
    profile = validate_palette_profile(document)
    observed: dict[str, tuple[int, int, int]] = {}
    unavailable: list[str] = []
    for color in profile["colors"]:
        x, y = color["local_x"], color["local_y"]
        if x >= region_image.width or y >= region_image.height:
            unavailable.append(color["id"])
            continue
        observed[color["id"]] = sample_color_at(region_image, x, y, radius=2)
    mismatches: list[str] = []
    for color in profile["colors"]:
        current = observed.get(color["id"])
        if current and max(abs(current[i] - color["rgb"][i]) for i in range(3)) > rgb_tolerance:
            mismatches.append(color["id"])
    return {"observed_colors": observed, "unavailable_color_ids": unavailable, "mismatched_color_ids": mismatches}

def check_profile_against_screenshot(
    document: dict[str, Any],
    screenshot: Image.Image,
    *,
    current_dpi_scale_percent: int | None = None,
    rgb_tolerance: int = 16,
) -> dict[str, Any]:
    """Validate a profile using its saved screen rectangle; no manual reselection required.

    The profile stores the palette rectangle in desktop coordinates and each swatch
    position relative to that rectangle. On a fresh screenshot, we crop exactly that
    saved rectangle and sample all stored swatch positions. If the browser/palette moved,
    the sampled colors usually differ and the profile is marked stale.
    """
    profile = validate_palette_profile(document)
    if not isinstance(screenshot, Image.Image):
        raise PaletteProfileError("Для проверки калибровки нужен снимок экрана PIL.Image.")

    region = profile["region"]
    width, height = screenshot.size
    left, top = int(region["x"]), int(region["y"])
    region_width, region_height = int(region["width"]), int(region["height"])

    # Check global screen conditions first. The expected region is intentionally reused
    # from the profile: asking the user to redraw it would reintroduce inconsistent bounds.
    if (left < 0 or top < 0 or region_width <= 0 or region_height <= 0
            or left + region_width > width or top + region_height > height):
        result = check_profile_freshness(
            profile,
            current_screen_size=(width, height),
            current_region=region,
            current_dpi_scale_percent=current_dpi_scale_percent,
            observed_colors={},
            rgb_tolerance=rgb_tolerance,
        )
        result["issues"].append(
            "Сохранённая область палитры выходит за границы текущего экрана: "
            f"область ({left}, {top}, {region_width}×{region_height}), экран {width}×{height}. "
            "Обновите экранную область в профиле."
        )
        result["status"] = "stale"
        return result

    region_image = screenshot.crop((left, top, left + region_width, top + region_height)).convert("RGB")
    samples = sample_profile_colors(profile, region_image, rgb_tolerance=rgb_tolerance)
    result = check_profile_freshness(
        profile,
        current_screen_size=(width, height),
        current_region=region,
        current_dpi_scale_percent=current_dpi_scale_percent,
        observed_colors=samples["observed_colors"],
        rgb_tolerance=rgb_tolerance,
    )
    unavailable = samples["unavailable_color_ids"]
    if unavailable:
        names = {item["id"]: item["name"] for item in profile["colors"]}
        result["issues"].append(
            "Не удалось проверить координаты цветов: "
            + ", ".join(names.get(color_id, color_id) for color_id in unavailable)
            + ". Обновите профиль палитры."
        )
    # A duplicate color elsewhere on the desktop is not proof of a correct pick area,
    # but any known mismatch must always result in a stale status.
    if result["issues"]:
        result["status"] = "stale"
    return result

