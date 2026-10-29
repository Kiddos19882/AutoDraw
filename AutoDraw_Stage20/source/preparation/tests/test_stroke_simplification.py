import cv2
import numpy as np
from PIL import Image, ImageDraw

from stroke_simplification import simplify_path


def test_simplification_uses_pillow_rasterization_for_transparency_safety():
    # For this diagonal, OpenCV LINE_8 paints (0, 2), while Pillow paints
    # (1, 2). Only the original path's pixels are safe. The simplified segment
    # must be rejected because the preview renderer (Pillow) paints (1, 2).
    points = [(0.0, 3.0), (0.0, 2.0), (1.0, 1.0)]
    safe_mask = np.zeros((5, 5), dtype=np.uint8)
    safe_mask[3, 0] = 1
    safe_mask[2, 0] = 1
    safe_mask[1, 1] = 1

    # Prove that this fixture distinguishes the two rasterizers: the OpenCV
    # line is safe, but Pillow's line includes a transparent pixel.
    cv_line = np.zeros((5, 5), dtype=np.uint8)
    cv2.line(cv_line, (0, 3), (1, 1), 1, 1, lineType=cv2.LINE_8)
    pillow_line = Image.new("1", (5, 5), 0)
    ImageDraw.Draw(pillow_line).line((0, 3, 1, 1), fill=1, width=1)
    pillow_mask = np.asarray(pillow_line, dtype=np.uint8)

    assert not np.any((cv_line > 0) & (safe_mask == 0))
    assert np.any((pillow_mask > 0) & (safe_mask == 0))

    result = simplify_path(
        points,
        closed=False,
        tolerance_px=2.0,
        safe_mask=safe_mask,
    )

    assert result == points
