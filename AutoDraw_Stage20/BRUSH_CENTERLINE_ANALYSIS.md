# Centerline-aware brush screenshot analysis

Branch: `feature/image-geometry-optimization`

Analyzer: `tests/analyze_brush_centerline_results.py`

CI run: https://github.com/Kiddos19882/AutoDraw/actions/runs/40749351745

## Summary

The centerline-aware analyzer successfully processed all 20 saved plan/screenshot pairs (brush values 1, 7, 14, and 20; five scenarios per brush). It differs from the first analyzer in that it checks dark pixels near the planned stroke path, projects them along the path, and treats zero-length controls as controls rather than successful lines.

Approximate width estimates from long straight strokes:

| Requested brush value | Estimated visible width in screenshot |
|---:|---:|
| 1 | approximately 1–3 px; estimate is unstable for very thin marks |
| 7 | approximately 11 px |
| 14 | approximately 19 px |
| 20 | approximately 24–25 px |

These are screenshot-pixel estimates, not verified engine brush diameters. In particular, the brush 1 estimate varies because a one-pixel centerline has little margin against antialiasing and threshold choices.

## Short-stroke findings

| Requested brush | 0 px control | 1 px | 2–10 px |
|---:|---|---|---|
| 1 | correctly not classified as a line | weak/missing trace | 2–3 px weak/missing; 5–10 px line-trace candidates |
| 7 | correctly not classified as a line | weak/missing trace | visible trace, but shape dominated by brush width |
| 14 | correctly not classified as a line | weak/missing trace | visible trace, but shape dominated by brush width |
| 20 | correctly not classified as a line | weak/missing trace | visible trace, but shape dominated by brush width |

“Line-trace candidate” means only that the screenshot contains dark pixels geometrically consistent with a trace. It does not establish that the game registered a stroke or charged paint. For brush values 7/14/20, the planned short segment is much shorter than the estimated footprint, so its visible shape is dominated by the brush rather than by the intended segment length.

## Practical implications

1. A zero-length movement is not a valid line and should remain a negative control.
2. With brush 1, the current screenshot evidence suggests that 1–3 px paths are not reliably distinguishable from a dot-like mark; 5 px is the first tested length classified as a line-trace candidate. This is not yet a game-registration threshold.
3. With brush 7 and 14, the 10 px straight test is already brush-width-dominated; brush 20 remains width-dominated at 20 px. These brush sizes are therefore poor choices for fine short geometry.
4. Brush 1 is the most promising option for fine geometry, while larger brushes may be useful for broad fill. That is a geometry recommendation only; resource efficiency and in-game acceptance still require separate verification.

## Limitations and next verification

- Each screenshot contains a complete test sequence, not a separate capture per stroke. Nearby/overlapping marks can influence measurements.
- The corridor tolerance uses the requested brush value as an approximate diameter; the actual UI setting was not machine-verified.
- Pixel analysis cannot read the game's internal stroke-registration result or paint balance.
- The old ROI-only report should be treated as a coarse diagnostic. Use this centerline report for the short-stroke geometry comparison, while keeping its limitations in mind.

Next, verify in-game registration and paint before/after for lengths 0, 1, 2, 3, 5, 8, and 10 using brush 1, then repeat a smaller comparison for brush 7/14/20. Record each trial independently rather than relying on a single combined screenshot.
