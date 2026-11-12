# AutoDraw — значимые изменения

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
