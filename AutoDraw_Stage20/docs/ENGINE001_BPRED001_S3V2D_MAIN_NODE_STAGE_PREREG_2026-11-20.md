# ENGINE-001 / BPRED-S3v2d — frozen E0: source-proven main BoardPane Canvas vs separate mask, full S3 C0 stage

**2026-11-20. E0 frozen BEFORE any S3v2d code/native scenes.** Active BPRED-001 S3 only, no deviation to S4/S5/S6 and no S0 BLIND. Baseline original source commit \`66351d251710aa7f263edf9f3617b8f3f75675d5\`, [S3v2c native success CI44687444859](https://github.com/Kiddos19882/AutoDraw/actions/runs/44687444859), [raw artifact14606962926](https://github.com/Kiddos19882/AutoDraw/actions/runs/44687444859/artifacts/14606962926), exact 8 frozen independent S3 scenes with all 16 genuine Canvas captures +8 WebGL, archive ZIP CRC/43 SHA PASS. Original S3 scientific H1 **FAIL30/40**, H2 PASS20/20, C1 MODEL_ONLY_UNSAFE; original S3v2/S3v2b technical BLOCKED are retained.

## 1. Empirical ground truth for original Egret node disambiguation

Every one of 8 pre-selected original S3 scenes had **exactly two** \`egret.CanvasRenderer.prototype.renderGraphics\` non-hit-test calls with genuine saved Canvas PNG:
- **Source main BoardPane GraphicsNode:** drawDataCount=3 for A_ONLY or4 for A_THEN_B; node bounds \`x=-2,y=-2,width=464,height=244\` logical; context 1392×732 physical; original Canvas context transform \`[3,0,0,3,6,6]\`.
- **Board mask graphics:** drawDataCount=1, node \`x=0,y=0,width=460,height=240\`; context1380×720; transform \`[3,0,0,3,0,0]\`.
Both have real distinct geometry and PNG dimensions. This is E3 observation for the eight scenes, not proof for all80. The original P4D15 experiment captured only source main by requiring drawData>10 for 21 strokes; for 1/2 strokes we must use **frozen grounded node semantics**, not assume count1 or pick the first capture.

## 2. Frozen full stage scene protocol

The same **80 S3 exact immutable original plans** (width1..10 × CROSSING/NEAR_PARALLEL_OVERLAP × A_ONLY/B_ONLY/A_THEN_B/B_THEN_A) from original S3 source artifact14604987986; +10 original S3 replay cases and blank=91 final true WebGL. Use identical owner RGB/color order/points/source game. Browser **explicit Firefox159 executable**, original Egret5.4.1 BoardPane game blob46cc74de00b6cb5d207b1e1a2ffcd81613b6d388 and renderer blob76d950e0a8911888a9df3b675b866519ecf7bba4. Same frozen original S3 model C0 source-over; no retuning.

For **each of 80 scenes** wrapper captures **all original Canvas calls** with P4D15-style \`try/finally\` restoration and enforces **exactly two** with one and only one structural-match main and one and only one structural-match mask:
- main: bounds -2/-2/464×244, physical1392×732, transform3,0,0,3,6,6, drawDataCount=\`2 + source stroke count\`;
- mask: bounds0/0/460×240, physical1380×720, transform3,0,0,3,0,0, drawDataCount1;
- any missing, extra, or ambiguous capture, invalid context, mismatched selected node, changed source method/plan = BLOCKED. Selection **by geometry only**, never order, actual output resemblance, or post-hoc color/alpha quality. Save **all 160 original Canvas PNG** (80 main and 80 mask) and raw provenance, even though only main may enter C0; 91 true final WebGL PNG (+original 10 repeats, blank); no raw edits or masking away errors.

Align true main Canvas to original 1380×720 WebGL using exactly node (-2,-2), backing×3 and transform[3,0,0,3,6,6], preserving all 80 real intermediate ROI. Strict S3v2b validated deBG-only PNG source provenance against original S3 archived 91 WebGL; retain per-file raw SHA and independent decoded RGBA pixel equality, never change E0 criteria. Original S3v2 raw byte equality gate remains **archived FAIL**.

## 3. Frozen stage comparisons and decision

For each **40 original ordered AB/BA** compare C0 source-over applied to **isolated real main Canvas** A/B vs true ordered main Canvas AB/BA and, separately, original isolated true final WebGL vs ordered final WebGL; same original S3 H1 **max≤2/255 and mean≤1/255 per ordered variant union nonzero alpha**, report per-layer FP/FN/alpha/RGB, error maps. Technical E3: 80 real main+80 real mask+91 final PNG, 10 actual replays/blank0, no source/path changes, 91 deBG-only valid proofs, all stage transforms and raw archive SHA, unit tests for both structural capture types and fail-closed, original S0 BLIND unopened. CI PASS not a scientific H1 PASS.

If native main Canvas H1 **FAIL**, localize composite mismatch to Canvas rendering/quantization or capture stage (without asserting one specific root); if main Canvas H1 **PASS** but final WebGL FAIL, localize to texture/upload/readback stage. A cross-stage mismatch without valid spatial mapping remains BLOCKED. Original S3 H1 FAIL30/40 preserved regardless outcome; no retrospective alpha/RGB threshold adjustments, no source RGB owner quality acceptance.

**Constraints:** DEC-042 future-only, original E/F P4D18 protected-white source-quality FAIL, E4/E5/exact CHALK NOT_RUN; production/master/Stage6/Bridge untouched. After full S3v2d results, only frozen next decision/experiment within S3 or progress to S4 under demonstrated safety—not automatic.
