# ENGINE-001 / V40 — internal color-boundary tolerance at 3 logical px

**2026-11-16 | PREREGISTERED / NOT_RUN**, created before V40 audit CI. Existing task ENGINE-001/V40; this is the **first diagnostic increment only**, not an unverified new paint planner. Explicit user approval: color fill **may overlap a neighboring color by up to 3 logical pixels**, including on both sides of the boundary, to close white gaps. Preserve all 410 user-preferred V35-B dark contours **above** the fill, unchanged. Do not reinterpret this as a zero-intersection or no-overlap policy.

## Frozen source and native evidence

- Original `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png` SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; 200×320 LANCZOS resized to 150×240 logical ROI at board x155..304/y0..239; BoardPane 460×240 logical and Egret WebGL PNG 1380×720 backing, exact scale3.
- Frozen actual native Egret [V37-P2 CI43747149144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43747149144), SHA `04e506a3bf41b5d197a19bb20e36e8f445d79dec`, artifact14175105717 ZIP SHA256 `a9d97229fada28875d718ba7c1c068464dfe8529fc1b313becb9a77e2ed50959`; 1945 width2 paint strokes followed by all410 width1 dark contours, 2355 strokes/5682 synthetic accepted vertices (not exact CHALK). Frozen C warm-paint variant, identical source-quantized native alpha for all A/B/C.
- Archived original source palette labels from `tests/run_engine001_native_color_boundary_audit_v38.py`: MEDIANCUT8, no dither, skip near-white palette IDs0..3, track classes4..7; PNG alpha thresholds24 and128 frozen. [V38](ENGINE001_V38_NATIVE_COLOR_BOUNDARY_AUDIT_PROTOCOL_2026-11-16.md) reported only **exterior from the whole silhouette**, which is **not** a check of *internal* wrong-color crossings. The negative [V39](ENGINE001_BOUNDARY_SHIFT_V39_PROTOCOL_2026-11-16.md) y-shift result remains rejected and will not be replayed as a candidate.

## Independent diagnostic policy

For every **actual** isolated color4/5/6/7 alpha PNG and each alpha threshold:
1. Identify native painted pixels whose **source owner** is another retained color4..7 (foreign required-class overlap). Report the total. This overlap is **not automatically an error**.
2. Measure Euclidean pixel distance at exact 3× native backing from each painted foreign-color pixel to the nearest original logical pixel belonging to that paint class, using `cv2.distanceTransform` with `DIST_L2` and `DIST_MASK_PRECISE` on the inverse frozen class target mask. **Allowed internal overpaint: distance <=9 native pixels =3 logical px.** Strictly >9 native px is internal out-of-tolerance. Count both populations, plus maximum foreign distance and per foreign class recipient; do not count the same pixel twice within a single owner-class layer.
3. Distinguish skipped near-white/transparent source foreground mask, exterior of overall retained-color silhouette, and outside logical source ROI x155..304; report overall-silhouette >9-native-pixel leakage separately. Internally allowed crossing is not an exterior pass, and an exterior pass is not an internal pass.
4. Report correct-class recall and missed source-target class pixels (as before). Do not credit another class' overpaint as correct own-class fill: coverage and tolerance are different dimensions. Report aggregate native painted pixels and fraction of foreign overlapping within tolerance, **not** synthetic or geometric brush proxies.
5. Verify original source SHA, frozen native artifact report and every report-linked SHA256; require pixel-exact A/B/C alpha across all six isolated/composite native PNG scenes. Reference final actual **composite** C PNG (includes real 410 later contour strokes); record its identity/hash and original-source RGB MAE / warm ROI MAE as a **separate recognizability/color diagnostic**. Do not infer final visible owner solely from isolated layers — layer compositing, dark-line occlusion and final RGB are a separate issue.

### Fixed outcomes and constraints

Audit CI PASS means source evidence integrity and deterministic metric execution **only**. Diagnostic internal tolerance PASS for this source requires **zero** foreign-color painted pixels farther than9 native px (for each alpha threshold and all required colors); report failures explicitly, no threshold tuning after result. This criterion does *not* replace the existing quality gate >=99% per required color, <=3logical px exterior, user-recognizability of facial/hair/hand details, or real game E4/exact CHALK `post.pointCount - pre.pointCount` and E5. If the source palette's segmentation does not correspond to actual visible semantic boundaries, flag interpretation as provisional, not as a license to hide violations.

**Next development after measurement:** preregister minimal resource-neutral **within-row endpoint allocation** using existing native brush/harness, preserving all410 contours and frozen 2355 strokes/5682 synthetic accepted vertices. Never move strokes without a signed A/B comparison: internal overpaint >3 px must not increase; each class own coverage and final-recognizability must not regress. Prior V39 entire-row y movement is excluded.


## After-run native archival alpha evidence — 2026-11-16

[CI43770499251](https://github.com/Kiddos19882/AutoDraw/actions/runs/43770499251) **E3 SUCCESS for archival source-bound audit only** SHA `13739e8b356df6bb8fef5aa3b627348f0f1652a7`, artifact **14183662948**, ZIP SHA256 `0d3af2787e38cfb2a9f8048eb7878e4b293cd2273fff3b3ceec00a36632734af`. Source and every frozen V37-P2 original native file hash verified, A/B/C actual Egret alpha pixel-exact on composite and all five isolates; original source RGB final native composite frozen source ROI MAE19.42033333, warm MAE27.90450328. The archived original C contains all 410 dark contours on top.

| α threshold | Actual foreign source-class native painted pixels (all owners) | ALLOWED within 9 native px | EXCESS >9 native px | Exterior >3 logical px |
|---|---:|---:|---:|---:|
| 24 | 38,479 | **38,479** | **0** | **0** |
| 128 | 35,660 | **35,660** | **0** | **0** |

Alpha24 by paint owner4: foreign11969/allowed11969/excess0, max distance6.708 native px; owner5:13630/13630/0,6.708 native px; owner6:7721/7721/0,6.0 native px; owner7:5159/5159/0,6.0 native px. At alpha128 corresponding foreign counts4:11067,5:12696,6:7126,7:4771, **zero** beyond 9 native px for each. **The agreed 3 logical px internal color crossing tolerance is already fulfilled in this source-bound Egret baseline**, so minimizing all wrong-owner overlap to zero would be counterproductive. These are overlap pixel counts **per isolated source-color paint class**; overlapping multiple owners may count the same native screen pixel more than once across classes. No inference of final semantic visible owner after dark outline compositing. Correct own-source-class recall remains4 71.08%,5 77.81%,6 57.71%,7 94.73% (alpha24), well below production >=99%; native alpha controls do not prove game E4/exact CHALK or E5.

**Decision:** V40-P1 diagnostic **PASS**, production/semantic color coverage still **BLOCKED**. Separately preregistered [V40-P2 horizontal endpoints](ENGINE001_V40P2_ENDPOINT_EXTENSION_PROTOCOL_2026-11-16.md): preserve all user-selected 410 contours, test actual Egret 0.25/0.5 logical x expansion and reject if resulting internal color excess>3px or own-color quality regresses. Historical V39 entire-row y-shift FAIL unchanged.
