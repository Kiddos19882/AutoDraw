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

## Pre-result diagnostic extension: distinguish foreign colors vs exterior

Before any confirmed P3a3 native output, explicitly extend report-only alpha24/128 diagnostics. `owner` frozen palette labels 0..7; required foreign color is `owner in [4,5,6] `, skipped/light background is 0..3. For each isolated class7 native stroke group:
- count alpha-positive ink on native pixels belonging to any **other required color class4/5/6** and separately on skipped/background labels0..3;
- define **source class7 boundary depth** as native backing-pixel Euclidean distance from the nearest class7 pixel; count foreign required-color coverage where depth exceeds9 native px (3 logical px);
- define **source foreground silhouette depth** as distance to required-class foreground union4..7; count painted outside silhouette beyond9 native px;
- retain original largest-component depth diagnostic as a separate component identity measure; it is NOT synonymous with forbidden cross-color leakage.
These are *native reference-image diagnostics*, not exact RGB quality or full-scene ownership: if a width has zero sampled paths, retain `NO_ELIGIBLE_PATHS`. All thresholds frozen (alpha24/128; 9 backing px) before report. No source candidate geometry changes, no posthoc filtering, no promotion to production.

## Native evidence completeness gate (before outcome)

Per width, `NO_ELIGIBLE_PATHS` remains a legitimate negative observation. For the **entire** run, however, zero eligible paths across all five widths means **no actual Egret ink was measured** and must be classified `NO_NATIVE_SAMPLE` / FAIL (retain source diagnostics and any outputs), not E3 native PASS. CI must run existing P3a and P3a2 unit suites because P3a3 directly imports their candidate path generator and source audit. Artifact upload remains `if: always()`.

## Native E3 result — 2026-11-16, CI43864508620

[CI43864508620](https://github.com/Kiddos19882/AutoDraw/actions/runs/43864508620) **completed SUCCESS**, head SHA `e2cc4d156f3b7946f2d88c2da056430be17b4083`, job133289482949 `isolated-native-footprint` SUCCESS, Python planner/probe preflight and 20 Node renderer regression tests PASS, Windows Firefox archived real BoardPane/Egret WebGL capture PASS. Artifact **14224453656**, original ZIP SHA256 `4565925cead78a67a993a0b4629a457d9f3d6f5bcea230a1baa91e33b817faa6`; ZIP CRC PASS and **6/6 report-linked PNG SHA256 matches** (3 sizes x color-7 and composite). PNG compare is source/isolation-only, not live game. Source identity pinned SHA `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`.

| lineStyle width | source candidate routes | native routes drawn | own color alpha24 ink backing pixels | foreign source classes4/5/6 alpha24 | foreign >3 logical px alpha24 | exterior silhouette >3 logical px alpha24 |
|---|---:|---:|---:|---:|---:|---:|
| 4 | 29 | 3 | 2244 | 0 | 0 | 0 |
| 6 | 17 | 3 | 3718 | 2 | 0 | 0 |
| 10 | 9 | 3 | 6510 | 0 | 0 | 0 |
| 20 | 0 | 0 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| 30 | 0 | 0 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

At alpha128 own-color backing pixels: width4=2208, width6=3669, width10=6426; **foreign required-color pixels=0** and excess>3logicalpx=0 on all rendered widths at this threshold. At alpha24: width6 foreign2 backing pixels (zero >3logicalpx); width4/10 foreign0. All sampled runs had zero outside silhouette>3logicalpx at both thresholds. Source class7 largest-component coverage ratios for **just those three routes** at alpha24: 4=4.9816849817%, 6=8.2539682540%, 10=14.4522144522%; these are **not full color coverage percentages**, cannot be compared to production >=99% gate. The 9 native isolated strokes are not a filled image or outline comparison. Width20/30 `NO_ELIGIBLE_PATHS` follows frozen source-distance/8logicalpx route restriction; **NOT a native failure or an assertion those brushes cannot be used elsewhere**.

**Evidence assessment:** E3_CAPTURE_PASS / three tested widths within tolerance on a narrow frozen sample; **full fill quality UNKNOWN, replacing old width2 source paths NOT_RUN, V44-B full-image new composite NOT_RUN, E4 exact CHALK NOT_RUN, E5 NOT_RUN**. Decision: advance only to separately frozen resource-saving route-replacement methodology, prioritizing width10 as a candidate but never globally selecting it without native alpha for the actual replacement strokes. Preserve raw positive/negative artifact and all thresholds.
