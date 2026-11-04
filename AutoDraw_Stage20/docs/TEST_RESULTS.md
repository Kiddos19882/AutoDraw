# TEST_RESULTS — единый реестр результатов тестирования AutoDraw

**Статус:** действующий сводный реестр результатов и доказательств  
**Дата формирования:** 2026-11-04  
**Рабочая ветка:** `feature/image-geometry-optimization`  
**HEAD перед дополнением D1–D5:** `63fdaf3f2a1b12bd90e1a588ca4e968facbe0103`  
**Область:** AutoDraw_Stage20, тесты приложения, лабораторные эксперименты, Game Monitor/Bridge, CHALK, FILL-001, геометрические модели, GitHub Actions и offline benchmarks.

> Этот файл — единая точка входа для понимания результатов тестирования. Здесь собраны проверяемые сводные результаты, статусы, ограничения и ссылки на первичные отчёты/артефакты. Первичные JSON, PNG, логи, frozen plans, manifests и подробные отчёты не удаляются и не переписываются: они остаются источниками доказательств. Если краткая сводка расходится с первичным отчётом, приоритет имеет первичный материал и фактический runtime/CI evidence.

## 1. Правила чтения и доказательности

### 1.1. Статусы

- **PASS** — конкретная проверка завершилась успешно по указанному критерию.
- **FAIL** — конкретный gate/тест не прошёл; это не означает, что весь проект неисправен.
- **CANCELLED** — запуск отменён; не приравнивать к FAIL или PASS.
- **SKIPPED** — проверка не запускалась в данном workflow/run.
- **BLOCKED** — выполнение запрещено/заблокировано незакрытым gate.
- **PENDING / UNKNOWN** — данных недостаточно для подтверждения.
- **HISTORICAL** — результат относится к более ранней версии/сценарию и не подтверждает текущее состояние.

### 1.2. Разделение уровней

| Уровень | Что подтверждает | Чего не подтверждает |
|---|---|---|
| Unit / regression tests | Проверяемые программные контракты и сценарии | Поведение игры, renderer, фактический CHALK |
| Integration / UI tests | Интеграционные связи, импорты, передачу данных, тестируемые UI contracts | Полную ручную работоспособность UI и рисование в игре |
| Build / startup smoke-test | Сборку и отсутствие немедленного сбоя старта | Корректность интерактивного UI и качество рисунка |
| GitHub Actions | Результат конкретных jobs на конкретном commit | Runtime вне тестовой среды, если он отдельно не проверялся |
| Offline benchmark | Сравнение реализаций на указанных fixtures и среде | Универсальный speedup, CHALK и эквивалентность игровому renderer |
| Live game experiment | Поведение игры в конкретном запуске при наличии пригодных captures | Автоматически — обобщение на все геометрии/параметры |
| Visual / PNG audit | Качество конкретных сохранённых изображений по указанным критериям | Точный CHALK без pointCount и неиспытанные сценарии |

### 1.3. Точный расход CHALK

Для игрового движка точный расход — только:

`CHALK = pointCount_after - pointCount_before`

Не использовать длину траектории, число штрихов, площадь, радиус кисти или оценку индикатора краски как точное измерение CHALK. Per-stroke значения должны быть связаны с конкретным run и его исходным/конечным pointCount. При исчерпании квоты до завершения рисунка фиксировать censored/неполный запуск; полная стоимость рисунка неизвестна.

### 1.4. Текущая граница инвентаризации

GitHub tree на HEAD `0a5fa41c` содержит 5 413 файлов; 5 011 файлов находятся под `AutoDraw_Stage20/data/results/`. Это инвентаризация файлов по дереву Git, а не утверждение, что каждый артефакт был независимо открыт и повторно проанализирован при создании этого реестра. Массовые первичные данные перечислены по семействам/каталогам; отдельные файлы не дублируются в Markdown.

Локальный `git status` через GitHub API недоступен. Данный документ отражает GitHub branch snapshot, а не локальную рабочую копию.

## 1.5. Egret WebGL renderer reference — mask/scrollRect correction (2026-11-04)

**Commit:** `5308fade07fbb11409a9afc5c3d40ed4cf82ca3a`  
**CI:** [41924481247](https://github.com/Kiddos19882/AutoDraw/actions/runs/41924481247) — SUCCESS.  
**Browser job:** `126905145909` — SUCCESS.  
**Artifact:** [13368272823](https://github.com/Kiddos19882/AutoDraw/actions/runs/41924481247/artifacts/13368272823), manifest + 54 PNG.

Причина прежних крупных `mask-corner` расхождений найдена в harness: mask object не был прикреплён к Egret Stage. В Egret 5.4.1 объектная маска переводит masked display object в renderMode=3 только если `mask.$stage` установлен. Harness теперь создаёт Stage и помещает board + mask в общую display-list сцену; assertions проверяют stage attachment, одинаковые stage/parent и boardRenderMode=3.

| Fixture | Width | Differing pixels | Max channel delta |
|---|---:|---:|---:|
| smooth-single-point | 10 / 30 | 0 / 0 | 0 / 0 |
| scrollrect-edges | 10 / 30 | 0 / 0 | 0 / 0 |
| mask-corner | 10 | 145 | 1 |
| mask-corner | 30 | 36 | 1 |
| Остальные fixtures (12 comparisons) | 10 / 30 | differing pixels присутствуют во всех 12 comparisons | 1 |

Итого: 18/18 WebGL comparisons созданы; 4 exact, 14 имеют max channel delta=1, ни одного delta выше 1. Для сравнения, до stage-binding correction mask-corner имел 193/84 differing pixels и max delta=255. Среда: Egret 5.4.1, Edge 156, WebGL 1 / ANGLE SwiftShader, rasterScale=3, board output 1380×720. Это E3 browser/CI evidence для offline renderer harness, не E4 live game capture.

**Ограничения:** residual delta=1 не классифицирован как дефект; exact popup transform и paired live board PNG + accepted points + pointCount из одной сессии не получены. CHALK и production footprint модель этим тестом не измерялись. FILL-001-RS 45-task matrix остаётся BLOCKED.

## 2. Сводный статус ключевых исследовательских серий

| Серия | Область | Подтверждённый итог | Текущий статус / ограничения |
|---|---|---|---|
| Brush behavior / первичные измерения | Горизонтальные/диагональные линии, короткие штрихи, повороты, контуры, пересечения, границы доски | Сохранены многочисленные планы, Game Monitor runs, JSON и PNG; агрегаты отдельных серий приведены в профильных отчётах | Не сводить все runs в один средний показатель: сценарии, радиусы и sampling configs различаются |
| CHALK radius matrix | Сравнение радиусов кисти | 21 live experiment, 7 радиусов, 3 независимых повтора/блока; средние расходы по радиусам около 724–727 CHALK, индивидуальные 722–728 | В этом сценарии систематическая зависимость pointCount от радиуса не обнаружена; не универсальный закон |
| CHALK G1 geometry matrix | Геометрия при контролируемых параметрах | 12 live runs; точные per-stroke CHALK зафиксированы в первичном отчёте | Отмечена проблема repeat metadata; учитывать ограничения отчёта |
| CHALK G2 geometry matrix | Дополнительная геометрическая серия | Отдельный results report существует | Подробные численные выводы брать из первичного отчёта; не объединять с G1 без проверки совместимости протоколов |
| CHALK G3 sampling matrix | Длинные горизонтальные линии, sampling step/delay | 27/27 completed, 0 failed, 0 pending; точный CHALK подтверждён для всех captures | Radius=10 и одна геометрия; перенос коэффициентов на произвольный рисунок не доказан |
| INT-006 V1–V5 | Независимая validation геометрии и CHALK | 45/45 accepted captures в основной серии; follow-up V1–V5 — ещё 45/45 captures | Принимать выводы только в границах frozen scenarios, профилей и критериев |
| INT-006 official validation | Проверка прогнозной модели на независимых captures | Официальный отчёт указывает 45/45 accepted | MAE/RMSE/bias, safety margin и production eligibility смотреть в отчёте; 45/45 accepted не означает автоматически production-ready |
| INT006R | Радиус × геометрия, D1–D5 × radius 1/10/30 | 45/45 completed; raw-data audit PASS; официальный analyzer PASS (45 accepted); ручной аудит 90 PNG завершён | CHALK-эффект радиуса мал в этой матрице; визуальные ограничения D2/radius=1 и D4/radius=30; см. подробную матрицу ниже |
| FILL-001 initial live preflight | Реальная заливка с радиусом 10 | Один run завершил 27 strokes; pointCount 1→6000, exact CHALK=5999, квота исчерпана до трёх последних consuming strokes | Неполный/censored run; полная стоимость завершённого рисунка неизвестна; 45-cell matrix заблокирована |
| FILL-001-RS live preflight | Versioned scanline spacing candidate | Run 27/27 strokes, pointCount 1→1261, exact CHALK=1260; Bridge diagnostics без потерь/ошибок | Capture REJECTED PNG gate: после исправленного audit coverage=98.430600%, leakage=11; требования coverage≥99% и leakage=0 не выполнены; 45-task matrix BLOCKED |
| FILL-001-RS static sweep | Offline OpenCV scanline spacing | Exhaustive sweep 2 238 candidates; 62 прошли существующий статический gate; выбраны 15/15 shape/radius cells | Только offline geometry proxy; не подтверждает фактический CHALK или renderer |
| Capsule footprint geometry | Offline ideal capsule rasterization | Independent oracle: 7 parametrized edge cases + 16 seeded polylines; masks совпали | Модель не подтверждена против deployed Egret renderer |
| Capsule broad-phase benchmark | Global-AABB vs per-segment candidate enumeration | 5 synthetic polylines; masks совпали во всех 5 сценариях | Скорость зависит от геометрии; benchmark не измеряет CHALK и не доказывает renderer equivalence |

## 3. Детальные результаты CHALK

### 3.1. G3 — sampling step и delay

Первичный источник: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md). В сценарии шесть горизонтальных линий по 400 logical px (суммарно 2400 logical px), radius=10, 3 повтора для каждой из 9 комбинаций `point_step_px` 1/2/4 и `point_delay_ms` 5/10/20.

| Step | Delay | CHALK repeats | Среднее CHALK | Средняя длительность |
|---:|---:|---:|---:|---:|
| 1 | 5 ms | 1359 / 1350 / 1344 | 1351.0 | 53.36 s |
| 1 | 10 ms | 1350 / 1360 / 1341 | 1350.3 | 53.38 s |
| 1 | 20 ms | 2087 / 2084 / 2038 | 2069.7 | 100.61 s |
| 2 | 5 ms | 717 / 717 / 716 | 716.7 | 29.76 s |
| 2 | 10 ms | 719 / 716 / 719 | 718.0 | 29.78 s |
| 2 | 20 ms | 1384 / 1381 / 1384 | 1383.0 | 53.40 s |
| 4 | 5 ms | 365 / 366 / 366 | 365.7 | 17.99 s |
| 4 | 10 ms | 363 / 366 / 366 | 365.0 | 18.04 s |
| 4 | 20 ms | 715 / 710 / 716 | 713.7 | 29.85 s |

- Для этой геометрии step=4 / delay=5 или 10 дал около 365 CHALK; визуальный аудит всех шести PNG показал непрерывные ровные линии.
- Delay=20 существенно увеличил расход для всех трёх шагов.
- Step=4 — кандидат для длинных прямых линий данного сценария, не универсальный production default.
- В G3 radius зафиксирован на 10; влияние радиуса исследовалось отдельной серией.
- Paint-meter image estimate не использовался как точный источник; exact game pointCount — источник расхода.
- В отчёте зафиксированы ограничения coalescing: промежуточные координаты не восстанавливаются полностью.

### 3.2. Radius matrix

Первичный источник: [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md).

- 21 experiment, 7 радиусов, 3 независимых блока.
- Средние CHALK по радиусам находятся примерно в диапазоне 724–727; индивидуальные результаты 722–728.
- В рамках данного сценария систематической зависимости игрового pointCount от радиуса не обнаружено.
- Это не доказывает, что радиус не влияет на качество, покрытие, ширину следа или число проходов. Он не должен вводиться в формулу CHALK как прямой множитель без дополнительных измерений.

### 3.3. G1 / G2 geometry matrices

- [G1 results](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md): 12 live runs, точные per-stroke значения; отчёт отмечает repeat metadata issue.
- [G2 results](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md): отдельная геометрическая серия; не объединять статистику с G1 без проверки условий, repeats и протокола.
- Общие выводы по коротким штрихам, диагоналям, поворотам, контурам и пересечениям брать из соответствующих первичных серий INT-006/INT006R и brush run JSON.

### 3.4. INT-006 V1–V5

- [Основная live-матрица](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md): 45/45 captures, exact/per-stroke CHALK, sampling profiles, первичная holdout-проверка модели и quality gates.
- [Follow-up V1–V5](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md): 45/45 дополнительных captures после исправления геометрии/сценариев; raw repeat CHALK, P0/P1/P2 и pixel-level gates.
- [Official independent validation](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md): официальный analyzer report, 45/45 accepted; метрики ошибки и safety-margin ограничения — в первичном документе.
- [PNG screening](CHALK_INT006_PNG_SCREENING_2026-11-02.md) и [pixel audit](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md) фиксируют визуальную/пиксельную сторону проверки отдельно от CHALK.

### 3.5. INT006R radius × geometry

Первичные источники: [live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md), [software gate](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md), [visual audit](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md).

- 45 captures по D1–D5 и радиусам 1/10/30.
- Exact CHALK и raw-data integrity проверялись отдельно от визуального качества.
- Отдельно задокументированы ограничения D2/radius=1 и D4/radius=30.
- Полнота captures не заменяет visual-quality gate.

### 3.6. INT006R — подробная матрица D1–D5 × радиус кисти

**Серия:** `chalk-20261103-030837-a20df5`  
**Block ID:** `a8e0b9ec87984f60aa294910d366e987`  
**Последний commit с live-данными:** [138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a](https://github.com/Kiddos19882/AutoDraw/commit/138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a)  
**Профиль:** P1 — `point_step_px=4`, `point_delay_ms=5`  
**Матрица:** 5 геометрий × 3 радиуса (1/10/30) × 3 повтора = 45 captures.

| ID | Геометрия | Radius 1: CHALK mean | Radius 10: CHALK mean | Radius 30: CHALK mean | Визуальный результат |
|---|---|---:|---:|---:|---|
| D1 | Mixed lines | 62.67 | 62.33 | 63.33 | Все четыре штриха видимы на всех радиусах; непредусмотренного слияния/потерь не найдено |
| D2 | Polygon | 71.67 | 71.00 | 71.00 | Radius 1: небольшой разрыв верхнего левого соединения первой и пятой сторон во всех 3 повторах; radius 10/30: контур замкнут |
| D3 | Intersections | 100.00 | 100.67 | 99.67 | Все 6 штрихов и ожидаемые пересечения видимы; пересечения соответствуют DrawingPlan |
| D4 | Short details | 14.33 | 14.67 | 15.33 | Radius 1: детали различимы, но очень тонкие; radius 10: все 6 разделены; radius 30: первые 3 детали (1/2/3 logical px) сливаются, остаётся 4 компонента |
| D5 | Repeated coverage | 88.33 | 89.67 | 89.67 | Повторные проходы совпадают с траекториями; ожидаемое наложение, посторонних следов нет |

Средние значения рассчитаны по трём повторам в каждой ячейке. Суммарный exact CHALK по 15 опытам каждого радиуса: radius 1 — 1011; radius 10 — 1015; radius 30 — 1017. Среднее на опыт: 67.40 / 67.67 / 67.80 соответственно. Разница между суммарными значениями крайних радиусов — 6 CHALK (около 0.6% от radius 1).

**Integrity / acceptance:**
- 45/45 задач имеют `status=completed`, по одной completed attempt на задачу.
- Во всех 45 Monitor reports `chalk.status=exact`; CHALK вычислен как `post.pointCount - pre.pointCount`.
- Сумма sampled `DRAW_SAMPLE.pointDelta` совпадает с exact CHALK; `point_delta_matches_chalk=true`.
- Observed radius совпал с requested radius (1/10/30).
- Dropped events, Monitor error delta, Bridge send-failure delta и collector sequence gaps — 0.
- Официальный CLI analyzer на реальном journal/capture bundle: [CI 41563236073](https://github.com/Kiddos19882/AutoDraw/actions/runs/41563236073), 45 accepted, 0 missing/rejected, PNG evidence complete.
- Ручной аудит всех 45 пар (90 PNG) завершён; все 45 пар присутствуют и читаемы, before ROI визуально пустые, after ROI содержат ожидаемую геометрию.

**Вывод по CHALK:** в рамках D1–D5, sampling P1 и радиусов 1–30 заметного преимущества большого радиуса по exact CHALK не обнаружено. Не вводить radius multiplier и не выбирать radius 30 ради предполагаемой экономии на основании этой серии.

**Вывод по качеству:** радиус влияет на визуальный результат в конкретных геометриях: radius 1 недостаточен для надёжного замыкания D2 при текущем P1; radius 30 сливает первые короткие элементы D4; radius 10 сохранил замыкание D2 и разделение деталей D4 в этой матрице. Это локальные наблюдения, не универсальное правило.

**Граница применимости:** D2 — геометрия полигона, а не полноценная заливка площади; D5 — повторное покрытие линий, а не заливка одноцветной области. INT006R не определяет лучший радиус для FILL. Для этого предназначен отдельный FILL-001.

Первичные документы:
- [INT006R live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md)
- [INT006R software gate](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md)
- [INT006R visual audit](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md)
- [INT006R live preflight and visual audit](CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md)
- [Radius × geometry cross-validation plan](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md)

## 4. FILL-001 и FILL-001-RS

### 4.1. FILL-001 quota-exhausted preflight

Источник: [CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md).

- Live preflight исчерпал лимит на 5999 CHALK до завершения трёх последних consuming strokes.
- Это censored run: наблюдаемый расход до остановки известен, но стоимость полного рисунка не измерена.
- Нельзя использовать 5999 как расход полного завершённого рисунка.
- 45-task matrix не открывается до успешного отдельного preflight gate.

### 4.2. FILL-001-RS rejected capture

Источники: [replay report](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md), [static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md), [postmortem](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md).

- Runtime binding подтверждён для single-task run; 27/27 strokes, pointCount 1→1261, exact CHALK=1260.
- Bridge diagnostics: 0 sequence gaps, 0 dropped events, 0 Monitor errors, 0 send failures.
- Первоначальный PNG audit: coverage=97.673218%, leakage=28.
- После исправления affine mapping и повторного audit исходной PNG пары: coverage=98.430600%, leakage=11.
- Улучшение audit не закрывает gate: acceptance требует coverage≥99% и leakage=0. Capture остаётся REJECTED.
- Exact CHALK=1260 относится только к данному run и не заменяет PNG quality gate.
- 45-task RS matrix остаётся BLOCKED.

### 4.3. Static sweep

- Проверено 2 238 сочетаний spacing/offset.
- 62 кандидата прошли существующие статические условия.
- Выбраны 15 конфигураций для 15/15 shape/radius cells.
- Использованы OpenCV coverage/leakage и estimated sampling points/path/strokes.
- Это статические proxy; они не являются точным CHALK и не доказывают поведение игрового renderer.

## 5. Brush behavior lab и первичные данные

### 5.1. Назначение каталога

Основной каталог: `AutoDraw_Stage20/data/results/brush_behavior_tests/`.

Содержит семейства планов и результатов по:
- горизонтальным и диагональным длинам;
- коротким и длинным изолированным линиям;
- непрерывным поворотам и замкнутым контурам;
- пересечениям и spacing;
- границам доски;
- потреблению краски на длинных линиях;
- INT-006 V1–V5 и follow-up;
- INT006R D1–D5 × radius 1/10/30;
- Game Monitor raw run JSON, per-stroke/experiment summaries, before/after PNG и auxiliary audit files.

Первичные файлы не следует редактировать при последующей аналитике. Для численных выводов использовать соответствующий сводный отчёт и связанные raw artifacts.

### 5.2. Существующие агрегаты

- [BRUSH_TEST_RESULTS_ANALYSIS_2026-10-30.md](../BRUSH_TEST_RESULTS_ANALYSIS_2026-10-30.md) — исторический анализ ранних brush tests.
- [ANALYSIS_RESULTS_2026-10-29.md](../data/results/brush_behavior_tests/ANALYSIS_RESULTS_2026-10-29.md) и [ANALYSIS_AUDIT_2026-10-29.md](../data/results/brush_behavior_tests/ANALYSIS_AUDIT_2026-10-29.md) — ранние сводка и аудит; считать историческими относительно более поздних INT-006/G3/INT006R серий.
- [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md) и [BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md](../BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md) — архитектура лаборатории/автосбора, не результаты фактического запуска.

### 5.3. Историческая модель расхода

[AutoDraw_Stage20/TEST_RESULTS.txt](../TEST_RESULTS.txt) — устаревшая сводка на 27 октября 2026, commit `6068366b`, CI run [40547157885](https://github.com/Kiddos19882/AutoDraw/actions/runs/40547157885). Она фиксировала ранние тестовые количества и эмпирическую модель «эффективная длина пути + 6,67 × число штрихов», основанную на четырёх наблюдениях. Это исторический baseline, не текущая точная модель CHALK. Не использовать эти коэффициенты как подтверждённую игровую формулу: дальнейшие live серии показали зависимость от sampling step/delay и необходимость калибровки по точному pointCount.

## 6. Capsule footprint geometry и benchmark

### 6.1. Геометрическая модель

Код: `source/preparation/brush_footprint_geometry.py`.  
Тест: `source/preparation/tests/test_capsule_footprint_masks.py`.

- Модель строит potential/guaranteed pixel-cell masks для swept capsule polyline.
- Добавлен independent full-canvas oracle, использующий собственные orientation tests и point-segment distance, а не production helpers.
- Проверены 7 parametrized edge cases и 16 seeded polylines.
- В тестовых случаях masks совпали.
- Это независимая программная геометрическая проверка, не эталон игрового renderer.

### 6.2. Per-segment broad-phase benchmark

Скрипт: `tests/benchmark_capsule_rasterization.py`.  
Workflow: `.github/workflows/geometry-tests.yml`.  
CI artifact: `autodraw-capsule-broad-phase-benchmark`, artifact ID `13338434277`.  
Final CI: [41859709320](https://github.com/Kiddos19882/AutoDraw/actions/runs/41859709320), commit `af30b5fdf1c926d3493bff90706806f5d3a28c43`.

| Synthetic scenario | Candidate slots reduction | Geometry predicate calls reduction | Median speedup |
|---|---:|---:|---:|
| Winding polyline | 91.09% | 89.30% | 10.91× |
| Large zigzag | 96.23% | 94.08% | 20.57× |
| Diagonal turns | 59.53% | 58.95% | 2.76× |
| Compact many-segment | 92.24% | 92.09% | 14.10× |
| Single long segment | 0% | 0% | 1.16× |

Во всех пяти случаях masks совпали. Время измерено на Windows GitHub runner, 7 repeats, synthetic inputs. Speedup не переносить на другие среды/геометрии как гарантию. Это offline rasterization benchmark, не CHALK measurement, не runtime benchmark игры и не renderer-equivalence test.

### 6.3. Benchmark history

- CI [41857043512](https://github.com/Kiddos19882/AutoDraw/actions/runs/41857043512): выявил ModuleNotFoundError из-за module path; benchmark не принят как финальный.
- CI [41858081222](https://github.com/Kiddos19882/AutoDraw/actions/runs/41858081222): workflow прошёл, но review artifact выявил неполный reference counter для вложенных predicate calls; эти счётчики не использовались для финального сравнения.
- Исправленный подсчёт вложенных вызовов: commit `af30b5f`; финальный benchmark artifact `13338434277` использует симметричную instrumentation обоих вариантов.

## 7. Автоматические тесты и GitHub Actions

### 7.1. CI workflow

Основной workflow: [geometry-tests.yml](../../.github/workflows/geometry-tests.yml).  
Подробная карта test modules, commands, jobs и artifact flow: [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md).

Workflow включает:
- Game Monitor/Bridge tests и WebSocket smoke;
- Preparation pytest;
- capsule broad-phase benchmark;
- FILL-001-RS static sweep;
- Application integration tests;
- Executor unittest discovery;
- INT-006 PNG/pixel analysis;
- Windows portable build и startup smoke-test;
- optional algorithm benchmarks (по умолчанию SKIPPED, запускаются отдельно через workflow_dispatch).

### 7.2. Важные CI runs

| Run | Commit / lineage | Статус | Результат и оговорки |
|---|---|---|---|
| [40547157885](https://github.com/Kiddos19882/AutoDraw/actions/runs/40547157885) | `6068366b` | PASS, historical | Ранние test counts и Windows build/startup smoke-test; см. старый `TEST_RESULTS.txt` |
| [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) | `974f949` lineage | PASS | Все 6 обязательных jobs SUCCESS; run предшествует последующим affine correction commits и не валидирует их |
| [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384) | pre-fix FILL-001-RS | FAIL | Preparation/G3: 799 passed, 5 failed; synthetic PNG fixtures/ROI test issues; остальные перечисленные jobs успешны, PNG audit/build skipped |
| [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) | `0f23731` | CI PASS / PNG gate FAIL | Regression tests и replay выполнены; corrected audit coverage=98.430600%, leakage=11; capture не принят |
| [41840281018](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840281018) | telemetry lineage | CANCELLED | Не приравнивать к FAIL или PASS; отдельные успешные jobs не заменяют полный CI |
| [41840582147](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840582147) | telemetry lineage | PASS | Обязательные jobs SUCCESS, optional algorithm benchmarks SKIPPED |
| [41842587672](https://github.com/Kiddos19882/AutoDraw/actions/runs/41842587672) | capsule candidate | PASS | 820 passed, 24 warnings, 82 subtests; более поздние oracle/benchmark refinements этим run не покрываются |
| [41848358502](https://github.com/Kiddos19882/AutoDraw/actions/runs/41848358502) | segmented capsule | PASS | Эквивалентность capsule rasterization на первоначальном наборе тестов |
| [41849580047](https://github.com/Kiddos19882/AutoDraw/actions/runs/41849580047) | independent oracle | PASS | Независимый oracle добавлен и проверен |
| [41859709320](https://github.com/Kiddos19882/AutoDraw/actions/runs/41859709320) | `af30b5f` | PASS | Preparation/G3 832 passed, 24 warnings, 82 subtests; Game Monitor/Bridge, Executor, Application integration, INT-006 PNG audit, Windows portable build/startup smoke-test SUCCESS; optional algorithm benchmarks SKIPPED. Capsule benchmark artifact опубликован отдельно |

**Важно:** PASS workflow означает успешное выполнение перечисленных jobs. Если внутри job отдельный evidence gate (например PNG acceptance) завершился FAIL, это должно быть явно указано; CI PASS не превращает rejected capture в accepted.

### 7.3. Что не запускалось в обязательном CI

- Длительный Stage 5/7/8 algorithm benchmark job по умолчанию SKIPPED.
- Live game drawing не выполняется GitHub Actions и не подтверждается успешной сборкой.
- Capsule benchmark — отдельный offline script/job step, не путать с optional algorithm-benchmarks job.
- Отсутствие PR-triggered workflow run в connector result не доказывает отсутствие push-triggered run.

## 8. Известные FAIL / BLOCKED / ограничения

| Объект | Статус | Причина / следующий gate |
|---|---|---|
| FILL-001 initial full fill | BLOCKED | Quota exhausted at 5999 before final 3 strokes; full-drawing CHALK unknown |
| FILL-001-RS capture | REJECTED | Coverage 98.430600% < 99%; leakage 11 > 0 |
| FILL-001-RS 45-task matrix | BLOCKED | Не пройден single-task live preflight; не запускать |
| Deployed Egret renderer identity/transform | UNKNOWN | Требуется подтвердить deployed runtime/version, global transform, screen/canvas mapping |
| Capsule model vs real renderer | NOT VALIDATED | Offline masks/oracle не являются renderer reference |
| Capsule planner integration | NOT RUN | Требует отдельного offline renderer acceptance и разрешения |
| Universal sampling/CHALK model | NOT ESTABLISHED | Различия геометрии, sampling, delays и повторного покрытия требуют независимой валидации |
| Production CHALK estimator/defaults | NOT APPROVED | Не делать выводов из одной серии; safety margin/eligibility задаются профильными validation reports |
| Local working tree status | UNAVAILABLE | GitHub API не предоставляет локальный `git status` |

## 9. Индекс первичных отчётов

### CHALK / brush
- [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md)
- [CHALK_G3_PARTIAL_RESULTS_2026-11-02.md](CHALK_G3_PARTIAL_RESULTS_2026-11-02.md)
- [CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md](CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md)
- [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md)
- [CHALK_GEOMETRY_MATRIX_G1_RESULTS.md](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md)
- [CHALK_GEOMETRY_MATRIX_G2_RESULTS.md](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md)
- [CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md](CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md)
- [CHALK_INT006_V1_V5_RESULTS_2026-11-02.md](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md)
- [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md)
- [CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md)
- [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md)
- [CHALK_INT006_PIXEL_AUDIT_2026-11-02.md](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md)
- [CHALK_INT006R_LIVE_RESULTS_2026-11-03.md](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md)
- [CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md)
- [CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md)

### FILL-001
- [CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md)
- [CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md)
- [CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md)
- [CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md)

### Architecture / tests / automation
- [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md)
- [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md)
- [BRUSH_MODULE_QUICK_INDEX.md](BRUSH_MODULE_QUICK_INDEX.md)
- [GAME_MONITOR_BRIDGE_REFERENCE.md](GAME_MONITOR_BRIDGE_REFERENCE.md)
- [CHALK_TEST_BLOCKS_DESIGN.md](CHALK_TEST_BLOCKS_DESIGN.md)
- [CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md)
- [CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md)

## 10. Правило обновления реестра

После каждого значимого теста/эксперимента/CI:
1. Сначала сохранить первичные данные и неизменяемые идентификаторы: experiment ID, block ID, run ID, commit SHA, workflow run, artifact ID, plan/mask hashes.
2. Обновить соответствующий первичный отчёт; не подменять raw evidence агрегатом.
3. Добавить или обновить запись в этом `TEST_RESULTS.md`: цель, условия, версия/commit, статус, фактический результат, критерии, ссылки на raw evidence, ограничения и следующий gate.
4. В `PROJECT_STATUS.md`, `TASKS.md`, `ROADMAP.md`, `WORK_LOG.md` и `CHANGELOG.md` оставлять короткий статус и ссылку на этот реестр вместо копирования численных результатов.
5. Сохранять FAIL, CANCELLED, SKIPPED и BLOCKED наряду с PASS.
6. Не менять frozen criteria, thresholds, masks, plans или defaults после просмотра результата без отдельного решения и новой версии эксперимента.

**Этот реестр не заменяет первичные отчёты и данные. Он является единой точкой навигации, сводки и актуального статуса результатов тестирования.**

## 2026-11-04 — Game Monitor runtime renderer diagnostics

**Commit:** `b2d467de6d7fb247d9014e47b1b58da782ff6d68`

- `node --check AutoDraw_Stage20/source/game_monitor/game_monitor.js` — PASS.
- `node --test AutoDraw_Stage20/source/game_monitor/tests/game_monitor.test.js` — PASS, 18/18 tests, включая runtime renderer snapshot, stage/client corner mapping и graceful no-runtime case.
- Локальный WebSocket smoke server test — PASS.
- GitHub Actions run [41896024383](https://github.com/Kiddos19882/AutoDraw/actions/runs/41896024383): Game Monitor and bridge tests — SUCCESS; Executor regression tests — SUCCESS; Application integration tests — SUCCESS; Preparation/G3 matrix tests — SUCCESS (включая capsule broad-phase benchmark и FILL-001-RS static sweep); Windows portable build/startup smoke-test — SUCCESS; INT-006 pixel-level PNG geometry audit, independent CHALK validation и INT006R validation — SUCCESS; optional algorithm benchmarks — SKIPPED. Полный workflow run завершился SUCCESS.
- Это программные проверки mock/runtime diagnostics, не live browser evidence. Реальный renderMode, screen transform, brush footprint и pixel equivalence ещё не получены.