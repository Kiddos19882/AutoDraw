# ENGINE001_ANILINES_BRUSH1_PATHS_V17 — exploratory contour-first prereg

**Task:** ENGINE-001 / next step after V14 authentic AniLines Detail and unregistered V15 cleanup. **Registered:** 2026-11-15 **before generating any V17 plan or preview**. **Status:** PREREGISTERED, NOT_RUN. **Authorization:** user waived the previously requested independent reviewer as a precondition to experimental work. The completed V16 independent-review protocol and validator are preserved but **no longer block this exploratory path**; they remain optional future validation, and no semantic seam-precision or E5 claim is permitted without real independent labels.

## Baseline and hypothesis

Source image `testImages/wV6VeZI9S1Y.png`: 200×320, 97308 bytes, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Actual V14 AniLines Detail `line-output.png` from [CI 43653371987](https://github.com/Kiddos19882/AutoDraw/actions/runs/43653371987), SHA256 `2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b`, 200×320, upstream `5d188fb68f40fb04fbe3c9c54dcc57b16c914818`, checkpoint `876e4efb8d4cb3602da2b034fdb3503e1816070b4ec6d4430783fc99c7fe02c8`. Use output **unchanged, threshold grayscale<128**, no semantic suit mask. FDoG and posthoc V15 cleanup are historical controls only, not V17 inputs.

H1: binary AniLines can produce deterministic, source-bound thin continuous brush-1 centerline paths that preserve recognizable suit seams better than V11 per-palette boundary paths. H0: skeleton branches, low resolution or vertex costs make resulting predicted drawing fragmented/unrecognizable; do not change thresholds after seeing image under this ID.

## Fixed geometry

1. At original resolution threshold AniLines grayscale **<128** into binary. Apply `skimage.morphology.skeletonize` to obtain a one-pixel centerline (no dilation, no closing and no morphological fusion).
2. Build 8-neighbor graph of skeleton pixels; trace maximal chains between degree!=2 graph nodes, and all remaining pure cycles deterministically using ascending `(y,x)` tie-breaking. Edge-disjoint tracing allowed shared junction endpoints but no arbitrary new line pixels. Reject chains of Euclidean arc length **<4 original pixels**. Simplify with Ramer-Douglas-Peucker maximum perpendicular deviation **0.6 original pixels**, preserve endpoints, then split into segments with **up to128 vertices**, sharing endpoints (max 4000 paths / 30000 synthetic vertices, else FAIL-CLOSED).
3. Map source coordinates into the frozen logical 460×240 `contain` ROI (150×240, offset155,0) with `(x*0.75+155, y*0.75)`. No modification of pinned source or executor, and no unverified calibration. Width argument **1** only for experimental stroke preview; actual Egret engine support for width1 not yet proven.
4. Static RGB preview: white 460×240 logical canvas, dark-brown contour color `(49,38,43)` chosen as fixed visual reference, OpenCV `LINE_8` `thickness=1` with integer-rounded endpoints, **NOT** a native game render. Do not change shade or geometry post-outcome. Optional source+outline overlay must be labeled diagnostic.
5. Preserve raw chain count, dropped lengths, simplification/splitting counts, all stroke points, path source->logical mapping, length, stroke/vertex count, canvas preview, error image and source SHA hashes. Source/image labels must not be treated as true seam masks.

## Fixed diagnostics and gates

- At source 200×320, path centerline within1px support compared to original skeleton and false segments outside original line-source mask. At logical 150×240, measure source AniLines resized nearest-neighbor line matching within1px. Report collisions/overlaps after rounding, lost branches (graph degree>=3), original dark-clothing proxy count if useful **not semantic ground truth**.
- FAIL-CLOSED for wrong source/image SHA, out-of-bounds or NaN points, invalid thickness, missing raw chains, over quotas; preserve raw failure as negative. Do not claim a pipeline PASS from edge coverage or successful HTML review.
- Do not generate fill paths or alter calibration. Production planners, Stage6 executor, Bridge, Game Monitor, master, V14 frozen inference, V16 optional independent evaluator remain unchanged.
- Only after actual static result and user visual feedback may a **NEW ID** add contour pruning, per-color ownership, fill, native Egret or game runtime. The existing >=99% fill geometry gate and symmetric 3 logical px diagnostic color boundary are unchanged; actual CHALK only verified run-bound `post.pointCount - pre.pointCount`; independent E5 remains NOT_RUN under this experiment.
