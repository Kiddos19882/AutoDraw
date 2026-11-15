# ENGINE-001 / V31 — prereg native Egret footprint versus ideal capsule

**2026-11-15. PREREGISTERED / NOT_RUN** (commit before capture). Implements accepted [game brush footprint testing policy](GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md), INV-012. No production, executor, Monitor, Bridge or master changes. Task ENGINE-001. Remote branch baseline before task `3c30818ba40250fa712f1753eda6ca1ba64cc392`, V30 archived E3 source-bound model NO_GAIN [CI43689298730](https://github.com/Kiddos19882/AutoDraw/actions/runs/43689298730).

## Scope, frozen inputs and hypothesis

Input complex `testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, 200×320 bytes97308; matches unchanged user difficult source, but isolated strokes (not full painting). Real game engine archived Egret5.4.1 `com.magnetjoy.pet.ui.board.BoardPane.redraw()`, normal path, actual game `Graphics.lineStyle` mapping and rounded `BoardPane` mask, **native WebGL renderer and CanvasRenderer**. Use existing `tests/game_renderer_reference.js`; all logical coords on 460×240 board, backing3×=1380×720. Source ROI x155..304, y0..239. Need record actual BoardPane stroke configuration and browser build with SHA; before interpreting results validate actual game image/engine bundle identity. No source/plan mode or game production path changes.

**H1:** ideal round-capped `source/preparation/brush_footprint_geometry.swept_capsule_pixel_masks` provides a useful but not identical proxy for native Egret stroke on discrete logical cells, especially curved/diagonal/edge paths. **H0:** mismatch or zero native output invalidates proxy for acceptance; preserve failure, no posthoc calibration.

## Frozen cases and data

Use exactly **6 trajectory templates × 5 brush line-width arguments =30 cases**: widths **[1,3,10,20,30]**, width is API `lineStyle` input not radius. Normal mode, fixed stroke RGB `#31A3D3` and no paint background. Each points list:
- dot: `(230,120),(230,120)`
- horizontal: `(215,120),(245,120)`
- diagonal: `(215,105),(245,135)`
- elbow: `(215,110),(230,110),(230,135)`
- curved polyline: `(210,125),(220,115),(230,112),(240,118),(250,127)`
- left ROI boundary: `(155,100),(170,100)`

A separate no-stroke blank at width1; alpha positive count zero required, also Canvas-vs-WebGL equality on blank.

For every real native BoardPane output record at 3× backing **lossless logical cells** which have WebGL alpha>=1 and >=128 after mapping floor(x/3),floor(y/3), full native PNG representative for width1 dot, width20 diagonal, width30 elbow, width30 ROI-edge; native WebGL source+mask settings, draw-call telemetry (zero is NOT proof of blank). At most 12000 logical cells per case, max 30 cases; reject invalid bounds, nonfinite coords, unauthorized widths/IDs and duplicate fixture cases. Store both native 3× alpha counts and native logical cell list, plus CanvasRenderer/WebGL equality/differences per case. Compare native logical cells with **same unchanged** capsule potential and guaranteed cell sets using `swept_capsule_pixel_masks(points,width,1,1,460,240)`. Record counts `native_not_potential` (native cells outside proxy safety envelope), `guaranteed_not_native` (guaranteed model missing in native), and per-width/per-trajectory mismatch; calculate diagnostic ROI x155..304 and board-edge clipping separately. Do not assume 1x1 rectangle or cap shape without evidence.

**Hard gates:** blank=0 alpha, 30 actual native outputs, source hashes valid, correct API width and board scale/mask, native no-op dot cases explicitly reported rather than dropped; no clipped or overlarge pixel capture silently accepted. If Canvas2D/WebGL differ, record real mismatch **not automatic assertion of equivalence**; model is never accepted if mismatched to native. **Native E3 PASS means valid reproduction of data**, not that a capsule is safe or that either backend equals live. 3 logical px and >=99% game fill/leakage remain NOT_EVALUATED without full color source target and runtime. No E4 or exact game CHALK without run-bound Monitor (post.pointCount-pre.pointCount), E5 NOT_RUN.

**Follow-up only after V31 evidence:** develop an isolated adaptive thickness/direction candidate driven by **actual native footprint** and importance of face/hair/hand and saturated orange region; prereg new ID before experiments; preserve V23–V30 failures and avoid promoting ideal geometry to gameplay.
