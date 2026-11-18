# ENGINE-001 / R2-P2-P2 — separate source micro-islands from unsupported G32 swatch regions

**ID:** `ENGINE001_COLOR_ISLAND_R2_P2_P2_SOURCE_SUPPORT_AUDIT`. **First registration:** 2026-11-18, BEFORE the new R2-P2-P2 diagnostic runner/CI. **Status:** E1 source/archive audit DONE; new diagnostic E2/E3 NOT_RUN; no pixel cleanup/production changes authorized by this research artifact. **Baseline branch SHA:** `6b7d6e34ad2c201a16f5c21e9ef38949fbf3a4ca`. Parent `ENGINE001_COLOR_ISLAND_R2_P2_STABLE_RGB_BASELINE` [root-cause plan](ENGINE001_COLOR_ISLAND_R2_P2_ROOT_CAUSE_AND_NUMERICAL_REBASE_PROTOCOL_2026-11-18.md) / DEC-033.

## 1. Motivation and independently checked pre-run E1 data

The original question is **false small painted color islands**, especially G32 assigning a vivid pink/magenta near original brown/dark RGB, *without erasing true original details*. Do not conflate the two different component spaces:

- (A) **Source region fragmentation:** 4-connected region IDs from original RGB after fine SLIC clipping to original background, built before any game color. These IDs have no inherent game32 owner.
- (B) **False/disconnected game swatch assignment:** G32 RGB to 32 real swatches derived from source pixels. A G32 color island can cross multiple original source regions, and a source singleton can be G32 white. Never infer that deleting A automatically fixes B.

Frozen inputs: original `testImages/wV6VeZI9S1Y.png` SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a` 200×320, source logical150×240; palette blob `461b5f3725b9b79888ad36e807b3cf4c9e445e98`; exact M1 [CI44216262024](https://github.com/Kiddos19882/AutoDraw/actions/runs/44216262024) SHA `5d31bcf0ef3d6f71848f7e89852c3ddf64a9d412`, artifact14388687061 ZIP SHA256 `8bedc496bf01cf7205ecc8ceb7be8eb0f68b751b11c53ea67dbdd3982c7fe583`; frozen G32 SHA256 `b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637`; archive M1 report SHA256 `89e4135ecd71820e21394751bb4a11f9a17b01edcddcfa6f1bd1f538f8a16969`.

**E1 only, no new candidate output:** independently opened the source-linked M1 ZIP, validated ZIP CRC and all 27 report-linked file hashes, and measured original `M1_original_region_ids.tiff`, `source_protected_union.png`, `original_RGB.png`, `B0_frozen_G32.png` directly. Exactly 179 source singletons: 81 protected, 98 unprotected; 68 have a distinct 4-neighbor source region, 83 diagonal-only, 28 fully 8-isolated (overlapping protection group). Of the 179, G32 maps 127 to **white**; 1 to dark-purple swatch `#A5015B`; **0 to `#E20085`**. None of these 179 original RGB samples is neon-pink under a simple high-ratio red-and-blue vs green check; a singleton is not unsupported original RGB just because G32 maps it to an unexpected swatch.

With diagnostic `CIELAB_chroma(G32)-CIELAB_chroma(original)>12` on the **complete** source ROI: 1368 G32 output pixels flagged, only12 overlap the source singleton mask. G32 swatch `#A5015B` occurs 217 pixels of which215 exceed +12 chroma vs source; `#E20085` occurs14, all14 exceed. These are **quantitative color-support suspects, not reviewed ground truth false colors**. No global pink ban; real original magenta details remain valid. `#A5015B` has 1 overlap with singleton source region. Attribution: 1368 excess-chroma pixels cannot be eliminated by blindly deleting 179 source singletons.

## 2. First diagnostic version P2-P2-A — frozen algorithm before new runner

**Research question H1:** pixelwise swatch mismatch and source tiny-region topology are separable; one or more G32 pink/magenta clusters have insufficient original chroma/hue support, while most source singletons are not the source of those palette artifacts. **H0:** reported metrics fail to distinguish source fragmentation from unsupported swatch assignment or the data provenance is inconsistent.

This is **read-only diagnostic**, not image modification. Independent outputs: per-source-region topology table, pixelwise swatch confidence and swatch-specific 4-connected suspicious component tables; all frozen source pixels and labels remain unchanged.

### Identity and required inputs

- Verify raw original PNG exact byte SHA; read logical RGB directly from *pinned M1 archive* and cross-check report.source SHA, dimensions (240,150,3) and M1 archive ZIP SHA/CRC/file hashes. No new interpolation or segmentation; frozen masks and region IDs only. Verify game palette as exact Git blob bytes SHA `461b5f37...`, parse exactly 32 unique swatches. `B0_frozen_G32.png` RGB pixels must match an existing swatch **exactly**, not a nearest swatch; any unknown RGB `BLOCKED_UNRECOGNIZED_G32_SWATCH`.
- Verify `source_protected_union.png`, `M1_original_region_ids.tiff`, `M1_merged_region_ids.tiff`, `source_white10_border_connected.png`, and original raw SHA. G32-white pixel mask is not a semantic background mask; compare only as separate diagnostics.
- For each original source region area≤1,2,4,8,24 compute original RGB region medoid, protected union, distinct adjacent 4-regions, adjacent 8-only regions and nearest source Lab ΔE00. **A diagonal-only pixel is not automatically false**; do not merge non-four-connected regions to claim fewer islands. Do not erase source pixels for this experiment.

### Swatch mismatch diagnostics — fixed thresholds

Using skimage CIE Lab (`rgb2lab(uint8/255)`) on original and exact frozen G32 colors:
1. `suspect_chroma` iff `C*_game - C*_source > 12.0`, independent of swatch name.
2. `suspect_deltaE` iff pixelwise original/G32 `ΔE00 > 22.0`.
3. `suspect_hue` iff source C*≥12 and G32 C*≥22 and wrapped absolute hue angle difference >45°. Hue check **disabled on neutral source** to avoid unstable hue.
4. `suspect_union` = any of 1–3. Also report intersection/chroma-only and p95 ΔE00 independently.
5. For each of the 32 actual swatches, compute **4-connected components** of the `suspect_chroma` and `suspect_union` masks **restricted to that exact swatch**; 4-neighbor connectivity, hist area1/2/4/8/24 and per-swatch pixel counts. Report all swatches, including white, but separate swatch white from original semantic background. The diagnostic hue/chroma labels are `SUSPECT`, never proof of false original detail.

Diagnostics must distinguish overlapping source singleton mask, protected pixels and B0-white/source-foreground mismatch; masks should be saved with correct logical pixel coordinates. Never use hue adjacency alone to claim dark and pink cannot coexist. User visual review of bright spots/skin/hair/dress is required.

### Preliminary safe micro-merge *eligibility ceiling* only, NO modification

Report a conservative **upper bound** for source singleton eligibility: source region unprotected, at least one **4-neighbor nonbackground** different region, neighbor seam unprotected, original-LAB ΔE00 to an actual neighboring original source pixel ≤4.0, same coarse SLIC region. No target if none; do not actually recolor/merge anything. This may yield very few candidates and is an honest result, not a reason to weaken guards. Same logic can later expand to area≤4 **only with a separate versioned P2-P2-B prereg**. Users' `leakage≤3 px` or brush quality gates are **not** proven by this geometric ceiling.

## 3. Controls, E2/E3 and acceptance

- **B0:** frozen G32, source original, pinned M1 source regions; **A1 diagnostics** only, no outputs transformed. A1 must reproduce canonical E1 counts 179 original singletons/81 protected/83 diagonal-only/28 isolated and report source swatch chroma/ΔE/hue counts. Do not hardcode expected measured image counts into classifiers; regression tests may independently check pinned data.
- Synthetic fixtures: genuine bright pink original vs game pink should NOT be chroma/hue-suspect; dark original vs magenta assigned should be suspect; neutral source should skip hue guard, not chroma; 4/8 connected diagonal source fragments counted separately; protected singleton not eligible; palette RGB not matching exact32 fail-closed; archive corruption and source SHA mismatch fail-closed.
- E3 separate lightweight GitHub Actions on working branch with bounded checkout 5m, pinned CPU numpy/scikit-image/scipy/Pillow, sha-linked download artifact14388687061 and stage-only tests, `upload-artifact if:always()`. Save original/G32/region/protection/chroma/union/overlays, RGB panel at 150×240 scales, 6 detail-ROI crops, swatch/component table, per-region ledger, JSON with SHA source/artifact and per-file hashes. No new DINO or BiRefNet inference; pretrained helpers are unnecessary for this diagnostic.
- **A1 technical PASS** iff all frozen identities, 32 swatches, exact RGB alignment, masks, image-level reconciliation, all unit contracts and file hashes pass. Any numerical difference/unknown swatch → `BLOCKED`; this is not a color-quality gate. **Color quality and visual** remain `NOT_VALIDATED/PENDING`. No new image candidate, N1/N2 effect, real game, brush E3/E4, independent E5 or CHALK can be inferred.
- **Next after A1:** evaluate top suspicious components visually and identify truly unsupported swatch decisions while retaining genuine small source features. Only then create new **P2-P2-B** candidate protocol for original-grounded region-level game32 assignment / source-safe tiny cleanup with source+visual acceptance; do not retroactively change M1, G32, R1/P1, or production.

## 4. Scope and implementation cap

Only new test-only runner `tests/run_engine001_color_island_r2_p2_p2_audit.py`, its synthetic tests, and one isolated workflow. Reuse existing source hash/CI hooks; do not modify `source/preparation`, legacy runners, `master`, frozen image/palette/G32, V44-B 410 LAST, Stage6, Game Monitor, Bridge or CHALK estimator. No new training, no new neural weights or extra GitHub large archives. **At registration P2-P2-A: PLAN_REGISTERED, new code/tests/CI NOT_RUN**.


## 5. Frozen first A1 diagnostic execution, 2026-11-18 (append-only result)

[CI44220144140](https://github.com/Kiddos19882/AutoDraw/actions/runs/44220144140), SHA `e59d74cbf4aaab818cb26245be670bf6be0f4376`, job `134519663417`, E3 technical SUCCESS; 15/15 synthetic source-contract tests PASS (E2). Artifact `14389304383`, ZIP SHA256 `6665d2215a2436c5d048d47a20cbd000ec0c11da2fa6f673da587742fe842c81`, CRC PASS, 21/21 report-linked SHA256 PASS, report SHA256 `2856754f3476db404da164ab9f98cde7180cbf6b690f9a63056f71e0cc0c695a`; environment-pip-freeze extra file SHA256 `d9977d3ffef5c8958eae1cd1e85921ae05cfb0e872809c0f67bfe52c26fa9810`. M1 archive and raw original/palette SHA checked. A1 technical `DIAGNOSTIC_PASS_IMAGE_QUALITY_NOT_VALIDATED`.

Original source has 755 4-connected fine regions, 179 singletons (81 protected, 83 diagonal-only, 28 fully 8-isolated; groups overlap), and 518 regions area<=24 of which332 touch protected pixels. Frozen G32 mapped127 of179 source singletons to white. Conservative **non-destructive source singleton merge eligibility ceiling only5/179** (unprotected, real four-neighbor seam, same coarse source region, original-source neighbor ΔE00<=4); these are not accepted merges. On **all 36,000 original pixels**, G32 has 1368 pixels with swatch chroma > original chroma +12, **12 overlap original source singletons**, 1145 overlap source protected geometry; 102 are ΔE00>22, 14 satisfy chromatic hue disagreement>45°, union1441. G32 #A5015B: 217 pixels, 215 chroma-suspect, 122 4-connected suspect components, 82 area1; #E20085: 14/14 chroma-suspect in10 suspect components. **These are heuristic suspects, not confirmed false-color labels; no global prohibition of pink**. B0-white/source-foreground disagreement3929 remains, source bg21376 versus palette white25305 (not a semantic background truth).

Source original and frozen G32 are unchanged: this was an **auditor, not a recoloring candidate**. Numeric ΔE00/chroma/hue flags are *suspicions*, not visually confirmed false colors; original protected pixels preserve geometry, not necessarily their wrong game swatch. Visual review PENDING, source-quality improvement NOT_VALIDATED, game32 output NOT_CHANGED, native Egret E4/E5 and exact CHALK NOT_RUN.

**Interpretation:** R2-P2-P2-A1 establishes that reducing 179 original-RGB source singletons is not an effective proxy for correcting 122 disconnected `#A5015B` suspicious game swatch components. 1145 chroma-suspect G32 pixels are on geometry-protected source pixels, so preserve their original geometry while independently testing whether the game swatch should change; **do not** treat a protected pixel as a mandate to retain a known-unreliable palette assignment. Any new correction requires a separately preregistered **B1** experiment ID and source+visual gates. A1 does not mean the 1368 pixels are all visually wrong or that simple desaturation is correct.
