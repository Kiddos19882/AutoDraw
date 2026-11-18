**ENGINE-001 B1-R-P3B (2026-11-18, prereg before run):** [P3B source-adaptive 32 of 128 engine RGB protocol](ENGINE001_B1R_P3B_ENGINE128_ADAPTIVE32_PREREG_2026-11-18.md). Engine (ф) `gameEngine/main.min_653f95bc.js` blob SHA `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388` statically includes exactly128 unique RGB swatches in `PainterPopup.createElaborateEasterEggs`; every historical JSON-selected32 matches an engine swatch (32/32), metadata original captured103→32. **E1 static only, engine128 runtime palette accessibility UNKNOWN** (conditional PainterExtend/easter eggs). No old G32 pixel map/V44 candidate. Four source P2D user-accepted RGB×two prereg greedy palette selectors, true32 source-grounded assignments; P3 eight previous SOURCE_GATE_FAIL preserved; P3B E2/E3 NOT_RUN prereg; deliver all results one ZIP.

**ENGINE-001 B1-R-P3 original-source→real game32: 8/8 image SOURCE_GATE_FAIL, technical PASS (2026-11-18):** [CI44278535963](https://github.com/Kiddos19882/AutoDraw/actions/runs/44278535963) SHA `c1bfbfa7b85d6cd86e793f81fb9f54e92fb8039d`: E2 13/13, E3 technical SUCCESS; [one ZIP artifact14415806718](https://github.com/Kiddos19882/AutoDraw/actions/runs/44278535963/artifacts/14415806718) SHA256 `e39f01342daf708d54eb30407e73d6ba36511b2a3b1eb22d83aadc08415215a9`, CRC and 59/59 file hashes PASS. All four user-approved P2D source RGB combinations preserved and recomputed from original; both real32 swatch methods N_NEAREST/S_GUARDED **fail original-source quality**. N_NEAREST male-face ROI ΔE00 12.58>12, glaring black/dark & pink artifacts, uses14/16 game swatches; S_GUARDED 1692/1709 unresolved pixels (threshold720), male-face14.89>12; **not drawable** as complete 32-color plan. D_BORDER and D_COMPONENT24 source logical differed106px but yielded identical 32-index maps under same C_096/C_192+method: keep **both** RGB source candidates approved, no false claim one guard is inferior. [Frozen P3 prereg and negative](ENGINE001_B1R_P3_ORIGINAL_SOURCE_GAME32_PREREG_2026-11-18.md) / DEC-036. Next E1 audit availability of full original **103 real-game swatches** (current JSON is screenshot-selected 32-of-103), source-target-adaptive palette must be freshly preregistered, no archived G32 pixel map/contour; game E4/E5/CHALK NOT_RUN.

**DEC-036 (2026-11-18) P2D source RGB visual signoff:** пользователь прямо подтвердил «D_component24 хорош и d_border тоже, оба проходят дальше»; **все четыре C096/C192×D_BORDER/D_COMPONENT24** разрешены для независимого B1-R-P3 game32 исследования, без выбора единственного победителя. [Решение DEC-036](DECISIONS.md#dec-036-engine-001--b1-r-p2d-ручное-визуальное-принятие-обоих-способов-подавления-серого-ореола) и [frozen P3 prereg](ENGINE001_B1R_P3_ORIGINAL_SOURCE_GAME32_PREREG_2026-11-18.md). Оценка P2D только source RGB, не 32-color/native/CHALK. P3 runner E2/E3 NOT_RUN до CI.

**ENGINE-001 B1-R-P2D gray-halo repair verified (2026-11-18):** [CI44275730549](https://github.com/Kiddos19882/AutoDraw/actions/runs/44275730549), exact SHA `6170db18fd249c551b4ca627606b5977d8a3958f`, 13/13 E2 PASS, E3 SUCCESS, independently downloaded [one source-image/visual review ZIP artifact14414227735](https://github.com/Kiddos19882/AutoDraw/actions/runs/44275730549/artifacts/14414227735) SHA256 `1899a2bf10413e787cc79bdbd69cf7ea8e5ffafc31f4f91a0380ba0cef303b43` CRC + 38/38 internal report-member hashes PASS. At the USER-marked light patch over hair, false dark source-bright NEAREST logical pixels fall **27→1** for both C_096/C_192 under both prereg source-only guards. D_BORDER affects only56 original full pixels, D_COMPONENT24 affects243; all four prereg numerical source gates PASS, source face/edge fidelity non-regressed and original P2C ink unchanged; full RGB remains347/443 (not game32). User explicitly says *both old C_096/C_192 mostly visually good so far*, but requires patch repair; **fresh P2D user signoff PENDING**, no promotion. [Frozen P2D protocol, CI and outcome](ENGINE001_B1R_P2D_BACKGROUND_HALO_GUARD_PREREG_2026-11-18.md) / [DEC-035](DECISIONS.md#dec-035-engine-001--b1-r-p2c-пользовательская-предварительная-оценка-и-локальное-исправление-светлого-фона). Production/master/native/E4/E5/exact CHALK NOT_RUN.

**DEC-035 / ENGINE-001 B1-R-P2D (2026-11-18, prereg):** Пользователь: оба C_096/C_192 «в основном визуально хороши пока что», но серый ореол на светлом фоне над волосами требует исправления. E1 root: original near-white RGB стал J_FINE flat-medoid (227,226,221) ещё до P2C, а не новый kmeans штрих. [DEC-035](DECISIONS.md#dec-035-engine-001--b1-r-p2c-пользовательская-предварительная-оценка-и-локальное-исправление-светлого-фона) и [P2D frozen prereg](ENGINE001_B1R_P2D_BACKGROUND_HALO_GUARD_PREREG_2026-11-18.md): два source-only background guard, не меняют true ink pixel RGB, baseline P2C frozen, user visual PENDING на исправленную версию. P2D E2/E3 NOT_RUN at prereg, no game32/native/E4/CHALK.

**ENGINE-001 B1-R-P2C source ink compression verified (2026-11-18):** [CI44263770838](https://github.com/Kiddos19882/AutoDraw/actions/runs/44263770838) exact SHA `b20d9e8ead30fa7605d69f655ae3d7ab6c0890fb`, 11/11 E2 PASS, E3 SUCCESS, [one review ZIP artifact14408783882](https://github.com/Kiddos19882/AutoDraw/actions/runs/44263770838/artifacts/14408783882) SHA256 `f396ed07bb9fb46427350c57a4bf37aa47f5bbc49e89db25b72a3f9093b09e42`, CRC/26-of-26 report-linked hashes PASS. C_096/C_192 source-ink masks use 96/192 original RGB medoids over 252 original region colors; resulting full composite347/443 distinct RGB, logical NEAREST347/442, visual LANCZOS10,778/11,068, mean source ΔE00 1.149/1.036. Both predefined source numerical gates PASS **but human visual PENDING**; no game32/native/E4/E5/exact CHALK. [Frozen P2C protocol and results](ENGINE001_B1R_P2C_SOURCE_INK_PALETTE_PREREG_2026-11-18.md). Next user ZIP visual review, then separate source-supported palette32 prereg (not archived G32).

**ENGINE-001 B1-R-P2C original-only detail palette (2026-11-18 prereg):** [Frozen protocol: reduce original RGB residual ink colors to ≤96/≤192 source-derived source-mask medoids without changing silhouette or old map](ENGINE001_B1R_P2C_SOURCE_INK_PALETTE_PREREG_2026-11-18.md). Two prereg candidates, original full RGB only, 252-color region base and P2B-K_DETAIL current-run footprint; no G32/V44/M1 game32, P2C E2/E3 NOT_RUN at prereg, human visual PENDING. Review results to be delivered in one ZIP archive.

**ENGINE-001 B1-R-P2B original detail source screening (2026-11-18):** [CI44261071470](https://github.com/Kiddos19882/AutoDraw/actions/runs/44261071470) at `699c5a641db31ff6f9be4e82bf0d3397109091d0` 9/9 unit PASS / full E3 SUCCESS, artifact CRC/25-of-25 hashes PASS. Source medoid 252 flat colors + source-exact residual mask recovers visual eyes/face/hair; K_RESTRAINED/K_DETAIL mean ΔE00 0.858/0.749, 1px original-edge recall1.0, both `SOURCE_SCREEN_PASS_VISUAL_PENDING`. **Combined preview still >11k RGB**, no palette32/native/game/CHALK acceptance. [Frozen P2B protocol and execution](ENGINE001_B1R_P2B_RGB_RESIDUAL_INK_PREREG_2026-11-18.md); next P2C detail-color compression study before game32; user visual PENDING.

**ENGINE-001 B1-R-P2B (2026-11-18), prereg before independent test:** [original RGB in-region medoids plus source-exact protected residual ink](ENGINE001_B1R_P2B_RGB_RESIDUAL_INK_PREREG_2026-11-18.md). K_RESTRAINED/K_DETAIL use original pixel residual detail to improve eyes/mouth/hair, distinct fresh ID from failed P2-V1; source-only/no G32-V44-M1 candidate, E2/E3 PENDING, no game32/native/CHALK.

**ENGINE-001 B1-R-P2 2026-11-18 negative:** [CI44259464359](https://github.com/Kiddos19882/AutoDraw/actions/runs/44259464359) at `ee9f492d51eb81a449697b67d5d4f814c5b46c1e` E2 10/10 and E3 SUCCESS, ZIP CRC/21-of-21 artifact hashes PASS, but source image quality **J_FINE/J_COARSE both FAIL** (p95 source ΔE00 25.475/26.241 and both face-eye ROIs >8). New 682/371-label region medoid RGB with own original-derived outline reduces source colors to252/163 but damages thin details/eyes/mouth; no G32/V44/M1 candidate. Full [frozen P2 protocol and negative outcome](ENGINE001_B1R_P2_JOINT_REGION_OUTLINE_PREREG_2026-11-18.md). Next fresh P2-B source-detail restoration before game32/native; user visual PENDING, game E4/E5/CHALK NOT_RUN.

**ENGINE-001 B1-R-P2 prereg (2026-11-18):** [Joint original-RGB region medoids + new per-candidate outline experiment](ENGINE001_B1R_P2_JOINT_REGION_OUTLINE_PREREG_2026-11-18.md). Two variants J_FINE/J_COARSE, original 200×320 RGB only, source in-region medoids and jointly derived original-source edges. No G32/V44/M1 candidate; no game32, native Egret, game E4/E5/CHALK. Protocol frozen BEFORE any P2 image run; E2/E3 PENDING; human visual PENDING. Previous B1-R-P1 unchanged.

**ENGINE-001 B1-R-P1 original-only 2026-11-18, verified:** [CI44244364830](https://github.com/Kiddos19882/AutoDraw/actions/runs/44244364830) SHA `6c90de357fcecdb86a38e581f59e0d7eea3cf671`, 8/8 unit E2 PASS, E3 standalone CI SUCCESS, artifact14400733930 ZIP SHA256 `86a56b6d24aabdbb683eb46c216e255f5e976fdf41f035fe9ce5c9c625ca330d`, CRC+14/14 SHA PASS. A_SOFT/A_MID both original-RGB-only source screening PASS_VISUAL_PENDING; mean ΔE00 0.189/0.250, flat roughness -15.7%/-24.4%, excess chroma0, protected logical13437/36000 exact. New derived contour **preview only** and visual user review pending; original G32/V44/M1 masks excluded from active candidate. See [frozen protocol and outcome](ENGINE001_B1R_P1_FULLRGB_EDGE_AWARE_PREREG_2026-11-18.md). Next coherent region-color+new-outline B1-R-P2, not game32 or paint yet.

**ENGINE-001 B1-R-P1 original RGB-only prereg (2026-11-18):** [B1-R-P1 full-resolution source-derived protection and independently generated new edge-outline protocol](ENGINE001_B1R_P1_FULLRGB_EDGE_AWARE_PREREG_2026-11-18.md). Fixed A_SOFT/A_MID bilateral, original 200×320 RGB → 150×240, no G32/M1/V44 candidates or historical masks, no palette32/native/game/CHALK. Test-only source runner registered, E2/E3 NOT_RUN until concrete CI.

## Текущая активная задача (2026-11-18) — ENGINE-001 / B1-R

**Решение пользователя [DEC-034](DECISIONS.md#dec-034-engine-001-перезапуск-с-b1-r-g32-и-старый-v44-b--только-история-и-сравнение):** G32/P4c1 и старый контур V44-B **больше не входят в новые кандидаты**; только отдельные исторические/сравнительные материалы. Нельзя возвращаться к их заливке или накладывать прежний V44-B как готовый контур новой картинки. Старые B1/B2/B3/B4 артефакты, workflow и отрицательные исходы **сохранены**, не являются текущим backlog.

**Новый активный план:** [B1-R — original RGB → защита важных деталей и новых границ → edge-aware упрощение → согласованные цветовые зоны и НОВЫЙ контур → отдельная game32 → настоящая круглая кисть Egret → лимиты одной доски / будущий multi-board](ENGINE001_B1R_RGB_FIRST_RESTART_PLAN_2026-11-18.md). Начало B1-R-P1: анализ и prereg source-only RGB-кандидатов без старых карт/контура. **E0 plan; B1-R E2/E3 NOT_RUN**, game E4/E5/CHALK NOT_RUN. Предыдущий B4 native source quality FAIL, [CI44236852882](https://github.com/Kiddos19882/AutoDraw/actions/runs/44236852882), остаётся историческим контролем.

**ENGINE-001 B4 genuine full Egret G32+V44B experiment (2026-11-18):** [CI44236852882](https://github.com/Kiddos19882/AutoDraw/actions/runs/44236852882) SHA `ec267856f9d0e0484ec774a406750efcae55d1b7` E2 B4 7/7 + historical P4c2 8/8 + Node20/20 PASS, E3 SUCCESS; artifact14398280766 ZIP SHA256 `140167978b9ffe45a0a33df9f9aa4117e487b01f0adf3614b2abf211f4578d59` CRC+44/44 SHA PASS. Real full native two variants each1133 game32-paint +410 unchanged V44-B geometry LAST (1543/5277 synthetic NOT CHALK). Original395 RGB contour vs nearest32 mapped only15 swatches: full native mean ΔE00 original6.8508 vs palette7.5929, **both FULL_IMAGE_QUALITY_FAIL**; 14/17 fill owner alpha24 below99 and owner28 outside ROI18 backing px, unchanged P4c2. Next **B5 source-first simplified coherent visual image**, not more old G32 island deletion or merely recoloring contour; no exact CHALK/game E4.

**ENGINE-001 B4 (2026-11-18, prereg before native run):** [full genuine Egret G32 paint +410 original contours LAST, and nearest game32 contour palette](ENGINE001_COLOR_ISLAND_R2_P2_P2_B4_NATIVE_FULL_COLOR_OUTLINE_2026-11-18.md). Frozen P4c1 1133 paint paths, unchanged original410 contours, 1543 paths/5277 synthetic vertices; existing P4c2 native paint FAIL (14/17 colors below99%). Two full actual Windows WebGL A/B images needed; protocol registered, B4 runtime NOT_RUN, original RGB contour NOT a game32-valid final plan.

**ENGINE-001 B3 real Egret native diagonal probe (2026-11-18, verified):** [CI44234300377](https://github.com/Kiddos19882/AutoDraw/actions/runs/44234300377) SHA `100e3432ee8ff8f41e3259b27b2d6bee71f29f2f`, E2 7/7 unit and Node 20/20 PASS, E3 SUCCESS, artifact14396257751 ZIP SHA256 `5a2ce0a013eb67bdfaf43b1df716ef8b44bd946bf94b94d7a46ede06cbeab0e6`, CRC and 25/25 report-linked SHA PASS. 12 real WebGL width2/4 isolated diagonal strokes: **2/12 pass the pre-registered strict zero foreign ink criterion** (both on white-cross), 10/12 fail strict; all12 had **zero native alpha24 beyond 3 logical pixels from owner and zero ROI exterior**, so do not confuse this conservative gate with the user-allowed 3px tolerance. No game E4/CHALK. [Frozen B3 protocol/results](ENGINE001_COLOR_ISLAND_R2_P2_P2_B3_DIAGONAL_NATIVE_FOOTPRINT_PROTOCOL_2026-11-18.md).

**ENGINE-001 B3 native diagonal 2026-11-18 — in execution:** isolated read-only actual Egret WebGL workflow [CI44234300377](https://github.com/Kiddos19882/AutoDraw/actions/runs/44234300377) at SHA `100e3432ee8ff8f41e3259b27b2d6bee71f29f2f`: original source/palette/renderer/B1/M1 pins verified, B3 7/7 synthetic contracts and original JS regression checks passed at step level; Windows native diagonal sample **IN_PROGRESS / E3 NOT_YET_CONFIRMED**, no native source safety claims or results until job/artifact completed. Separate [B3 protocol](ENGINE001_COLOR_ISLAND_R2_P2_P2_B3_DIAGONAL_NATIVE_FOOTPRINT_PROTOCOL_2026-11-18.md). No production/game E4/CHALK.

**ENGINE-001 R2-P2-P2-B3 (2026-11-18):** [preregistered real Egret diagonal brush micro-join protocol](ENGINE001_COLOR_ISLAND_R2_P2_P2_B3_DIAGONAL_NATIVE_FOOTPRINT_PROTOCOL_2026-11-18.md). B1 4-vs-8 connectivity lead now has a frozen source-protected native method: at most two real B1 diagonal pairs per crossing class and widths2/4 using existing Windows Firefox/WebGL BoardPane harness. **E0 PLAN_REGISTERED, B3 implementation/E2/E3 NOT_RUN**; no new native safe-join, game CHALK or production claim.

**ENGINE-001 B2 (2026-11-18) completed, SOURCE_GATE_FAIL:** [CI44232121497](https://github.com/Kiddos19882/AutoDraw/actions/runs/44232121497), SHA `e5b9f1553b2fa11d473e1e558cfcb983edbdc903`, E2 6/6 PASS, E3 SUCCESS; artifact14396035800 verified CRC/15-of-15 hashes. B2_SAFE4 original-safe 8 regions/8 pixels changed, 4-connected game-color regions 1427→1417, singletons 883→874, still >G32 (1284/779). New E1 topology audit: B1 has 816 eight-connected regions vs G32 924, **not native brush proof**. Next study Egret true round-brush diagonal connectivity; stop broad tiny-island cleanup.

**ENGINE-001 R2-P2-P2-B2 (2026-11-18):** [new frozen conservative source-safe game32 island cleanup protocol](ENGINE001_COLOR_ISLAND_R2_P2_P2_B2_SOURCE_SAFE_COMPONENT_CLEANUP_PROTOCOL_2026-11-18.md) after rejected B1, original B1_CHROMA12_SPATIAL and Egret V44-B410 are immutable controls. Test-only experiment pending E2/E3, no source/game/native/CHALK PASS until independent results.

**ENGINE-001 R2-P2-P2-B1 P0→game32 (2026-11-18, verified negative):** [CI44230985963](https://github.com/Kiddos19882/AutoDraw/actions/runs/44230985963) SHA `774dedb4f6a7cc51d91cf6b2567e14d38bd9d7f8`, E2 7/7 PASS, E3 SUCCESS, artifact14394179902 CRC/19-of-19 SHA PASS; four B1 game32 candidates **all SOURCE_GATE_FAIL**. Original-source chroma+12 reduces excess-chroma flags 1368→0 but has1427 nonwhite components vs frozen G32 1284, 883 vs779 singletons. P0→nearest32 is worse fragmented2210. Frozen V44-B410 unchanged; next separately prereg conservative island cleanup without erasing authentic protected details.

**ENGINE-001 R2-P2-P2-B1 / P0→game32 (2026-11-18):** [frozen source-supported palette protocol](ENGINE001_COLOR_ISLAND_R2_P2_P2_B1_P0_GAME32_SOURCE_SUPPORT_PROTOCOL_2026-11-18.md) — исследование реальных 32 игровых цветов после P0, chroma support original RGB, original protected-details seam, V44-B410 неизменен; G32 и P0 frozen controls. До проверки конкретного CI/PNG эксперимент NOT_RUN и native brush/CHALK NOT_RUN.

**ENGINE-001 / RGB-VISUAL-MVP-P0 (2026-11-18, verified):** [preregistered protocol](ENGINE001_RGB_VISUAL_MVP_P0_EDGE_AWARE_PREFILTER_PROTOCOL_2026-11-18.md), [CI44229576245](https://github.com/Kiddos19882/AutoDraw/actions/runs/44229576245) SHA `b0b134d98c7ed7093dc61fcf02e0ba87e3f1e3c2` E3 SUCCESS, 5/5 E2 PASS, artifact14393769123 CRC +14/14 SHA PASS. 4/4 filter candidates pass *preliminary source-RGB screening*, original-source protected 7947 pixels and immutable original Egret V44-B410 alpha; user visual pending. Still ~10k+ RGB colors, **NOT** a valid game32/native fill or CHALK result. Next: B1 original-grounded color-region/game32 choice after visual review.

**ENGINE-001 R2-P2-P2-A1 (2026-11-18):** [A1 source region / G32 support protocol](ENGINE001_COLOR_ISLAND_R2_P2_P2_SOURCE_SUPPORT_AUDIT_PROTOCOL_2026-11-18.md); [CI44220144140](https://github.com/Kiddos19882/AutoDraw/actions/runs/44220144140) E3 source-only diagnostics SUCCESS, 15/15 tests PASS, ZIP CRC/21-of-21 SHA PASS. Выявлены не только 179 исходных островков, но и 1368 неподдержанных по chroma пикселей G32 (только12 в исходных однопиксельных регионах). Карта цветов не менялась, visual/native PENDING; **следующий шаг — отдельно prereg source-supported color-assignment B1, а не массовое удаление областей**.

**ENGINE-001 R2-P2-P2-A (2026-11-18):** [source micro-islands / G32 color-support diagnostic](ENGINE001_COLOR_ISLAND_R2_P2_P2_SOURCE_SUPPORT_AUDIT_PROTOCOL_2026-11-18.md). Исходные мелкие сегменты и ложные назначения игровых цветов проверяются отдельно. Добавлена только неразрушающая диагностика без изменения пикселей; source/game quality, native brush и CHALK не подтверждены.

**ENGINE-001 R2-P2-P1 M1 (2026-11-18):** [CI44216262024](https://github.com/Kiddos19882/AutoDraw/actions/runs/44216262024) 26/26 tests PASS, technical CI SUCCESS, quality SOURCE_GATE_FAIL (mean ΔE00 after merges > before). M1 fixed original-source Sobel threshold preserved 1397→1397 edge intersections; medoid numeric tie stable. Next: [R2-P2 existing root-cause + M1 evidence](ENGINE001_COLOR_ISLAND_R2_P2_ROOT_CAUSE_AND_NUMERICAL_REBASE_PROTOCOL_2026-11-18.md) §5-6—source-supported micro-island classification, before new cleanup. P1 history and production untouched.

**ENGINE-001 / R2-P2 (2026-11-18):** [R2-P2 root-cause и протокол M1](ENGINE001_COLOR_ISLAND_R2_P2_ROOT_CAUSE_AND_NUMERICAL_REBASE_PROTOCOL_2026-11-18.md) — R2-P1 M0/N1/N2 завершены, все E3 technical PASS, source quality FAIL. N2 BiRefNet [CI44212777049](https://github.com/Kiddos19882/AutoDraw/actions/runs/44212777049) изменил пять безопасных merge-решений, но ΔE00 ухудшилась; 33/33 синтетических тестов PASS. Подтверждены 3929 G32-white/source-foreground расхождений и численная неоднозначность 78 RGB px; P2-P1 M1 со стабильным medoid и фиксированным исходным градиентом **PLAN_FROZEN / CODE_NOT_RUN**. P1 frozen; production и V44-B410 untouched.

**R2-P1 M0/N1 source-only evidence (2026-11-18):** [frozen R2-P1](ENGINE001_COLOR_ISLAND_R2_P1_FROZEN_PRECOMPUTED_NEURAL_MERGE_PROTOCOL_2026-11-18.md). Mathematical M0 [CI44208734155](https://github.com/Kiddos19882/AutoDraw/actions/runs/44208734155) E3 technical SUCCESS / source quality FAIL (43 merges/1328px, 755→712 original RGB regions, mean ΔE00 3.15476, protected-edge overlap slightly worse). Genuine pretrained DINOv2 S4 archived-feature replay N1 [CI44210879678](https://github.com/Kiddos19882/AutoDraw/actions/runs/44210879678) 24 unit tests PASS / E3 technical SUCCESS, 27 changed merge choices, but quality `SOURCE_GATE_FAIL` (paired mean ΔE00 3.15471→3.15539, frozen M0 render 78px numeric drift). **No accepted game32 conversion/native fill/production**; next R2-P2 prereg only after cause review; frozen P1 thresholds/results unchanged.\n\n**R2-0 E1 завершён (2026-11-18):** [R2-P1 frozen protocol](ENGINE001_COLOR_ISLAND_R2_P1_FROZEN_PRECOMPUTED_NEURAL_MERGE_PROTOCOL_2026-11-18.md) — зарегистрирован до первого R2-result. Подтверждены genuine S4 DINOv2 dense (240×150×384) и S5-P2 BiRefNet alpha (240×150) с SHA/CRC; R2-P1 код, inference и CI ещё NOT_RUN. Следующий шаг — R2-1 математический M0.

**Актуальный приоритет ENGINE-001 / COLOR-ISLAND-R2 (2026-11-18):** [новый гибридный план](ENGINE001_COLOR_ISLAND_R2_NEURAL_ASSISTED_MATH_PLAN_2026-11-18.md), [решение DEC-033](DECISIONS.md). **Нейросеть помогает математике**: M0 исходный RGB + многоуровневые мелкие области/защита деталей; N1 DINOv2 real features только для ранжирования допустимого merge/keep; N2 BiRefNet soft foreground как отдельная абляция. Исходный RGB и математические guards определяют цвет и границы, никакого Recolorization-Pro или автоматического удаления реальных микрообластей. Исторический [план R1](ENGINE001_COLOR_ISLAND_R1_SOURCE_AWARE_REGION_PLAN_2026-11-18.md) сохранён. R1 frozen: [CI44201266143](https://github.com/Kiddos19882/AutoDraw/actions/runs/44201266143) E3 technical PASS, source quality FAIL (1017 abstained, 3929 bg mismatch); R1 native BLOCKED. **R2 E0 PLAN_REGISTERED, R2 code/CI NOT_RUN**. V44-B410 LAST, Stage6, production, master, exact CHALK неизменны.

**ENGINE-001 S5-P4 (2026-11-18):** [S5-P4 foreground-balanced visual protocol](ENGINE001_S5_P4_FOREGROUND_BALANCED_SIX_RECOLOR_PROTOCOL_2026-11-18.md). Новая отдельная source-RGB visual-only гипотеза: настоящая BiRefNet foreground-mask, один source nearwhite фон + пять разнообразных source foreground conditioning colors, неизменённая Recolorization-Pro модель. [Runner](../tests/run_engine001_s5p4_foreground_balanced_recolor.py), [тесты](../tests/test_engine001_s5p4_foreground_balanced_recolor.py), [CI](../../.github/workflows/engine001-s5p4-foreground-balanced-six-recolor.yml). E1 COMMITTED; E2/E3 и визуальный итог **NOT_VERIFIED** до конкретного CI/PNG. P3 и game32 frozen unchanged; V44-B410 LAST, production/master untouched.

# Документация AutoDraw — быстрый вход

**ENGINE-001 S5-P3 / визуальный эксперимент без ограничения game32:** [протокол реальной предобученной перекраски шестью исходными цветами Recolorization-Pro](ENGINE001_S5_P3_NATIVE6_PRETRAINED_RECOLOR_VISUAL_PROTOCOL_2026-11-17.md); только original RGB, результат сравнивается визуально, без дообучения, production и оригинального контура.


**ENGINE-001 S5-P2:** [пререгистрация проверки реальной pretrained BiRefNet General Lite ONNX для foreground-only](ENGINE001_COLOR32_S5P2_PRETRAINED_BIREFNET_ONNX_FOREGROUND_PROTOCOL_2026-11-17.md). Без дообучения, без замены 32-цветной модели и без production-изменений.


**ENGINE-001 S5-P1 pretrained-model experiment:** [исходный RGB → настоящая семантическая карта OneFormer, без фиктивной game32 покраски](ENGINE001_COLOR32_S5P1_PRETRAINED_ONEFORMER_ORIGINAL_SEMANTIC_PROTOCOL_2026-11-17.md). Pinned upstream checkpoint, self-contained source-only CI, original V44-B410 unchanged; model inference/visual quality remain NOT_VERIFIED pending CI.


**Новый следующий эксперимент S5 (2026-11-17):** [пререгистрация обучаемой game32 head](ENGINE001_COLOR32_NEURAL_S5_TRAINABLE_PALETTE_HEAD_PROTOCOL_2026-11-17.md); пока только проверка доступности достоверных label и независимых holdout, `BLOCKED_DATASET_LABEL_VALIDATION`. Реальное обучение не проводилось. S3 [CI44145478173](https://github.com/Kiddos19882/AutoDraw/actions/runs/44145478173) успешен технически (7/7 tests, authenticity), но все четыре source color кандидата **QUALITY FAIL**, V44-B410 immutable.


**CI-AUDIT-001:** `geometry-tests.yml` запускает обязательные fast regression jobs на push; длительные FILL-001 и INT-006 перенесены в reusable `geometry-research.yml` и доступны через **Actions → AutoDraw validation → Run workflow → `run_full_validation=true`** (один ручной запуск включает также benchmark и Windows portable build). При обычном push остальные обязательные тесты и Egret reference остаются. [Зависимости и evidence](WORK_LOG.md); [открытые проверки](TASKS.md). Изменение CI не доказывает новую игровую validation.


**CI trigger hygiene (2026-11-17):** historical neural S1/S2/S3, P4c0/P4c1/P4c2, P4a/P4b and Egret P2/P3 workflows no longer run on shared documentation-index updates alone. Their own code/workflow triggers and manual dispatch are preserved. Only `docs-integrity.yml` should normally run when the shared index itself changes. One-time workflow-change runs and CI queue are not evidence of cost savings. [Work log](WORK_LOG.md).


**Текущая точка ENGINE-001 / NEURAL-S4 (2026-11-17):** [S4 CI44137289780](https://github.com/Kiddos19882/AutoDraw/actions/runs/44137289780), source SHA `439e95c9b7dd226c4b1cbb1a554fb6f1b3475eb8`, job `134230185321` SUCCESS; official DINOv2-small revision `ed25f3a31f01632728cabb09d1542f84ab7b0056`, weights SHA256 `ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1` verified in job log. Artifact `14352502866` (uploaded ZIP digest SHA256 `408f26b7d349bb5ee503bdf8f825c9f1dde9d639abd4bf4c96ee575beb3c860e`); report SHA256 `ac197d22a54ba0b586e708efa39ec384f7827a7f94fbfbec0cfd41fc8c9c1ef9` printed after report-file hash checks. D0→D1 changed 593 pixels, genuine DINOv2 contribution exists, but original-first D1 quality `SOURCE_QUALITY_FAIL`: mean ΔE00 8.586 vs B0 5.531, large white-background drift, only 8 of allowed32 colors used. Next: source/background diagnosis + separately preregistered S5 trained palette-head hypothesis; 410 original V44-B contours LAST immutable, no production or native/game CHALK validation. Older `NOT_VERIFIED` statements below are dated snapshots and superseded by this verified current result. [Active status](PROJECT_STATUS.md) · [tasks](TASKS.md) · [result index](TEST_RESULTS.md).


**Актуальный ENGINE-001 / NEURAL-S4:** [отдельный протокол настоящих DINOv2 признаков и игрового выбора цвета](ENGINE001_COLOR32_NEURAL_S4_DINOV2_CONTEXT_PALETTE_PROTOCOL_2026-11-17.md), [Python-модуль](../tests/run_engine001_color32_neural_s4_dinov2.py), [регрессии](../tests/test_engine001_color32_neural_s4_dinov2.py), [отдельный CI](../../.github/workflows/engine001-color32-neural-s4-dinov2-context.yml). Контроль D0 без нейропризнаков vs D1 с настоящей pretrained DINOv2; V44-B410 original LAST только как immutable опциональный guide. **Действительно нейронный encoder**, но обученная 32-color classification head НЕ существует; game color assignment пока математический. CI/inference ещё не подтверждены, production не меняется.


**Актуальный ENGINE-001 / NEURAL-S3:** [совместный протокол областей, цветов и оригинального контура V44-B](ENGINE001_COLOR32_NEURAL_S3_JOINT_COLOR_CONTOUR_PROTOCOL_2026-11-17.md), [test-only source graph runner](../tests/run_engine001_color32_neural_s3_joint.py), [regression tests](../tests/test_engine001_color32_neural_s3_joint.py), [CI](../../.github/workflows/engine001-color32-neural-s3-joint-contour-source.yml). Варианты J0 без контурной подсказки и J1 с исходным нативным V44-B (строго архивный, 410 последних штрихов не изменять) проверяются как отдельный E2 source-only контурный prior; **обученный нейросетевой выбор цвета пока NOT_RUN**, используются лишь реальные SAM2 предложения областей + математический региональный граф. После E2/визуальной оценки решать дальнейший шаг, production и live CHALK не затрагивать.


**Текущий ENGINE-001 / NEURAL-S2:** [протокол независимой сегментации оригинала](ENGINE001_COLOR32_NEURAL_S2_ORIGINAL_FIRST_FLATTING_PROTOCOL_2026-11-17.md), [исходный runner](../tests/run_engine001_color32_neural_s2.py), [тесты](../tests/test_engine001_color32_neural_s2.py), [CI](../../.github/workflows/engine001-color32-neural-s2-original-first.yml). В отличие от S1 новые C1/C2-кандидаты создаются только из RGB оригинала, без G32 как seed; S1 genuine SAM2 mask 2шт берутся из SHA-linked архива. SLIC — не нейросеть. В локальном source-only пилоте 1284→368 цветовых островков, но ΔE ухудшилась с5.53 до8.58 и фон drift 10.9%; поэтому **кандидат отклонён по prereg source quality**. Новый CI ещё не подтверждён, Egret E3/E4/E5 и CHALK NOT_RUN.


**ENGINE-001 / COLOR32-NEURAL-S1 (2026-11-17):** [пререгистрированный отдельный neural experiment](ENGINE001_COLOR32_NEURAL_S1_REGION_SEGMENTATION_PROTOCOL_2026-11-17.md), [source-only mask adapter](../tests/run_engine001_color32_neural_s1.py), [real SAM2.1 Tiny mask exporter](../tests/run_engine001_color32_neural_s1_sam2.py) и [Linux workflow](../../.github/workflows/engine001-color32-neural-s1-sam2-source.yml). Сравнение замороженной G32 (B0) с настоящими нейросетевыми масками SAM2.1 (N1) и теми же масками плюс защищённые исходные границы (N2). Только 32 игровых цвета. Фиксированные предварительные source-гейты и отдельный визуальный review; **neural CI/model evidence пока NOT_VERIFIED**. Оригинальный P4c2 [CI44119887018](https://github.com/Kiddos19882/AutoDraw/actions/runs/44119887018) genuine Egret paint-only E3, job success но `P4C2_NATIVE_PAINT_FAIL`, 14/17 цветов ниже native99%, полные 410 V44-B contours LAST отсутствуют. Production/CHALK не затронуты.


**P4c2 Windows pre-native recovery (2026-11-17):** [CI44113999297](https://github.com/Kiddos19882/AutoDraw/actions/runs/44113999297) `BLOCKED_P4C1_ORIGINAL_G_DRIFT` after docs/tests PASS; no Egret PNG. Native P4c2 now reads and verifies original frozen P4c1 ZIP+G32+1133 paths instead of regenerating G on Windows. Separate cross-platform G diagnostic added; **new CI and actual Egret E3 not yet verified**. Original410 V44-B LAST, E4/E5/CHALK remain NOT_RUN.

**2026-11-17 / ENGINE-001 P4c1 verified E2 and P4c2 E1:** [P4c1 CI44098998634](https://github.com/Kiddos19882/AutoDraw/actions/runs/44098998634) SHA `02303521af46bc0f5d60241592b861f73d03a253` complete SUCCESS (5 P4c1 and 3 P4c0 unit tests); artifact14334728680 original ZIP SHA256 `fac1fcf1ff6a43ac6e59da116b68b86e2238c2da13be0b167cf34f8241ac5eeb`, CRC and 5/5 linked hashes PASS, report SHA `1badb1913369cbad690c1cfbdf04778a4e6fde126042d633f8548fc77d606873`. Status `SOURCE_INCREMENTAL_PASS_NATIVE_PENDING`; 12/17 G32 owners source-model≥99%, five remaining 4/5/16/23/28, 327 combined residual pixels (301 belong to28), 1014 additions incl628 width2 micro, 1543 strokes/5277 synthetic vertices incl410 original V44-B details reserved LAST. **E2 source-only not native image quality.** [P4c2 independent prereg](ENGINE001_COLOR32_P4C2_FULL_NATIVE_17_OWNER_PROTOCOL_2026-11-17.md) plus test-only runner, unit tests and [Windows workflow](../../.github/workflows/engine001-color32-p4c2-full-native.yml) committed, E1 static; P4c2 CI/E3 UNKNOWN, and this first stage renders genuine all-owner **PAINT ONLY** (original 410 details NOT rendered), no E4/E5 or exact CHALK.


**Историческая точка до завершения P4c1 (2026-11-17):** P4c0 [E2 source CI44096977608](https://github.com/Kiddos19882/AutoDraw/actions/runs/44096977608) завершён (выполнение PASS, модельное покрытие всех 17 цветов ниже99% — QUALITY FAIL). P4c1 prereg/source runner/tests/workflow записаны в GitHub, **P4c1 CI и артефакты подтверждены последующим CI44098998634 (E2 source-only)**; полный native Egret, E4/E5 и игровой CHALK NOT_RUN. [Текущий статус](PROJECT_STATUS.md) · [активные задачи](TASKS.md) · [порядок работ](ROADMAP.md). В более ранних абзацах ниже сохранены исторические формулировки PENDING, не действующие статусы.

**ENGINE-001 / P4c0→P4c1 все 17 цветов G32 (2026-11-17):** [P4c0 CI44096977608](https://github.com/Kiddos19882/AutoDraw/actions/runs/44096977608) E2 source-only PASS, но качество исходной геометрической модели `MODEL_LOW_OWNER_COVERAGE`:119 кольцевых штрихов/1457 вершин, все17 исходных цветов ниже99% модели, лимит ресурсов не исчерпан. [Пререгистрация P4c1](ENGINE001_COLOR32_P4C1_DIRECTIONAL_MICRO_RESIDUAL_PROTOCOL_2026-11-17.md), [источник](../tests/run_engine001_color32_p4c1_directional_micro.py), [тесты](../tests/test_engine001_color32_p4c1_directional_micro.py): поверх неизменного исходного P4c0 короткие горизонтальные, вертикальные, диагональные и адаптивно ориентированные штрихи, включая микроштрихи width2 для одиночных ячеек. **Пока source-only; actual Egret E3, full visual, E4/E5/CHALK NOT_RUN**. 410 оригинальных контуров V44-B LAST резервируются и не меняются.

**ENGINE-001 / P4c0 ресурсная осуществимость всех цветов G32 (2026-11-17):** [независимая пререгистрация P4c0](ENGINE001_COLOR32_P4C0_ALL_OWNER_RESOURCE_PROTOCOL_2026-11-17.md), [source runner](../tests/run_engine001_color32_p4c0_all_owner_feasibility.py), [регрессии](../tests/test_engine001_color32_p4c0_all_owner_feasibility.py). Первая ограниченная выборка колец существующего B3 для всех 17 ненулевых цветов G32; резерв410 исходных контуров V44-B LAST/1792 вершин, максимум2590 штрихов/4108 вершин для краски. При нехватке ресурса записать BLOCKED_RESOURCE, никогда не считать незакрашенные зоны успехом. **P4c0 source E2 подтверждён CI44096977608, model QUALITY FAIL; native E3 NOT_RUN**, модель OpenCV не подтверждает след кисти Egret, E4/E5/CHALK NOT_RUN.

**ENGINE-001 / P4a E2 complete, P4b hybrid visual control (2026-11-17):** [P4a CI44015038442](https://github.com/Kiddos19882/AutoDraw/actions/runs/44015038442) source-gate PASS, но лишь67/36000 пикселей изменены, G/H визуально почти одинаковы. [Новый пререгистрированный протокол P4b](ENGINE001_COLOR32_S2B_P4B_V44B_HYBRID_PREVIEW_PROTOCOL_2026-11-17.md) повторно использует **оригинальный Egret V44-B color-100 PNG** из user-preferred [native CI43813812976](https://github.com/Kiddos19882/AutoDraw/actions/runs/43813812976), где только410 последних цветных контуров, поверх source-only bitmap G/H. **HYBRID, не настоящий Egret fill и не game CHALK**. [Runner](../tests/run_engine001_color32_s2b_p4b_v44b_hybrid.py), [tests](../tests/test_engine001_color32_s2b_p4b_v44b_hybrid.py); [P4b CI44016120503](https://github.com/Kiddos19882/AutoDraw/actions/runs/44016120503) **E2 HYBRID INTEGRITY PASS** (8/8 исходных PNG SHA, оригинальные 410 native Egret контуров LAST); оригинал G32 RGB MAE14,099→с контурами13,257, H14,108→13,265. Это не native Egret paint, game E4/E5/CHALK NOT_RUN.

**ENGINE-001 / P4a component-aware G32 island audit (SOURCE-ONLY, 2026-11-17):** [отдельный prereg-протокол P4a](ENGINE001_COLOR32_S2B_P4A_COMPONENT_ISLAND_PROTOCOL_2026-11-17.md) создан до runner/tests. Сравнивает неизменный CI S2b G с H: только целые незащищённые 4-связные островки до24 пикселей, соседний nonwhite из32 игровых цветов, ΔE00 прибавка<=2, не изменяя защищённые границы. [Source runner](../tests/run_engine001_color32_s2b_p4a_component_islands.py), [tests](../tests/test_engine001_color32_s2b_p4a_component_islands.py). **E1 implementation, E2/visual/E3 не подтверждены до CI и PNG.** Ещё не разрешает обновление P3b и production.

**ENGINE-001 / актуальная проверенная цепочка P2→P3→P3b (2026-11-17):** P2 [E3 CI44008672803](https://github.com/Kiddos19882/AutoDraw/actions/runs/44008672803) α24 dark31/skin29=90.95/68.18%, safe3px; P3 [E3 CI44012588733](https://github.com/Kiddos19882/AutoDraw/actions/runs/44012588733) improved to95.65/80.46%, but **FAIL**: 141/120 native pixels beyond3 logical px; P3b [E3 CI44013208184](https://github.com/Kiddos19882/AutoDraw/actions/runs/44013208184) reused exact frozen56 paths with **only** width6→4, **isolated numeric PASS** (94.96/78.24%, 0 beyond3px at α24/128), but **NOT accepted as finished recognizable picture**: scattered dark/pink specks, neither owner≥99%, no full game32 or original410 V44-B contours rendered LAST. [Full evidence](TEST_RESULTS.md), [next unfinished P4 direction](TASKS.md), [P3b prereg](ENGINE001_COLOR32_S2B_EGRET_P3B_SAFE_WIDTH_PROTOCOL_2026-11-17.md). E4/E5/live CHALK NOT_RUN.

**ENGINE-001 / P3 отрицательный native результат и отдельная P3b:** [P3 CI44012588733](https://github.com/Kiddos19882/AutoDraw/actions/runs/44012588733) SHA `7112270e` E3 valid native PNG, **incremental QUALITY FAIL**: α24 dark31 95.65% (P2 90.95%), pink29 80.46% (P2 68.18%), но 141/120 пикселей >3 logical px; все56 добавленных отрезков использовали width6, source OpenCV недооценил реальный след. [Отдельная пререгистрация P3b с единственным изменением ширины6→4 на неизменных56 маршрутах](ENGINE001_COLOR32_S2B_EGRET_P3B_SAFE_WIDTH_PROTOCOL_2026-11-17.md); P3b E2/E3 пока PENDING. Архивы P1/P2/P3, V44-B410, CHALK/production неизменны.

**Источники подтверждённых S2b/P1:** [source-only RGB S2b protocol](ENGINE001_COLOR32_S2B_RGB_EDGE_PROTOCOL_2026-11-17.md) — E2 PASS на [CI44003045004](https://github.com/Kiddos19882/AutoDraw/actions/runs/44003045004); [isolate actual Egret P1 protocol](ENGINE001_COLOR32_S2B_EGRET_P1_PROTOCOL_2026-11-17.md) — E3 PASS на [CI44007375262](https://github.com/Kiddos19882/AutoDraw/actions/runs/44007375262). Это текущие доказательства, не новое исследование; source-only S2b не равен нативной покраске.

**ENGINE-001 / P3 адаптивная заливка по локальному свободному месту (2026-11-17):** [протокол P3](ENGINE001_COLOR32_S2B_EGRET_P3_DIRECTIONAL_PROTOCOL_2026-11-17.md) зарегистрирован до реализации. Продолжение P2 E3: сохраняет исходные 55 штрихов двух зон G31/G29 и предлагает дополнительные 2-точечные маршруты шириной 30/15/10/6/4/2 под углами 0,15,…,165° (обратные направления эквивалентны для прямых); проверка source-only distance transform и прироста незакрашенных пикселей на вершину, затем A/B в настоящем Egret. **P3 E1 implementation only; E2/E3 pending**, не подменять модельный прогноз реальным покрытием/CHALK.

**Текущий ENGINE-001 / Color32, 2026-11-17:** [S2b source E2](https://github.com/Kiddos19882/AutoDraw/actions/runs/44003045004) PASS (визуальная приёмка ожидается); [P1 Egret E3](https://github.com/Kiddos19882/AutoDraw/actions/runs/44007375262) PASS на изолированной круглой кисти; [P2 Egret E3](https://github.com/Kiddos19882/AutoDraw/actions/runs/44008672803) PASS на двух исходных игровых цветах (31 тёмный 90,95% и 29 розовый 68,18% нативного покрытия при α24, чужих пикселей дальше 3 логических px нет), **но полный quality gate ≥99% НЕ ПРОЙДЕН**. [Протокол P2](ENGINE001_COLOR32_S2B_EGRET_P2_MULTIRING_PROTOCOL_2026-11-17.md), [первичные измерения](TEST_RESULTS.md), [задачи](TASKS.md). Сохранены 410 неизменных контуров V44-B LAST; остальные G-цвета, полное изображение, game E4/E5 и exact CHALK пока NOT_RUN.

**COLOR32-S2 local E1 (2026-11-17):** [Зафиксирован отрицательный source gate](TEST_RESULTS.md): G сохраняет больше исторических RGB-границ, но S2 индексная метрика отличается от S1 и её неизменный gate FAIL; подробности в [протоколе](ENGINE001_COLOR32_S2_EDGE_PROTECTED_PROTOCOL_2026-11-17.md). GitHub E2 пока UNKNOWN, native Egret NOT_RUN.

**COLOR32-S2 (2026-11-17, source-only E1, E2 UNKNOWN):** [Новый протокол edge-protected merging](ENGINE001_COLOR32_S2_EDGE_PROTECTED_PROTOCOL_2026-11-17.md) и отдельный CI [workflow](../../.github/workflows/engine001-color32-s2-edge-protection.yml). Сравнение неизменных B/E против G, защищающего сильные границы исходного изображения; новые тесты и отчёты CI пока **не подтверждены**, native Egret/game/CHALK NOT_RUN.

**COLOR32-S1 (2026-11-17, source-only):** [Протокол A/B/C/D — 32 реальных игровых цвета, CIEDE2000, SLIC и пространственное объединение](ENGINE001_COLOR32_SPATIAL_SEGMENTATION_PROTOCOL_2026-11-17.md). Исходный E2 [CI43997569635](https://github.com/Kiddos19882/AutoDraw/actions/runs/43997569635) PASS, но coarse SLIC C/D теряют детали; дополнительный E2 [PAL32 V1 CI43997979526](https://github.com/Kiddos19882/AutoDraw/actions/runs/43997979526) PASS для E=мягкого объединения и F=fine SLIC. Вариант E сокращает компоненты на55.93%, но важные границы требуют дальнейшей проверки; контуры V44-B неизменны.

**ТЕКУЩАЯ НАВИГАЦИЯ (17.11.2026):** [PAL32-REGION-V1 — отдельный протокол дополнительных сравнений](ENGINE001_PAL32_REGION_V1_PROTOCOL_2026-11-17.md) · [COLOR32-S1 — 32 реальные игровых цвета, CIEDE2000, SLIC, объединение регионов](ENGINE001_COLOR32_SPATIAL_SEGMENTATION_PROTOCOL_2026-11-17.md) · [статус](PROJECT_STATUS.md) · [открытые задачи](TASKS.md) · [замороженный первый B0](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md) · [замороженный B1](ENGINE001_V43P4_B1_OWNER_CONSTRAINED_PROTOCOL_2026-11-17.md) · [изолированная native-проверка B2](ENGINE001_V43P4_B2_NATIVE_SINGLETON_PROBE_PROTOCOL_2026-11-17.md) · [пререгистрация полного B2](ENGINE001_V43P4_B2_FULL_BOUNDARY_REPAIR_PROTOCOL_2026-11-17.md) · [B3 — контурно-параллельная заливка, собственный цвет можно перекрывать повторно](ENGINE001_V43P4_B3_CONTOUR_PARALLEL_PROTOCOL_2026-11-17.md) · [B3a — кольца + внутренние направленные штрихи + короткий ремонт](ENGINE001_V43P4_B3A_CONTOUR_MEDIAL_REPAIR_PROTOCOL_2026-11-17.md) · [B3b — непрерывные линии по скелету собственного цвета](ENGINE001_V43P4_B3B_OWNER_SKELETON_PROTOCOL_2026-11-17.md) · [инвентаризация](DOCUMENTATION_INVENTORY_2026-11-16.md). **P4.1/P4.2 E2/E3 capture PASS**, но **B0 QUALITY FAIL** [CI43983619222](https://github.com/Kiddos19882/AutoDraw/actions/runs/43983619222) (больше лишних цветов и RGB MAE19.93 vs A11.13); **B1 E2/E3 capture PASS, QUALITY FAIL** [CI43986256204](https://github.com/Kiddos19882/AutoDraw/actions/runs/43986256204) (105 paint, потеря покрытия до3.58/20.61/6.15/81.01% на α24). Эталон V44-B и неизменные410 цветных контуров LAST сохранены. **B2 isolated genuine Egret E3 PASS** [CI43987609480](https://github.com/Kiddos19882/AutoDraw/actions/runs/43987609480): 12/12 однопиксельных целей покрыты при α24/128 для кистей2/4; кисть2 даёт 237 чужих native-пикселей против 955 для кисти4, пересечения >3px отсутствуют. Это только изолированные пробы; полный B2 пока NOT_RUN; E4/E5/run-bound CHALK не запускались. Следующие исторические разделы — справка, не active backlog. **Обновление:** B3 contour source E2 [CI43991126674](https://github.com/Kiddos19882/AutoDraw/actions/runs/43991126674) PASS/низкое модельное покрытие, B3 isolated Egret E3 [CI43991432235](https://github.com/Kiddos19882/AutoDraw/actions/runs/43991432235) PASS только14 тестовых кольцевых маршрутов, B3a [CI43992170465](https://github.com/Kiddos19882/AutoDraw/actions/runs/43992170465) E2 workflow PASS, но planner **BLOCKED_RESOURCE** при5899/5900 vertices и следующем кандидате +2; полная native A/B3a НЕ запускалась.


**Рабочая ветка:** `feature/image-geometry-optimization`. **Актуальный evidence baseline ENGINE-001:** `177165361b0340515fe3bb74f4847ab3ec579ebc` (9/9 live E4, E5 PARTIAL; см. §21). Исторический baseline прежней системы документации — `a2d1f0a52d47`. Текущий remote HEAD проверять заново в каждом чате. Это вход в существующую систему документации, а не отдельный источник статуса. Полная предыдущая редакция индекса сохранена [здесь](README_HISTORY_THROUGH_2026-11-08.md).

**ENGINE-001 V43-P4.1 (2026-11-17, experimental source-only):** [детерминированный multi-angle planner](../tests/run_engine001_full_adaptive_fill_v43p4.py), [regression tests](../tests/test_engine001_full_adaptive_fill_v43p4.py), [isolated CI](../../.github/workflows/engine001-v43p4-full-adaptive-source.yml). Код вырабатывает B0 *MODEL_ONLY* кандидата без старых paint strokes, `safe_to_execute=False`; модельный OpenCV результат не является нативным покрытием, baseline A/full B0 Egret/E4/CHALK отсутствуют. [Evidence и границы](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md#p41-implementation-checkpoint--2026-11-17-e1local-partial-e2-ci-unknown).

**Обязательное правило игровых кистей:** [GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md](GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md) — использовать реальный след BoardPane/Egret во всех brush-dependent тестах; модели не заменяют native quality.

**ENGINE-001 V44-P1 (2026-11-16; завершённое исследование):** [исходная пререгистрация и результаты](ENGINE001_ADAPTIVE_COLOR_OUTLINE_V44_PROTOCOL_2026-11-16.md), [настоящий Windows BoardPane/Egret CI43813812976](https://github.com/Kiddos19882/AutoDraw/actions/runs/43813812976) E3 SUCCESS. Все 410 исходных контуров сохранены геометрически; вариант **V44-B выбран пользователем как визуальный эталон** для `wV6VeZI9S1Y`, source RGB MAE 11.13399074 (warm 16.42272007). Это подтверждает native-рендер и выбор эталона, **не** per-class ≥99%, E4 game CHALK, E5 и не production acceptance. Для нового V43-P4 сохранять точно все 410 цветных V44-B контуров последними.

**V43-P3a:** [исследование ориентированной width4/6 заливки с V44-B контуром](ENGINE001_V43P3_ORIENTED_REPLACEMENT_PROTOCOL_2026-11-16.md), первая стадия SOURCE_ONLY без заявлений о native-качестве.

**V43-P3a2:** [ширины 4/6/10/20/30 — отдельная модельная проверка](ENGINE001_V43P3A2_BROAD_BRUSH_AUDIT_PROTOCOL_2026-11-16.md), без native/игровых выводов.

**V43-P3a3:** [настоящий Egret width4/6/10/20/30 для ориентированных мазков](ENGINE001_V43P3A3_NATIVE_ORIENTED_FOOTPRINT_PROTOCOL_2026-11-16.md) — изолированная проверка отпечатков, full fill/CHALK NOT_RUN.

**V43-P3b-P1 завершённый native опыт:** [протокол и отрицательные результаты поштучной замены](ENGINE001_V43P3B_P1_ROW_INTERSECTION_PROTOCOL_2026-11-16.md), [CI43882838806](https://github.com/Kiddos19882/AutoDraw/actions/runs/43882838806) E3 Egret capture SUCCESS, 0/36 целых линий заменены. Отдельная стратегия P4 полной заливки выше — текущая.

**V43-P3a3 actual native:** [CI43864508620](https://github.com/Kiddos19882/AutoDraw/actions/runs/43864508620) width4/6/10 real Egret isolated alpha result, width20/30 NO_ELIGIBLE. [P3b path replacement protocol](ENGINE001_V43P3B_NATIVE_REPLACEMENT_PROTOCOL_2026-11-16.md) (исторический P0/P1, завершён отрицательно); V44-B full colored contours must remain last.

## Начните с этих документов

| Вопрос | Куда идти |
|---|---|
| Что подтверждено и что заблокировано? | **[PROJECT_STATUS.md](PROJECT_STATUS.md)** |
| Что ещё нужно сделать? | **[TASKS.md](TASKS.md)** |
| В каком порядке? | **[ROADMAP.md](ROADMAP.md)** |
| Почему принято решение? | [DECISIONS.md](DECISIONS.md) |
| Где фактический CHALK и проверки? | **[TEST_RESULTS.md](TEST_RESULTS.md)** |
| Как ИИ должен работать с проектом? | [AI_WORK_GUIDE.md](AI_WORK_GUIDE.md) |
| Архитектура, входы и API? | [ARCHITECTURE.md](ARCHITECTURE.md), [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md), [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md), [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) |
| Найти готовый код для повторного использования? | **[Карта возможностей AutoDraw](COMPONENT_CATALOG.md)** → [API preparation](PREPARATION_API_REFERENCE.md), [executor](EXECUTOR_API_REFERENCE.md) → [тесты и CI](TESTS_AND_CI_MAP.md) |
| Как проверяются факты и эксперименты? | [EVIDENCE_AND_VALIDATION.md](EVIDENCE_AND_VALIDATION.md), [EXPERIMENT_STANDARD.md](EXPERIMENT_STANDARD.md) |
| История и прежние версии? | [WORK_LOG.md](WORK_LOG.md), [CHANGELOG.md](CHANGELOG.md), snapshot файлы `*_HISTORY_THROUGH_2026-11-08.md` |

**Поиск в терминале / агенте:** `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20 --find "очистить доску"` — read-only кандидаты с owner/entrypoint (E1, не runtime). Если нет совпадений, искать вручную в [каталоге](COMPONENT_CATALOG.md) и исходниках.

**Большие GitHub-файлы:** [проверенный GitHub fetch_blob по SHA](AI_WORK_GUIDE.md#чтение-больших-файлов-github--проверенный-git-blob-способ-2026-11-13). Все 6 Monitor JSON FILL001 (12–51 млн символов) прочитаны и разобраны через GitHub connector; прямой RAW/curl в текущей среде BLOCKED.

**Минимальный старт ИИ:** проверить текущий remote HEAD и последние commits; прочитать `PROJECT_STATUS` → `TASKS` → `ROADMAP`, затем профильный DECISION/инварианты/первичный эксперимент и актуальный код для конкретной задачи. Не перечитывать все 90+ файлов без причины.

**Актуальное FILL001/Egret исследование (2026-11-13):** [6 оригинальных игровых фигур ↔ native Egret Stage WebGL, IoU 0.991656–0.999448, причины ограничений](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#23-fill001-series-001--native-egret-replay-шести-игровых-фигур-2026-11-13) · [CI 43431139220](https://github.com/Kiddos19882/AutoDraw/actions/runs/43431139220) PASS для offline renderer и 19 Node tests, 6 оригинальных игровых PNG; две из шести реконструкций только диагностические из-за pointDelta=2. Исторические FILL quality FAIL и QUOTA_LIMITED неизменны. Сначала читать актуальные PROJECT_STATUS/TASKS/TEST_RESULTS, затем §23.

**ENGINE-001 V34 (preregistered, NOT_RUN):** [native warm-color fidelity on frozen V33 real Egret strokes](ENGINE001_NATIVE_WARM_COLOR_V34_PROTOCOL_2026-11-15.md) — сравнить исходные цвета V33 с deterministic source-RGB medians при идентичной геометрии 1945 strokes; native E3 обязателен, E4/CHALK отсутствуют.

**ENGINE-001 V43-P2b — тонкие края и широкая середина штриха:** [отдельно замороженный native Egret опыт](ENGINE001_V43P2B_NATIVE_SPLIT_INTERIOR_PROTOCOL_2026-11-16.md) после отрицательного P2a; ширина2 на границах исходного тёмного цвета, ширина4/6 внутри крупных компонент. Полный слой из410 контуров V35-B неизменен и рисуется последним; внутренний/внешний допуск3px и RGB-гейты сохраняются. P2b не заявляет экономии игровых точек, поскольку сегментов становится больше.

**ENGINE-001 V43-P2a — нативная проверка широких кистей внутри тёмной области:** [отдельная пререгистрация](ENGINE001_V43P2A_NATIVE_WIDE_INTERIOR_PROTOCOL_2026-11-16.md) и Windows Egret A/B/C ширина2/4/6 только на исходных глубоких участках класса7; весь исходный план и все410 пользовательских V35-B контуров остаются, внутренний допуск3px и RGB-гейты не смягчаются. Это feasibility-проверка, не полноценная гибридная заливка.

**ENGINE-001 V43 — адаптивная заливка по форме области (исследование):** [отдельная предрегистрация](ENGINE001_SHAPE_ADAPTIVE_FILL_V43_PROTOCOL_2026-11-16.md), сочетание локально ориентированных проходов, медиальной оси и многоразмерной настоящей Egret-кисти. Этап P1 анализирует компоненты исходных цветовых масок с переиспользованием `skeletonization.py` — **MODEL_ONLY, не native-кандидат и не готовый план**. P2 требует отдельной проверки настоящим BoardPane/Egret при сохранении всей обводки V35-B и внутреннего допуска 3 px.

**ENGINE-001 V41 — избирательное удлинение концов заливки по настоящему Egret alpha:** [пререгистрация](ENGINE001_V41_SELECTIVE_NATIVE_ENDPOINT_PROTOCOL_2026-11-16.md), выбор только недокрашенных исходных цветовых точек за краем кисти и нативное A/B/C; все 410 предпочитаемых тёмных контуров сохранены, внутренний допуск 3 логических px и критерии RGB не смягчаются.

**ENGINE-001 V40-P2 — изменение концов существующих строк заливки:** [пререгистрация и отдельный нативный Egret A/B/C](ENGINE001_V40P2_ENDPOINT_EXTENSION_PROTOCOL_2026-11-16.md). Сохранены все 410 тёмных контуров V35-B поверх 1945 исходных штрихов заливки; тестируются x-удлинения концов0/0,25/0,5 логических пикселя при допустимом внутреннем цветовом заходе≤3px и неизменном синтетическом бюджете. Критерии native quality/CHALK не объявлять PASS до отчёта.

**ENGINE-001 V40 — допуск 3 логических px на внутренних границах цветов:** [отдельный протокол V40](ENGINE001_V40_INTERNAL_COLOR_TOLERANCE_AUDIT_PROTOCOL_2026-11-16.md). Нативные Egret color-layer PNG измеряются отдельно по собственному классу, допустимому заходу на соседний цвет ≤3px и превышению >3px; внешняя граница и итоговый composite с 410 контурами — отдельные метрики. CI выполняет аудит, не новый планировщик.

**ENGINE-001 V39 — щадящая коррекция границ без новых штрихов:** [предрегистрация нативного Egret A/B/C со сдвигом существующей заливки на 0/0,25/0,5 логического пикселя](ENGINE001_BOUNDARY_SHIFT_V39_PROTOCOL_2026-11-16.md); все 410 тёмных контуров V35-B и число точек неизменны, качество до CI UNKNOWN.

**ENGINE-001 V38 — аудит нативных пропусков заливки:** [пререгистрация измерений границ цветовых областей](ENGINE001_V38_NATIVE_COLOR_BOUNDARY_AUDIT_PROTOCOL_2026-11-16.md) на замороженных PNG V37-P2; не создаёт новых рисунков и не подменяет реальную кисть CV2. Два порога alpha24/128, классы4–7, границы/внутренние пробелы, реальные ресурсы отдельно.

**ENGINE-001 V37-P2 — цвета заливки при неизменной тёмной обводке V35-B:** [отдельная предрегистрация](ENGINE001_LOCAL_FILL_COLOR_V37_P2_PROTOCOL_2026-11-15.md) и opt-in native Egret A/B/C. Только RGB 1945 существующих штрихов заливки; все 410 контуров остаются тёмными и последними. Никакой новый расход точек не обещается без E4 CHALK.

**ENGINE-001 V37-P1 — сохранение всех 410 контуров V35-B:** [предрегистрация цветовой A/B/C проверки полной обводки](ENGINE001_FULL_OUTLINE_V37_P1_PROTOCOL_2026-11-15.md). Пользовательский визуальный эталон V35-B не заменять V35-C/V36 с 297 линиями; текущий эксперимент меняет только RGB линий, не рисунок/ресурс.

**ENGINE-001 V36 source-colored contours:** [предрегистрация native Egret: исходный V35-C → RGB оригинала на штрихах → смешанный оттенок](ENGINE001_SOURCE_COLOR_CONTOUR_V36_PROTOCOL_2026-11-15.md). Изменяются только цвета линий после заливки, геометрия/alpha остаются контрольными; ожидаемый native E3 нельзя считать PASS до CI.

**ENGINE-001 V35 (experimental paint → detail):** [предрегистрация отдельной покраски с последующими контурами поверх](ENGINE001_PAINT_THEN_DETAIL_V35_PROTOCOL_2026-11-15.md). Первый шаг: тестируемый слойный план/ресурсный валидатор, без claims native quality; исходный V34R E3 PASS, детали ещё NOT_RUN.

**ENGINE-001 V34R native replay verification (preregistered):** [отдельный протокол V34R после FAIL исходного V34](ENGINE001_NATIVE_WARM_COLOR_V34R_REPLAY_PROTOCOL_2026-11-15.md) — пиксельно точное RGBA/IDAT совпадение, служебные PNG метаданные не считаются изменением игровой кисти; до успешного CI не объявлять quality PASS.

**Текущий V6 structural exploration:** [предрегистрация source-vs-V5 edge retention после визуального FAIL](ENGINE001_COMPLEX_STRUCTURE_V6_PROTOCOL_2026-11-14.md). Это диагностический анализ до stroke planner, а не новый renderer/recognition PASS.

## Основные исследовательские контуры

- **Ресурс CHALK:** [G1/G2/G3, INT-006 и INT006R — общий реестр](TEST_RESULTS.md) → [официальный INT-006](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md) → [frozen model/analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md). Только exact `CHALK = post.pointCount - pre.pointCount` — реальное измерение.
- **Заливка и качество:** [FILL-001-RS capture/replay](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) → [временный план эксперимента](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md); baseline: CHALK 1260 измерен, **PNG quality FAILED** (98.430600%, leakage 11). Новая чистая исследовательская пара ON/OFF: [FILL001_SMOOTH_AB_V1](GAME_MONITOR_BRIDGE_REFERENCE.md#12-fill-001--чистый-парный-smooth-ab-v1); новые live результаты ещё не получены.
- **ENGINE-001, актуальная лаборатория:** [§20–22 — live E4 и независимый native Stage E5 screen-RGB](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) → [исходный commit 1771653](https://github.com/Kiddos19882/AutoDraw/commit/177165361b0340515fe3bb74f4847ab3ec579ebc) → [E4 full CI 42449898657](https://github.com/Kiddos19882/AutoDraw/actions/runs/42449898657) → [E5 CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181). Exact CHALK 846 по 9 runs; native Stage screen-RGB 9/9 PASS_PER_RUN при DEC-025; прямой live alpha и temporal renderer order НЕ проверены, общий ENGINE-001 PARTIAL.
- **Геометрия/рендерер, исторический анализ:** [архитектура игровой доски и движка](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) → [game engine cost и renderer](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) → [PRR CI 6/6 PASS](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715).
- **Корпус 81 изображения:** [offline screening и N](TEST_RESULTS.md#3-кандидатный-корпус-81-реального-изображения-offline-only) → [генератор и ограничения](VALIDATION_CORPUS_GENERATOR_2026-11-07.md). Это кандидатные Stage8 mono / Stage6 color scanlines, а **не** валидированная D1–D5 CHALK-популяция.
- **Цель CHALK 95%:** [проект safety margin](CHALK_SAFETY_MARGIN_POLICY_DESIGN_2026-11-07.md) → [предложенный протокол 19/59](CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md); ещё **не** production gate PASS.
- **Game Monitor / Bridge:** [текущие API](GAME_MONITOR_BRIDGE_REFERENCE.md) и [README Game Monitor](../source/game_monitor/README.md).

## Файлы игрового движка

- [Архитектура и цикл рисования BoardPane](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) — актуальная систематизация источников и открытых вопросов ENGINE-001.

- [Текущий комплект клиентских bundle и manifest](../gameEngine/) — сохранённые файлы Egret/BoardPane. Копия в репозитории не доказывает соответствие именно текущей живой игре.
- [Аудит движка, принятых точек и renderer](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) — сопоставление версий, доказательства и границы выводов.
- [Game Monitor / Bridge API](GAME_MONITOR_BRIDGE_REFERENCE.md) — фактические интерфейсы наблюдателя.

## Автоматический контроль документации

- [Markdown integrity CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709): **SUCCESS**, 99/99 .md в индексе; 0 найденных broken internal links; 0 дублирующихся DEC ID; 9/9 неизменённых historical snapshots.
- [Скрипт аудита](../tools/check_markdown_docs.py), [его пять тестов](../tools/tests/test_check_markdown_docs.py), [workflow](../../.github/workflows/docs-integrity.yml), [manifest исторических SHA](HISTORY_SNAPSHOT_PROVENANCE.json).
- Ручная read-only проверка: `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20 --report docs-integrity.json`.
- Проверяется стандартный Markdown link/heading syntax и SHA истории. Внешние URL, статус GitHub run, поведение приложения и смысловое содержание старых отчётов этим инструментом не подтверждаются.

## Правила интерпретации

1. `PROJECT_STATUS.md` — текущее состояние; старые файлы/планы и snapshots — хронология с локальной датой на каждом утверждении.
2. Код и валидаторы определяют реализацию; конкретный CI — результат конкретного commit; runtime evidence — только реальное поведение; Game Monitor `pointCount` — точный CHALK.
3. Удалённый GitHub **не показывает локальный `git status` и текущую игру пользователя**. Новые live-запуски требуют отдельного разрешения.
4. Старые отчёты, failed captures и временные планы не уничтожены при переорганизации. Для технических решений читать [инварианты](ENGINEERING_INVARIANTS.md) и [DECISIONS](DECISIONS.md).

## Полный каталог всех Markdown-файлов репозитория

Ниже файлы из Git tree рабочего коммита при составлении индекса; каталоги и исторические версии включены. Для быстрых ответов сначала используйте таблицу выше. **Название файла не является доказательством актуальности его содержимого.**

### Основное управление, регламенты и история (23)

- [`AI_WORK_GUIDE.md`](AI_WORK_GUIDE.md)
- [`AI_WORK_GUIDE_HISTORY_THROUGH_2026-11-08.md`](AI_WORK_GUIDE_HISTORY_THROUGH_2026-11-08.md)
- [`CHANGELOG_HISTORY_THROUGH_2026-11-08.md`](CHANGELOG_HISTORY_THROUGH_2026-11-08.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`DECISIONS_HISTORY_THROUGH_2026-11-08.md`](DECISIONS_HISTORY_THROUGH_2026-11-08.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`ENGINEERING_INVARIANTS.md`](ENGINEERING_INVARIANTS.md)
- [`EVIDENCE_AND_VALIDATION.md`](EVIDENCE_AND_VALIDATION.md)
- [`EXPERIMENT_STANDARD.md`](EXPERIMENT_STANDARD.md)
- [`KNOWLEDGE_ARCHITECTURE.md`](KNOWLEDGE_ARCHITECTURE.md)
- [`PROJECT_STATUS_HISTORY_2026-11-02.md`](PROJECT_STATUS_HISTORY_2026-11-02.md)
- [`PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md`](PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md)
- [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- [`README_HISTORY_THROUGH_2026-11-08.md`](README_HISTORY_THROUGH_2026-11-08.md)
- [`README.md`](README.md)
- [`ROADMAP_HISTORY_THROUGH_2026-11-08.md`](ROADMAP_HISTORY_THROUGH_2026-11-08.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`TASKS_HISTORY_THROUGH_2026-11-08.md`](TASKS_HISTORY_THROUGH_2026-11-08.md)
- [`TASKS.md`](TASKS.md)
- [`TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md`](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md)
- [`TEST_RESULTS.md`](TEST_RESULTS.md)
- [`WORK_LOG_HISTORY_THROUGH_2026-11-08.md`](WORK_LOG_HISTORY_THROUGH_2026-11-08.md)
- [`WORK_LOG.md`](WORK_LOG.md)

### ENGINE-001 — дополнительные experimental source-bound protocols (24)

Эти протоколы зарегистрированы для исследовательских сравнений на сложной картинке. Не являются production gate PASS; актуальный статус — в [PROJECT_STATUS](PROJECT_STATUS.md) и [TEST_RESULTS](TEST_RESULTS.md).

- [`ENGINE001_STRUCTURE_FIRST_V7_PROTOCOL_2026-11-14.md`](ENGINE001_STRUCTURE_FIRST_V7_PROTOCOL_2026-11-14.md) — контуры до заливки, отрицательный line-only preview.
- [`ENGINE001_STRUCTURE_COLOR_COMPOSITE_V8_PROTOCOL_2026-11-15.md`](ENGINE001_STRUCTURE_COLOR_COMPOSITE_V8_PROTOCOL_2026-11-15.md) — двухслойный contour+fill, низкое покрытие и зарегистрированное отклонение.
- [`ENGINE001_COMPATIBLE_REGIONS_V9_PROTOCOL_2026-11-15.md`](ENGINE001_COMPATIBLE_REGIONS_V9_PROTOCOL_2026-11-15.md) — отклонённая до запуска цветовая группировка.
- [`ENGINE001_COMPATIBLE_REGIONS_V10_PROTOCOL_2026-11-15.md`](ENGINE001_COMPATIBLE_REGIONS_V10_PROTOCOL_2026-11-15.md) — цветобезопасная группировка, offline FAIL.
- [`ENGINE001_DARK_SUIT_LINES_V13_PROTOCOL_2026-11-15.md`](ENGINE001_DARK_SUIT_LINES_V13_PROTOCOL_2026-11-15.md) — слабые внутренние линии пиджака, classical methods E2 partial.
- [`ENGINE001_FDOG_ANILINES_V14_PROTOCOL_2026-11-15.md`](ENGINE001_FDOG_ANILINES_V14_PROTOCOL_2026-11-15.md) — настоящие FDoG / AniLines Detail, [CI 43653371987](https://github.com/Kiddos19882/AutoDraw/actions/runs/43653371987) E3 PASS только для inference.
- [`ENGINE001_ANILINES_SEAM_REFERENCE_V16_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_SEAM_REFERENCE_V16_PROTOCOL_2026-11-15.md) — подготовка независимого эталона: без ручной blind-разметки semantic evaluation BLOCKED.
- [`ENGINE001_ANILINES_BRUSH1_PATHS_V17_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_BRUSH1_PATHS_V17_PROTOCOL_2026-11-15.md) — AniLines Detail → source-bound скелетные траектории кисти 1 без обязательной blind-разметки; offline exploratory, не качество game/CHALK.
- [`ENGINE001_ANILINES_JUNCTION_REPAIR_V18_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_JUNCTION_REPAIR_V18_PROTOCOL_2026-11-15.md) — A удаление избыточных диагоналей в графе AniLines; B объединение ветвей по направлению, без дорисованных линий; exploratory, не native/CHALK.
- [`ENGINE001_ANILINES_V19_MISSING_DETAIL_AND_COLOR_AUDIT_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_V19_MISSING_DETAIL_AND_COLOR_AUDIT_PROTOCOL_2026-11-15.md) — source-bound аудит пропущенных линий V18-B и соседств палитры, без изменения траекторий.
- [`ENGINE001_ANILINES_V20_OWNER_GUARDED_SHORT_RECOVERY_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_V20_OWNER_GUARDED_SHORT_RECOVERY_PROTOCOL_2026-11-15.md) — предрегистрация коротких line fragments с консервативной палитровой защитой; offline E2/E3, не качество Egret/CHALK.
- [`ENGINE001_ANILINES_V21_OWNER_SPLIT_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_V21_OWNER_SPLIT_PROTOCOL_2026-11-15.md) — prereg цветобезопасного разделения V20-отклонённых коротких цепочек, без bridging и изменений production.
- [`ENGINE001_ANILINES_V22_PALETTE_PROXY_AUDIT_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_V22_PALETTE_PROXY_AUDIT_PROTOCOL_2026-11-15.md) — prereg диагностики 3×3 палитровых отбраковок, без восстановления линий и без изменения production.
- [`ENGINE001_ANILINES_V23_NATIVE_WIDTH1_FOOTPRINT_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_V23_NATIVE_WIDTH1_FOOTPRINT_PROTOCOL_2026-11-15.md) — prereg isolated archived Egret BoardPane width1/Canvas2D/WebGL footprint для 56 вершин и 33 соединений V22.
- [`ENGINE001_ANILINES_V24_NATIVE_FOOTPRINT_PROVENANCE_PROTOCOL_2026-11-15.md`](ENGINE001_ANILINES_V24_NATIVE_FOOTPRINT_PROVENANCE_PROTOCOL_2026-11-15.md) — prereg нулевого BoardPane-контроля, поточечной альфы и цветового риска V23 без новых маршрутов.
- [`ENGINE001_ANILINES_VISUAL_RECOGNIZABILITY_REVIEW_V25_2026-11-15.md`](ENGINE001_ANILINES_VISUAL_RECOGNIZABILITY_REVIEW_V25_2026-11-15.md) — ретроспективный визуальный обзор узнаваемости V14/V18/V20 на сложной картинке, без утверждений об итоговой цветной игре.
- [`ENGINE001_VISUAL_COLOR_PLAN_V26_PROTOCOL_2026-11-15.md`](ENGINE001_VISUAL_COLOR_PLAN_V26_PROTOCOL_2026-11-15.md) — prereg сравнения существующих цветных Stage20-планов scanline/contour/skeleton на том же изображении.
- [`ENGINE001_VISUAL_COLOR_DIAGNOSTIC_V27_PROTOCOL_2026-11-15.md`](ENGINE001_VISUAL_COLOR_DIAGNOSTIC_V27_PROTOCOL_2026-11-15.md) — V27 сохраняет ROI FAIL из V26 и строит все исходные цветные планы только для сравнения видимых деталей.
- [`ENGINE001_VISUAL_ROI_PALETTE_V28_PROTOCOL_2026-11-15.md`](ENGINE001_VISUAL_ROI_PALETTE_V28_PROTOCOL_2026-11-15.md) — V28 предрегистрация сравнения цветных палитр: A canvas8, B ROI8, C ROI6, D ROI8 без почти белых штрихов.
- [`ENGINE001_VISUAL_BUDGET_V29_PROTOCOL_2026-11-15.md`](ENGINE001_VISUAL_BUDGET_V29_PROTOCOL_2026-11-15.md) — V29: prereg сопоставления действующего resource-aware optimizer с цветным V28-D по узнаваемости и прогнозному лимиту 6000.
- [`ENGINE001_VISUAL_ADAPTIVE_FILL_V30_PROTOCOL_2026-11-15.md`](ENGINE001_VISUAL_ADAPTIVE_FILL_V30_PROTOCOL_2026-11-15.md) — V30: независимые только модельные проверки existing interior-fill/outline-first с широкой кистью и сохранением деталей.
- [`ENGINE001_NATIVE_GAME_BRUSH_V31_PROTOCOL_2026-11-15.md`](ENGINE001_NATIVE_GAME_BRUSH_V31_PROTOCOL_2026-11-15.md) — V31: native archived Egret BoardPane 5 ширин × 6 траекторий, сравнение с ideal capsule MODEL_ONLY.
- [`ENGINE001_NATIVE_ADAPTIVE_COLOR_V32_PROTOCOL_2026-11-15.md`](ENGINE001_NATIVE_ADAPTIVE_COLOR_V32_PROTOCOL_2026-11-15.md) — V32: дополнение V5 shape-guided цветными штрихами, измерение настоящим Egret WebGL без production.
- [`ENGINE001_NATIVE_V29_BRUSH2_V33_PROTOCOL_2026-11-15.md`](ENGINE001_NATIVE_V29_BRUSH2_V33_PROTOCOL_2026-11-15.md) — V33: неизменный ресурсный цветной V29-план, настоящая кисть Egret width2 и измерение нативного качества.

### CHALK, FILL, INT — отчёты и протоколы (37)

- [`CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md`](CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md)
- [`CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md`](CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md)
- [`CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md`](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md)
- [`CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md`](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md)
- [`CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md`](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md)
- [`CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md`](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md)
- [`CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md`](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md)
- [`CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md`](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md)
- [`CHALK_G3_PARTIAL_RESULTS_2026-11-02.md`](CHALK_G3_PARTIAL_RESULTS_2026-11-02.md)
- [`CHALK_G3_RESULTS_2026-11-02.md`](CHALK_G3_RESULTS_2026-11-02.md)
- [`CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md`](CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md)
- [`CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md`](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md)
- [`CHALK_GEOMETRY_MATRIX_G1_RESULTS.md`](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md)
- [`CHALK_GEOMETRY_MATRIX_G2_RESULTS.md`](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md)
- [`CHALK_INT006_EXECUTION_PROTOCOL_2026-11-02.md`](CHALK_INT006_EXECUTION_PROTOCOL_2026-11-02.md)
- [`CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md`](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md)
- [`CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md`](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md)
- [`CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md`](CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md)
- [`CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md`](CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md)
- [`CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md`](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md)
- [`CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md`](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md)
- [`CHALK_INT006_PIXEL_AUDIT_2026-11-02.md`](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md)
- [`CHALK_INT006_PNG_SCREENING_2026-11-02.md`](CHALK_INT006_PNG_SCREENING_2026-11-02.md)
- [`CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md`](CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md)
- [`CHALK_INT006_V1_V5_RESULTS_2026-11-02.md`](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md)
- [`CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md`](CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md)
- [`CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md`](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md)
- [`CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md`](CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md)
- [`CHALK_INT006R_LIVE_RESULTS_2026-11-03.md`](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md)
- [`CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md`](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md)
- [`CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md`](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md)
- [`CHALK_NEXT_STEPS_PLAN_2026-11-02.md`](CHALK_NEXT_STEPS_PLAN_2026-11-02.md)
- [`CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md`](CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md)
- [`CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md`](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md)
- [`CHALK_RADIUS_MATRIX_RESULTS.md`](CHALK_RADIUS_MATRIX_RESULTS.md)
- [`CHALK_SAFETY_MARGIN_POLICY_DESIGN_2026-11-07.md`](CHALK_SAFETY_MARGIN_POLICY_DESIGN_2026-11-07.md)
- [`CHALK_TEST_BLOCKS_DESIGN.md`](CHALK_TEST_BLOCKS_DESIGN.md)

### Справочники архитектуры, UI, API и процессов (21)

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`BRUSH_MODULE_QUICK_INDEX.md`](BRUSH_MODULE_QUICK_INDEX.md)
- [`BRUSH_TEST_AUTOMATION_VISION.md`](BRUSH_TEST_AUTOMATION_VISION.md)
- [`COMPONENT_CATALOG.md`](COMPONENT_CATALOG.md)
- [`CONFIGURATION_AND_DATA.md`](CONFIGURATION_AND_DATA.md)
- [`DATA_CLEANUP_INVENTORY_2026-11-01.md`](DATA_CLEANUP_INVENTORY_2026-11-01.md)
- [`DATA_FORMATS_AND_MODELS.md`](DATA_FORMATS_AND_MODELS.md)
- [`DATA_FORMATS_AND_PROFILES.md`](DATA_FORMATS_AND_PROFILES.md)
- [`DEPENDENCY_MAP.md`](DEPENDENCY_MAP.md)
- [`DEVELOPMENT.md`](DEVELOPMENT.md)
- [`DOCUMENTATION_INVENTORY_2026-11-03.md`](DOCUMENTATION_INVENTORY_2026-11-03.md)
- [`EXECUTOR_API_REFERENCE.md`](EXECUTOR_API_REFERENCE.md)
- [`FILE_STORAGE_CATALOG.md`](FILE_STORAGE_CATALOG.md)
- [`GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md`](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md)
- [`GAME_MONITOR_BRIDGE_REFERENCE.md`](GAME_MONITOR_BRIDGE_REFERENCE.md)
- [`GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md`](GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md)
- [`MODULE_REFERENCE.md`](MODULE_REFERENCE.md)
- [`PREPARATION_API_REFERENCE.md`](PREPARATION_API_REFERENCE.md)
- [`TESTS_AND_CI_MAP.md`](TESTS_AND_CI_MAP.md)
- [`UI_INTEGRATION_MAP.md`](UI_INTEGRATION_MAP.md)
- [`VALIDATION_CORPUS_GENERATOR_2026-11-07.md`](VALIDATION_CORPUS_GENERATOR_2026-11-07.md)

### Корневые и исторические материалы Stage20 (16)

- [`BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md`](../BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md)
- [`BRUSH_TEST_RESULTS_ANALYSIS_2026-10-30.md`](../BRUSH_TEST_RESULTS_ANALYSIS_2026-10-30.md)
- [`CHALK_GEOMETRY_MATRIX_PLAN.md`](../CHALK_GEOMETRY_MATRIX_PLAN.md)
- [`CHALK_RADIUS_MATRIX_PLAN.md`](../CHALK_RADIUS_MATRIX_PLAN.md)
- [`CI_VERIFICATION_2026-10-30.md`](../CI_VERIFICATION_2026-10-30.md)
- [`GAME_MONITOR_BRUSH_LAB_PLAN.md`](../GAME_MONITOR_BRUSH_LAB_PLAN.md)
- [`MASTER_ROADMAP.md`](../MASTER_ROADMAP.md)
- [`PRE_REFACTORING_READINESS_2026-10-29.md`](../PRE_REFACTORING_READINESS_2026-10-29.md)
- [`PROJECT_ANALYSIS_PLAN_10_STAGES.md`](../PROJECT_ANALYSIS_PLAN_10_STAGES.md)
- [`PROJECT_DOCUMENTATION.md`](../PROJECT_DOCUMENTATION.md)
- [`PROJECT_GUIDE.md`](../PROJECT_GUIDE.md)
- [`README.md`](../README.md)
- [`REFACTORING_AUDIT_2026-10-29.md`](../REFACTORING_AUDIT_2026-10-29.md)
- [`REFACTORING_PLAN_2026-10-29.md`](../REFACTORING_PLAN_2026-10-29.md)
- [`TECHNICAL_AUDIT_2026-10-29.md`](../TECHNICAL_AUDIT_2026-10-29.md)
- [`TEMP_PLAN_OUTLINE_FIRST_FILL.md`](../TEMP_PLAN_OUTLINE_FIRST_FILL.md)

### README модулей и первичные Markdown-отчёты (3)

- [`ANALYSIS_AUDIT_2026-10-29.md`](../data/results/brush_behavior_tests/ANALYSIS_AUDIT_2026-10-29.md)
- [`ANALYSIS_RESULTS_2026-10-29.md`](../data/results/brush_behavior_tests/ANALYSIS_RESULTS_2026-10-29.md)
- [`README.md`](../source/game_monitor/README.md)

