from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

PROFILE_SCHEMA_VERSION = 1
FIT_MODES = {"contain", "cover", "stretch"}
THRESHOLD_MODES = {"otsu", "manual"}

DEFAULT_EXECUTION_SETTINGS: dict[str, int | float] = {
    "point_step_px": 2.0,
    "point_delay_ms": 10,
    "after_mouse_up_ms": 20,
    "before_mouse_down_ms": 20,
    "after_mouse_down_ms": 40,
    "end_hold_ms": 50,
    "countdown_seconds": 5,
}


class ProfileValidationError(ValueError):
    """Raised when a profile cannot be safely used or exported."""


def _int_field(data: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ProfileValidationError(f"Поле '{key}' должно быть целым числом.")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProfileValidationError(f"Поле '{key}' должно быть целым числом.") from exc
    if parsed < low or parsed > high:
        raise ProfileValidationError(f"Поле '{key}' должно быть в диапазоне {low}–{high}.")
    return parsed


def _float_field(data: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ProfileValidationError(f"Поле '{key}' должно быть числом.")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProfileValidationError(f"Поле '{key}' должно быть числом.") from exc
    if not (low <= parsed <= high):
        raise ProfileValidationError(f"Поле '{key}' должно быть в диапазоне {low}–{high}.")
    return round(parsed, 4)


@dataclass(frozen=True, slots=True)
class ScreenArea:
    x: int
    y: int
    width: int
    height: int
    screen_width: int | None = None
    screen_height: int | None = None

    def validate(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ProfileValidationError("Экранные координаты X и Y не могут быть отрицательными.")
        if not (50 <= self.width <= 32768 and 50 <= self.height <= 32768):
            raise ProfileValidationError("Размер экранной области должен находиться в диапазоне 50–32768 px.")
        if (self.screen_width is None) != (self.screen_height is None):
            raise ProfileValidationError("Размер экрана нужно указать одновременно по ширине и высоте.")
        if self.screen_width is not None and self.screen_height is not None:
            if not (1 <= self.screen_width <= 65536 and 1 <= self.screen_height <= 65536):
                raise ProfileValidationError("Размер экрана вне допустимого диапазона.")
            if self.x + self.width > self.screen_width or self.y + self.height > self.screen_height:
                raise ProfileValidationError("Экранная область выходит за пределы сохранённого разрешения.")

    def to_dict(self) -> dict[str, int]:
        result = {"x": self.x, "y": self.y, "width": self.width, "height": self.height}
        if self.screen_width is not None and self.screen_height is not None:
            result["screen_width"] = self.screen_width
            result["screen_height"] = self.screen_height
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScreenArea":
        if not isinstance(data, dict):
            raise ProfileValidationError("Экранная область должна быть JSON-объектом.")
        area = cls(
            x=_int_field(data, "x", 0, 0, 65535),
            y=_int_field(data, "y", 0, 0, 65535),
            width=_int_field(data, "width", 646, 50, 32768),
            height=_int_field(data, "height", 323, 50, 32768),
            screen_width=_optional_int(data, "screen_width", 1, 65536),
            screen_height=_optional_int(data, "screen_height", 1, 65536),
        )
        area.validate()
        return area


@dataclass(frozen=True, slots=True)
class CalibrationSettings:
    point_step_px: float = 2.0
    point_delay_ms: int = 10
    after_mouse_up_ms: int = 20
    before_mouse_down_ms: int = 20
    after_mouse_down_ms: int = 40
    end_hold_ms: int = 50
    countdown_seconds: int = 5

    def validate(self) -> None:
        if not (0.5 <= self.point_step_px <= 20):
            raise ProfileValidationError("Шаг точек должен быть в диапазоне 0.5–20 px.")
        for key, value in (
            ("Задержка точки", self.point_delay_ms),
            ("Пауза после mouseUp", self.after_mouse_up_ms),
            ("Пауза перед mouseDown", self.before_mouse_down_ms),
            ("Пауза после mouseDown", self.after_mouse_down_ms),
            ("Удержание в конце штриха", self.end_hold_ms),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise ProfileValidationError(f"{key}: нужно целое число миллисекунд.")
        if not 0 <= self.point_delay_ms <= 100:
            raise ProfileValidationError("Задержка точки должна быть в диапазоне 0–100 мс.")
        for value in (self.after_mouse_up_ms, self.before_mouse_down_ms, self.after_mouse_down_ms, self.end_hold_ms):
            if not 0 <= value <= 500:
                raise ProfileValidationError("Паузы и удержание должны быть в диапазоне 0–500 мс.")
        if not isinstance(self.countdown_seconds, int) or isinstance(self.countdown_seconds, bool) or not 1 <= self.countdown_seconds <= 30:
            raise ProfileValidationError("Обратный отсчёт должен быть в диапазоне 1–30 секунд.")

    def to_dict(self) -> dict[str, int | float]:
        return {
            "point_step_px": self.point_step_px,
            "point_delay_ms": self.point_delay_ms,
            "after_mouse_up_ms": self.after_mouse_up_ms,
            "before_mouse_down_ms": self.before_mouse_down_ms,
            "after_mouse_down_ms": self.after_mouse_down_ms,
            "end_hold_ms": self.end_hold_ms,
            "countdown_seconds": self.countdown_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CalibrationSettings":
        data = data or {}
        if not isinstance(data, dict):
            raise ProfileValidationError("Настройки калибровки должны быть JSON-объектом.")
        result = cls(
            point_step_px=_float_field(data, "point_step_px", 2.0, 0.5, 20),
            point_delay_ms=_int_field(data, "point_delay_ms", 10, 0, 100),
            after_mouse_up_ms=_int_field(data, "after_mouse_up_ms", 20, 0, 500),
            before_mouse_down_ms=_int_field(data, "before_mouse_down_ms", 20, 0, 500),
            after_mouse_down_ms=_int_field(data, "after_mouse_down_ms", 40, 0, 500),
            end_hold_ms=_int_field(data, "end_hold_ms", 50, 0, 500),
            countdown_seconds=_int_field(data, "countdown_seconds", 5, 1, 30),
        )
        result.validate()
        return result

    def to_stage6_settings(self) -> dict[str, int | float]:
        """Return the exact key names read by Stage 6's ExecutorConfig settings loader."""
        return self.to_dict()


@dataclass(frozen=True, slots=True)
class WorkspaceProfile:
    profile_id: str
    name: str
    canvas_width: int = 646
    canvas_height: int = 323
    fit_mode: str = "contain"
    brightness: int = 0
    contrast: float = 1.0
    denoise_level: int = 0
    threshold_mode: str = "otsu"
    threshold: int = 128
    row_step_px: int = 1
    screen_area: ScreenArea | None = None
    calibration: CalibrationSettings = CalibrationSettings()
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create_default(cls, name: str = "Основной") -> "WorkspaceProfile":
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        return cls(profile_id=uuid.uuid4().hex, name=name, created_at=now, updated_at=now)

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name.strip()) > 100:
            raise ProfileValidationError("Имя профиля должно содержать от 1 до 100 символов.")
        if not isinstance(self.profile_id, str) or not self.profile_id.strip() or len(self.profile_id) > 80:
            raise ProfileValidationError("Некорректный идентификатор профиля.")
        if not (1 <= self.canvas_width <= 16384 and 1 <= self.canvas_height <= 16384):
            raise ProfileValidationError("Размер холста должен быть в диапазоне 1–16384 px.")
        if self.canvas_width * self.canvas_height > 40_000_000:
            raise ProfileValidationError("Размер холста не должен превышать 40 млн пикселей.")
        if self.fit_mode not in FIT_MODES:
            raise ProfileValidationError("Неизвестный режим масштабирования.")
        if not isinstance(self.brightness, int) or isinstance(self.brightness, bool) or not -100 <= self.brightness <= 100:
            raise ProfileValidationError("Яркость должна быть в диапазоне −100…100.")
        if not (0.5 <= self.contrast <= 2.5):
            raise ProfileValidationError("Контраст должен быть в диапазоне 0.5–2.5.")
        if not isinstance(self.denoise_level, int) or isinstance(self.denoise_level, bool) or not 0 <= self.denoise_level <= 4:
            raise ProfileValidationError("Подавление шума должно быть в диапазоне 0–4.")
        if self.threshold_mode not in THRESHOLD_MODES:
            raise ProfileValidationError("Неизвестный режим бинаризации.")
        if not isinstance(self.threshold, int) or isinstance(self.threshold, bool) or not 0 <= self.threshold <= 255:
            raise ProfileValidationError("Порог бинаризации должен быть в диапазоне 0–255.")
        if self.row_step_px not in (1, 2, 3, 4, 5, 8, 10):
            raise ProfileValidationError("Шаг строк должен быть одним из значений: 1, 2, 3, 4, 5, 8, 10 px.")
        if self.screen_area is not None:
            self.screen_area.validate()
            if self.screen_area.width < 50 or self.screen_area.height < 50:
                raise ProfileValidationError("Экранная область меньше минимального размера 50 × 50 px.")
        self.calibration.validate()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "name": self.name.strip(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workspace": {
                "canvas_width": self.canvas_width,
                "canvas_height": self.canvas_height,
                "fit_mode": self.fit_mode,
                "row_step_px": self.row_step_px,
                "image_processing": {
                    "brightness": self.brightness,
                    "contrast": self.contrast,
                    "denoise_level": self.denoise_level,
                    "threshold_mode": self.threshold_mode,
                    "threshold": self.threshold,
                },
            },
            "screen_area": self.screen_area.to_dict() if self.screen_area else None,
            "calibration": self.calibration.to_dict(),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkspaceProfile":
        if not isinstance(data, dict):
            raise ProfileValidationError("Профиль должен быть JSON-объектом.")
        version = data.get("schema_version", PROFILE_SCHEMA_VERSION)
        if version != PROFILE_SCHEMA_VERSION:
            raise ProfileValidationError(f"Неподдерживаемая версия профиля: {version}.")
        workspace = data.get("workspace", {})
        if not isinstance(workspace, dict):
            raise ProfileValidationError("Поле workspace должно быть JSON-объектом.")
        processing = workspace.get("image_processing", {})
        if not isinstance(processing, dict):
            raise ProfileValidationError("Поле image_processing должно быть JSON-объектом.")
        screen_doc = data.get("screen_area")
        calibration_doc = data.get("calibration", data.get("execution_settings", {}))
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        profile = cls(
            profile_id=str(data.get("profile_id") or uuid.uuid4().hex),
            name=str(data.get("name") or "Импортированный профиль"),
            canvas_width=_int_field(workspace, "canvas_width", 646, 1, 16384),
            canvas_height=_int_field(workspace, "canvas_height", 323, 1, 16384),
            fit_mode=str(workspace.get("fit_mode", "contain")),
            brightness=_int_field(processing, "brightness", 0, -100, 100),
            contrast=_float_field(processing, "contrast", 1.0, 0.5, 2.5),
            denoise_level=_int_field(processing, "denoise_level", 0, 0, 4),
            threshold_mode=str(processing.get("threshold_mode", "otsu")),
            threshold=_int_field(processing, "threshold", 128, 0, 255),
            row_step_px=_int_field(workspace, "row_step_px", 1, 1, 10),
            screen_area=ScreenArea.from_dict(screen_doc) if screen_doc is not None else None,
            calibration=CalibrationSettings.from_dict(calibration_doc),
            notes=str(data.get("notes", "")),
            created_at=str(data.get("created_at") or now),
            updated_at=str(data.get("updated_at") or now),
        )
        profile.validate()
        return profile

    @classmethod
    def from_external_dict(cls, data: dict[str, Any], *, name: str | None = None) -> "WorkspaceProfile":
        """Import a full AutoDraw profile, Stage 6 target profile, Stage 12 canvas profile, or executor settings JSON."""
        if not isinstance(data, dict):
            raise ProfileValidationError("Файл профиля должен содержать JSON-объект.")
        if "workspace" in data or data.get("schema_version") == PROFILE_SCHEMA_VERSION and "name" in data:
            profile = cls.from_dict(data)
            return replace(profile, name=name.strip() if name and name.strip() else profile.name)

        area_doc = data.get("area", data)
        if not isinstance(area_doc, dict):
            area_doc = {}
        area = None
        if all(key in area_doc for key in ("x", "y", "width", "height")):
            area = ScreenArea.from_dict(area_doc)
        width = data.get("width", area.width if area else 646)
        height = data.get("height", area.height if area else 323)
        # Stage 6 settings JSON stores the executor values at its top level.
        known_timing_keys = set(DEFAULT_EXECUTION_SETTINGS)
        timing_doc = data.get("calibration", data.get("execution_settings", data))
        if not isinstance(timing_doc, dict):
            timing_doc = {}
        calibration = CalibrationSettings.from_dict({key: timing_doc[key] for key in known_timing_keys if key in timing_doc})
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        profile = cls(
            profile_id=uuid.uuid4().hex,
            name=(name or str(data.get("name") or "Импортированный профиль")).strip() or "Импортированный профиль",
            canvas_width=_coerce_external_int(width, 646, "width"),
            canvas_height=_coerce_external_int(height, 323, "height"),
            fit_mode=str(data.get("fit_mode", "contain")),
            screen_area=area,
            calibration=calibration,
            created_at=now,
            updated_at=now,
        )
        profile.validate()
        return profile

    def to_canvas_profile(self) -> dict[str, int]:
        self.validate()
        return {"width": self.canvas_width, "height": self.canvas_height}

    def to_stage6_target_profile(self) -> dict[str, dict[str, int]]:
        self.validate()
        if self.screen_area is None:
            raise ProfileValidationError("В профиле не задана экранная область X/Y/ширина/высота.")
        # Stage 6 expects precisely this shape: {"area": {"x", "y", "width", "height"}}.
        return {"area": {key: self.screen_area.to_dict()[key] for key in ("x", "y", "width", "height")}}

    def to_stage6_settings(self) -> dict[str, int | float]:
        self.validate()
        return self.calibration.to_stage6_settings()


def _coerce_external_int(value: Any, fallback: int, field_name: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        return int(value)
    except (TypeError, ValueError, OverflowError):
        raise ProfileValidationError(f"В импортируемом файле отсутствует корректное поле '{field_name}'.")


def _optional_int(data: dict[str, Any], key: str, low: int, high: int) -> int | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ProfileValidationError(f"Поле '{key}' должно быть целым числом.")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ProfileValidationError(f"Поле '{key}' должно быть целым числом.") from exc
    if not low <= parsed <= high:
        raise ProfileValidationError(f"Поле '{key}' вне диапазона {low}–{high}.")
    return parsed


class ProfileStore:
    """Small JSON registry. Writes are atomic so an interruption cannot truncate the registry."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[WorkspaceProfile]:
        if not self.path.exists():
            default = WorkspaceProfile.create_default()
            self.save_all([default])
            return [default]
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProfileValidationError(f"Не удалось прочитать реестр профилей: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != PROFILE_SCHEMA_VERSION:
            raise ProfileValidationError("Неверная структура или версия реестра профилей.")
        items = data.get("profiles")
        if not isinstance(items, list):
            raise ProfileValidationError("В реестре отсутствует список profiles.")
        profiles = [WorkspaceProfile.from_dict(item) for item in items]
        ids = [p.profile_id for p in profiles]
        if len(ids) != len(set(ids)):
            raise ProfileValidationError("В реестре обнаружены повторяющиеся ID профилей.")
        return profiles

    def save_all(self, profiles: list[WorkspaceProfile]) -> None:
        profiles = list(profiles)
        ids = [p.profile_id for p in profiles]
        if len(ids) != len(set(ids)):
            raise ProfileValidationError("ID профилей должны быть уникальными.")
        payload = {
            "schema_version": PROFILE_SCHEMA_VERSION,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "profiles": [profile.to_dict() for profile in profiles],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{self.path.name}.", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def upsert(self, profile: WorkspaceProfile) -> list[WorkspaceProfile]:
        profile.validate()
        profiles = self.load()
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        candidate = replace(profile, name=profile.name.strip(), updated_at=now)
        if any(item.profile_id == candidate.profile_id for item in profiles):
            profiles = [candidate if item.profile_id == candidate.profile_id else item for item in profiles]
        else:
            candidate = replace(candidate, created_at=candidate.created_at or now)
            profiles.append(candidate)
        self.save_all(profiles)
        return profiles

    def delete(self, profile_id: str) -> list[WorkspaceProfile]:
        profiles = [item for item in self.load() if item.profile_id != profile_id]
        if not profiles:
            raise ProfileValidationError("Нельзя удалить последний профиль. Сначала создайте другой профиль.")
        self.save_all(profiles)
        return profiles

    @staticmethod
    def export_json(path: str | Path, payload: dict[str, Any]) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        target.write_text(data, encoding="utf-8")
        return target
