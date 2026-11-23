# ENGINE-001 / S5-LANE-P1 — signed native Egret 180-case seam E3 evidence (2026-11-23)

**Experiment:** `ENGINE001_S5_LANE_P1_NATIVE_ADJACENT_STROKE_SPACING_V1`, [prospective frozen E0](ENGINE001_S5_ADJACENT_LANE_NATIVE_SPACING_PREREG_2026-11-23.md). **Working branch:** `feature/image-geometry-optimization`. Repro code/CI commit [`9296a3434b43ec6c4936ae66a3e99adc347b63a6`](https://github.com/Kiddos19882/AutoDraw/commit/9296a3434b43ec6c4936ae66a3e99adc347b63a6) includes only upload fix after identical initial native runner SHA14a6935. Corrected complete [CI45089280114](https://github.com/Kiddos19882/AutoDraw/actions/runs/45089280114) job `137414902418` **COMPLETED SUCCESS**, exact head SHA9296a343. Earlier [CI45087460920](https://github.com/Kiddos19882/AutoDraw/actions/runs/45087460920) native successful but original ZIP absent due hidden directory filter; [negative trace](ENGINE001_S5_LANE_P1_NATIVE_E3_FIRST_RUN_AND_ARTIFACT_RETRY_2026-11-23.md) is not overwritten.

## Independent raw evidence validation

[Artifact 14780372372](https://github.com/Kiddos19882/AutoDraw/actions/runs/45089280114/artifacts/14780372372), ZIP `engine001-s5-lane-p1-180cases-normal-real-egret`: GitHub digest, separately downloaded ZIP SHA256 **`37673151b25bbb838bcd918f65fa0b81dad464db35842ce3cf6518c0a9e33705` MATCH**; ZIP CRC PASS 723/723, 722/722 report member SHA256 PASS. Windows source report uses backslash `\\` paths whereas GitHub Linux-style ZIP contains forward slashes `/`; only the path separator was normalized before independent validation, bytes and SHA digests were unchanged. `report.json` experiment ID, GitHub SHA/run ID, pinned sources, 180 distinct cases, 541 native PNG, 180 exact plans, native blank and raw member names all verified. Further 540/540 independent per-case A/B/AB `native_sha256` references match source PNG bytes. Blank native alpha max0. Independently decoded all 180 **actual** AB native PNG and recomputed masked backing-pixel holes at both alpha24 and alpha128 using saved exact lane geometry, with **0/180 disagreements** against result JSON. This is direct read of Egret-produced pixels, not a synthetic drawing.

Source pinned Egret5.4.1 BoardPane/WebGLRenderer engine Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer Git blob `76d950e0a8911888a9df3b675b866519ecf7bba4`, normal only `smooth=false`; 460×240 logical board and 1380×720 3× PNG backing. The job also passed Python 5/5 synthetic tests, source pins, existing JS+doc audit, and final member SHA validation. Historical effective widths1..10 derive from [archive E2](ENGINE001_S5_NATIVE_BRUSH_1TO10_CORE_WIDTH_MEASUREMENTS_E2_2026-11-23.md).

## Native observed results — same fixed E0 matrix, no threshold adjustment

| Gap ratio to nominal `lineStyle(width)` | Cases / width1..10×3 angles×2 phases | No holes in inter-centerline strip alpha≥24 | No holes alpha≥128 |
|---|---:|---:|---:|
| 0.75 | 60 | 60/60 | 60/60 |
| 0.90 | 60 | 60/60 | 60/60 |
| 1.00 | 60 | 60/60 | 60/60 |
| **All** | **180** | **180/180** | **180/180** |

Recomputed union comprises **157267 tested backing pixels** in exactly predefined strips between the two lane centerlines, central axial 20 logical units, full width1..10, angles 0°,45°,90° and phases (0.25,0.375)/(0.50,0.625). **Zero inter-centerline native alpha holes** in the tested matrix. Tests use 34-logical long two-point constant-width strokes, both individually (A,B) and true native A→B composite. Report overlap alpha-positive pixel count ranges 0..1052; at nominal 1.00 ratio overlap may be exactly zero on some positions even though both alpha gates have no holes in *between-lines* pixels. Do not misinterpret that as guaranteed continuous high-opacity paint beyond the tested strip or as an optimal universal stride. No alpha/RGB-over-foreign-owner, contours/curves, arbitrary offsets, Canvas parity, paint order among different colors, live transform or exact CHALK were tested here.

**Measured candidate geometric lane step for the initial S5-R4 experiment:** `pitch = 1.0 × nominal game lineStyle(width)` for these **specific sampled straight direction/phase configurations** is supported as *model proposal only*, not universal native guarantee. Conservative 0.90 ratio remains a preregisterable comparator in a future experiment, but do not switch thresholds after outcome or present one pitch as proven everywhere. Native revalidation and source ownership/leakage rules still apply to each proposed real scene.

## Acceptance status / next

- E0 design frozen before code: PASS provenance.
- E2 pure case construction and native geometry tests: PASS 5/5 on exact run.
- E3 native archive technical completeness and independent pixel seam analysis: **PASS for 180 fixed cases**, exact run SHA9296a343, ZIP SHA above.
- Game source full coverage, alpha RGB quality, 3-logical-pixel leakage, protected details and S5-R4 actual regional paths: **NOT_RUN**.
- Source owner MISSING, native coordinate mapping UNVERIFIED; production, Stage6, live E4/E5 and run-bound exact CHALK **BLOCKED/NOT_RUN**.

**Single next step:** freeze S5-R4 *new* E0 based on S5-R3 four-original×2 model baseline and these measured Egret lane-spacing constraints: repeated region-stratified, EDT-guided offset lanes, initial pitch 1.0 nominal width as **candidate** and optional 0.90 separate fixed comparator only if preregistered; maintain same 2000/200 and 1400/80+600/120 budgets, no invalid foreign-cell proposals, protected dot≥120 and normal smooth=false. Synthetic E2 then four-original source-only E2. No jumping directly to gameplay from this seam measurement.
