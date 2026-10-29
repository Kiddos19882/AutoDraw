import numpy as np

from stroke_simplification import simplify_path


def test_simplification_rejects_segment_that_pillow_would_draw_over_transparency():
    # The original path is a safe 3-pixel zigzag. RDP at this tolerance would
    # replace it with a horizontal segment through (2, 1), which is transparent.
    points = [(1.0, 1.0), (2.0, 2.0), (3.0, 1.0)]
    safe_mask = np.zeros((5, 5), dtype=np.uint8)
    safe_mask[1, 1] = 1
    safe_mask[2, 2] = 1
    safe_mask[1, 3] = 1

    result = simplify_path(
        points,
        closed=False,
        tolerance_px=2.0,
        safe_mask=safe_mask,
    )

    assert result == points
