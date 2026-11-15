# ENGINE-001 / V38 — frozen native color-boundary gap audit

**2026-11-16 | PREREGISTERED / NOT_RUN** before dedicated audit CI. Task ENGINE-001. This is **measurement only**, no new brush algorithm, no changed production/Stage6/Bridge/executor/Monitor, no new image candidate, no game E4. User's full **V35-B 410 dark contours** must remain unchanged.

## Evidence and why now

Native V37-P2 [CI43747149144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43747149144), SHA `04e506a3bf41b5d197a19bb20e36e8f445d79dec`, frozen artifact14175105717 ZIP SHA256 `a9d97229fada28875d718ba7c1c068464dfe8529fc1b313becb9a77e2ed50959`. Archived A/B/C: identical Egret alpha footprints, same 1945 width2 paint then 410 width1 dark detail =2355 strokes/5682 synthetic vertices **NOT exact CHALK**, only 218 synthetic-vertex native harness headroom to5900. Color-only fixes restore orange/pink appearance but cannot repair geometric color coverage. Historical per-class native alpha24 recall 4 71.0778%, 5 77.8104%, 6 57.7122%, 7 94.7256%; whole source-quantized four-class silhouette union93.8684%. Need identify **where** missed pixels occur and distinguish edges/interior/class spill before rearranging any strokes.

Original `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, 200×320, LANCZOS resized150×240. Frozen labels: Pillow MEDIANCUT8, dither NONE, source-ROI, skip near-white classes0..3. Pad with background -1 to logical460×240 at x155..304; repeat each logical pixel 3× in native 1380×720. Do not use a rectangular/CV2 brush proxy; all actual stroke alpha masks come directly from archived original true Egret WebGL PNG.

## Frozen audit method and gates

1. Validate immutable source SHA, artifact `report.json` experiment ID and `source` metadata, **all listed artifact file SHA256** before measurement; verify A/B/C decoded native RGBA alpha *pixel-for-pixel identical* across original five isolated paint/detail layers and composite; refuse on any drift.
2. For each required palette class 4..7 and alpha thresholds **24 and 128** report target pixels, painted target pixels and recall; missed target pixels; off-class painted pixels within required palette foreground, painted skipped near-white pixels, exterior logical-board ROI pixels; connected missed components with 8-connectivity and counts at area>=9/36/144 native pixels, largest component area and centroid (record these only as descriptive diagnostics).
3. **Boundary vs interior:** compute cv2 Euclidean distanceTransform of **target class mask** in actual 3× backing; report missed target pixels where source target-class interior distance>=3 native pixels (1 logical px), and total missed. A large share of misses near a boundary suggests class allocation/brush placement; it does *not* by itself establish the correct stroke shift. Avoid interpretation if source mask itself is unsuitable. Record distinct target class interior counts.
4. Composite (fill union isolated classes4..7 **excluding detail**), report silhouette recall and precision at both alpha thresholds, missed target foreground and off-foreground paint. For leakage count any painted pixels >3 logical px (9 native pixels) from **any** original quantized foreground, plus board-ROI exterior count. Preserve all raw PNGs and output JSON with raw input hashes, tool versions and analysis code SHA; no extra synthetic render is permitted.
5. At this diagnostic phase original native RGB color candidate A/B/C may differ but identical mask geometry must be demonstrated. Existing game color coverage acceptance >=99% per required class, <=3 logical px exterior, exact `CHALK=post.pointCount-pre.pointCount`, and E4/E5 remain unchanged. CI PASS for audit means reproducible measurements, **not** quality PASS.

**Decision:** only after audit, design independently preregistered resource-neutral boundary-placement V39 on frozen full V35-B contours and source mask, **not** simply adding paths that violate 5900 native cap or actual game CHALK. Keep all historical V35–V37 results and failures. For new brush-dependent hypotheses use actual BoardPane/Egret WebGL A/B; model-only candidate planning must be labeled E1/E2 and never counted as native quality.


## After-run archived Egret alpha audit — 2026-11-16

[CI43767506202](https://github.com/Kiddos19882/AutoDraw/actions/runs/43767506202) **SUCCESS (E3 audit execution only)**, SHA `e31d920e9b8cf40a9d1cac42c76f7a3ec1a56221`; archived input original Egret PNGs from V37-P2 verified by all report-linked hashes. New V38 evidence artifact **14182976831**, ZIP SHA256 `b3638a459fcdeeaac1cf2d2e3a58b7a08f211f7eec527221b6d5f85db6fd3208`, `audit.json`. A/B/C archived true native alpha exact across all composite+five isolate scenes.

| α threshold | Class 4 recall | Class 5 recall | Class 6 recall | Class 7 recall | Fill-only source foreground recall / precision | missed foreground native px | outside >3 logical px |
|---|---:|---:|---:|---:|---:|---:|---:|
| 24 | 71.0778% | 77.8104% | 57.7122% | 94.7256% | 93.8684% / 87.9985% | 9127 | **0** |
| 128 | 68.0485% | 75.7529% | 55.5366% | 93.9692% | 92.4938% / 88.8773% | 11173 | **0** |

At **α24** each required class misses **zero** pixels with its quantized source-class distanceTransform>=3 native px (~1 logical), while class misses 4=10235, 5=9534, 6=8902, 7=2608 native px occur nearer boundaries. At **α128**, the corresponding deeper class misses are 19,21,8,49 native px (very small relative to class miss counts), demonstrating sensitivity to opacity threshold. There are hundreds of tiny disconnected missed target components per class (α24 809,643,507,157); these measurements indicate **thin local class allocation/edge registration** rather than large class interiors unpainted. This is a diagnostic about **MEDIANCUT source target classes**, not verified source RGB semantic gap nor direct proof any specific shift repairs it. Native alpha paint outside original board ROI = 0, >3logical px from quantized original figure=0 on this frozen image. Full 410 contour geometry and real game quota untouched.

**Action:** independently prereg V39 native 0.25 / 0.5 logical y-shift of current paint segments toward own-class supporting source neighbors, **all410 V35-B dark contour paths immutable**; no extra points, source RGB or brush proxy. Require real Egret test and existing quality gates; do not reinterpret V38 audit `E3 SUCCESS` as per-color coverage quality PASS.
