## 2026-11-18 — ENGINE-001 B1-R-P3B static engine128 palette32 research (no production)

- Independent prereg P3B, source-only 32-of-exact-engine128 greedy swatch facility selection A_BALANCED/B_FACE_DETAIL, full original RGB+accepted P2D recomputation, new 13 source regression tests, bounded CI and one ZIP of all source/32/128 diagnostic/ROI images. [CI44282755427](https://github.com/Kiddos19882/AutoDraw/actions/runs/44282755427) SHA `1db7d085e96b1a0449ae388c4dc663d997392a88` E2 13/13/E3 PASS, ZIP CRC/83 hashes PASS. Both selectors use identical selected 32-set per source; all 8 prereg numerical original-source gates PASS but **user game32 visuals PENDING**, ~4.9k tiny color islands remain. Old P3 8/8 image FAIL frozen; initial CI44282518621 key assertion technical FAIL retained. Static engine128 RGB does NOT prove runtime color-accessibility; no Stage6/Monitor/Bridge/master edits or CHALK assertions.

## 2026-11-18 — DEC-036 and ENGINE-001 B1-R-P3 actual game32 research negative

- User visual signoff approves **both P2D guards D_BORDER and D_COMPONENT24** across source C096/C192 for next stage; DEC-036, old P2D frozen outputs unchanged, no forced winner.
- Added prereg separate P3 original-first game32 with 2 ablations per 4 approved RGB candidates, deterministic 32 real game swatch pin, protected-source hue/chroma abstention instead of unsupported pink, 13 synthetic tests, one ZIP artifact. [CI44278535963](https://github.com/Kiddos19882/AutoDraw/actions/runs/44278535963) SHA `c1bfbfa7b85d6cd86e793f81fb9f54e92fb8039d`, E2 13/13, E3 SUCCESS, CRC/59 file SHA PASS. **8/8 original-image gates FAIL**, primarily male face and >720 unresolved on guarded: no game32 or native acceptance. Further full swatch provenance E1 before new variants. No G32 prior map, V44, master or production changes.

## 2026-11-18 — ENGINE-001 B1-R-P2D (test-only halo repair, DEC-035)

- Recorded user's **qualified** positive visual response to both P2C variants and identified source-level artifact: original pale hair/background pixels were darkened by J_FINE source-region medoid *before* P2C. Original P2B/P2C frozen baselines not overwritten; no old G32/V44 inputs.
- Added independent frozen prereg, original-source bright-halo correction D_BORDER/D_COMPONENT24, source immutable-ink protections, 13 regression tests and bounded artifact-producing CI. [CI44275730549](https://github.com/Kiddos19882/AutoDraw/actions/runs/44275730549) SHA `6170db18fd249c551b4ca627606b5977d8a3958f` E2 13/13 and E3 SUCCESS; downloadable ZIP SHA `1899a2bf10413e787cc79bdbd69cf7ea8e5ffafc31f4f91a0380ba0cef303b43` CRC/38 member SHA PASS. Both C096/C192 marked source false gray ROI27→1, original color count347/443 unchanged; four `SOURCE_SCREEN_PASS_VISUAL_PENDING`. First doc-index CI44275465194 FAIL preserved; corrected before valid run. No playable game32/native/production/CHALK claims.

## 2026-11-18 — ENGINE-001 B1-R-P2C source-mask ink palette compression (research only)

- Added independent prereg, test-only deterministic CIELAB source-member palette selection on original-source K_DETAIL residual ink (96/192 swatches), 11 synthetic tests, bounded CI, and one ZIP review bundle. Old G32/V44/M1 and frozen P2/P2B images not consumed as candidates.
- [CI44263770838](https://github.com/Kiddos19882/AutoDraw/actions/runs/44263770838) `b20d9e8ead30fa7605d69f655ae3d7ab6c0890fb` E2 11/11 and E3 PASS, ZIP CRC/26 hashes PASS. Original full discrete 347/443 RGB, logical NEAREST 347/442, source numerical quality PASS for both, human visual PENDING; no game32/native Egret/CHALK/production claims.

## 2026-11-18 — ENGINE-001 B1-R-P2B source-original detail layer experiment

- Isolated original-RGB residual detail source overlay using independently recomputed SLIC source medoids and only original edge/color evidence; no G32/V44/M1 source candidates, no production changes.
- [CI44261071470](https://github.com/Kiddos19882/AutoDraw/actions/runs/44261071470) `699c5a641db31ff6f9be4e82bf0d3397109091d0`: 9/9 E2 tests and E3 SUCCESS, archive CRC/25-of-25 SHA PASS; prereg source gates PASS for both K variants but visual user acceptance pending. Combined output >11k RGB despite flat medoid 252 colors; no game32/native/CHALK promotion. Initial uniform-fixture CI FAIL preserved.

## 2026-11-18 — ENGINE-001 B1-R-P2 test-only joint RGB segmentation and source contour

- Added independently preregistered source-only P2-V1 script, 10 synthetic regression guards and bounded GitHub Actions. Immutable original source medoids per region, own source-edge-linked contour previews; forbidden old G32/V44/M1 maps never used as candidate.
- [CI44259464359](https://github.com/Kiddos19882/AutoDraw/actions/runs/44259464359) E2 10/10/E3 SUCCESS with archived 21/21 hashes, but both source image-quality gates FAIL due faces and p95; no approval for palette32 or production. Negative experiment preserved, next separately versioned original-detail restoration.

## 2026-11-18 — ENGINE001 B1-R-P1 original-source prefilter and new outline diagnostics

Added test-only B1-R original full200×320 RGB protection from original Sobel/ΔE, two fixed bilateral filters, original-only extracted outline preview, synthetic tests and independent source-only workflow. [CI44244364830](https://github.com/Kiddos19882/AutoDraw/actions/runs/44244364830) 8/8 E2, E3 successful, 14/14 member hashes verified; A_SOFT/A_MID numeric SOURCE_SCREEN_PASS_VISUAL_PENDING, no added chroma excess and no G32/V44/M1 old candidate inputs. Real native brush, new playable contour, game32, exact CHALK NOT_RUN. Source SHA typo first CI FAIL preserved; no production/master changed.

## 2026-11-18 — DEC-034: B1-R RGB-first image preparation restart

По прямому решению пользователя прежние G32/P4c1 и V44-B контуры исключены из активного проектирования рисунка; теперь разрешены только history/comparison controls. Новый [B1-R plan](ENGINE001_B1R_RGB_FIRST_RESTART_PLAN_2026-11-18.md) возвращает исследование к оригинальному RGB, предварительной защите деталей/новых границ, edge-aware упрощению, совместному построению цветовых зон и нового контура; затем отдельная palette32, Egret round brush, лимиты CHALK/возможный split-to-boards. Отрицательные B1/B2/B3/B4 и настоящие PNG сохраняются. Пока это документы/принятый plan, не новая проверенная реализация или CI изображения.

## 2026-11-18 — B4 genuine complete Egret color+contour negative study

Experimental test-only real BoardPane/WebGL opt-in B4 method and validated Python native_batch whitelist with unchanged historical behavior; frozen 17-game-color P4c1 paint + 410 native V44-B detail strokes LAST in two A/B scenes (original395-color details vs CIEDE2000-nearest15 game32 detail colors). [CI44236852882](https://github.com/Kiddos19882/AutoDraw/actions/runs/44236852882) E2 15 Python/20 Node PASS, E3 SUCCESS, both quality FAIL, 44/44 artifact hashes verified. Avoid further production optimization on rejected G32 map; B5 will research visually coherent source zones independently. No game/live/CHALK changes.

## 2026-11-18 — ENGINE-001 B3 actual Egret diagonal brush evidence

Added test-only B3 authentic BoardPane/WebGL source-pinned diagonal isolated width2/4 probe with original B1 source/protected masks, frozen fixture selection, unit contracts and Windows Actions. [CI44234300377](https://github.com/Kiddos19882/AutoDraw/actions/runs/44234300377) E2/E3 successful execution, 12/12 native traces, 2/12 conservative safe-join PASS vs 10/12 foreign-alpha failures; no foreign ink farther than3logical px in these narrow samples. No game runtime, no production integration or original V44 modification.

## 2026-11-18 — B2 negative report and E1 diagonal topology

Verified B2 safe-area4/12 original-supported island cleanup ([CI44232121497](https://github.com/Kiddos19882/AutoDraw/actions/runs/44232121497)), technical PASS but both source quality FAIL; 8/7 merges accepted. Added diagnostic 4-vs-8 same-swatch component topology and next research on genuine Egret round-brush footprint; original map, contour, production/master unchanged.

## 2026-11-18 — ENGINE-001 B1 game32 source-support candidates (negative)

Added test-only B1 original RGB chroma/brightness guard and deterministic protected-seam Potts candidate for 32 actual game swatches, synthetic contracts and independent GitHub workflow. [CI44230985963](https://github.com/Kiddos19882/AutoDraw/actions/runs/44230985963) E2/E3 technical PASS, all four candidates SOURCE_GATE_FAIL on nonwhite connected-component/singleton counts; real V44-B410, production, master, Stage6 unchanged. Preserve negative PNG/labels for new separately preregistered B2 source-safe cleanup.

## 2026-11-18 — original RGB prefilter MVP-P0 test-only controls

Preregistered one source-only P0 edge-aware experiment, four bilateral/mean-shift original-input filters, 5 synthetic regression tests and dedicated bounded GitHub Actions. [CI44229576245](https://github.com/Kiddos19882/AutoDraw/actions/runs/44229576245) E3 successful with pinned M1/V44 archives and 14/14 SHA. Screens pass source-only; no production or game-color/native promotion, user visual pending. Documentation-index initial failure and repair retained. Exact original410 and M1 historical FAIL unchanged.

## 2026-11-18 — source micro-island vs unsupported game32 swatch diagnostic

Added preregistered test-only `ENGINE001_COLOR_ISLAND_R2_P2_P2_SOURCE_SUPPORT_AUDIT` runner, 15 regression tests and isolated CI; [CI44220144140](https://github.com/Kiddos19882/AutoDraw/actions/runs/44220144140) E3 technical PASS with verified original M1 archive hashes. M1 source singletons and false-looking G32 swatch fragments measured separately, no silent recolor/removal. Same original V44-B410, production, master and frozen negative outcomes. Next independent B1 source-supported region color plan.

## 2026-11-18 — R2-P2-P1 stable medoid and fixed-edge mathematics

Added independent source-only M1 with numerical CIELAB medoid tie at 1e-9 squaredLab, fixed original Sobel90 threshold comparisons, complete 4/8-connected island diagnostics and pinned M0 baseline provenance. [CI44216262024](https://github.com/Kiddos19882/AutoDraw/actions/runs/44216262024) technical 26/26 PASS, source FAIL because mean ΔE worsens when merging; all old source errors/frozen history preserved. Next E1 classify 179 singleton regions rather than blindly delete. No production or native change.

## 2026-11-18 — ENGINE-001 R2 N2 optional source diagnostic; P2 independent plan

Added safe optional BiRefNet soft-alpha merge ranking N2 with genuine frozen ONNX-mask replay, 9 unit contracts and CI; [CI44212777049](https://github.com/Kiddos19882/AutoDraw/actions/runs/44212777049) technical SUCCESS, source quality FAIL, negative evidence kept. Created [R2-P2 root-cause и протокол M1](ENGINE001_COLOR_ISLAND_R2_P2_ROOT_CAUSE_AND_NUMERICAL_REBASE_PROTOCOL_2026-11-18.md) for separately preregistered stable source-Lab medoid and fixed original gradient scoring; preserves all frozen P1 thresholds and avoids more model downloads.

## 2026-11-18 — ENGINE-001 R2-P1 M0/N1 source-only controlled experiments

Added original RGB fine-partition mathematical M0, synthetic tests and bounded CI. Added N1 using original pretrained S4 DINOv2 *dense feature replay* only as eligible mathematical merge ranking, with explicit original artifacts/shape/label checks and negative numerical render-drift handling. M0 E3 PASS/source quality FAIL; N1 E3 PASS/source quality FAIL (27 changed eligible decisions but slightly worse source mean ΔE00, 78px archived M0 RGB render mismatch). All 24 unit contracts and original data hashes validated; R1/P1 gates and V44-B410 LAST unchanged; no production or native tests. Next research requires new R2-P2 ID/prereg.

## 2026-11-18 — ENGINE-001 R2-0 verification and frozen R2-P1

Completed E1 pinned-S4/S5 archive verification, confirming real DINOv2 dense features and BiRefNet soft alpha reusable from immutable artifacts. Registered [R2-P1 frozen protocol](ENGINE001_COLOR_ISLAND_R2_P1_FROZEN_PRECOMPUTED_NEURAL_MERGE_PROTOCOL_2026-11-18.md) before first R2 source run: original RGB and detail protected M0 math baseline, genuine DINOv2 N1 eligible-merge ranking, independent BiRefNet N2; same source guards and negative evidence. No new R2 model, code or native tests.

## 2026-11-18 — DEC-033 / ENGINE-001 R2 neural-assisted mathematics plan

New independent R2 protocol supersedes R1 as *active research priority* after R1 E3 technical PASS / SOURCE_GATE_FAIL. Color truth remains original RGB; mathematical source edges/geometry/ΔE/chroma hold final authority; verified DINOv2 real features may influence only safe merge ordering, optional BiRefNet soft-alpha is a separate foreground ablation, SAM2/OneFormer not assumed to provide flat-color owners. Pre-register M0/N1/N2 controls, detail preservation, false-accent localization, separate unrestricted-RGB visual stage and pinned game32 projection/abstention before experiment. R1 histories and thresholds frozen, V44-B410 LAST, production/master untouched. Documentation-only; R2 tests and native NOT_RUN.

## 2026-11-18 — experimental ENGINE-001 COLOR-ISLAND-R1 code

Added separate original-RGB first source regions, conservative adjacent region cleanup, source-supported game32 assignment with explicit unrepresentable swatch abstention, 8 synthetic regression tests, and isolated source-only Actions workflow. Local first-image candidate SOURCE_GATE_FAIL (1017 unrepresentable pixels, background drift3929, fine detail regression); no retune or production integration. Official E3 CI pending exact run44198309906. Frozen G32/P4a/S5-P3/P4 and V44-B410 unchanged.

## 2026-11-18 — ENGINE-001 color-island cleanup planning

Documented new user-directed first-priority `ENGINE001_COLOR_ISLAND_R1_SOURCE_AWARE_REGIONS` plan: original-RGB region consistency, unsupported local accent detection, protected selective tiny-island cleanup, brush-ready geometry diagnostics, and separate 32-swatch projection. Recolorization-Pro no longer next research priority; all S5-P3/P4 negative artifacts kept. Docs only, no implementation/testing/native/production changes.

## 2026-11-18 — experimental S5-P4 (research only)

Added preregistered S5-P4 foreground-balanced source-RGB conditioning prototype, synthetic contracts and isolated GitHub Actions workflow. S5-P3 source/outputs frozen. No game32, production, Stage6, master or V44-B contour modifications. E3 inference not yet verified.

**2026-11-17 — S5-P3 native RGB pretrained visual trial:** user temporarily removed game32 gate only for new visual experiments; historical S3/S4 controls untouched. Pinned Recolorization-Pro original RGB, six-color source conditioning, genuine neural CPU CI44151445030 PASS, artifact14359920550, 15890 RGB colors, user visual evaluation PENDING; no training, production or frozen contours changed.

**2026-11-17 — S5-P1/S5-P2 real pretrained research:** OneFormer semantics pretrained E3 CI44148335302 PASS, only two numeric classes, not game32. BiRefNet Lite ONNX real pretrained E3 CI44149349577 PASS, mask-only foreground at alpha128=51.5%, verified ONNX checkpoint SHA; no 32-swatch trained palette model or production changes. Keep V44-B410 frozen.\n\n**2026-11-17 — S3 real source CI regression fix and S5 prereg:** S3 prior repeated CI failed on NumPy int64 report JSON; fix + 7 tests CI44145478173 E3 PASS, 4/4 source candidate quality FAIL (ΔE/background), original410 V44-B preserved. New S5 trained game32 head readiness preregistration added; training BLOCKED until independent trustworthy labels and heldout manifests verified, no production changes.

**2026-11-17 — CI historical workflow trigger hygiene:** after shared README update unexpectedly launched ten archived S1/S2/S3/P4/P2/P3 experiments, removed README-only push triggers from those ten individual workflows while preserving their code/test-specific and manual triggers. One-time CI reruns due to the workflow edits are expected; no claimed runtime savings until measured. S3 run44139251570 failed in source-only original contour/region graph step; separate diagnostic follow-up required.

**2026-11-17 — ENGINE-001 S4 verification + CI trigger optimization:** [CI44137289780](https://github.com/Kiddos19882/AutoDraw/actions/runs/44137289780) real pretrained DINOv2 SHA-verified inference, 593 changed pixels, numerical source `SOURCE_QUALITY_FAIL` (ΔE and background), no trained 32-color output head. Documentation synchronized to actual run; S4 costly job restricted to its own runner/tests/workflow (manual dispatch retained), S4-only test changes excluded from generic full validation triggering, pip cache/concurrency added. Quality gates and original410 V44-B contours/production unchanged; future CI performance not yet measured.

**2026-11-17 — ENGINE-001 NEURAL-S4 real pretrained feature-based color prototype:** preregistered S4; added DINOv2-small SHA-pinned real CPU feature inference, D0/D1 original-region graph comparison, optional authenticated immutable native V44-B alpha prior, synthetic contracts and new GitHub CI. This is neural-assisted context, **not trained direct palette32 head**. S4 CI/model quality NOT_VERIFIED, production unchanged.

**2026-11-17 — NEURAL-S3 immutable contour exact-source E1:** original V44-B native alpha24 raster 50,832 backing / 8,855 logical pixels, all within ROI; Sobel gradient source correspondence diagnostic 91.5% vs 26.5% off contour. Implemented verified optional native outline graph and testable J1 fail-closed/J0 source fallback without changing original contours; synthetic CI not yet verified.

**2026-11-17 — ENGINE-001 NEURAL-S3 joint color/contour prototype:** Preregistered separate J0/J1 source experiment and implemented test-only original RGB region graph with fixed 32-color palette, optional verified native V44-B alpha24 guidance, registered saturation ablation and fail-closed exact original410/1792 contour checks. Archived original V44-B SHA/CRC native α24 50832 inside ROI. Not a trained neural contextual color scorer, CI/source quality not yet verified, production unaffected.

**2026-11-17 — NEURAL-S2 independent original-first color segmentation:** prereg new ID `ENGINE001_COLOR32_NEURAL_S2_ORIGINAL_FIRST_FLATTING` before S2; added test-only SLIC source-only C1 and SHA-pinned real SAM2+SLIC C2, reg tests, independent CI. Local pilot regions B0 1284 vs C2 368, but ΔE00 +3.05 and background drift10.9% -> source-quality FAIL, no production promotion. Bright magenta G32 index10 source-RGB provenance diagnosed; user original/visual pending.

**2026-11-17 — NEURAL-S1 completed E2 (negative candidate quality):** [CI44127991472](https://github.com/Kiddos19882/AutoDraw/actions/runs/44127991472) genuine SAM2.1 Hiera Tiny inference PASS, two masks; full artifacts SHA/CRC verified. Frozen G32 B0 1284 components; N1 1237 (−3.66%), N2 1259 (−1.95%), both FAIL predeclared −25% source quality gate. Original segmentation/production unchanged; new independent color-region method must be preregistered.

**2026-11-17 — COLOR32-NEURAL-S1 B0 verified E2 / SAM2 shell preflight fix:** [CI44127150880](https://github.com/Kiddos19882/AutoDraw/actions/runs/44127150880) baseline PASS, ZIP14346804951 SHA-linked 1284 regions/779 singletons/1097≤4px; SAM2 install PASS but checksum command literal `\\n` FAIL before model inference. Corrected command newline `0d8e276`; N1/N2 pending. Production unaffected.

**2026-11-17 — NEURAL-S1 CI44126371197 import correction:** baseline job compile PASS but unit import FAIL, missing transitive `selenium`; SAM2 skipped/no artifacts. Added `selenium>=4,<5` to both source workflow jobs at `52a4b600`. E2/inference result still UNKNOWN, no model/production changes.

**2026-11-17 — NEURAL-S1 CI pre-inference fix:** [CI44125694634](https://github.com/Kiddos19882/AutoDraw/actions/runs/44125694634) FAIL due literal `\\n` in Python exporter; model never ran, no artifacts. Fixed syntax only `9162756`; new CI pending. No source G32/P4c2/model parameters changed.

**2026-11-17 — NEURAL-S1 CPU preflight and model provenance:** Disabled SAM2 CUDA-extension build on CPU job (`SAM2_BUILD_CUDA=0`), shared exact pinned Meta SAM2 source/checkpoint SHA across exporter and mask consumer, added synthetic manifest/archive tampering regression. Neural CI/inference result not verified; production and frozen P4c2 unchanged.

**2026-11-17 — ENGINE-001 / COLOR32-NEURAL-S1:** Following actual P4c2 [CI44119887018](https://github.com/Kiddos19882/AutoDraw/actions/runs/44119887018) E3 paint-only QUALITY FAIL (14/17 native owners below99, no >3px but color28 outside ROI), preregistered independent neural region study and added test-only real SAM2.1 Tiny mask exporter, source segmentation evaluation B0/N1/N2, regressions and Linux CI workflow. Original G32/P4c1/P4c2 and final410 V44-B outlines preserved. No neural CI results yet, no production promotion.

**2026-11-17 — ENGINE-001 P4c2 Windows source-drift recovery:** [CI44113999297](https://github.com/Kiddos19882/AutoDraw/actions/runs/44113999297) genuine native step FAIL before WebGL on `BLOCKED_P4C1_ORIGINAL_G_DRIFT`; all regressions/docs PASS. Fixed P4c2-only replay to use SHA-pinned original source ZIP14334728680 with exact 17 G32 owner source, CRC/linked hashes, frozen119+1014 stroke identity; added non-gating Windows-vs-Linux pixel diagnostic. Original P4c1/P4c0 evidence and production unchanged; new native CI pending.

**2026-11-17 — ENGINE-001 P4c1 E2 evidence/P4c2 test-only E1:** Confirmed [P4c1 CI44098998634](https://github.com/Kiddos19882/AutoDraw/actions/runs/44098998634) SHA02303521 original artifact14334728680 ZIP CRC+5/5 SHA PASS, source-model12/17 owner≥99%; all17 native E3 still NOT_RUN. Independently preregistered P4c2 and added frozen all17 actual Egret paint-only workflow, regression and runner without touching user-preferred original410 V44-B final contours, production or master. First P4c2 CI result UNKNOWN, native quality/CHALK unverified.

**2026-11-17 — DOC-SYNC P4c1:** Current documentation index, active tasks, roadmap and evidence checkpoint synchronized with committed P4c1 prereg/source implementation and verified P4c0 source-negative run. Historical P4a/P4b/P3b outcomes preserved; native E3/E4/E5/CHALK not claimed. Docs-only; checker pending.

**2026-11-17 — ENGINE-001 P4a/P4b safe source color and original contour evidence:** preregistered source-only P4a before implementation, original frozen G32 from S2b pixel-identical, [P4a CI44015038442](https://github.com/Kiddos19882/AutoDraw/actions/runs/44015038442) E2 numeric PASS but negligible visual change H vs G (67/36000 pixels,12 protected-safe source islands). Preregistered read-only P4b real-Egret original V44-B410 contour-only alpha overlay on G/H source rasters; initial CI44015951717 HTTP401 artifact redirect fixed in workflow without changing data/gates; [P4b CI44016120503](https://github.com/Kiddos19882/AutoDraw/actions/runs/44016120503) E2 HYBRID integrity PASS, 8/8 original output hashes, unchanged 410 original Egret colored detail strokes, G source RGB MAE14.099→with original contours13.257. Hybrid source background is not true native Egret paint; full 17 nonwhite owner G32 brush fill, 99%/3px, resource cap, live E4/E5 and exact CHALK remain unverified. 410 original V44-B details, master and production untouched.

**2026-11-17 — ENGINE-001 color32 Egret P3/P3b experiments:** preregistered local distance-aware directed residual brush sizes30/15/10/6/4/2 in [P3 protocol](ENGINE001_COLOR32_S2B_EGRET_P3_DIRECTIONAL_PROTOCOL_2026-11-17.md), original archived Egret [CI44012588733](https://github.com/Kiddos19882/AutoDraw/actions/runs/44012588733) native E3 execution PASS but quality FAIL (141/120 native foreign beyond3px α24). Independent [P3b prereg](ENGINE001_COLOR32_S2B_EGRET_P3B_SAFE_WIDTH_PROTOCOL_2026-11-17.md) frozen exact56 P3 positions but only width6→4; [CI44013208184](https://github.com/Kiddos19882/AutoDraw/actions/runs/44013208184) native E3 isolated incremental PASS, 0 >3px α24/128, α24 owner dark94.96%/pink78.24%, still fails full per-color99% and has visually scattered source swatch islands. Original P1/P2/P3 failures and native captures preserved. Existing production, master, original410 V44-B detail strokes and game CHALK unchanged.\n\n**2026-11-17 — ENGINE-001 real Egret P2 multiring:** native [CI44008672803](https://github.com/Kiddos19882/AutoDraw/actions/runs/44008672803) E3 isolated adaptive rings vs P1-W10 PASS (artifact14296385245 CRC and7/7 source hashes verified). Real alpha24 owner31 coverage90.95%, owner29 coverage68.18%; 0 foreign native pixels beyond3logical px, but894/271 foreign within tolerance and below99% full owner quality.55 new strokes/1097 source vertices (NOT CHALK), V44-B410 details unchanged. Full-image visual/game/E4/E5/CHALK NOT_RUN; P2 original pre-index docs CI negative preserved in [TEST_RESULTS](TEST_RESULTS.md).

**2026-11-17 — ENGINE-001 COLOR32-S2b-EGRET-P1 native brush study:** [Preregistered genuine BoardPane width sweep](ENGINE001_COLOR32_S2B_EGRET_P1_PROTOCOL_2026-11-17.md); isolated source G palette32 interior contours, widths2/4/6/10, real archive renderer via reused `native_batch`, per-owner native RGBA α24/128 plus foreign/exterior leakage and file hashes. Windows Firefox workflow created; results remain E3 UNKNOWN pending actual jobs/artifacts. Input palette and renderer pinned by Git blob; production, V44-B410 details and game CHALK unchanged. See [TEST_RESULTS](TEST_RESULTS.md).

**2026-11-17 — ENGINE-001 COLOR32-S2b source-only follow-up:** New preregistered [RGB-edge experiment](ENGINE001_COLOR32_S2B_RGB_EDGE_PROTOCOL_2026-11-17.md) uses existing frozen B/E/G and historical S1 gradient score instead of the invalid-for-this-purpose saturated S2 index overlap. Standalone test runner, regression and GitHub workflow added on feature branch. No production change, no historical result rewritten. E1 candidate projected from previous independent local diagnostics, new E2 CI/visual/Egret/game/CHALK not yet verified. See [TEST_RESULTS](TEST_RESULTS.md).

# AutoDraw — значимые изменения

**2026-11-17 — PAL32-REGION-V1 supplementary offline experiment E2:** [CI43997979526](https://github.com/Kiddos19882/AutoDraw/actions/runs/43997979526) 4/4 Python tests PASS, 20/20 artifact SHA valid; six source color/region variants, E (direct32 + small neighbor merge) 2369→1044 4-connected components (−55.93%) and mean ΔE00 5.44375→5.55870, with posthoc strong-edge overlap B86.17%→E84.42%. SLIC C/D/F lose details; no native Egret fill/CHALK. [Results](TEST_RESULTS.md), [protocol](ENGINE001_PAL32_REGION_V1_PROTOCOL_2026-11-17.md).

**2026-11-17 — COLOR32-S1 source-only A/B/C/D spatial palette experiment:** [CI43997569635](https://github.com/Kiddos19882/AutoDraw/actions/runs/43997569635) E2 PASS 5/5; A MEDIANCUT8 3507 owner components, B real32 ΔE00 mapping actually20 colors/1575 components, C SLIC400→337 source superpixels/18 components and D 268 merges→69 regions but **C/D exactly same mapped colors**, strong-edge retention drops from A90.94% to B86.17% / C-D51.47%. Original Egret V44-B detail overlay generated offline for visual comparison; no new Egret fill, no production changes. [Complete metrics](TEST_RESULTS.md) and [prereg](ENGINE001_COLOR32_SPATIAL_SEGMENTATION_PROTOCOL_2026-11-17.md).

**2026-11-17 — COLOR32-S1 first A/B/C/D E2 comparison:** [CI43997569635](https://github.com/Kiddos19882/AutoDraw/actions/runs/43997569635) PASS 5/5 tests;32 real game swatches, B uses20 with1575 regions and ΔE00mean5.44 vs legacy A3507/3.70; SLIC C/D use8 and18 regions but destroy facial details and source strong-edge agreement falls to51.47%. D performs268 SLIC merges but game-color output exactly matches C. Frozen negative captured; no native/production/CHALK claim. [Source evidence](TEST_RESULTS.md).

**2026-11-17 — real Egret diagnostic of 1838 color-zone boundaries:** [CI43995008472](https://github.com/Kiddos19882/AutoDraw/actions/runs/43995008472) E3 capture PASS / artifact14289576492; 1838 all-source boundaries (4/5/6/7 counts746/544/443/105), 5649 synthetic vertices, 3/3 Python and20/20 Node tests, no fill. PNGs show source zones alone and with original Egret V44-B detail layer. This diagnostic is not game/E4/CHALK or accepted fill geometry. [Evidence](TEST_RESULTS.md).

**2026-11-17 — B3b owner-mask skeleton first source E2:** [CI43993003719](https://github.com/Kiddos19882/AutoDraw/actions/runs/43993003719) tests 5/5 PASS, source BLOCKED_RESOURCE on next 5902 synthetic vertices after1078 new paint. Model coverage4–7=81.82/81.78/81.87/91.86%, better than B3a 63/63/63/92 but not accepted. 883 owner skeleton routes/0 residual micro executed, same-color overlap penalty0, full native B3b NOT_RUN. [Evidence](TEST_RESULTS.md).

**2026-11-17 — B3a frozen negative source result:** CI43992170465 E2 workflow SUCCESS / 4 tests PASS, but generated1339 paint /5899 projected vertices and blocked next +2 vertices >5900. Model coverage4/5/6/7=63.28/63.28/63.36/91.86%; 1144 residual micros, 0 usable owner-medial routes. The next method needs actual source-mask skeleton/continuous polylines; same-color overpaint remains free. No full B3a Egret. [Detailed evidence](TEST_RESULTS.md).

**2026-11-17 — B3 actual isolated Egret contour rings:** [CI43991432235](https://github.com/Kiddos19882/AutoDraw/actions/runs/43991432235) E3 capture PASS, 14 source-selected contour paths /283 synthetic vertices NOT CHALK, no foreign/exterior>3px; coverage only isolated tiny sample, not full fill. Source B3 MODEL_LOW_COVERAGE, full B3 NOT_RUN. [Evidence](TEST_RESULTS.md).

**2026-11-17 — B3 contour-parallel first source E2:** 195 new ring paths, same-color overlap penalty zero, source CI43991126674 PASS 4 tests/605 total strokes/3611 synthetic vertices, but source quality **MODEL_LOW_COVERAGE** (17.98/44.45/23.34/91.86%). Isolated Egret path probe workflow added; full B3 not accepted. [Protocol](ENGINE001_V43P4_B3_CONTOUR_PARALLEL_PROTOCOL_2026-11-17.md), [evidence](TEST_RESULTS.md).

**2026-11-17 — ENGINE-001 B2-FULL source-only implementation:** added opt-in deterministic source-only broad width10/6/4 plus micro width2 0.25px plan and regression+GitHub CI with strict BLOCKED_RESOURCE/no partial native, retaining frozen B0/B1 and user-selected410 colored contours requirement. E2 result not verified at writing; no full Egret B2 yet. [Protocol](ENGINE001_V43P4_B2_FULL_BOUNDARY_REPAIR_PROTOCOL_2026-11-17.md).

**2026-11-17 — V43-P4/B2 full-image research preregistration:** registered separate deterministic broad-interior width10/6/4 and owner-residual width2 0.25px microstroke model, unmodified V44-B RGB410 LAST, strict resource and quality gates. No B2-FULL code or native quality claimed; [protocol](ENGINE001_V43P4_B2_FULL_BOUNDARY_REPAIR_PROTOCOL_2026-11-17.md).

**2026-11-17 — ENGINE-001 B2 genuine Egret singleton E3:** [CI43987609480](https://github.com/Kiddos19882/AutoDraw/actions/runs/43987609480) successful 4 Python +20 Node and true BoardPane fractional strokes; 12/12 isolated singletons hit at alpha24/128 by both width2 and4, but actual alpha24 foreign pixel count width2=237 versus width4=955. All foreign/exterior beyond3 logicalpx zero in bounded probes. Archived original ZIP/11 hashes, no full B2 acceptance, E4/E5/CHALK NOT_RUN. [B2 protocol](ENGINE001_V43P4_B2_NATIVE_SINGLETON_PROBE_PROTOCOL_2026-11-17.md).

**2026-11-17 — ENGINE-001 P4 B2 isolated real-brush research:** registered and implemented separate original-source singleton micro-stroke test, 12 native short0.25px paths per width2 and width4, reuse existing V5 BoardPane/Egret `native_batch`, fixed source/owner RGB, alpha24/128/3px diagnostics and Windows CI with SHA-linked artifacts. No new production renderer or full B2 plan yet, B0/B1 quality negatives preserved. [B2 protocol](ENGINE001_V43P4_B2_NATIVE_SINGLETON_PROBE_PROTOCOL_2026-11-17.md).

**2026-11-17 — V43-P4 B1 real Egret result:** [CI43986256204](https://github.com/Kiddos19882/AutoDraw/actions/runs/43986256204) E3 capture PASS; original V44-B replay pixel-exact and B0 archived SHA correct. B1 105 fresh paint/410 frozen RGB contours, 515 strokes/2002 synthetic vertices; alpha24 class coverage 3.58/20.61/6.15/81.01% = QUALITY FAIL, warm RGB MAE46.96 (vs A16.42). Foreign color greatly reduced but almost all fine fill lost. B0 and B1 both frozen negatives, no production acceptance or CHALK. [B1 full evidence](TEST_RESULTS.md).

**2026-11-17 — ENGINE-001 V43-P4/B1 correction exploration:** after first full B0 native QUALITY FAIL, preregistered separate source-only B1 owner-constrained selection, created isolated planner/tests/workflows and real Egret B1 runner using immutable B0. B1 source CI43985871223 E2 PASS (3/3 tests) but coverage model fails badly:4/5/6/7=3.94/22.10/6.50/83.69%; native B1 quality UNKNOWN. No change to frozen B0, original thresholds or production. [B1 protocol](ENGINE001_V43P4_B1_OWNER_CONSTRAINED_PROTOCOL_2026-11-17.md).

**2026-11-17 — ENGINE-001 P4 first real A/B0 native E3 RESULT:** source CI43983625827 PASS; native CI43983619222 PASS with full real Egret archive14285005715. A V44-B pixel-exact, all410 contours preserved; B0 955 new paint/1365 total/3702 synthetic vertices vs A2355/5682, but **B0 QUALITY FAIL**: native per-class alpha24 83.10/87.60/80.46/94.75%, RGB MAE19.93 vs11.13, warm33.70 vs16.42; visually heavy foreign boundary smearing. Markdown integrity CI43983778165 PASS on prior SHA. Frozen negative B0 preserved for B1 prereg. E4/E5/CHALK NOT_RUN. [Evidence](TEST_RESULTS.md).

**2026-11-17 — ENGINE-001 V43-P4.2 experimental native A/B0 infrastructure:** opt-in original Egret method for new width2/4/6/10 paint IDs, strict frozen V44-B A replay SHA and pixel-exact before first B0, 410 color RGB details unchanged, alpha24/128/class/3px and RGB diagnostics, Windows native workflow. No production defaults changed; actual CI E3 outcome UNKNOWN. [Preregistered B0 method](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md#p42-fixed-b0-native-execution-rule--registered-before-first-b0-native-run-2026-11-17).

**2026-11-17 — ENGINE-001 V43-P4.1 experimental planner:** new isolated source-only class4–7 adaptive multi-angle/width10→6→4→2 greedy selector, deterministic provenance, fail-closed budget, 3 regression methods and separate GitHub workflow. Preliminary original-PNG OpenCV MODEL_ONLY 955 paint strokes; candidate not yet combined with frozen V44-B details, and E3 native game quality not claimed. CI E2 UNKNOWN. [Protocol](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md).

**2026-11-17 — ENGINE-001 P4 source feasibility evidence:** подтверждён source SHA и palette, учтены 1575 фрагментов и отрицательный эвристический horizontal-width proxy (5934 paint paths vs предельные2054 для 2-point); записано, что это MODEL_ONLY не native. Уточнён ресурсный риск в активной задаче без изменения кода, production/CI. [P4 addendum](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md).

**2026-11-17 — DOC-SYNC-20261116 continued:** clarified active P4 vs legacy V44-P2 next phrasing in ROADMAP, scoped archival checkboxes to ENGINE-001 without closing other tasks, corrected README so NOT_RUN P4 is not presented as an ongoing test. No code/master/CI execution; [audit addendum](DOCUMENTATION_INVENTORY_2026-11-16.md).

**2026-11-17 — DOC-SYNC-20261116 (повторная проверка документации):** выделена действующая задача V43-P4 от исторических `[ ]` в TASKS, исправлен преднативный V44-P1 статус в README по уже подтверждённому Egret CI43813812976; дополнена инвентаризация с честным `PARTIAL`, старые tree counts не выданы за текущие. Документирование без изменения production/master/кода; CI на новом SHA не запускался. [Инвентаризация](DOCUMENTATION_INVENTORY_2026-11-16.md).

**2026-11-16 — ENGINE-001 V43-P4 / DOC-SYNC-20261116 (документация):** утверждён и записан единый протокол **полной замены старых1945 paint strokes** новым adaptive fill B0 (required classes4–7, widths10/6/4/2), неизменные410 пользовательских цветных V44-B контуров последними; B1 исправляет ошибки только после архивирования B0. [Протокол](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md), [новая инвентаризация](DOCUMENTATION_INVENTORY_2026-11-16.md); действующие индексы согласованы с CI P3b-P0/P1, 0/18 и 0/36 полных замен. Исторические отрицательные материалы и production не менялись; P4 code/CI/native NOT_RUN.


**2026-11-15 — ENGINE-001 V18 topology research:** prereg A triangle-aware diagonal graph repair and B direction-based junction chain joining (without added gap-bridging ink); local pinned-source A=527 paths/95.19% skeleton support, B=410 paths/97.46%. Isolated runner/tests/CI and README protocol index added; first CI import mismatch corrected without changing methods. Production, native/game CHALK, master unchanged.


**2026-11-15 — ENGINE-001 V17 isolated AniLines brush1 exploratory preview:** user removed independent annotation requirement as prerequisite to experimental planning; original V16 reviewer tool preserved. Registered new V17 before preview, generated 417 brush1 path candidates from frozen real V14 AniLines, 1499 synthetic vertices; preserved short-chain losses and non-native status. Added dedicated opt-in repository runner/tests/Actions, indexed protocol. No production, executor or master changes.


**2026-11-15 — ENGINE-001 V16 reviewer readiness correction:** repaired incorrect V14 FDoG artifact SHA pin (actual `ab83ae44…`), added fail-closed regression; source-only offline HTML reviewer utility exports binary grayscale annotation masks and manifest checksums, bundled by V16 CI. [Run43671763378](https://github.com/Kiddos19882/AutoDraw/actions/runs/43671763378) E3 PASS on `8581f87` for readiness only; external human seam ground truth missing, production unchanged.


**2026-11-15 — ENGINE-001 V16 research validation readiness (no production changes):** new prereg blind-source jacket-seam protocol, fail-closed positive/definite-negative mask validator, seven synthetic tests and dedicated Actions workflow; [run43668919593](https://github.com/Kiddos19882/AutoDraw/actions/runs/43668919593) E3 PASS for *readiness only*, semantic seam assessment remains BLOCKED pending independent annotation. Updated README protocol index after observed Markdown unindexed-file failures; old V15 posthoc cutoff mismatch remains documented.


**2026-11-15 — ENGINE-001 AniLines evidence clarification (documentation only):** indexed post-V14 local filtering as unregistered exploratory analysis, clarified threshold mismatch (V14<128, local<180), missing seam truth and non-semantic suit proxy. Updated canonical status/task/roadmap/log/test-index without changing any experiment algorithm, production files or `master`. V14 authentic FDoG/AniLines CPU jobs remain verified E3 PASS on SHA `df362426`; cleanup and artwork quality still NOT_ACCEPTED.


**2026-11-15 — ENGINE-001 V14 experimental CI (production unchanged):** prereg original-image pinned authentic FDoG vs AniLines Detail CPU jobs, fixed upstream repository SHAs, source/hash validation and bounded jacket ROI PNG/JSON evidence; isolated Python reporter and regression tests. Weights auto-fetched from publisher Google Drive to ephemeral runner only. No evidence of completed V14 workflow yet; no native game CHALK or semantic recognition claim.


**2026-11-14 — ENGINE-001 V6/V7 research (production unchanged):** verified pinned 200×320 original, local replicated V6 source edge recall 90.4087% and 7/48 component failures; prereg V7 `2844a2f` before local 84-stroke line-only preview, which is visually insufficient despite 98.91% edge proxy. Added isolated GitHub V7 runner, five tests, dedicated workflow (`c9edc35`, `520b985`, `9b868dd`) for reproducibility; CI NOT_VERIFIED, V5 frozen and master untouched.


**2026-11-14 — ENGINE-001 exploratory V6 (no production changes):** после пользовательского визуального FAIL сложного V5 разработан отдельный [пререгистрированный анализ потери структурных границ](ENGINE001_COMPLEX_STRUCTURE_V6_PROTOCOL_2026-11-14.md): `tests/run_engine001_complex_structure_v6.py`, `tests/test_engine001_complex_structure_v6.py`, `.github/workflows/engine001-complex-structure-v6.yml`. Добавлены E1 source-palette edge diagnostics и red/green RGB overlay для визуальной локализации потерь линий; пререгистрирована 3×4 сетка source/palette edge-loss и 2 regression fixtures и 12 unit fixtures; CI/result UNKNOWN до проверки, recognize quality не улучшена и не заявлена. Frozen V5, production и master не менялись.


- 2026-11-14 / ENGINE-001: completed source-bound **V5 complex multicolor holdout** with original repository artwork `testImages/wV6VeZI9S1Y.png` pinned Git blob `d3cd95b8` 200×320 (chat copy not same bytes). Protocol prereg `dfc626cc`: aspect-fit to logical150×240 centered, 8 MEDIANCUT palette classes and three variants V3/V4/color-protected V5. Added isolated native BoardPane per-stroke color research renderer, standalone runner, five synthetic tests and Windows CI. [Actual native CI 43600695050](https://github.com/Kiddos19882/AutoDraw/actions/runs/43600695050) SUCCESS E2/E3 on `a8df52a`, [raw artifact 14116113816](https://github.com/Kiddos19882/AutoDraw/actions/runs/43600695050/artifacts/14116113816). **All color geometry FAIL** 99%: native foreground silhouette coverage35.055%/36.760%/35.055%, 123 strokes/558 synthetic vertices all variants; V5 rejected all 46 brush widenings because near-color interference, one white-ish palette class unpaintable by existing long-line planner. V4 foreign-color overlap6648 vs V3/V5 3862. Two earlier CI failures kept: empty long-stroke class and unhandled width15 fixed in test adapter only. Image source, production, acceptance thresholds and historical data unchanged; CHALK/E4/E5 not measured.


- 2026-11-14 / ENGINE-001: **V4** pre-registered at `56613cb` after static V3 screening, selective existing mixed-width `4→6` and `8→10` with every original coordinate, 323 strokes, 674 synthetic vertices and 3 width switches preserved; separate opt-in V4 runner, five synthetic tests, native dual V3/V4 Windows workflow and JS opt-in width extension. [Native CI 43567176919](https://github.com/Kiddos19882/AutoDraw/actions/runs/43567176919) SUCCESS on `d843c58`, [full artifact 14103101899](https://github.com/Kiddos19882/AutoDraw/actions/runs/43567176919/artifacts/14103101899): V4 coverage **99.3107%** (V3 97.6681%), exterior max **1.6667** logical px (0 beyond3), **offline geometric PASS**, but IoU89.4052% (V3 93.5282%), near-border leakage17456 native px (V3 6974); V4 misses1086. No actual game CHALK, independent E4/E5 or live DEC-030 quality acceptance; preserved baseline V0–V3 and production untouched.


- 2026-11-14 / ENGINE-001: preregistered mixed-brush **V3** adaptive contour-first+long centreline test (`219fc6be8`), added opt-in per-stroke Egret BoardPane sizes 2/4/8/15/30, new Python research planner, five synthetic regression tests and dedicated Windows CI. [Actual native CI 43565322109](https://github.com/Kiddos19882/AutoDraw/actions/runs/43565322109) SUCCESS at `969812e`; [artifact 14101843435](https://github.com/Kiddos19882/AutoDraw/actions/runs/43565322109/artifacts/14101843435). 97.6681% coverage / 93.5282% IoU / 3674 missing / 6974 leakage all within0.667 logical px; 198 missing deeper than symmetric 3px interior boundary. 323 strokes/674 synthetic vertices vs V2 403/1943; only 2/4/8 actually selected, 15/30 unused. **OFFLINE QUALITY FAIL** (<99%), no CHALK/E4/E5. All original V0/V1/V2 data, production settings and acceptance gates preserved.


- 2026-11-14 / ENGINE-001: new preregistered (task commit `e83c324`) V2 experimental **painted-stripe frontier** planner, using 24 long contour segments over original 379 horizontal strokes, native Egret WebGL [CI 43563405147](https://github.com/Kiddos19882/AutoDraw/actions/runs/43563405147) SUCCESS code `d6ef11e`; [artifact 14101297101](https://github.com/Kiddos19882/AutoDraw/actions/runs/43563405147/artifacts/14101297101). **OFFLINE QUALITY FAIL** coverage96.4742% <99%, mask IoU92.3523%, missing5555; leaked7032 within allowed 3-logical-px **diagnostic** halo (max1.0541, far=0). Stroke and synthetic vertex counts increase to 403/1943 versus original 380/760; exact CHALK unknown. Includes 5 new deterministic tests and fixed preview/native PNG audit. No source/production/acceptance change, no game E4/E5.


- 2026-11-14 / ENGINE-001: added preregistered opt-in `ENGINE001_TWO_ICON_PREDICTIVE_CONTOUR_V1` for two existing source icons, long target-contour segments selected by forecast holes, and horizontal endpoint trimming (`38f5b58` protocol; `27521f3` code); 5 synthetic tests, native Egret WebGL [CI 43549152669](https://github.com/Kiddos19882/AutoDraw/actions/runs/43549152669) SUCCESS, [artifact 14095253373](https://github.com/Kiddos19882/AutoDraw/actions/runs/43549152669/artifacts/14095253373). Coverage92.7288% / IoU92.5327% / leakage334, vs old coverage92.1094% / IoU91.9157% / leakage332; 381 vs 380 strokes. **OFFLINE QUALITY FAIL**, not exact CHALK or independent E4/E5. First [CI 43548972752](https://github.com/Kiddos19882/AutoDraw/actions/runs/43548972752) FAILED due test-only 2-vertex guard, corrected by bounded contour polyline support without fitting geometry. Production behavior, thresholds, original source icons, historical captures remain unchanged.


- 2026-11-14 / ENGINE-001: added an opt-in actual native Egret WebGL two-icon composite-mask experiment using two unchanged `testImages` PNGs (home+envelope), synthetic radius2 normal plan and five regressions (`d60956a`; [CI 43546565112](https://github.com/Kiddos19882/AutoDraw/actions/runs/43546565112) SUCCESS; [artifact 14093549419](https://github.com/Kiddos19882/AutoDraw/actions/runs/43546565112/artifacts/14093549419)). Mask IoU 91.9157%, coverage 92.1094%, missing12432/outside332: **offline quality FAIL**, preserved. No new live E4/E5, exact game CHALK, production defaults, thresholds or original captures altered.


- 2026-11-14 / ENGINE-001: added reproducible fixed-boundary residual analyzer and five synthetic regressions to the six-run native Egret CI (`ae7ecc4`, [CI 43541756465](https://github.com/Kiddos19882/AutoDraw/actions/runs/43541756465) SUCCESS; [artifact 14091649173](https://github.com/Kiddos19882/AutoDraw/actions/runs/43541756465/artifacts/14091649173)). Six frozen residual totals 40/535/659/40/530/404, all within a fixed 2px boundary band; no posthoc projection or threshold fitting. Still DIAGNOSTIC_ONLY, no E4/E5 or quality acceptance, no production changes.


- 2026-11-14 / ENGINE-001: bounded source-faithful `POINT_QUOTA_UPDATE`→`DRAW_SAMPLE` coordinate recovery with fail-closed alignment, eight negative/positive unit regressions, opt-in native Egret re-render and separately archived PNGs (`7581b7c`, [CI 43536560568](https://github.com/Kiddos19882/AutoDraw/actions/runs/43536560568) SUCCESS attempt 2). Two missing points traced to immutable run-bound Monitor streams; C1-F3 IoU slightly decreased, C2-F2 unchanged, so FILL quality/E5 acceptance not claimed. Default renderer path and production Stage6/CHALK/thresholds unchanged.

- 2026-11-12 / FILL001 exact binder: distinguish cumulative browser-local Monitor export buffer overflow from genuine loss of run-recorder/Bridge events. Requires lossless per-run and internally consistent buffer counters; negative regressions and frozen 50MB raw replay in CI `874f2e1`, 43274926194 PASS. No retroactive reclassification or safety threshold change.

- 2026-11-12 / FILL001 screenshot: stricter cursor parking 160 px down rather than 32, no side fallback in series captures, 0.4 s tooltip settling, synthetic tests + CI trigger. Legacy Brush Lab unaffected; live proof pending.

- 2026-11-12 / FILL001 native BoardPane: unified fail-closed screenshot ROI, repeat native probes after Clear, cursor hover settling and standalone Clear-only calibration without manually selected board ROI; synthetic negative tests and CI scope expanded (`20fccadf`). Legacy Brush Lab/manual calibration unaffected; E2/E3/E4 pending verification.

- FILL001-SERIES-001 (2026-11-12): two `QUOTA_LIMITED` E4 runs from [`9dbb74b`](https://github.com/Kiddos19882/AutoDraw/commit/9dbb74bb683bab30bbbb9b06a6cbfbd856ea5d74) both have run-bound exact CHALK but Clear comparator blocks next task. [`0b851c1`](https://github.com/Kiddos19882/AutoDraw/commit/0b851c19cdd569aa83c7528aa5cbf8d550601ce0) adds rejected-comparison metrics/hashes to fail-closed Clear error, [`b106fa1`](https://github.com/Kiddos19882/AutoDraw/commit/b106fa13dacf4c8ea68e2acfd70bdb1b8e0f4a40) adds negative regression; acceptance tolerance remains 0.15%. New E2/E3 pending.

- FILL001-SERIES-001 (2026-11-12): [`4822ccf`](https://github.com/Kiddos19882/AutoDraw/commit/4822ccf6e401dcf1cd56fdc43c926ccdf6432fa6) adds E4 BLOCKED raw runtime after 29/141. V5 gate error now names the read exception class without permitting game input; added three negative tests and CI path/test selection (`a4622c2`, `0b0b95e`, `1d590b8`). Code change is diagnostics only; E2/E3 pending, live re-run not performed.

- DOC-CODE-REUSE-001 (2026-11-12): E2/E3 validation completed for two separate committed versions: [FILL001 series CI 43140218990](https://github.com/Kiddos19882/AutoDraw/actions/runs/43140218990) SUCCESS at `4dfec5c` (165 offline regression tests plus syntax/geometry smoke), [docs integrity CI 43164791087](https://github.com/Kiddos19882/AutoDraw/actions/runs/43164791087) SUCCESS at `b317348` (11 docs tests, 130 source files scanned, CAP-009/012/013 cross-domain discovery, 0 unconditional root SCC). Documentation updated with CI provenance; no gameplay or acceptance thresholds changed, E4 quota recovery remains NOT_RUN.

- DOC-CODE-REUSE-001 (2026-11-12): static capability consumer search now covers the root `integrated_app.py` and narrowly scoped preparation imports from Stage6 executor. Added synthetic/real CAP-009/012/013 tests while retaining `source/preparation`-only import-cycle gate. [Code `fe4a1de`](https://github.com/Kiddos19882/AutoDraw/commit/fe4a1de300fc670373b76be52341385423569cae), [tests `f2e5919`](https://github.com/Kiddos19882/AutoDraw/commit/f2e5919e659f558b19de6fea7d2631bee3eab542). No game runtime change; new E2/E3 status not verified.

- DOC-CODE-REUSE-001 (2026-11-12): experimental FILL001 offline preview and signed DrawingPlan handoff now reuse `resolve_series_scanline_spacing`, preserving frozen dense/spaced parameters and source signatures. Added negative spacing tests and 30-cell preview/signature regression checks ([code/test `4dfec5c`](https://github.com/Kiddos19882/AutoDraw/commit/4dfec5cdd9b8cf973fe109c925f7314100872e84)); no executor, production estimator, game input, mask, legacy or acceptance threshold changes. New CI validation is not yet confirmed.

- DOC-CODE-REUSE-001: added read-only `--usage` AST consumer/import-cycle inventory in the existing `tools/capability_catalog.py` + `check_markdown_docs.py`; static direct-call aliases, nested imports and producer owner relationships reported as E1 candidates. Separates 2 all-scope SCCs from **0 root-level SCCs** on current source; new unconditional `source/preparation` SCCs fail docs CI, without touching production/game code. [CI 43135827499](https://github.com/Kiddos19882/AutoDraw/actions/runs/43135827499) SUCCESS on `23a5a516`, 10 tests; first synthetic-fixture failure [43134688617](https://github.com/Kiddos19882/AutoDraw/actions/runs/43134688617) retained.


## 2026-11-12 — DOC-CODE-REUSE-001 knowledge reuse and AST contract check

- CLI `--find` ranks documented reuse candidates with E1-only provenance; extracted the capability registry/AST/search into `tools/capability_catalog.py` while keeping `check_markdown_docs.py` compatible. Added five real-repository lookup tests. [Final code CI 43126121772](https://github.com/Kiddos19882/AutoDraw/actions/runs/43126121772) SUCCESS on `dd9ec43e` (8 tests, 20 entries). No gameplay code affected.

- Expanded existing COMPONENT_CATALOG with 20 capability owner/entrypoint/scope/test-path entries, README navigation, reuse-first AI_WORK_GUIDE and DEC-031. Extended existing check_markdown_docs.py with read-only AST verification of indexed Python symbols/parameter names, duplicate capability IDs and owner/test paths; added regressions and source-aware docs CI triggers. No runtime, Stage6 or Monitor changes; [docs-integrity CI 43124607337](https://github.com/Kiddos19882/AutoDraw/actions/runs/43124607337) SUCCESS on `7b8f4aaa` (7 tests, 20 indexed AST capability contracts).


## 2026-11-12 — FILL001-SERIES-001 experimental quota-limited capture and verified Clear continuation

- After first live E4 resource stop ([raw evidence 5acb2e6](https://github.com/Kiddos19882/AutoDraw/commit/5acb2e6284a4425cdfea8812257fa85ea55ed88f), 100/141 strokes, remaining 241, existing guard 300), added run-bound exact prefix capture with settled PNG and QUOTA_LIMITED diagnostic-only status. Only verified same-session closed Monitor events and released mouse authorize original ENGINE-001 Clear, then fresh preflight for next task. Partial CHALK is kept separately from completed/quality PASS ranking. [Code 90701e8](https://github.com/Kiddos19882/AutoDraw/commit/90701e8adb22cada121ccc6f1a2f5076baca1fde), [test 1236ce9](https://github.com/Kiddos19882/AutoDraw/commit/1236ce9d8f6ea8438294d31948a51226a1c70563), [tally 6eae2c9](https://github.com/Kiddos19882/AutoDraw/commit/6eae2c94a7cd72c6be3662374c9cb816c16a17e2); [series CI 43114637544](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114637544) SUCCESS, [main 43114637531](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114637531) SUCCESS. New quota→Clear live E4 NOT_RUN; no production promotion, threshold/estimator changes or overwrite of historical raw.
## 2026-11-12 — FILL001-SERIES-001 Selenium Firefox branch isolation

- Existing shared Selenium/Firefox + Monitor/Bridge worker retained. Moved V5 trim-only `build_fill001_v5_source_plan` behind the series early-return branch, so signed series figures no longer depend on selected V5 candidate; added AST source-contract regression preserving common browser owner. [Fix 0e5075b](https://github.com/Kiddos19882/AutoDraw/commit/0e5075bdecf0557752533b46837b1401cf138427), [series CI 43109628909](https://github.com/Kiddos19882/AutoDraw/actions/runs/43109628909) SUCCESS; [main CI 43109630346](https://github.com/Kiddos19882/AutoDraw/actions/runs/43109630346) **IN_PROGRESS** (финальный E3 статус ещё не определён). No game E4/E5, no production behavior/threshold change.


## 2026-11-11 — FILL001-SERIES-001 live orchestration code added using proven ENGINE-001 Clear

- Added opt-in «Запустить серию (тестовая доска)» to existing FILL-001 GUI, wired through original integrated app/Stage6 owner with normal Stop; one signed figure at a time, fresh BoardPane passive witness/Monitor radius, generic exact CHALK binding, PNG quality, immutable reports then original calibrated Clear+blank comparator. Preserved ENGINE-001 0.15% tolerance and standard stage6/executor production defaults. Shared experiment cross-process owner lock. Synthetic regression [42975744219](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975744219) SUCCESS на `fcd29dc`; latest [series safety 42975856803](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975856803) и [main validation 42975856883](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975856883) SUCCESS на `fea265f` (Windows portable SKIPPED); new multi-figure E4/E5 NOT_RUN. No production promotion.

## 2026-11-11 — FILL001-SERIES-001 verified offline per-task variants (исторический этап до live-подключения)

- Experimental configurable loop now has 30 frozen-shape/scanline/brush preview variants, source DrawingPlan export, immutable run-statistics aggregation, and read-only Clear screen/counter pilot. Repeated Bridge session use requires verified Clear freshness and new run IDs. UI manifest/preview/analysis controls added, no auto game Clear or live multi-task execution. `execution_allowed=false`, existing FILL-001 legacy batch and production executor defaults unchanged. [CI 42970208091](https://github.com/Kiddos19882/AutoDraw/actions/runs/42970208091) 58 synthetic PASS. End-to-end game E4 NOT_RUN; latest SHA follow-up CI pending.

## 2026-11-11 — FILL-001 V5: W3 E4 quality PASS and provisional lower exact CHALK

- Archived W3 [`832bf2b`](https://github.com/Kiddos19882/AutoDraw/commit/832bf2bd52a8f5a3ca908562b4723c2983d603b6) completed Stage6 29/29, exact run-bound CHALK `1707-1=1706`, and active `FILL001_CHALK_FIRST_PERIMETER_V2` PNG PASS (99.3775% coverage, zero overshoot beyond 3 logical px). Previously quality-PASS W2 [`1c722ba`](https://github.com/Kiddos19882/AutoDraw/commit/1c722ba82be2c91b03570460101061df74e6b9a2) CHALK1709; W3 provisionally lower by 3 CHALK. Historic V1/V2 diagnostic FAIL unchanged. [CI 42923577993](https://github.com/Kiddos19882/AutoDraw/actions/runs/42923577993) SUCCESS on W3 commit; optional jobs skipped. Independent E5 and repeatability NOT_RUN; no production changes.

## 2026-11-10/11 — FILL-001 V5 first run-bound exact CHALK + active PNG quality PASS

- [`1c722ba`](https://github.com/Kiddos19882/AutoDraw/commit/1c722ba82be2c91b03570460101061df74e6b9a2) recorded experimental W2 E4 29/29, exact completed Bridge CHALK1709 and **PASS** of existing versioned `FILL001_CHALK_FIRST_PERIMETER_V2`: coverage99.3578%, max overshoot1.327083 logical px ≤3, no distant pixels; pointer parked off ROI on before/settled captures. V1/V2 zero-leakage diagnostics still FAIL, E5 NOT_RUN. Historical failed `36e95e4` remains unmodified; no production changes.


## 2026-11-10 — FILL-001 V5 captured PNG pointer decontamination (experimental)

- New live [36e95e4](https://github.com/Kiddos19882/AutoDraw/commit/36e95e49acfecdbae1969bdf3d7358f06ea72f54) confirms automated `EXACT_RUN_BOUND` CHALK1701 for 29/29, but independently reports perimeter PNG quality **FAIL**, not a quality-accepted candidate. Original before/after PNGs preserved.
- Visual RGB confounder: in-game cursor sprite visibly shifts between captured frames, contributing changed pixels outside target. Added V5-only verified no-click pointer parking outside ROI before future baseline and settled screenshots (`c1fe1f8`, `1b48fb1`, `0ca2a42` tests). No historical revision or acceptance relaxation; new live validation pending.


## 2026-11-10 — FILL-001 V5 float-radius Bridge compatibility (research-only)

- Fixed strict V5 finalizer rejecting mathematically integral radii serialized as JSON floats (`10.0`, `2.0`) with `type(v) is int`. Accepted values remain finite integer-valued numerics within 1..30; fractional, nonfinite, boolean and other unplanned drawing radii remain blocked. Code `252228c`, regression `6506774`.
- Added pre-draw loaded-finalizer contract guard for experimental V5 only (`aa56bb0`, `f1455b4`) and real E4 Bridge replay regression on immutable `3825d57` data (`88a12aa`). No generic executor/defaults, production estimator or quality thresholds changed.
- Historical Stage6 auto report stays BLOCKED; separately confirmed E4 closed Bridge source CHALK1694 and missing settled PNG/E5. Latest CI must be read at its exact SHA.

## 2026-11-10 — experimental FILL-001 V5 full single-run gate in existing Stage6

Добавлен opt-in запуск одной frozen V5 задачи после Firefox passive ROI, чистой доски exact `pointCount=1` и подтверждённой калибровки ползунка. Использованы существующие Stage6 MouseExecutor и closed-loop BrushSliderController: 29 strokes с 28×10 и финальным 2/3, stop, сохранение screen before/after PNG. Exact CHALK/quality отчет формируется только при проверенных run-bound Bridge events и Screen Mask V2; E5 независимый не выполняется автоматически. Ordinary Stage6 V5 loader и production defaults неизменны.


## 2026-11-10 — экспериментальная автоматическая Firefox ROI-диагностика

FILL-001 Firefox после подтверждения доски выполняет попытку безопасной пассивной BoardPane/OS ROI проверки с native Win32 foreground PID свидетельством и сохраняет версионированный неисполняемый JSON. Добавлена обработка отсутствующего Selenium в CI. Полное V5 исполнение и real CHALK не включены.


## 2026-11-10 — FILL-001 V5 immutable logical-plan export (experimental)

Из исходной frozen DEC-030 native fixture доступен экспорт двух экспериментальных DrawingPlan по 29 штрихов с mixed width 10/2 или 10/3. Зафиксированы исходный geometry SHA, версия quality policy и запрет исполнения; Stage6 mono loader явно отклоняет смешанную диагностическую ширину до появления проверенного handoff. Добавлены unit/regression tests. Production execution остаётся без изменений.


## 2026-11-10 — FILL-001 Firefox Monitor opt-in (experimental)

Добавлено опциональное подключение Firefox/Selenium к Game Monitor/Bridge из вкладки FILL-001: портал/iframe origin, подтверждение оператора, отдельный runtime, новая session, телеметрия, явное завершение. Исполнитель Stage6, frozen V5 geometry, CHALK estimator и production defaults не изменены. V5 automated mixed brush и live acceptance пока не готовы.


## 2026-11-09 — FILL-001 V5 native CHALK-first perimeter screening

Extended existing FILL001 fixture generator, Egret BoardPane WebGL harness, Firefox runner, alpha analyst, regression tests and isolated native CI with `FILL001_CHALK_FIRST_NATIVE_V5` / `FILL001_CHALK_FIRST_NATIVE_AUDIT_V5`. New frozen 4×2 lateral trim vs bottom brush combinations plus unchanged V4 source control; all native RGBA/SHA and rejected candidates preserved. Native trim0 alpha128 coverage >99.42% and max leakage depth 1 logical px, but **no game quality PASS or exact CHALK**. [Native CI](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385), [raw evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385/artifacts/13707703988). No production, runtime, historical mask, executor or default updates.


Дополнен DEC-030 capture E4 provenance gate: before/after PNG SHA-256 и размеры ROI, exact CHALK, task/plan/run/session теперь сверяются непосредственно с independently verified source E4 report. Stale/mismatched PNG fail-closed; explicit V3 BoardPane-only geometry применяется только через ранее проверенный binder. [CI](https://github.com/Kiddos19882/AutoDraw/actions/runs/42645465734); existing legacy FILL001 capture and matrix remain unchanged.


## 2026-11-09 — FILL001 DEC-030 full capture acceptance API

Версионированный `build_fill001_chalk_first_capture_from_runtime()` и `validate_fill001_chalk_first_capture()`: сохраняются строгие прежние инварианты Monitor/Bridge/executor и CHALK telemetry, добавлена новая приёмка independent screen ROI по DEC-030 (99% coverage, ≤3 logical px periphery). Shared core исключает дублирование и сохраняет legacy `build_fill001_capture_from_runtime`/`validate_fill001_capture` leakage=0 без изменений исторического результата. Regression tests positive/negative, full CI [42643765113](https://github.com/Kiddos19882/AutoDraw/actions/runs/42643765113). Без production/UI/45-cell batch изменений и без live запусков.


## 2026-11-09 — FILL-001 new forward PASS, CHALK first

Accepted policy `FILL001_CHALK_FIRST_PERIMETER_V2` for new run-bound FILL-001 quality: ≥99% coverage and Euclidean perimeter overshoot ≤3 **logical board pixels** everywhere, instead of legacy leakage=0. Further minimization of permitted leakage is subordinate to validated exact CHALK. Implemented separate versioned quality result in existing Screen Mask V2 audit/CLI with tests for far-away spill, threshold, scale and unchanged historical FAIL. No executor/legacy matrix changes; previous runs and artifacts not reclassified. [DEC-030](DECISIONS.md#dec-030-fill-001-новый-pass-с-ограниченной-утечкой-и-приоритетом-фактического-chalk).


## 2026-11-09 — FILL001 native lower stripe V4

Source fixture raw SHA added to V4 reproducibility contract without modifying candidate geometry. Saved exact input bytes in artifact and independently verified they match the fixture provenance and the per-case renderer manifest; test for input tampering fails closed. [Native CI 42577013425](https://github.com/Kiddos19882/AutoDraw/actions/runs/42577013425) SUCCESS, [artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/42577013425/artifacts/13655990846). Original V4 metrics remain unchanged.



Existing `chalk_fill_strategy_comparison.py`, `game_renderer_reference.js`, `run_egret_stage_reference_firefox.py`, targeted pytest and `engine001-e5-offline.yml` extended with independent versioned V4 bottom-row 1/2/3 px brush candidates on unchanged V2 trim3 and pixel-exact source control. Stores all positive, zero-delta, and leaking PNG cases, SHA/provenance and independent alpha / lateral / bottom audits. Native E3 SUCCESS; no game CHALK, no production executor/planner/default/threshold changes. [V4 raw evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168617/artifacts/13655800959).


## 2026-11-09 — FILL001 native spatial residual map V1

В existing FILL001 offline geometry analyzer, regression tests и CI добавлена версия `FILL001_NATIVE_CONTOUR_SPATIAL_AUDIT_V1`: SHA-verified read-only per-row/per-side decomposition исходных V2/V3 native PNG на top/bottom/left/right/interior, leakage zones и connected components при alpha 1/128/254, с независимой сверкой ранее сохранённых метрик. Не меняет production planner/executor/CHALK defaults/target thresholds и не генерирует исполняемые штрихи. [Native evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42573526457/artifacts/13653904396).


## 2026-11-09 — FILL-001 isolated native Egret footprint A

В существующие browser renderer/Firefox/native analysis/test/CI средства добавлена версия `FILL001_NATIVE_FOOTPRINT_A_V1` с 10 real Egret brush probes (normal/smooth, width5/10, straight/diagonal/corner). Сохраняются native PNG, manifest/provenance SHA и независимые измерения thickness/endpoint extents/alpha thresholds. Результат offline diagnostic only; не менялись production planner, executor, CHALK estimator, frozen masks и quality gates. [Versioned artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011/artifacts/13653019564).


## 2026-11-09 — native geometry studies FILL-001 V2/V3

Existing offline FILL-001 tools now support frozen versioned native-width10 contour endpoint trims (V2) and mixed native width5 outline + width10 interior (V3), preserved manifests/PNG/alpha sensitivity reports, with actual Egret WebGL and tests. All tested variants fail native-local coverage/leakage tradeoff; not integrated into production or executor. No thresholds, frozen masks, default brush or game runtime modifications. [Native evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42552197466/artifacts/13645982484).


## 2026-11-09 — FILL-001 native contour-first offline harness

В существующие FILL-001 geometry tools и renderer Firefox/BoardPane harness добавлен отдельный versioned режим генерации frozen native fixture, многолинейного WebGL replay и alpha-only сравнения с логической маской на backing ×3. Доказано в native reference: одинаковая геометрия C/E при разном порядке даёт 0 пикселей различия; контур добавляет 754 native пикселя относительно sparse-only. Результаты и негативные residual (coverage/leakage) сохранены в отдельном CI artifact [13644514101](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549813024/artifacts/13644514101), с запретом выдавать alpha-model за live screen quality. Существующий ENGINE-001 E5 и V3 live recorder не ослаблены, production planner/executor/CHALK defaults/quality thresholds не менялись.

## 2026-11-09 — исследовательские варианты FILL-001 contour-first

В существующем `chalk_fill_strategy_comparison.py` добавлены **два изолированных** режима сравнения: `--contour-first` (V1: порядок/глубокий inset) и `--contour-edge-trims` (V2: сначала замкнутый контур, горизонтальные линии прежних рядов с X-trim 1..4). Каждый режим создаёт отдельные versioned JSON и diagnostic PNG, отказывается перезаписывать результаты и запрещает трактовать sampling proxy как exact CHALK. Добавлены тесты и артефакты существующего GitHub Actions workflow [42547807009](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009). Legacy A–D, frozen mask, production Stage6/executor/CHALK estimator и quality thresholds не изменены. V1 глубокие отступы FAIL на всех трёх масках, V2 проходит только rectangle/wide; перенос в production запрещён до independent validation.


Записывать только изменения интерфейсов, форматов, возможностей и значимые изменения сопровождения. Ход проверки каждой задачи — [WORK_LOG](WORK_LOG.md). Полная прежняя редакция без изменений: [CHANGELOG_HISTORY_THROUGH_2026-11-08.md](CHANGELOG_HISTORY_THROUGH_2026-11-08.md).

## 2026-11-08 — FILL-001 V3: устранение ложного отказа после настройки кисти

- Из [первой Windows-попытки 76a58ab](https://github.com/Kiddos19882/AutoDraw/commit/76a58abc7444519841c3d8548ba8bee3979a708f) получены две сохранённые Monitor-серии регулировки радиуса, обе с `stroke_count=0`. Причина остановки — изменение размеров анимируемого `Preloader` в полном renderer SHA при неизменной BoardPane.
- Изолированно для V3 введён fingerprint только координатно значимой BoardPane-системы и её клиента/окна; raw full SHA продолжает сохраняться. Новые passive witness и проверка после before PNG используют стабильную геометрию; реальный сдвиг BoardPane, stale heartbeat и незнакомый session остаются блокирующими.
- Аудит V3 и его V2-derived Screen Mask binder сопоставляют координатную геометрию при сохранении полной raw provenance, без изменения V1/V2, frozen target, CHALK или Stage6 defaults. Регрессионный тест воспроизводит реальный архивный случай.

## 2026-11-08 — кнопки подключения Game Monitor/Bridge во вкладке FILL-001

- Добавлен отдельный блок из четырёх кнопок FILL-001: **запуск Bridge с Input Telemetry ON**, **копирование Game Monitor JS**, **копирование одноразового Bridge JS**, **проверка свежей live-сессии** (в том числе до создания manifest). Подключение JS в игровой iframe остаётся ручным действием в DevTools.
- Запуск переиспользует штатный Bridge контроллер лаборатории кистей, но явно включает телеметрию независимо от выбранного brush test scenario. Сессия с telemetry OFF не признаётся совместимой; недействующий Bridge не может предоставить старый snippet через кнопку FILL.
- Добавлены regression-тесты делегирования, forced telemetry, отрицательной проверки session и защиты от устаревшего snippet. Production executor, CHALK, игровая кисть и FILL V2/V3 измерения не менялись. Результаты тестов и CI — в [TEST_RESULTS](TEST_RESULTS.md).

## 2026-11-08 — отдельный FILL-001 Smooth A/B V3 BoardPane pilot

- Новый `FILL001_SMOOTH_AB_V3` с отдельными задачами ON/OFF и `FILL001_BOARDPANE_PREFLIGHT_V1`: логическая маска, 27-штриховой план, CHALK measurement, executor defaults и старые V1/V2 evidence не изменены.
- Вкладка FILL-001: новая кнопка **«Новый Smooth A/B V3 (BoardPane)»**. До загрузки Stage6 выполняется обязательная свежая проверка BoardPane geometry; некорректный/stale mapping блокирует игровой ввод, без fallback к старому ROI transform.
- Game Monitor Bridge (opt-in) дополняет read-only session metadata пассивными `isTrusted` событиями движения курсора при `buttons=0`; сохраняет до 16 samples с session/geometry SHA. Путь draw telemetry и штатные режимы не менялись.
- Добавлены regression tests для V3 manifest, provenance, preflight и Bridge, расширен существующий focused CI. Новый игровой E4, нативная Egret E5 и подтверждение исправленной утечки — **NOT_RUN**; подробности в [TASKS](TASKS.md), [TEST_RESULTS](TEST_RESULTS.md) и [Game Monitor §14](GAME_MONITOR_BRIDGE_REFERENCE.md#14-fill-001--отдельный-boardpane-anchored-smooth-ab-v3-исследовательский-пилот).

## 2026-11-08 — отдельный FILL-001 Smooth A/B V1

Добавлен экспериментальный двухзадачный режим ON/OFF с отдельными task IDs и frozen 27-stroke plan, predeclared smooth mode и raw подтверждением по реальным Egret ENGINE_FRAME_SAMPLE. UI сохраняет по каждому запуску raw audit и независимый FILL PNG quality outcome даже при quality FAIL; есть парное сравнение exact CHALK, coverage, leakage и пограничных пропусков с контролем одинаковых before ROI. Старые V1/RS данные, 45-cell matrix и production execution defaults не меняются. Новый E4 и регрессионный CI на момент подготовки NOT_RUN.

## 2026-11-08 — FILL-001: opt-in native Monitor 0.2.4 single-task diagnostic

- Версия `FILL001_MONITOR_SAME_RUN_V1`: существующая вкладка FILL-001 получила диагностический флаг/создание неизменного RS 27-stroke rectangle плана, однокадровые пары full-screen/board-ROI PNG и дополнительный строгий raw Monitor/Bridge audit без ослабления основного PNG gate.
- Legacy 0.2.1 и modern 0.2.4 bind/capture работают по отдельным exact versioned contracts; смешанные и неизвестные версии fail-closed. Перед input требуется свежий Bridge + Egret observation + native WebGL BoardPane geometry и ≥1600 exact remaining CHALK. Private desktop screenshots требуют явного предупреждения и не должны автоматически публиковаться.
- [CI 42458832846](https://github.com/Kiddos19882/AutoDraw/actions/runs/42458832846) **SUCCESS** для `b98d9e0` (995 Preparation/G3 PASS, 82 subtests); игровой runtime новой версии ещё **NOT_RUN**. Не изменены production draw/executor paths, frozen FILL001 quality gates и исходные E4 captures.

## 2026-11-08 — FILL-001: versioned right-edge spatial diagnostics

- Existing committed screen-residual analyzer now outputs opt-in-compatible supplementary `FILL001_RIGHT_EDGE_SPATIAL_V1.json`, pinning the actual saved screenshot + 27-stroke endpoint derivation with strict SHA/run/CHALK checks. **No change** to frozen comparison report, original screenshots, thresholds or production paths. [Evidence artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289/artifacts/13607454421), [CI 42456241289](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289) Preparation/G3 977 PASS.
- 499 right middle misses form a 3–7px-wide strip across 114/114 screen rows; 134 left middle misses median1, 11 original leaked pixels remain. Causality undecided (legacy FILL001 same-run Stage mapping missing), quality FAIL unchanged. Initial Windows newline-test failure [CI 42456007010](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456007010) retained, negative test corrected in `c4fefe6`.

## 2026-11-08 — ENGINE-001: offline E5 native screen-RGB reference validation

- Исследовательский Egret harness расширен для raw Monitor 0.2.4 `accepted_points` с fail-closed проверкой `DRAW_SAMPLE` и observed mode; добавлены immutable 9-run Firefox Stage A–D и independent screen-RGB validator. Старые paired-renderer пути, пороги DEC-025, production и FILL-001 thresholds не менялись.
- [E5 CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181) SUCCESS: 9/9 `PASS_PER_RUN`, реальные финальные screen RGB IoU по направлениям H/V/D в §22. Первый [CI 42453831682](https://github.com/Kiddos19882/AutoDraw/actions/runs/42453831682) дал 9/9 инструментальных REJECTED из-за отсутствовавших bbox; corrected в `6810f75`, отрицательные отчёты сохранены. Direct live native alpha и temporal order остаются открытыми.

## 2026-11-08 — ENGINE-001: live 9/9 evidence и актуализация E5-границы

- После `7b129c2` исправлена ложная остановка `lab_bridge_gate`: readiness опирается на отдельный timestamp валидного heartbeat, а не на тип последнего игрового event. [CI 42448779447](https://github.com/Kiddos19882/AutoDraw/actions/runs/42448779447) SUCCESS.
- Приняты и индексированы raw runtime results `1771653`: E4 9/9 clean-board single-stroke runs, exact CHALK 846, 861 Egret `ENTER_FRAME` samples, [full CI 42449898657](https://github.com/Kiddos19882/AutoDraw/actions/runs/42449898657) SUCCESS. Начат независимый E5 geometry fit из 1641 samples; full native PNG/Egret pixel parity **NOT_RUN**, статус ENGINE-001 остаётся PARTIAL.
- Обновлён текущий слой документации без изменений production-кода и исходных/historical raw данных; FILL-001 98.430600% coverage, 11 leakage сохраняется FAIL.

## 2026-11-08 — ENGINE-001: one-click isolated Windows laboratory preparation

- В существующей вкладке Brush Tests создана кнопка полного автономного блока 9 одиночных штрихов (3 axis scenarios ×3 repeats) с fail-closed Bridge/Monitor preflight, Clear-before-run, existing Stage6, independent raw PNG/CHALK/geometry audit, durable journal.
- Monitor 0.2.4 поддерживает opt-in native Egret `ENTER_FRAME` observer и raw stroke smooth option; Bridge хранит эти events и rollups отдельно от старого RAF probe. Изменены только исследовательские файлы; новый gameplay run не выполнен, производственные параметры прежние.
- Исходный FILL-001 live остаётся FAIL (98.430600% coverage / 11 leaked pixels / CHALK=1260 historical). Live E4 и independent E5 требуют отдельного запуска.

## 2026-11-08 — ENGINE-001: controlled stationary duplicate frames in native BoardPane

- Исследовательский opt-in `?frames=fill001`: 0/1/3 rejected-point `ENTER_FRAME` simulations per stroke, same frozen 27/1260, six Canvas2D/WebGL PNG, Python independent threshold audit. [Full CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) SUCCESS at `a35d782`, 0 final RGBA differences in each backend.
- Negative path-count gate [42440726798](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440726798) exposed next-stroke `redraw(full)` clearing old paths; corrected expected counts 70/71/73 rather than 70/97/151. Production unaffected, live quality and CHALK untested.

## 2026-11-08 — ENGINE-001: native 5px contour across endpoint variants

- Исследовательский opt-in `?outline=fill001` в существующем Egret browser harness добавляет одинаковый замкнутый 5 logical px contour из pinned rectangle mask ко всем трём endpoint режимам; 15 дополнительных native PNG, независимый OpenCV audit с four-alpha metrics и CI artifacts. [Full CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) SUCCESS (`f381ffe`).
- После добавления обводки board-local coverage улучшилась, но новый modeled leakage >0 и zero right-middle recovery в smooth. Исторический live capture остаётся FAIL; production code/game bundle, executor и estimator не менялись.

## 2026-11-08 — ENGINE-001: native Painter endpoint reference

- Добавлен opt-in `?endpoint=fill001` в существующий browser harness, 15 PNG (27-stroke aggregate и три изолированных штриха, game-smooth / native forced-last / normal), independent board-local OpenCV raster analysis в [validation CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) **SUCCESS** на `1805ebf`.
- Экспериментальные методы не затрагивают production и историю. Исправлен диагностический учёт пустого atom slot после первого Egret job FAIL. Same-run screen calibration/live PNG остается отдельным открытым gate.

## 2026-11-08 — ENGINE-001 accepted-only Egret temporal reference

- Добавлен opt-in исследовательский режим `?temporal=fill001` **в существующий** `tests/game_renderer_reference.js`: actual `BoardPane` one-pass / incremental redraw, 27 run-bound strokes/1260 accepted points, строгая входная валидация, 4 Canvas2D/WebGL PNG, manifest. Production и прежние 20 renderer fixtures не изменены.
- [CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) browser job SUCCESS на `8d5d088`: 0 difference между двумя итоговыми растрами и 70 vs 29 накопленных Graphics paths. Данные исторические; exact live CHALK новых алгоритмов не измерялся, full temporal/screen equivalence не доказаны.

---

## 2026-11-08 — подтверждённая граница источников ENGINE-001

- [Архитектура доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#14-финальная-сверка-источников-game-monitorbridge-prr-и-runtime-2026-11-08) дополнена сравнением Egret E1, Monitor/Bridge, PRR 6/6 E3 и snapshot E4; устранено ошибочное утверждение, будто старый JSON содержал вычисленные `boardClientCorners`.
- Уточнены пределы PRR PASS по ранее установленной DEC-025 (≥0.92) и отделены от pixel identity и FILL-001 качества. Новых исходников, экспериментальных данных или runtime проверок нет.

---

## 2026-11-08 — полная статическая цепочка input/frame/Canvas/WebGL для доски

- [GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), §13: документирована desktop/mobile доставка pointer событий, фактический `mouse.enable` hook, порядок `SystemTicker.render → ENTER_FRAME`, матрицы `globalToLocal`, Canvas2D raster внутри WebGL, offscreen `destination-in` mask, scrollRect clipping и stage/backing/CSS преобразования.
- `ENGINE-001` остаётся PARTIAL до финальной сверки с Monitor/PRR; новые тесты, изменения приложения и runtime запуск не выполнялись.

---

## 2026-11-08 — прямой разбор BoardPane из byte-verified main bundle

- [Справочник игровой доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) расширен исходными методами `BlackBoardAtom/BoardPane/Painter/PainterPopup`, таблицей состояний и бинарного `Atom`, различием `redraw()`/`redraw(false)`, границами one-pass Egret replay.
- Это E1 документирование, не изменение кода и не доказательство нового live-рисунка; план future tests обновлён без запуска.

---

## 2026-11-08 — документация игровой доски и перенос тестов в будущий план

- Добавлен [GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md): сопоставленная архитектура Egret/BoardPane, детали input sampling/CHALK/normal-smooth path/Canvas-WebGL/маски/координатные пространства и пределы доказательств.
- [ENGINE-001](TASKS.md) назначен текущим P0; реализованные A–D/PRR/RS и предложенные E1–E4, Egret multi-stroke replay зафиксированы [в ROADMAP](ROADMAP.md#отложенная-программа-тестов-fill-001-geom-001-и-связанных-gates) как будущие, без запусков и без изменения прежних результатов.
- Production code, original evidence и master не изменены.

---

## 2026-11-08 — сохранённый game PNG против модельной контурной коррекции

- Добавлен изолированный (ф) `source/preparation/chalk_fill_screen_residual_comparison.py` с pinning actual evidence SHA, идентичным capture-audit screen transform, counterfactual overlays offset5–8, baseline-model discrepancy и ±1px sensitivity. Добавлены tests и CI artifact; никакой executor integration.
- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS на `16f0e1b`, [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Первый [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) FAILED из-за LF/CRLF JSON checkout, исправлен через канонический SHA только JSON без ослабления проверки PNG; сохранён в WORK_LOG.
- Actual live FILL-001 quality FAIL не изменён; contour model и sampling proxy не являются измеренным CHALK.

---

## 2026-11-08 — экспериментальный анализ FILL-001 A–D

- Изолированный (ф) `source/preparation/chalk_fill_strategy_comparison.py`: плотные/редкие scanline, связный contour, модельная oracle-коррекция residual; reuse frozen FILL masks и current OpenCV painter; **not executor ready**.
- Unit tests и GitHub Actions выгрузка 15 PNG/JSON. [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS, [artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597). CHALK estimator, Stage6 и production settings не изменены.

---

## 2026-11-08 — проверяемый актуальный слой и сохранённая история

- `docs/README.md` — полная навигация по 99 Markdown; текущие `PROJECT_STATUS/TASKS/ROADMAP/TEST_RESULTS` отделены от истории; архивы девяти старых редакций имеют проверяемые SHA-1 Git blob.
- Второе решение `DEC-016` перенумеровано в `DEC-027` с traceable mapping; методология в `AI_WORK_GUIDE` ускоряет выбор профильных источников.
- Введён Markdown integrity workflow и 5 unit tests: [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS; ноль найденных нарушений локальных ссылок, индексирования и уникальности решений. Внешние GitHub URLs, runtime и semantic correctness этот CI не проверяет.
- Исходный код приложения, CHALK predictor и первичные экспериментальные файлы не изменялись.

---

## 2026-11-08 — документация: быстрый актуальный контекст

- Текущие [PROJECT_STATUS](PROJECT_STATUS.md), [TASKS](TASKS.md), [ROADMAP](ROADMAP.md) отделены от полной исторической записи: исторические версии сохранены Git blob-for-blob.
- [TEST_RESULTS](TEST_RESULTS.md) преобразован в реестр доказательств G1–G3, INT-006/R, FILL-001-RS, renderer/PRR и 81-image offline corpus; сохранены все прежние подробные измерения.
- Не изменены форматы .autodraw, исходники algorithms/executor, Game Monitor, CHALK profiles, пользовательские данные или production settings.

## 2026-11-08 — последние подтверждённые функциональные изменения до документационной реорганизации

- В `screen_candidate_corpus.py` и tests добавлена проверка source images/geometry/color source summaries для 81 plans; [offline CI 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) SUCCESS на `5a55e9f`.
- [AutoDraw validation 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) SUCCESS на `5a55e9f`. Успех автоматических проверок не подтверждает live CHALK или FILL-001 PNG PASS.

Все предыдущие даты, тесты, неудачные прогоны и SHA доступны в [истории CHANGELOG](CHANGELOG_HISTORY_THROUGH_2026-11-08.md).
