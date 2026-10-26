## Stage 19/20 — Adaptive brush planning

`board_resource_model.py` records the known 3,000 / 6,000 / 12,000 stored-point quotas separately from the empirical ink-equivalent model. The extended slider is known to offer integer values 1–30; the planner currently limits recommendations to 1–20.

`brush_planner.py` produces a separate `autodraw_adaptive_brush_plan` from the color scanline plan and the exact palette-index map. It checks the complete conservative brush footprint against the source map. Long horizontal runs may be split into a narrow leading edge, a thicker interior section and a narrow trailing edge. Transparent pixels or pixels of another palette index prevent a thick brush from crossing that area. Where no safe mapping is proven, the output retains a marked legacy fallback instead of claiming the stroke is safe.

The parameters `brush_scale_x` and `brush_scale_y` mean source-map pixels per game brush unit. They must be calibrated for the actual board mapping. Until `calibration_confirmed=True` is supplied after calibration, the returned plan is a recommendation and is not marked ready for automatic execution. This initial planner preserves coverage but may increase strokes by splitting long runs; reducing stroke count by safely skipping covered rows is a later optimization step. Tests: `python -m unittest discover -s tests -v`.
