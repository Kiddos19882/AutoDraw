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

## V31 actual post-run evidence — 2026-11-15 (append-only)

Preregistration and original widths/paths/mismatch criteria above remain frozen. The first three workflow attempts failed **before any native measurement**: [CI43692852270](https://github.com/Kiddos19882/AutoDraw/actions/runs/43692852270) FAIL missing `pytest` in runner, [CI43692958657](https://github.com/Kiddos19882/AutoDraw/actions/runs/43692958657) FAIL `ModuleNotFoundError: brush_footprint_geometry` because test search path missing, [CI43693062388](https://github.com/Kiddos19882/AutoDraw/actions/runs/43693062388) FAIL `Egret WebGL context is unavailable` on Linux runner (Node 20/20, pytest 4/4 PASS). Fixed only CI dependency, PYTHONPATH and switched to previously E3-proven Windows Firefox WebGL runner; no frozen case/gate or numerical threshold changed.

**[Focused CI43693170456](https://github.com/Kiddos19882/AutoDraw/actions/runs/43693170456) E3 SUCCESS** SHA `8ad9778f5e52b5ef7d4ad2f225db49ad1351f573`. Existing Node renderer 20/20 PASS, existing capsule 4/4 pytest PASS, **30/30 authentic archived Egret BoardPane WebGL normal-path rasterizations** (widths1/3/10/20/30 × 6 fixed trajectories), blank BoardPane **0 alpha>0**, actual CanvasRenderer comparisons and cap-model geometry captured. Artifact **14153785043** `engine001-v31-native-game-brush-footprint-evidence` (original GitHub ZIP **98393 bytes, SHA256 `f6ad6127075047bac7cd29ca984a48ffe74d4d4b9fabe3ae49ff866852f6f435`**). Independent audit of all six report-listed file hashes PASS, raw 30 cases and four real Egret PNGs preserved. Verified game bundle hashes: engine `362192291d421ee895ad0684a07f7d66a533390f1091556e85ba14d84902e85c`, game `097253b4e921810128d49402b967123781b4a586aacd64311e557c8aa20dd2c3`; report's `engineVersion` field is null, **do not infer dynamically reported engine version** (bundle path identifies archival family).

| Real BoardPane lineStyle width | Native logical alpha>=128 outside ideal potential — cases/6 | Cases native alpha>=128 | Native CanvasRenderer/WebGL differ |
|---:|---:|---:|---:|
| 1 | 0 | 6/6 | 6/6 |
| 3 | 0 | 6/6 | 6/6 |
| 10 | 6 | 6/6 | 6/6 |
| 20 | 6 | 6/6 | 6/6 |
| 30 | 6 | 6/6 | 6/6 |

Overall **18/30** cases have native logical alpha>=128 cells **outside ideal round capsule's `potential_cells`**; alpha>=1 outside potential in **22/30** cases. Differences at alpha>=128 are small (usually 2–9 logical cells per case) but violate using the ideal capsule as a **strict game safety enclosure** without native correction. The ideal capsule's `guaranteed_cells` were all present in native alpha>=128 for these fixtures (0/30 missing); that says nothing about future widths, paths or live E4. Native Canvas2D/WebGL differed in **30/30 cases**, so use the actual game WebGL path as authoritative for this archived reference, not Canvas2D. At ROI boundary x155, native width30 `roi_edge` had 368 logically covered alpha>=128 cells left of the 150×240 **source artwork ROI**; summed all per-case ROI outside alpha>=128 count 581 (overlapping cases, not unique drawing). This is **not** gameplay or breach of an accepted color boundary by itself: this test draws deliberately at ROI edge, and board mask can include those pixels. No actual per-color target/paint or fill acceptance was run.

**Decision: native-reference measurement PASS / IDEAL_CAPSULE_STRICT_ENVELOPE FAIL** at widths10,20,30. Never substitute a rectangle or ideal capsule when deciding color leakage or safety. Keep V30 MODEL_ONLY evidence negative and frozen. Next new-ID adaptive direction/variable-width path planning must measure each actual game stroke in native Egret and then validate full-color visual recognizability and resource estimate before any E4. This V31 CI is archived offline **E3**, not live game E4 or exact run-bound CHALK; no production changes.
