"""Canonical image-processing pipeline shared by preparation and execution."""
from .pipeline import (
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
