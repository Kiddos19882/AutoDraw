# ENGINE-001 / S5-LANE-P2 — signed real Egret 1..10 normal joint raster E3 (2026-11-23)

**Technical E3: PASS for the frozen 120 native cases. Geometric finding:** one connected `moveTo+lineTo` 3/5-point normal path and its separately drawn same-color two-point segments differ in RGBA for 120/120 cases, but no alpha≥24 or alpha≥128 native pixel lies farther than `width/2+3 logical px` from the original centerline on this tested board. This is an experimental **positive conditional basis** to research source-owner-safe connected filling, **not** full image-quality, native-game calibration or exact CHALK proof. [Frozen E0 before code](ENGINE001_S5_LANE_P2_NATIVE_NORMAL_MULTI_VERTEX_JOINTS_PREREG_2026-11-23.md).

## Code SHA and raw evidence

- Branch `feature/image-geometry-optimization`; exact P2 runner/test/CI SHA **`fc75e750c75a45abd87e4d6595b166694319fb3b`**. [CI45123140170](https://github.com/Kiddos19882/AutoDraw/actions/runs/45123140170), job `137521300877`, completed **SUCCESS** on all required steps: six synthetic geometry/alpha tests, existing real renderer JS tests, docs audit, pinned sources, 120 real Egret WebGL scenes and native raw pixel member verification. Native Egret5.4.1 source blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, original renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`.
- [GitHub artifact14795090359](https://github.com/Kiddos19882/AutoDraw/actions/runs/45123140170/artifacts/14795090359) `engine001-s5-lane-p2-normal-multipoint-joints-120-native-cases`; **ZIP SHA256 `a7693e3deccac39baa0a7e7447234c791a2027b683e30aee8a1c3fd772e66672`** exactly matches GitHub digest and independently downloaded ZIP; **363/363 ZIP CRC PASS**, **362/362 internal member SHA256 PASS**. 120 source geometry PLAN JSONs, 240 actual Egret PNGs P/S, true blank (alpha max0), all 120 per-image native sha256 references validated.
- Independently decoded all **240 native images** with Pillow/numpy, rebuilt pixel-center logical mapping `((x+.5)/3,(y+.5)/3)`, remeasured ROI alpha≥24/128, 3px overshoot to true centerline-segment distance, RGBA differences, joint disks around all internal vertices and checked every reported metric for **120/120 cases**. No synthetic capsule image used as evidence. Sources and output are offline native WebGL; no fresh user-PC game runtime, E4/E5, source owner game mapping or exact CHALK.

## Frozen observed matrix

10 nominal widths1..10 × turn deflections45°,90°,135° × two XY phases (0.25,0.375)/(0.50,0.625) × 3-point L/5-point serpentine paths = **120** cases. Two images per case: P = one connected `smooth=false` normal path, S = independent two-point segments rendered sequentially in native source-over.

| Native outcome | alpha≥24 | alpha≥128 |
|---|---:|---:|
| P-vs-S XOR threshold-ink backing pixels summed across all120 | **408** | **742** |
| Native P backing pixels beyond Euclidean distance `width/2+3px` from any segment | **0** | **0** |
| Native S backing pixels beyond same `width/2+3px` | **0** | **0** |
| P-vs-S RGBA array changed cases (all channels, all phases) | **120/120** | **120/120** |

The union across many cases is a count of **distinct image-coordinate pixels in independent scenes**, not one painted image; these are not normalized appearance percentages or game CHALK. Difference at joints can arise from alpha compositing and rasterization despite both being contained in the tested broad envelope. This experiment **did not** test source owner boundaries or color mixing: a 3px allowance is only a diagnostic threshold and must not justify overpainting foreign pixel owners in S5. Nor did it test angles beyond45/90/135, moving pointer FPS, production client transform, variable thickness in one path or arbitrary nonaxis paths. Round-join API docs are prior expectation, native PNG is the actual measurement.

## Network method attribution, historical runtime and next step

[Egret Graphics API](https://www.egret.uk/docs/egretengine/engine/egret.Graphics/) **consulted as source** for `lineStyle` round cap/joint possibilities; actual E3 **APPLIED original Egret WebGL renderer**, not ideal geometric cap. [LaValle coverage planning](https://msl.cs.uiuc.edu/planning/node351.html), [Choset/Pignon](https://publications.ri.cmu.edu/coverage-path-planning-the-boustrophedon-cellular-decomposition) and [connected Boustrophedon optimization](https://arxiv.org/abs/1907.09224) **used to motivate connected route candidate**, but **NOT** implemented in this renderer-only P2. EDT/Medial Axis/Contour-Parallel/Spiral not used for P2 native rendering (EDT remains E2 source preflight in R7).

Historic Nov1 game monitor [continuous_turns CHALK211](../data/results/brush_behavior_tests/experiment-20261101-085442-b10-continuous_turns-9906a108/monitor_report.json) and Nov2 [int006_turns CHALK193](../data/results/brush_behavior_tests/experiment-20261102-061433-b10-int006_turns-6157d6d8/monitor_report.json) were **actual historic run-bound** point deltas; live smoothing setting was not explicitly logged, so they DO NOT validate current normal/smooth=false gameplay or permit a predictive points-per-stroke formula. Game Monitor/Bridge and desktop state remain unverified for present S5.

**Single next:** freeze separate **S5-R8 original-source research E0** to build connected within-owner multi-offset sweep paths with entire polyline `swept_capsule_pixel_masks` owner/alpha check, signed candidate/vertex budgets and independent four-original visual gates. Reuse native P2 as conditional joint evidence, require a new native scene/coordinate calibration before any executor/Stage6 gameplay. Do not change frozen S5-R7 failure or production. Historical R3–R7 two-point stroke budgets are not game CHALK.
