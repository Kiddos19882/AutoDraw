# ENGINE-001 / V34 — prereg native warm-color fidelity on frozen V33

**2026-11-15. Status: PREREGISTERED / NOT_RUN.** Task ENGINE-001. Registered before any V34 measurement. Remote baseline HEAD before prereg: `d30a40f4a3b7fd188cde0928f10de248571f947b`. Scope: isolated experiment only; no master, Stage6, production defaults, executor, Bridge, Monitor or live game modifications.

## Why and falsifiable hypothesis

V33 genuine archived Egret WebGL [CI43696364638](https://github.com/Kiddos19882/AutoDraw/actions/runs/43696364638), SHA `386c8c24c0e99765230e7de0e11c864716a1e815`, artifact14154601656, achieved source-quantized silhouette coverage **93.868365%**, precision **87.9984885%** with 1945 width2 strokes, 3890 synthetic accepted vertices (447 +0.25 logical-x endpoint shims), but **all four drawn color classes below 99%** (71.08%,77.81%,57.71%,94.73%), high cross-color overlap and missing source warm/orange. Hypothesis V34: source-RGB-driven selection of warmer, faithful stroke colors on **identical V33 geometry** improves color fidelity without changing native silhouette footprint, counts, or exterior leakage. This is color-only stage; it cannot restore unpainted spatial details and may FAIL if original quantization discarded entire warm regions.

## Frozen inputs/control

- Source original `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, original 200×320. Logical board460×240, ROI x155..304,y0..239 (150×240), native backing1380×720, scale3.
- V33 immutable evidence artifact14154601656 and identical native strokes from `native-width2-strokes.json`, derived from frozen V29 `budgeted-plan.json` SHA256 `e3dfb8b36831c74283b21ed694335e93d262e383938a9f1fb38222c7939d57cd`. Verify artifact ZIP SHA256 `d3eeb4dc7bc37924aef7713b4b77c76ad3e4adeb2f7baad17b782f4764b66fb1` and V33 manifest SHA before use.
- Native renderer: existing `tests/game_renderer_reference.js:renderComplexHoldoutColorProbe`, existing `run_engine001_complex_holdout_v5.native_batch`, archived real BoardPane/Egret WebGL on the proven Windows/Firefox environment. Canvas comparison where available. No PIL/OpenCV footprint used as acceptance.
- Control A: exact **unmodified** V33 strokes/colors/order/width2/endpoints. Verify native result and compare pixel hashes with original V33 on same runtime; if baseline reproduction differs, halt `BLOCKED` until source/environment difference explained.

## Candidate B (single variable: color assignment)

Do not add, remove, move, split or reorder strokes; preserve all 1945 width2 paths, 447 shims and 3890 synthetic vertices. Do not modify canvas background, alpha, mask, stroke mode, caps or join.

For each V33 source palette class **4,5,6,7**, derive one RGB replacement from actual original RGB pixels whose frozen V28 ROI8 quantized target label equals that class. Compute deterministic per-channel median of original RGB for that class, with tie resolved to lower byte. Four replacements only; ignore background/skipped target classes; do not choose colors from output image, hand-tune after preview, or invent warm stroke paths. Report per-class pixel count, old RGB, new RGB, delta, source warm/orange pixel coverage. If medians reproduce muted tones, record this as a meaningful negative result. Guard against empty class and non-uint8 samples (FAIL-CLOSED). No extra colors are permitted in V34 B; introducing a new source-color class requires separately preregistered V35 experiment.

## Measurement, criteria, and honesty

Before running, save source/target hashes, exact source transformation, raw PNG/alpha and hash manifests. Use same individual-color and composite true Egret native PNG as V33, white background for visual comparison. Measure:
1. Native geometry sanity: width2 alpha footprints and silhouette coverage/precision/IoU against original V33 must be identical in isolated colors, or candidate invalid; native size 1380×720.
2. RGB fidelity: mean absolute RGB error and class/ROI warm-region RGB error **against original source ROI**, using equal-size logical composite of actual native capture (not pasted source texture); report both V33 and V34 B. Define warm pixels on original RGB as HSV hue 5–55 degrees, saturation>=0.30, value>=0.20 (predeclared diagnostic, not quality gate), report count and RGB MAE. Report quantized-target class recall and wrong-class native alpha>=24/128 overlap using fixed V33 masks and threshold; expected unchanged because only colors change, but verify.
3. Compare native source original / V33 A / V34 B for both full body and face/hand/hair crops, no textured target overlay. Qualitative impression exploratory, not independent E5.
4. Forecast cost: same 1945/3890 synthetic counts do not imply exact CHALK. Existing V29 forecast4498 applies only to V29; do not claim V34 under 6000 until correctly recalculated/real game measured.

**Decision:** V34 candidate `COLOR_FIDELITY_IMPROVEMENT` only if V34 full ROI RGB MAE is strictly lower than V33 AND warm-region RGB MAE strictly lower, while native geometry pixel alpha identical, no increased wrong-color alpha spill and no extra strokes. Otherwise `NO_GAIN` or `FAIL`; do not tune thresholds posthoc. Full production acceptance remains **>=99% each required color**, **<=3 logical px native/game exterior leakage**, meaningful face/hair/hand recognition and actual game budget/safe margin. Since V33 per-color fails, this prereg cannot yield full quality PASS even if color B improves. Require separate geometry/detail V35 experiment and independent validation before any production promotion.

## Execution and evidence handling

Create opt-in V34 runner reusing V33/native helpers; opt-in Windows GitHub Actions workflow in same proven environment, with isolated artifacts `V34-A` and `V34-B` and replay checks. Minimum E2: deterministic medians, unchanged frozen geometry, correct warm mask, rejects corrupted hashes, no overwrite. E3: complete CI jobs, source-bound raw native PNG and JSON with SHA256 per file and captured software versions. Preserve negative and failed CI runs. No game E4, independent E5, exact run-bound `CHALK = post.pointCount - pre.pointCount` in this experiment; explicitly `NOT_RUN`. No output is accepted without true BoardPane native alpha. User priority: recognizability and faithful color rather than an artificially low numeric error.
