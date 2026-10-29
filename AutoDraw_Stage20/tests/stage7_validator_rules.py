from __future__ import annotations

from typing import Any


def skeleton_transparency_error(
    item: dict[str, Any],
    report_name: str,
    *,
    max_transparent_pixels: int = 3,
) -> str | None:
    """Return a diagnostic if skeleton transparency exceeds the bounded policy."""
    transparent_count = int(item.get("painted_transparent_pixel_count", -1))
    samples = item.get("transparent_stroke_samples", [])
    sampled_pixels = [
        tuple(pixel)
        for sample in samples
        for pixel in sample.get("transparent_pixels", [])
    ]
    if transparent_count < 0 or transparent_count > max_transparent_pixels:
        return (
            f"{report_name}: skeleton painted {transparent_count} transparent pixels; "
            f"allowed maximum is {max_transparent_pixels}"
        )
    if len(sampled_pixels) != transparent_count or len(set(sampled_pixels)) != len(sampled_pixels):
        return f"{report_name}: skeleton transparency diagnostics do not match the pixel count"
    if any(len(sample.get("transparent_pixels", [])) != 1 for sample in samples):
        return f"{report_name}: skeleton tolerance permits only isolated one-pixel hits per stroke"
    if transparent_count and len(samples) != transparent_count:
        return f"{report_name}: each tolerated skeleton pixel must be attributed to a separate stroke"
    return None
