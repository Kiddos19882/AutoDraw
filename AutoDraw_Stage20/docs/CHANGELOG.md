# AutoDraw — значимые изменения

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
