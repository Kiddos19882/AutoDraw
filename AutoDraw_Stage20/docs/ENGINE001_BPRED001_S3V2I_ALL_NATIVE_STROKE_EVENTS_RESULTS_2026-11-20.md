# ENGINE-001 / BPRED-S3v2i — оригинальные события `Canvas2D.stroke()`: успешная физическая локализация (2026-11-20)

**Статусы:** E2 **PASS 45/45**, E3 технический **PASS**, H1 `last genuine stroke snapshot == real main Canvas` **PASS 24/24**; прежний источник двухцветного Canvas source-over C0 остаётся научно **FAIL**. Не переходить в S4 BLIND и не переносить модель в production.

Frozen independent-before-code [S3v2i E0](ENGINE001_BPRED001_S3V2I_ALL_NATIVE_STROKE_EVENTS_PREREG_2026-11-20.md) Git blob `9350e69c5f83747a46c71eeb9142065be928a7a5`; previous strict S3v2h [BLOCKED evidence](ENGINE001_BPRED001_S3V2H_STROKE_STEP_BLOCKED_RESULTS_2026-11-20.md) remains unchanged. First S3v2i [CI44718005217](https://github.com/Kiddos19882/AutoDraw/actions/runs/44718005217) technical FAIL **before E3** on two unindexed new documentation records, while 45 E2 tests passed. Markdown navigation indexed in docs and [CI44718171159](https://github.com/Kiddos19882/AutoDraw/actions/runs/44718171159) PASS. Rerun unchanged research runner [CI44718397908](https://github.com/Kiddos19882/AutoDraw/actions/runs/44718397908), exact source SHA **`8f93ceaaf21573c7bbf8f26422424080a8e201ef`** technical **SUCCESS**, original Windows Firefox159/Egret5.4.1. [Native raw artifact14621430428](https://github.com/Kiddos19882/AutoDraw/actions/runs/44718397908/artifacts/14621430428) downloaded and independently validated ZIP CRC + **344/344** report-listed SHA256; ZIP has **345** total entries including `report.json`.

## 1. Exact frozen source and acquisition

Same 24 existing original S3v2f source scenes, width **1,5,10** × relation **CROSS_ROTATED,NEAR_SKEW** × variants **A_ONLY,B_ONLY,A_THEN_B,B_THEN_A**, original immutable [S3v2f parent E3 artifact14617442073](https://github.com/Kiddos19882/AutoDraw/actions/runs/44710870514/artifacts/14617442073) source code SHA819b7fd2, ZIP CRC+655 member SHA verified before new acquisition. Source plans read from stored original JSON, no trig regenerated/heuristic rerank. Original game and reference renderer blobs byte-pinned, 13/13 files pinned. Scope reuses original unmodified JS observer blob383e0b..., original Egret CanvasRenderer true main and true mask, no changes to engine/compositor/executor.

- 24 real main Canvas1392×732 original PNG, 24 separate mask Canvas1380×720 PNG, 24 real WebGL plus3 true replay and 1 blank alpha0 = **28** native final PNG.
- **60 authentic immediate post-`stroke()` main Canvas PNG**: 6 width/relation families, each A_ONLY2+B_ONLY2+A_THEN_B3+B_THEN_A3 = **10** per family.
- **6/6 A_ONLY** and **6/6 B_ONLY** show **2** main Canvas `stroke()` calls; **6/6 A_THEN_B** and **6/6 B_THEN_A** show **3**. All 24 source scenes have 2 distinct original CanvasRenderer nodes, source meta preserved; mask `stroke()` count 0 in first strict v2h (v2i per-scene recorded separately), native methods restored.
- Frozen pre-source main and final native WebGL content verified against parent; 3 replay controls exact on declared 162×162 ROI (NOT full-frame). Frozen exact last-event vs original same-run main Canvas: **0 RGBA different pixels across all24** = H1 PASS.

## 2. Original actual stroke effects, no count-based owner guess

The offline posthoc audit used only raw event PNG and `ALL_NATIVE_STROKE_COMPARISONS_24.json` from successful E3. These are **observations** of the original renderer, not a reconstructed stroke predictor.

| Original variant | Main calls per scene | First immediate snapshot vs independently rendered first owner | Later meaningful Canvas change | Final call vs previous |
|---|---:|---:|---|---|
| A_ONLY | 2 | exact RGBA | none | **0 RGBA pixels** |
| B_ONLY | 2 | exact RGBA | none | **0 RGBA pixels** |
| A_THEN_B | 3 | exact A_ONLY RGBA | second call changes pixels | **0 RGBA pixels** |
| B_THEN_A | 3 | exact B_ONLY RGBA | second call changes pixels | **0 RGBA pixels** |

**24/24** first snapshots exactly match true same-run independent isolated first-owner Canvas RGBA, physical backing1380×720 after fixed source-node alignment. In **12/12 ordered** scenes, second event causes nonzero true physical RGBA changes (individual changed physical pixels **282..2813** across observed ordered width1/5/10 cases). The final native event is **pixel-neutral in all24**: raw first vs second isolated and second vs third ordered RGBA byte-equivalent after decode, **zero** pixels changed. These measurements explain earlier strict S3v2h expectation "1 / 2 actual `stroke()` calls" was wrong, while evidence supports first logical owner followed by genuine second logical owner effect, plus a final visually no-op call. Do NOT infer why the last `stroke()` was called; its path/operation intent has not been proven.

Actual event `globalCompositeOperation` = `source-over`, `globalAlpha` = 1, `lineCap` = `round`, `lineJoin` = `round` in all60 raw events. **Subpixel geometric distinction:** true `getTransform()` inside stroke width1 = `[3,0,0,3,7.5,7.5]` (all width1 events), whereas widths5 and10 = `[3,0,0,3,6,6]`. The original Canvas main node final source transform is `[3,0,0,3,6,6]` for all. This shows width1 native stroke subpixel-offset handling, **not** independently proven causal explanation for source-over RGB discrepancy; keep source physical vs logical distinct.

## 3. The original failure is not solved by this observation

Using unchanged original S3 C0 straight-sRGB source-over on **12 ordered** A/B variants from these six selected pairs:
- original Canvas source-over H1 max≤2/mean≤1 passes **8/12**, fails **4/12**;
- original C0 followed by frozen QH→WebGL passes **6/12**, fails **6/12**.
- original full prospective source S3v2f two-owner H2 **FAIL14/40** preserved; S3v2g integer P2 **FAIL**; S3 original C0 H1 **FAIL30/40**.

No original quality gate is relaxed. The real first/second event chronology and exact owners now provide a genuine pixel oracle for next research, but knowing the pixels *after* each stroke is not yet predicting those RGB pixels from inputs in advance.

## 4. Next bounded step

**NEXT within S3:** preregister a separately versioned study of *original Canvas2D source-over implementation* using observed exact first (source A or B), exact isolated second (source B or A) and true post-second Canvas, with original actual alpha/rounding and transform phases. Examine possible non-associativity, quantization and coverage by true physical pixels; no change to game, original model H1 gates or prior S3v2g P2 result. Any newly proposed formula must then be tested on separately frozen **new** native scenes before claiming safe RGB prediction. No S4 BLIND, no S5 full E/F safe claim, no S6 cost optimization.

P4D18 original E/F protected quality still FAIL. E4 live game/E5 independent/exact game CHALK `post.pointCount-pre.pointCount` NOT_RUN. Production, Stage6 executor, Bridge, Monitor, original game/renderer and master untouched.
