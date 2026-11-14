# AutoDraw — дорожная карта будущих работ

**ENGINE-001 next after selective-width V4 (2026-11-14):** frozen V3 stroke-plan-only brush upgrade (111 width4→6, 13 width8→10) on same two icons, [native CI 43567176919](https://github.com/Kiddos19882/AutoDraw/actions/runs/43567176919) SUCCESS at `d843c58`. Actual Egret normal radius-varied V4 coverage **99.3107%** with max exterior **1.6667 logical px** (zero outside3px), **same 323 strokes/674 synthetic points/3 width switches**, so pre-registered **offline geometric gate PASS**, unlike V3 97.6681%. Critically IoU falls **93.5282%→89.4052%**, native leaked pixels **6974→17456**, and game CHALK **UNKNOWN**. This is an offline source-mask success, NOT run-bound DEC-030 RGB acceptance or color mixing safety. Next explicitly preregister independent **wide/narrow/multicolor holdout with true native mixed-width geometry and per-color boundary tests**, separately test actual setRadius width/diameter and leakage near adjacent color, then bounded real game E4 with exact pointCount pre/post and independent E5 before production decision. V0–V3 negative history and V4 protocol immutable; no fitting the same two icons to assert generality.


**ENGINE-001 next after native adaptive brush V3 (2026-11-14):** opt-in V3 prereg `219fc6be8` / [CI 43565322109](https://github.com/Kiddos19882/AutoDraw/actions/runs/43565322109) code `969812e` **SUCCESS E2/E3**; native coverage improved to **97.6681%** (vs V2 96.4742%), IoU93.5282% (vs V2 92.3523%), **323 strokes/674 synthetic vertices** (vs V2 403/1943), but >=99% coverage **FAIL**, exact CHALK UNKNOWN. Exterior leakage6974 native pixels all <=0.667 logical px; within symmetric 3px interior boundary are 3476 misses, **198 missing pixels deeper than 3px**. Selected setRadius values 2/4/8 only, no 15/30 candidate for present narrow icon geometry; radius argument is not independently calibrated physical brush diameter. **Next research V4 (new prereg ID before changes):** audit gaps in archived V3 residual and true native/proxy differences, then test minimally intrusive longer boundary+centre passes for last 1.3319 percentage points with explicit cap on strokes/vertices/switches; avoid short per-hole repairs. Keep symmetric 3px boundary diagnostic distinct from unchanged 99% coverage and full run-bound FILL DEC-030 policy. Real game E4 exact CHALK and independent E5 separately remain open; production defaults untouched.


**ENGINE-001 next after painted-strip-frontier V2 (2026-11-14):** [CI 43563405147](https://github.com/Kiddos19882/AutoDraw/actions/runs/43563405147) on `d6ef11e` confirmed authentic native WebGL for a proposed long-stroke frontier extracted from painted baseline stripes, not the original source outline. Coverage improved from baseline 92.1094% / source-contour V1 92.7288% to **96.4742%**, but native target has 5555 missing pixels, 7032 near-boundary leaks (max1.0541 logical px, 0 beyond DEC-030 3 logical px geometry), and plan cost grew to **403 strokes/1943 synthetic vertices**, compared with V1 381/772. **OFFLINE QUALITY FAIL** at 99% coverage and no exact CHALK. NEXT gate: preregister new independent ID for **resource-aware consolidation of long painted-frontier passes and boundary coverage**, seeking >=99% without multiplying stroke/vertex count; preserve all baseline/V1/V2 negative evidence. Use the fixed 3 logical-pixel halo as diagnostic only until run-bound RGB/live comparison, do not retroactively reinterpret V1 zero-leakage gate. Source game E4/GPU temporal and independent E5 remain outstanding.


**ENGINE-001 next after `ENGINE001_TWO_ICON_PREDICTIVE_CONTOUR_V1` (2026-11-14):** source-mask-contour predictive joint-fill experiment on pinned home+envelope completed [native CI 43549152669](https://github.com/Kiddos19882/AutoDraw/actions/runs/43549152669) SUCCESS, but offline quality **FAIL** (coverage92.728842%, IoU92.532681%, extra334 native pixels; requirement coverage>=99% / leakage=0 unchanged). It covered 976 more target pixels than fixed horizontal-only V1, at cost +1 total stroke; synthetic vertices 760->772, not real CHALK. This experiment traced **eroded target-mask contours near predicted gaps**, not the user's intended boundaries of already painted strokes. **Next:** explicitly preregister a **new** version deriving long interior contour corridors from the analytically predicted painted-stripe frontier adjacent to residual holes, then jointly place horizontal endpoints for minimal overlap, record rejected/short segments and match genuine native Egret masks before any acceptance. Do not retrofit the completed V1; treat emulator preview errors as measured; no production change without independent game-quality E4/E5 and exact CHALK.


**ENGINE-001 follow-up to user's two-icon mask smoke (2026-11-14):** the single composite `home + envelope` source-mask test completed [CI 43546565112](https://github.com/Kiddos19882/AutoDraw/actions/runs/43546565112) on `d60956a`. Actual Egret normal/radius2 fixed row-step2 synthetic plan achieved coverage **92.1094%**, IoU **91.9157%**, 12432 missing / 332 outside backing pixels, so FILL-like 99% target is **NOT MET**. The test is independent of prior six FILL live/replay cases but is **not** held-out real game-vs-renderer validation: no live game capture exists for these two icons. Preserve this baseline and work on planner edge/row coverage with a new preregistered experiment ID before comparing changes. Separately retain actual live-vs-Egret held-out source bindings and temporal GPU E4/E5 for ENGINE-001. No acceptance threshold retrofits or production promotion.


**ENGINE-001 next after fixed residual audit (2026-11-14):** [CI 43541756465](https://github.com/Kiddos19882/AutoDraw/actions/runs/43541756465) E3 confirmed that all 2,208 original residual pixels across six frozen 694×363 images lie within the fixed 2px band of either binary-mask boundary (40+535+659+40+530+404=2,208); original/first-party quota-recovered images maintain historical negative acceptance. Do **not** treat a 2px boundary-localized mismatch as acceptable, nor tune projection/resampler/thresholds to these six seen results. Next preregister held-out geometry and objective residual metrics under frozen mapping, then compare native game GPU/ENTER_FRAME temporal evidence supplied by the user; E4 and independent E5 separately. No PC control by assistant.


**ENGINE-001 next: residual raster/temporal validation (2026-11-14).** Quota coordinate recovery itself is evidenced E1/E3; [CI 43536560568](https://github.com/Kiddos19882/AutoDraw/actions/runs/43536560568) opt-in native Egret replay on `7581b7c` shows slight IoU decrease for C1-F3 and unchanged C2-F2, so two missing coordinates do not explain remaining pixel residuals. Freeze existing transforms/thresholds and preserve original PNG/CHALK. Next design held-out projections and independent live GPU/temporal ordering validation; no rerun on user PC while its remote runtime is offline.


**ENGINE-001 / next research gate (2026-11-14):** [CI 43535607144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43535607144) on `52c8c41` verified first-party quota-stream provenance of two omitted accepted coordinates (C1-F3, C2-F2), 8/8 negative/positive tests, unchanged frozen source. Next make an **opt-in** Egret replay of the two affected figures using separately validated quota events without altering original Monitor JSON or default diagnostic outputs; compare new PNG/IoU at fixed pre-registered mapping, preserve historical negative results. Only after this separate experimental replay pursue held-out/live GPU/temporal validation; do not promote E3 source parity to E5 pixel/quality PASS.


**FILL001 third-run per-run binding (2026-11-12):** frozen 50MB run root cause diagnosed (local Monitor buffer overflow count 17806 misclassified as transport loss), binder fixed with strict per-run recorder/send/sequence gates and synthetic+real-frozen CI replay PASS `874f2e1` / 43274926194. Next fresh E4 3→4 transition with verified Clear and independently bound CHALK; then E5. Legacy blocked result not rewritten.

**FILL001 pointer hover/screenshot gate (2026-11-12):** для baseline и after-Clear PNG изменён перенос курсора с legacy margin32 на строгую нижнюю точку `board/meter.bottom+160px` (без lateral fallback) и popup settle 0.4 s. Следующий E2/E3 dedicated CI, затем пользовательский E4 с PNG и подтверждением исчезновения overlay. Не считать саму координату защитой от всех иных интерактивных UI, и не ослаблять Clear comparator.

**BoardPane migration gate (2026-11-12):** FILL001 screenshot capture hardened through exact native ROI contract, post-Clear re-probe and cursor-off-board; point-only Clear calibration removes manual board_area requirement at series launch (`20fccadf`). Next E2/E3 check on new commit, followed by E4 Windows 1×2; only then design Brush Lab authenticated browser/Bridge owner adapter. Standalone Brush Lab still legacy/manual; no unverified CSS client-to-desktop conversion, no threshold change.

**Auto BoardPane screenshot ROI migration (2026-11-12):** FILL001 series board crop и blank reference переведены с ручного `board_area` на verified native ROI и per-series blank proof (`2448650` с тестами `92fdea7`); сначала CI E2/E3, затем E4 с новым series ID. Остальные Brush Lab autonomous screenshot workflows требуют отдельного Monitor-enabled path и provenance model (поскольку Monitor не всегда запущен). Preserve old profile for click/slider/meter; не создавать shadow screenshot calibration, не изменять frozen threshold `0.15%`.

**FILL001-SERIES-001 / актуальный следующий gate после `9dbb74b` (2026-11-12):** два настоящих `QUOTA_LIMITED` с run-bound CHALK=5745/5742 и settled PNG; обе серии остановлены на ENGINE-001 Clear comparator. Сначала E2/E3 для read-only error-metrics patch `0b851c1` и test `b106fa1`; затем независимый анализ двух after-clear PNG относительно original blank reference (pixel diff, ROI, SHA), и только после установления причины — одно совместимое исправление, если необходимо. Порог 0.15%, reserve 300, Clear UI action/executor оставлять frozen. Следующий реальный опыт user-only с новым ID; E5 независимо.

**FILL001-SERIES-001 / новый первый gate (2026-11-12):** после [E4 BLOCKED `4822ccf`](https://github.com/Kiddos19882/AutoDraw/commit/4822ccf6e401dcf1cd56fdc43c926ccdf6432fa6) (29/141, missing Bridge session evidence) внесена минимальная fail-closed диагностика и synthetic tests на `1d590b8`. Сначала подтвердить E2/E3 конкретного SHA; затем пользовательский E4 с новым ID и server stderr/runtime files для установления причины, не изменяя CHALK estimator, safety margin=300, Clear comparator=0.15% или executor defaults. После run-bound закрытой первой фигуры — переход Clear/следующая; независимая E5 позже.

**DOC-CODE-REUSE-001 / следующий этап после подтверждённого CI (2026-11-12):** [FILL001 series CI 43140218990](https://github.com/Kiddos19882/AutoDraw/actions/runs/43140218990) SUCCESS на code SHA `4dfec5c` (165 offline tests), [docs integrity CI 43164791087](https://github.com/Kiddos19882/AutoDraw/actions/runs/43164791087) SUCCESS на `b317348` (11 unittest; source inventory 130 файлов, 0 unconditional root SCC). В текущем порядке: точечно проверить callbacks/reexports CAP-011 и CAP-017, не создавать вторую реализацию runner/statistics; затем закрыть архитектурную ревизию либо описать конкретное открытое ограничение. **Не переносить E3 PASS на E4 quota-limited → Clear → next**, следующий реальный запуск остаётся независимым user-only gate.

**DOC-CODE-REUSE-001 / next gate (2026-11-12):** scoped `--usage` extension coded on `fe4a1de` with tests through `f2e5919`. E2/E3 позднее подтверждены раздельно: docs integrity на `b317348` и FILL001 series на `4dfec5c`, включая 0 новых unconditional root SCC. Once verified, examine whether any remaining indirect callback use is materially unrecorded; no further refactor until evidence. User-only FILL001 E4 is separate.

**DOC-CODE-REUSE-001 / текущий следующий gate (2026-11-12):** завершён E1-аудит CAP-009/011/012/013/017, обнаружены external executor/integrated_app consumers и косвенные entrypoints. В экспериментальном FILL001 вынесен один общий resolver scanline spacing без изменения frozen mask/signature формулы; код+регрессии на `4dfec5c`, E2/E3 ещё не подтверждены. CI позднее подтверждён и запрещённых root-level SCC не обнаружено; read-only коррекция охвата `--usage` для executor/integrated_app также выполнена (см. верхние записи). E4 quota recovery отдельно NOT_RUN; к нему не переходить по факту одного статического рефакторинга.

**Факт этапа E1/E3:** аудит реальных imports/call candidates завершён [CI 43135827499](https://github.com/Kiddos19882/AutoDraw/actions/runs/43135827499) на `23a5a516e788b2030663fc7ad11b3604dee3c5a4`, 129 модулей, 20 карточек; all-scope SCC 2, безусловных root-level SCC 0. Отчёт [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) и [raw JSON CI artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/43135827499/artifacts/13906713385). Исторически следующим шагом был поиск непрямых вызовов и одного кандидата на переиспользование; E1 исследование и один небольшой refactor уже выполнены позже на code SHA `4dfec5c` (см. первый абзац). Новый root-level SCC теперь блокирует docs CI, deferred cycles не считаются runtime FAIL.



## DOC-CODE-REUSE-001 — порядок внедрения каталога возможностей (2026-11-12)

Read-only терминальный поиск и отдельный модуль `tools/capability_catalog.py` реализованы; [CI 43126121772](https://github.com/Kiddos19882/AutoDraw/actions/runs/43126121772) SUCCESS на `dd9ec43e` (8 tests, пять проверенных поисковых запросов). Следующий архитектурный этап — выборочная инвентаризация реальных consumers и import cycles, затем точечное совместимое извлечение при подтверждённой необходимости. E4 игрового рисунка этим CI не подтверждается.

Первый шаг: reuse-first навигация в существующем [COMPONENT_CATALOG.md](COMPONENT_CATALOG.md) (20 возможностей на baseline `7cc938af`), read-only AST-контроль owner/entrypoint/args/test и новая regression проверка в Markdown CI; никакого runtime рефакторинга. [docs-integrity CI 43124607337](https://github.com/Kiddos19882/AutoDraw/actions/runs/43124607337) E3 SUCCESS на `7b8f4aaa`. Следующий шаг — повторяемый тест навигации из нового ИИ-чата, затем read-only анализ реальных consumers, прямых зависимостей и только при доказанной пользе — маленькие совместимые извлечения с обязательными тестами. Не подменять граф импортов знанием об actual runtime и не повышать experimental до production без validation. Приоритет FILL001-SERIES-001 E4 остаётся отдельным.


## Следующий gate FILL001-SERIES-001: quota-limited → ENGINE-001 Clear → следующая фигура (2026-11-12)

Первая игровая попытка из [5acb2e6](https://github.com/Kiddos19882/AutoDraw/commit/5acb2e6284a4425cdfea8812257fa85ea55ed88f) E4 BLOCKED: radius1, 100/141 штрихов, remainingPoints=241, не создан полный exact/settled результат. Добавлен экспериментальный QUOTA_LIMITED путь, который фиксирует частичный exact run-bound CHALK и PNG, но не признаёт quality PASS, выполняет штатный Clear только после точной привязки и разрешает следующий task только по прежнему verified blank-board gate. [Series CI 43114637544](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114637544) SUCCESS, [main 43114637531](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114637531) SUCCESS.

Следующий один live gate: пользовательский ограниченный опыт 1 цикл × 2 фигуры с ресурсно тяжёлой первой задачей, новой серией и оригинальными raw captures; отсутствие exact run/settled PNG/Clear-подтверждения должно приводить к BLOCKED. Затем повторяемость/E5, без изменения production defaults, оценки CHALK или acceptance thresholds. Подробности — [TASKS.md](TASKS.md).
## Текущий приоритет — FILL001-SERIES-001: ограниченный E4 smoke (2026-11-11)

Экспериментальная opt-in интеграция FILL-001 → существующий Stage6 → run-bound Monitor/PNG/exact CHALK → штатный откалиброванный ENGINE-001 Clear → следующая фигура **реализована в коде**. E3 SUCCESS на `fea265f92aac`: [series CI 42975856803](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975856803) и [main validation 42975856883](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975856883). Серийные E4/E5 **NOT_RUN**, production eligibility FALSE; Windows portable job в последней main validation `SKIPPED`.

**Следующий gate (только при отдельном разрешении на live):** на ПК пользователя проверить **1 цикл × 2 фигуры** на тестовой чистой доске. Зафиксировать действительные profile/Firefox/Bridge/Monitor preflight, per-figure run ID, before/settled PNG, exact `post.pointCount - pre.pointCount`, штатную ENGINE-001 очистку с исходным допуском 0.15% и двумя settled exact snapshots. Неоднозначный reset/calibration/CHALK → fail-closed до следующей фигуры. Только после подтверждённого E4 — repeatability и остальные frozen варианты с независимой E5, затем отдельное production-решение; не менять estimator, executor defaults или acceptance thresholds. [Активные задачи](TASKS.md).

**Остальные планы ниже** — ранее записанные этапы V5/ENGINE-001/геометрии. Их хронология сохранена; они не отменяют текущий первичный E4 gate FILL001-SERIES-001. Актуальный backlog — [TASKS.md](TASKS.md).

## После V5 DEC-030 — native geometry proxy пройден, реальный CHALK впереди

В нативном Egret BoardPane/WebGL frozen rectangle V5 два заранее зафиксированных trim0 варианта с одним нижним штрихом превысили 99% покрытия; утечка 54 backing-пикселя и не дальше 1 логического px по distanceTransform/3, на alpha128. Это **native alpha proxy**, не экранная качество/CHALK-валидация. [Raw evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385/artifacts/13707703988). Следующий этап: проверить новый mixed-width brush switch (W10 + W2 или W3), same-run Stage↔desktop screen geometry, реальный `FILL001_CHALK_FIRST_PERIMETER_V2` PNG audit и exact `post.pointCount-pre.pointCount` на отдельных изолированных E4 запусках; без такого измерения W2/W3 не ранжировать. Затем frozen wide/narrow, multi-color leakage visual holdout и отдельный production decision. Executor defaults, estimator, frozen masks и historical runs не изменять.


## FILL-001 после DEC-030 full capture acceptance

Новый программный runtime entrypoint и отдельная версия capture validator используют общий строгий Monitor/Bridge/executor/CHALK contract, проверенный E4 screen binding и DEC-030 perimeter quality. Old 45-cell matrix/legacy capture validator и executor defaults не менялись. Следующее: закончить CI на code SHA `8e2920b9d7410f596a89684ed3f85d44eaafb479`, получить независимый новый run-bound E4 с актуальной screen geometry и frozen mask, затем сравнить **только прошедшие quality** кандидатные планы по точному `pointCount delta` (не оценочным штрихам). Отдельно проверить multi-color визуальный halo и wide/narrow holdout; не делать production PASS без E4/E5 validation и без новой отдельной execution permission. [Validation](https://github.com/Kiddos19882/AutoDraw/actions/runs/42643765113).


## Новый приоритет FILL-001 — CHALK-first PASS (DEC-030)

Пользователь **изменил acceptance** будущих FILL-001: coverage≥99%, допускается до 3 логических пикселей выхода реальной кисти за frozen mask по всему контуру, но не дальше, даже единичным пикселем. После достаточного качества оптимизировать **exact CHALK**, а не нулевую утечку. Новый screen-mask quality evaluator версионирован как `FILL001_CHALK_FIRST_PERIMETER_V2`, legacy отчёты/матрицы не переписываются. Сначала versioned run-bound capture acceptance и контроль screen mapping, затем bounded native/screen кандидаты с боковым и нижним заполнением и multi-color holdouts, сравнение подтверждённых точных CHALK, потом решение о production/45-cell. Приоритет zero leakage в старых V1–V4 документах — исторический, не обязательный для следующего протокола. [Решение](DECISIONS.md#dec-030-fill-001-новый-pass-с-ограниченной-утечкой-и-приоритетом-фактического-chalk).


## Следующая геометрическая проверка после FILL-001 V4

Один lower-boundary native stripe с width2/Y190 или width3/Y189 почти целиком закрыл 2457 backing-пикселей нижнего пропуска при alpha≥128 и **не увеличил leakage** (control G_trim_3 zero). Width3/Y190 пересёк нижнюю границу на 2414 backing-пикселей — сохраняется как отрицательный результат. Все кандидаты всё ещё ниже 99% coverage из-за боковых gaps. Следующий ограниченный шаг: adaptive left/right endpoint repair с реальным native footprint и фиксацией ширины/вертикального положения, затем frozen holdout wide/narrow, independent run-bound Stage/screen, и только при доказательности live E4. [Raw V4 evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168617/artifacts/13655800959). Не менять production и acceptance gates.


## После FILL001 spatial V1 — локальная нижняя граница и боковые концы

Построчная разметка native-пропусков выявила отдельный нижний блок 2457 backing pixels (3×819) и боковые потери; при alpha128 исправление X endpoint trim3 устраняет утечку, но нижний блок не меняет и ухудшает coverage. Поэтому следующий **ограниченный offline** gate — проверить узкую граничную коррекцию снизу на реальном native brush footprint и сохранить боковой leak=0, не добавляя глобальных проходов. Затем повторить на frozen wide/narrow, изучить run-bound projection и лишь после E5 решать E4. [Evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42573526457/artifacts/13653904396). Производство и пороги не менять.


## FILL-001: после native brush footprint A

Для width5/10 normal + smooth измерены реальными Egret WebGL PNG (10 probes) поперечная толщина, торцы, углы и диагонали; обнаружено отсутствие последних 300 backing px в smooth относительно normal на фиксированном двухточечном отрезке (действует `drawLast=false`). [Native evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011/artifacts/13653019564). Дальше — **не** расширять бесконтрольно глобальный trim/brush sweep, а применить эмпирический footprint к per-row/per-side residual, затем bounded adaptive candidate на rectangle и frozen holdouts wide/narrow, Stage/screen E5 и только после принятого решения одиночный game E4. Не менять существующий executor или acceptance thresholds.


## Следующий этап — локальная footprint-диагностика FILL-001

Native V2 fixed X-trim существенно уменьшил leakage, но ухудшил coverage. V3 с тонким contour5/inset3 тоже FAIL в native WebGL, хотя OpenCV предполагал PASS. Вместо дальнейшего общего отступа требуется измерение per-row/per-side native отпечатка кисти и локальные безопасные коррекции, затем frozen wide/narrow holdout и независимый run-bound Stage/screen gate. Production-код/пороги менять нельзя до E5 и отдельного решения. [Evidence](https://github.com/Kiddos19882/AutoDraw/actions/runs/42552197466/artifacts/13645982484).


## Следующая геометрическая проверка после native contour-first

Проверка настоящим offline BoardPane/Egret WebGL показала **нулевую разницу при перестановке одного и того же контура** (C последний vs E первый) и дополнительные 754 native-пикселя по сравнению со sparse-only B. Однако native local nearest-3× alpha diagnostic всё ещё даёт пропуски и утечки; это не run-bound live screen PNG. Значит, отдельная оптимизация **положения, толщины и перекрытия контура/заливки** перспективнее перестановки порядка. Следом — ограниченный geometry candidate с заранее зафиксированными native metrics + независимым V3 Stage/client/desktop mapping gate; после успешной проверки только одно новое versioned live измерение exact CHALK. Frozen masks, thresholds и production code не менять. [Native artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549813024/artifacts/13644514101).

## Текущий следующий шаг: FILL-001 контур первым

После V3 OFF user предложил **сначала один замкнутый контур, затем редкие внутренние штрихи с перекрытием**. Existing A–D C рисовал контур последним; новая офлайн-проверка E держит ту же геометрию и подтверждает равенство OpenCV растров при смене порядка. Исследовательский V1 inset 7–9 FAIL на 3/3 frozen shapes; V2 endpoint trim 1–4 PASS только rectangle/wide, FAIL narrow. **Общего прошедшего для всех форм варианта обрезки нет**; нельзя автоматически переносить trim в production или утверждать live quality. Дальше: independent native Egret Stage replay новой геометрии, затем — только по evidence — versioned single-run live quality/CHALK, без batch и смены thresholds. [Source and output CI](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009); действующая задача — [TASKS](TASKS.md#p1--fill-001-outline-first--interior-overlap-контролируемый-вариант).


**Дата:** 2026-11-08 · **Текущая evidence-база:** `177165361b0340515fe3bb74f4847ab3ec579ebc` (историческая база `a2d1f0a52d47` сохранена в прежних записях) · **Ветка:** `feature/image-geometry-optimization`. Подробная прежняя редакция полностью сохранена: [ROADMAP_HISTORY_THROUGH_2026-11-08.md](ROADMAP_HISTORY_THROUGH_2026-11-08.md).

Этот файл задаёт **последовательность**, а не историю. Пункты выполнения и владельцы конкретных gate — [TASKS](TASKS.md); подтверждённые факты — [PROJECT_STATUS](PROJECT_STATUS.md) и [TEST_RESULTS](TEST_RESULTS.md).

**Этап 0 завершён:** 99/99 Markdown в навигации, девять сохранённых исторических редакций, автоматический audit [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS. Далее только будущие приоритеты.

## Следующий исследовательский запуск — чистый FILL-001 Smooth A/B

По заданию пользователя текущий приоритет переключён на FILL001_SMOOTH_AB_V1. Последовательность: software/regression CI → два индивидуальных Windows preflight с явно заданными ON/OFF и новой чистой доской → сохранение raw+PNG даже для quality FAIL → независимый same-mask анализ покрытия, утечек, правого края и точного CHALK. До двух новых E4 capture статусы нового теста NOT_RUN; архивные A/B данные не выдаются за новые. При несовпадении before ROI или экранного преобразования итог пары PARTIAL, без подгонки изображения. Production и 45-cell batch остаются заблокированы. [TASKS](TASKS.md#p1--активный-следующий-эксперимент-fill-001-smooth-ab).

## Текущий этап — ENGINE-001: независимая E5 сверка после live лаборатории

**Достигнут следующий gate:** [CI E5 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181) зафиксировал 9/9 `PASS_PER_RUN` для native Egret WebGL Stage A ↔ live screen RGB на run-bound accepted coordinates, без post-hoc alignment. Результат **E5 screen-RGB PASS**, но direct native-to-live alpha и temporal order не закрыты; ENGINE-001 остаётся PARTIAL. **Далее:** оценить необходимость отдельно наблюдаемого native render timeline и `normal` live control, не переносить этот результат на FILL-001. Числа и границы в [§22](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md).

**Приоритет на 2026-11-08:** статический разбор Egret 5.4.1 выполнен в проверенной части, а `ENGINE001_ONE_CLICK_LAB_V1` теперь прошёл **9/9 E4** на `1771653` (точный CHALK=846). Ранее запланированный run-bound Stage/client/desktop projection и сравнительный native Egret WebGL replay выполнен для 9 runs ([E5 CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181)); на момент исходной E5 geometry диагностики native PNG был **NOT_RUN** (исторический статус, заменён новым evidence). Прямой live alpha и полная temporal validation остаются **NOT_RUN**, ни E4, ни screen-RGB PASS нельзя выдавать за них.

**Выход:** [архитектура §21 и E5 boundary](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), связь 9 run/PNG/accepted-points, самостоятельный native WebGL renderer reference и независимая PNG-маска с зафиксированными критериями до итоговой оценки. **Gate:** accepted/rejected/missing 9/9, sha256/provenance, pixel overlap/missing/leakage и endpoint bounds без подбора thresholds, отдельный результат по каждому run; при нехватке данных PARTIAL/UNKNOWN. Затем аудит Markdown и CI соответствующего SHA. Ни production, ни FILL-001 quality thresholds не менять; FILL-001 live experiments по-прежнему отложены.

## Этап 1. Офлайн-сравнение качества геометрии

**Промежуточный gate до оптимизации:** `FILL001_MONITOR_SAME_RUN_V1` подготовлен в существующей вкладке (не live-валидирован). После подтверждения нового software/build выполнить **одну** rectangle/r10/step5/o0/rep1 задачу и получить run-bound full-screen+ROI PNG, raw `DRAW_SAMPLE`, `MOUSE_MOVE_SAMPLE`, `ENGINE_FRAME_SAMPLE`, `observed_stroke_modes`, BoardPane CSS/Stage/canvas geometry, Bridge/executor. Проверить не только `PASS_E4_RAW_CAPTURE`, но и отдельное **FILL001 quality FAIL/PASS** без изменения исходных порогов. Затем на независимом offline comparison построить одинаковые региональные residual metrics: правый/левый периметр, верх/низ, 11 старых leakage, 738 старых model-only pixels, фактические accepted endpoints и тот же frozen mask при *собственной* calibration каждой сессии. Старые screenshot Stage geometry нельзя реконструировать из новой. Поскольку этого нового E4 ещё нет, old/new E5 **NOT_RUN**. [Технический протокол](GAME_MONITOR_BRIDGE_REFERENCE.md).

**Новый FILL-001 spatial baseline (`c4fefe6`):** [CI 42456241289](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289) Preparation/G3 977 PASS; [артефакт FILL001_RIGHT_EDGE_SPATIAL_V1](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289/artifacts/13607454421). Пропуски справа распределены полосой по всем 114 middle ROI rows (499px, ширина 3–7, median4), слева 134px; старые 11 leakage сосредоточены у левого верхнего и нижнего периметра. На 27 run-bound accepted paths правая конечная точка находится правее плановой, так что автоматическое удлинение планов не следует из evidence. Дальше отделить screen mapping, smooth midpoint/round cap от геометрии планировщика; проверить отдельно 11 leakage и model-only 738 до выбора bounded correction. Текущие frozen quality gates ≥99%/leakage=0 не меняются.

Определить неизменный baseline на уже доступных изображениях. В FILL-001 воспроизвести perimeter-localized failure, сравнить scanline и outline-first / contour-correction без изменения production executor. Сопоставлять coverage, leakage, boundary errors, details, path length, strokes и expected operation count раздельно.

**Промежуточное доказательство 2026-11-08:** Новый FILL-001 A–D offline [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123): SUCCESS на workflow SHA `6d790cd`. 3 frozen mask × 4 strategy, 15 диагностических PNG + JSON ([artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597)). Для варианта C coverage rectangle=99.516%, wide=99.593%, narrow=99.381%, leakage=0 в OpenCV. Эффект не подтверждён на реальном PNG. Вариант D использует oracle residual и создаёт слишком много дополнительных штрихов. Paired screen-ROI residual comparison теперь выполнен: [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS (`16f0e1b`), [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Actual ROI target 71110 screen px: 1116 uncovered, 11 leaked. Hypothetical contour inset6 recovers 734, leaves 382, would yield 99.462804% coverage with 0 NEW model leakage, but existing 11 leakage remain, so this is not a game PASS. Первый CI [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) FAILED из-за LF/CRLF проверки JSON, исправление протестировано. **Следующий шаг:** калибровать actual endpoint/brush footprint и источник 11 leakage; отобрать domain-representative подвыборку 81 изображений после уточнения geometry assumptions. Quality gate оригинального game capture остаётся FAIL.

**Gate:** качество ≥99% coverage и leakage=0 для ранее заданных FILL-001 targets до новой live-проверки; offline simulation не утверждает runtime.

## Отложенная программа тестов FILL-001, GEOM-001 и связанных gates

Это **сохранённый план будущих экспериментов**, не разрешение запускать их и не список новых PASS. Возобновление только после ENGINE-001 и после отдельного protocol/quality review.

**Базовые уже выполненные проверки (не запускать заново без новой причины):**

| Вариант | Гипотеза / протокол | Нынешние доказательства |
|---|---|---|
| `A` плотные scanlines | Одна линия практически в каждую строку | OpenCV/CI PASS для трёх frozen masks, число штрихов велико |
| `B` разреженные scanlines | Изменить `scanline_row_step/offset` | 2238 offline combinations; rectangle/r10/step5/offset0 — 27 strokes; live CHALK=1260, PNG **FAIL** 98.430600%/11 leaks |
| `C` B + связная контурная обводка | Поправить края одним проходом | OpenCV/CI для трёх frozen masks; screen-ROI offsets 5–8 model counterfactual — не игровой запуск |
| `D` B + контур + локальные residual corrections | Достичь покрытия без массового уплотнения | OpenCV oracle знает эталонную residual mask; алгоритм не готов к игре |
| `RS` sweep | Влияние радиуса, вертикального шага и offset | 15 shape×radius configs подобраны offline; 45 live cells **BLOCKED** до принятого preflight |
| `PRR` | Paired Egret renderer vs live screenshot, vertical/diagonal | 6/6 PASS_PER_RUN на radius10, но IoU ~0.938–0.952, не pixel-identical |

**Возможные НОВЫЕ кандидаты, пока только E0:**

- `E1 adaptive brush width` — широкая кисть на безопасных прямых, 5px/малые толщины у закруглений/опасных границ; учитывать реальный `lineWidth`, перекрытия и переключения; маленькие значения 1/3 могут иметь renderer-specific pixel alignment.
- `E2 adaptive contour inset` — постоянный размер кисти, локально меняющийся внутренний отступ по curvature/safety margin; сравнение с фиксированными offsets 5/6/7/8.
- `E3 joint adaptive width+inset` — объединить E1/E2; проверить переходы между штрихами, концевые caps и отсутствие новых разрывов.
- `E4 bounded local correction` — короткие локальные проходы по обнаруженным пропускам без доступа к oracle mask исполнительного алгоритма, с отдельной оценкой числа strokes и смен кисти.
- `ER multi-stroke Egret replay` — **переиспользовать существующий** [`tests/game_renderer_reference.js`](../tests/game_renderer_reference.js) вместо нового симулятора: 27 run-bound accepted-point штрихов FILL-001, реальный `BoardPane.redraw`, Canvas/WebGL PNG, mode/width/colors/options, clipping, проверка сохранённого `after.png` и 738 model-only / 11 leakage pixel discrepancies. Текущий live-replay принимает один штрих и требует same-run renderer snapshot; отсутствие такового у старого FILL-001 отражать как `UNCALIBRATED`, не подставлять другие session transforms. Из прямого аудита [ENGINE-001 §12](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) следует дополнительный исследовательский риск: игра накапливает `StrokePath` через `redraw(false)`, а existing harness делает one-pass `redraw()`. Accepted-only версия `ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1` теперь **выполнена offline** на старых 1260/27: 0 pixel differences по итоговым Canvas2D/WebGL RGBA; [доказательства](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [browser CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046). Следующий возможный offline test — повторные `redraw(false)` без новых точек и промежуточные render/upload, с новым experiment ID; live screen mapping/PNG для старого run остаются UNCALIBRATED/BLOCKED. Это не закрывает полный ER и не объясняет FILL-001 leakage.
- `EXT` coarse/edge-targeted candidate sweep — локальная коррекция вместо глобального dense rowstep; проверка покрытия по corners/left/right/top/bottom отдельно, ограничения смещения и растровой неопределённости.

**Тестовый протокол для возобновления (до запуска зафиксировать новые versioned experiment IDs):** неизменные SHA frozen masks/планов и 3 формы; один и тот же brush/renderer profile; дополнительные representative image families из 81 после CORP-001 review (Stage8 mono и Stage6 color отдельно). Для каждого кандидата хранить PNG, coverage, leakage, boundary error zones, details, length, stroke count, width/color switches, runtime cost **отдельно** от measured CHALK. Продолжать только при исходных gates: FILL coverage ≥99%, leakage=0; использовать ±1 screen px/аналогичную чувствительность как риск-анализ, не как независимое доказательство игры.

**Зависимости и запреты:** сначала закрыть источник 11 actual leakage и 738 model-only discrepancies либо явно классифицировать причину; не принимать 45-cell FILL-001 matrix до **нового одиночного live preflight PASS**; сохранять Monitor/Bridge exact run identity и `CHALK=post.pointCount-pre.pointCount`; даже качественный offline Egret не считается E4. Не менять production estimator/executor/defaults и frozen evidence без новой независимой validation.

## Этап 2. Изучение фактического цветного execution pipeline

Отделить monochrome Stage8 scanlines от Stage6 color scanlines. Учитывать порядка 942206 source strokes, 395455 singletons и 916312 source color transitions на 81 изображении, но не приписывать эти числа одному рисунку и не превращать в CHALK. Проводить safety/overlap проверку перед попыткой сокращать цветовые переключения.

**Gate:** воспроизводимый сравнительный dataset, provenance и критерии качества, visual family independence отдельно.

## Этап 3. Оптимизация CHALK на основе уже выполненных опытов

Использовать измеренные G1–G3, V1–V5, D1–D5 и INT006R, не повторяя их без причины. При необходимости 95%-й policy заранее определить поддерживаемый domain и провести отдельную замороженную независимую validation (19/59 на профиль). Exact CHALK — только `post.pointCount-pre.pointCount`.

**Gate:** safety margin и применимость модели установлены для заявленного domain, а не для всех изображений по умолчанию.

## Этап 4. Интеграция resource preflight (INT-007)

Только после этапа 3 и других required quality gates: fail-closed UNKNOWN для неподдержанной геометрии, provenance модели, бюджетные предупреждения, regression, Windows startup и разрешённые live tests.

**Статус INT-007:** **BLOCKED**.

## Не смешивать уровни доказательств

CI/build, offline quality, real game `pointCount`, pixel equivalence и статистическая predictive coverage подтверждаются отдельно. История всех решений и неудач остаётся в [архиве дорожной карты](ROADMAP_HISTORY_THROUGH_2026-11-08.md) и специализированных отчётах.

## Совместимость старой ссылки на план калибровки

<a id="уточнённый-временный-план--автоматическое-определение-геометрии-доски-и-handoff-калибровки"></a>
Старый раздел перенесён в [полную дорожную карту до 2026-11-08](ROADMAP_HISTORY_THROUGH_2026-11-08.md#уточнённый-временный-план--автоматическое-определение-геометрии-доски-и-handoff-калибровки). Эта запись — навигация, а не возобновление закрытых задач.

## Новый приоритет — свежий FILL-001 Smooth A/B V2 вместо повторного анализа старых PNG

Согласно последнему заданию пользователя следующая экспериментальная серия использует `FILL001_SMOOTH_AB_V2`: два совершенно новых индивидуальных Monitor 0.2.4 прогона ON и OFF, один и тот же frozen logical rectangle и неизменный 27-штриховой план, но **новая run-bound экранная проекция `FILL001_SCREEN_MASK_V2`** для диагностики. Подмена целевой логической маски экранной проекцией запрещена. До ручного запуска требуются successful software/regression CI на актуальном коде, чистая доска, fresh Bridge/session/run и подтверждённая screen geometry; если доказательства невалидны, тест fail-closed. Только после двух новых E4 → независимое сравнение V2 и при необходимости native Egret E5. Предыдущий A/B V1 — историческая методика, её результаты нельзя переносить в V2. [Инструкция §13](GAME_MONITOR_BRIDGE_REFERENCE.md#13-fill-001--новая-чистая-smooth-ab-v2-под-screen-mask-v2).

## Следующий FILL-001 gate — V3 BoardPane-corrected pilot

После независимого spatial V2 и точного воспроизведения неверного ROI→Egret roundtrip введена изолированная новая серия `FILL001_SMOOTH_AB_V3` с обязательной свежей `FILL001_BOARDPANE_PREFLIGHT_V1` привязкой. Дальше после successful CI — **один новый реальный Smooth OFF** (clean board, confirmed brush lineWidth=10, full 27 strokes), затем оценить фактический первый accepted Y, границы новой V2 projected mask, coverage≥99% и leakage=0, exact CHALK и native footprint. Второй V3 ON — только отдельно после успешного preflight/анализа OFF, без смешения экспериментальных версий. Если критерии не пройдены, raw + ошибки сохранять, качество не объявлять исправленным. См. [Game Monitor §14](GAME_MONITOR_BRIDGE_REFERENCE.md#14-fill-001--отдельный-boardpane-anchored-smooth-ab-v3-исследовательский-пилот).
