# ENGINE-001 / V43-P3a3 — genuine Egret probe of isolated oriented fill strokes

**Дата:** 2026-11-16. **Статус:** PREREGISTERED / NOT_RUN. Эксперимент: `ENGINE001_V43P3A3_NATIVE_ORIENTED_FOOTPRINT`. Это этап той же задачи ENGINE-001/V43-P3, **не изменение** замороженных P3a/P3a2 исходных данных, отрицательных P2a/P2b или V44-B.

## Primary question

The existing P3a2 source-only PCA-width4/6/10/20/30 candidates may spill native ink across palette/color boundaries because real archived Egret WebGL lineStyle differs from an ideal capsule, as independently observed at widths10/20/30 in [V31 CI43693170456](https://github.com/Kiddos19882/AutoDraw/actions/runs/43693170456). Evaluate the actual native alpha for the **original proposed path geometries**, not a rectangle, distance proxy or user game's live runtime.

## Frozen source, selection, and independent baseline

Source `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Use existing `original_labels(source)[::3,::3]` for 240x460 source classes and exact `largest_dark_component`: class7 largest component5005 px. Reuse `source_width_audit` output width4/6/10/20/30 unmodified. **Fixed selection:** first 3 generated two-point routes for each width (or all if fewer than3, recording INSUFFICIENT count), sorted in existing generator order. A width with no eligible paths reports `NO_ELIGIBLE_PATHS`, not a fictitious successful native draw. Input is only immutable original target mask, never any P3a2 CI output or prior renderer B/C image.

## Experimental native method

Reuse `run_engine001_complex_holdout_v5.native_batch` and the archived Egret WebGL BoardPane/Stage, with an opt-in method `renderV43P3PaintBrushProbe` enabling actual widths4/6/10/20/30. Default V5/V43/V44 methods, their accepted widths and frozen outputs **must remain unchanged**. Each width gets only its selected independent `icon-N` fill strokes with a single constant color for isolation (no contour strokes), path endpoints in logical 460×240 and native backing1380×720; no full V44-B image is claimed. Record native isolated alpha>=24 and >=128, overlap outside source class7 and outside its largest component, with distance beyond 3logical px, actual painted area inside class7, per-path count, synthetic vertices NOT_CHALK, raw PNG and SHA hashes. Source owner labels expanded exactly threefold. Native/color boundary result is E3 archived Egret reference only and does not establish full per-color >=99% coverage. If no paths for a width, emit NO_ELIGIBLE and no fabricated image.

## Safety and gate

No existing 1945 source paint paths are deleted/changed, no original 410 V44-B outline routes changed, no Stage6/executor/Monitor/Bridge/master edits. Probe cap each width <=3 native paths, <=6 synthetic vertices; strict source SHA, class area5005 and width set. This native reference does not certify CHALK; exact game CHALK remains E4 run-bound `post.pointCount-pre.pointCount`. Any actual Egret off-color ink >3 logical px marks that width/path **unsafe for P3b replacement**; <=3 only clears this one diagnostic, not full visual acceptance. Never recalibrate thresholds after results; keep negative cases. Re-use CI artifact storage and do not overwrite existing files.

**Next after run:** audit each width's native image and decide whether any candidate is worth a separate pre-registered resource-saving **replacement** experiment with original 410 V44-B colored outlines LAST. No acceptance without full native A=V44-B replay/quality/coverage, then game E4/E5.

## Implementation — 2026-11-16

Opt-in isolated experimental method `renderV43P3PaintBrushProbe` added to existing `tests/game_renderer_reference.js`. It delegates to `renderComplexHoldoutColorProbe(strokes, true)` to enable only the frozen widths4/6/10/20/30; **default** `renderComplexHoldoutColorProbe(strokes)` still validates original [2,4,6,8,10,15,30] and unchanged pixel renderer. The existing `native_batch` method whitelist includes the new opt-in method only. Existing V43 methods and V44-B colored contour rendering unchanged.

Added `tests/run_engine001_v43p3a3_native_probe.py`: for each width it independently reuses existing P3a2 paths, selects first at most3 and renders real Egret WebGL via `native_batch`, preserving all generated raw source JSON identities in report. Actual native isolated alpha at thresholds24/128 evaluated against frozen class7 source mask and largest component at backing3×, including outside-component >9 native px. Source-distance guards never certify native safety. No eligible path => `NO_ELIGIBLE_PATHS` with no invented image. Report files+SHA linked and original negative findings saved. Add `tests/test_engine001_v43p3a3_native_probe.py` for freeze, 3px and empty-width behavior. [Windows opt-in/push CI](../../.github/workflows/engine001-v43p3a3-native-oriented-footprint.yml) performs 20 existing Node tests, unit tests, archived WebGL capture and output hash check.

At writing: **E1 code inspection only, E2/E3 CI UNKNOWN, E4/E5/exact CHALK NOT_RUN**. Do not claim width20 is native safe before this probe's actual results. Production untouched.

## Pre-CI static compatibility correction

Static audit of the actual remote JS revealed that first opt-in wrapper commit `b3eb2fb2` added `renderV43P3PaintBrushProbe` but left its underlying V5 brush-width predicate unchanged; without correction the width20 call would fail before WebGL capture. Commit `4b3d87d305764c47ffe2decaee20c3a0a34eb289` explicitly switches the width set only when `allowV43P3Widths=true`: width4/6/10/20/30 new opt-in; original V5 default exactly2/4/6/8/10/15/30. The historical native V31 width20 exists but does not prove this new method has run. The bug is detected **E1 static**, fixed in source; E2/E3 for P3a3 **UNKNOWN** until its own CI executes; no accepted native PNGs yet.
