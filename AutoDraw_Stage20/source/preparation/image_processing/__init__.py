"""Совместимые экспорты общего конвейера обработки изображений."""
from shared_image_processing import (
    FitMode,
    ProcessingResult,
    ProcessingSettings,
    ThresholdMode,
    fit_to_canvas,
    load_rgb_image,
    process_image,
)

__all__ = [
    "FitMode", "ThresholdMode", "ProcessingResult", "ProcessingSettings",
    "fit_to_canvas", "load_rgb_image", "process_image",
]
