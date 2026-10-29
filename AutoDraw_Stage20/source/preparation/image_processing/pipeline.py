"""Совместимый импорт общего конвейера обработки изображений."""
from shared_image_processing.pipeline import (
    FitMode,
    ProcessingResult,
    ProcessingSettings,
    ThresholdMode,
    _validate_crop_box,
    fit_to_canvas,
    load_rgb_image,
    process_image,
)

__all__ = [
    "FitMode", "ThresholdMode", "ProcessingResult", "ProcessingSettings",
    "fit_to_canvas", "load_rgb_image", "process_image",
]
