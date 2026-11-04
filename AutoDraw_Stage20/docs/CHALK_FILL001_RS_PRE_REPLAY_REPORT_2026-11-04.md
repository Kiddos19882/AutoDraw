# FILL-001-RS — отчёт повторного аудита исходного live preflight

**Дата:** 2026-11-04  
**Задача:** `FILL-001-RS-PRE-REPLAY-001`  
**Статус результата:** REJECTED — replay выполнен, PNG quality gate повторно не пройден  
**Ветка:** `feature/image-geometry-optimization`

## 1. Область и способ проверки

Повторно проверена исходная пара PNG и связанное evidence запуска `fill001-rs-preflight-20261104-7.04`. Использован committed replay test `test_chalk_fill_committed_capture_replay.py`, который вызывает реальный `Fill001Tab.finalize_capture()` и передаёт в него исходные manifest, attempt, executor report, runtime DrawingPlan, Bridge session/run records, legacy session и before/after PNG.

Тест копирует исходные файлы в изолированный `tmp_path` и переписывает только абсолютные локальные пути в копиях metadata. Содержимое PNG и экспериментальные значения не заменяются synthetic fixtures. Исходные файлы в репозитории не изменялись.

- Evidence commit: [`5308214`](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288).
- PNG audit implementation: [`4797aa5`](https://github.com/Kiddos19882/AutoDraw/commit/4797aa5e2e3d9f78656c91dcddf285304eae55c1).
- Replay test: [`974f949`](https://github.com/Kiddos19882/AutoDraw/commit/974f949e9639acc90e7f4d6f4588c3fb96f9abb2).
- Test fixture alignment: [`1f28436`](https://github.com/Kiddos19882/AutoDraw/commit/1f28436ab20fe949e4d53cfeea4a5560ed3cbcae), [`0f23731`](https://github.com/Kiddos19882/AutoDraw/commit/0f23731848f0c148fe5e1309d1e305576dd4b6b7).
- Подтверждающий CI: [run 41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017), checkout HEAD `0f23731848f0c148fe5e1309d1e305576dd4b6b7`.
- В checkout использовался `chalk_fill_capture_adapter.py`, Git blob SHA `0d7fdcf75db841f09e29900fd35af01b371f239a`; replay test blob SHA `88e349efc6a637f4286c766433d53481fdc127b9`.

В логе шага Preparation/G3 зафиксирован фактический вывод теста:

```text
FILL-001 committed PNG audit: coverage=98.430600%, leakage=11, status=failed
```

В этом же job завершился весь набор: **804 passed, 24 warnings, 82 subtests passed**. Остальные обязательные jobs run 41780241017 также завершились SUCCESS; optional benchmarks были SKIPPED. CI успешен как программная проверка: тест корректно подтвердил отказ PNG gate. Это **не** означает принятие capture.

## 2. Связь evidence и фактическое исполнение

| Поле | Подтверждённое значение |
|---|---|
| Series | `fill001-rs-preflight-20261104-7.04` |
| Task | `fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1` |
| Session ID | `bb261898-8296-41f5-a333-eb0b81016410` |
| Выбранный Monitor run ID | `6a17a297-ea14-4527-9527-bfd8de3bd335` |
| Форма / радиус | rectangle / 10 |
| Planner | version 2, `scanline_row_step=5`, `scanline_offset=0` |
| Plan signature | `a0e422160f222276baafea73aa884e3407255d7b3da5ab47778a4d70f434e417` |
| Ожидаемые / выполненные штрихи | 27 / 27 |
| Sampling | P1, `point_step_px=4`, `point_delay_ms=5` |
| Screen ROI | x=566, y=253, width=581, height=304 |
| Exact pointCount | 1 → 1261 |
| Exact CHALK | 1260 |
| Observed brush radius | 10 |

Выбранный run `6a17a297-ea14-4527-9527-bfd8de3bd335` связан с executor task. Более ранняя запись в той же Bridge session, run `9ea6d0bb-6786-4315-91d7-0b4dcdfef394`, была подготовительной: 0 consuming strokes и CHALK=0; она не подменяет run исполнения.

Для выбранного run Game Monitor подтвердил: 27 stroke candidates / 27 consuming strokes, 0 non-consuming candidates, `sampled_point_delta_total=1260`, сумма sample deltas совпадает с exact CHALK. Dropped events=0, Monitor errors=0, Bridge send failures=0, sequence gaps=0. Session report содержит ту же исходную и конечную пару pointCount.

Исходный executor report фиксирует completed 27/27 strokes, 2 637 move calls, длительность 50.531 s и конфигурацию step=4/delay=5. В исходном report runtime binding ещё имел статус `not_ready`; replay через `finalize_capture()` повторно выполнил discovery и тест подтвердил `runtime_binding_status=passed`, правильный run ID и exact CHALK=1260. Canonical plan hash `848b6875e34bad388a48706346a9939cdf508200edf2536d8da99121a5d8b6b9` совпадает с `executor_plan_sha256` в committed runtime plan; task plan signature также совпадает.

## 3. Результат PNG audit

| Метрика | Предыдущий audit до affine correction | Replay с исправленным transform | Критерий |
|---|---:|---:|---:|
| Coverage | 97.673218% | **98.430600%** | ≥99% |
| Leakage | 28 px | **11 px** | 0 |
| Статус | failed | **failed** | passed |

Исправление affine mapping улучшило результат на 0.757382 процентного пункта и уменьшило leakage на 17 пикселей. Однако текущий capture всё ещё не проходит оба неизменённых условия: coverage ниже 99%, leakage не равен нулю.

Исправленный audit использует согласованное с executor преобразование screen ROI и inverse nearest-neighbor rasterization. Порог изменения RGB остаётся 8. ROI PNG — 581×304, frozen logical board — 460×240.

**Решение:** capture остаётся REJECTED/PENDING. Capture JSON не принимается, 45-task matrix остаётся BLOCKED. Exact CHALK=1260 является достоверным измерением этого исполнения, но не отменяет PNG quality gate.

## 4. SHA-256 исходных файлов

Хэши вычислены для исходных файлов evidence commit `530821497ce3a6bd5152318a78e1f06cb836f288`; для PNG — по исходным бинарным байтам, для JSON — по UTF-8 содержимому. Исходные файлы не изменялись.

| Исходный файл | SHA-256 |
|---|---|
| `fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1-before.png` | `ce5560ef85b8c63b2e2fc93056eae685bb0c6f8146f106c843daad7f97577576` |
| `fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1-after.png` | `a001c62264dac32c2331179ba6a4e39c609aaaf8749381cc6a967803dd338321` |
| `attempts/...-rep1.json` | `79a42cf03756ea6f52b4327fc43d9338abc4ea7f004289d206f3455fd89b134b` |
| `fill001_rs/fill001-rs-preflight-20261104-7.04.json` | `3224fe751ca260e682c741b528f6ebccd934d05b2926d22235007488cacd33eb` |
| `execution_20261104_070545_500355_cf845f.json` | `8e5c8b059674dac9a5c8b00d1f117acd98eb2726d8bc8d56ed45779710c96745` |
| `fill001/plans/...-rep1.json` | `430b79ad350b3ffd70183ca3da29c99b36f54d70079e482d6e553313c9355108` |
| `runtime/current_brush_behavior_test.json` (repository bytes) | `31ca4c81d3dc8524ee98dcd584473f62060c131c65c23dad8bfd684115aac321` |

В executor report записан runtime `source_plan_file_sha256=644cbf85a44481a5ecbe0fb2d88383dd1b13835c443dc240c0aa5700b4a8565f`. Он отличается от SHA-256 committed runtime plan bytes в таблице, но при пересчёте того же текста с Windows CRLF line endings получается **точное совпадение** с runtime hash. Следовательно, расхождение объясняется нормализацией LF/CRLF при помещении файла в Git, а не отличием содержимого плана. Canonical `source_plan_sha256`/executor plan hash и task signature также совпадают. Replay validator действительно проверяет формат source file hash, но не пересчитывает его по relocated copy; независимое сравнение LF и CRLF представлений закрывает это ограничение для данного evidence.
| `game_monitor_bridge/.../session.json` | `2e521c711c2d6c768a77ef84a9f01228c6cdf9af9ff52de0e54b03aa12962fe9` |
| `game-monitor-run-...-9ea6d0bb.json` (подготовительный run) | `8bcf8943cc37a50f0f3b0064878089fab8380ca182d392e4fa8333be61f39a56` |
| `game-monitor-run-...-6a17a297.json` (run исполнения) | `0453db0e230d07702aef61e0e7945c64e845b68b47b3ee0dd33cf252f04e10f6` |
| `3323cf8e-01ca-4009-8f16-27d657d857f8/session.json` (legacy session, проверялась discovery) | `aefb1968626d6b5d741ca7b77f72be14f899571d39e4bc6cdda092870023270a` |

## 5. Что установлено и что остаётся неизвестным

**Установлено:**
- исходные PNG и связанные JSON evidence доступны и используются replay test;
- task/session/run binding проходит, выбран правильный run;
- exact CHALK и per-sample delta согласованы;
- affine mismatch старого audit был реальным дефектом и его исправление улучшило метрики;
- исправленный audit всё ещё обнаруживает 11 пикселей вне frozen mask и неполное покрытие.

**Не установлено:** конкретная причина оставшихся 1.569400% недопокрытия и 11 leakage pixels. Текущая replay-метрика не позволяет однозначно выбрать между различием footprint/cap игрового renderer и офлайн-модели, дискретизацией/округлением координат, особенностями границы ROI или взаимодействием этих факторов. Это гипотезы, а не подтверждённые причины.

Byte-level различие runtime plan hash объяснено и подтверждено: SHA-256 committed LF bytes — `31ca4c81d3dc8524ee98dcd584473f62060c131c65c23dad8bfd684115aac321`; SHA-256 того же содержимого с CRLF — `644cbf85a44481a5ecbe0fb2d88383dd1b13835c443dc240c0aa5700b4a8565f`, что точно совпадает с executor report. Это line-ending normalization, не содержательное расхождение.

## 6. Следующий шаг

Продолжить только offline-анализ той же пары PNG: получить координатную карту uncovered target pixels и leakage pixels, разложить их по границам/штрихам и сопоставить с frozen mask, executor plan и screen transform. Сохранить диагностические overlays и численные breakdown. Не менять пороги, frozen mask, исходный plan или production defaults.

До локализации остаточного несоответствия:
- не запускать новый live preflight;
- не запускать 45-task matrix;
- не менять production-код и конфигурации;
- не объявлять capture принятым.

Replay выполнен; блокировка следующего запуска остаётся активной.

## 7. Визуальное наблюдение и уточнение диагностической гипотезы

## Дополнение — краевые промежутки и будущая контурная обводка (2026-11-04)

При просмотре исходного `after.png` отмечен округлый профиль боковых краёв заливки. Пользовательская гипотеза: между круглыми окончаниями соседних scanline-проходов остаются незаполненные промежутки. В предпоследнем тесте, по наблюдению пользователя, следующая линия начиналась ниже и такого эффекта не было. Это направление offline-проверки, а не установленная причина.

Проверить на неизменённых исходных данных:
1. Разложить uncovered target pixels по боковым краям, верхней/нижней границам, углам и внутренней области.
2. Сопоставить пропуски с координатами начала/конца линий, вертикальным шагом и фактической rasterized footprint/cap кисти.
3. Отдельно локализовать 11 leakage pixels.
4. Сопоставить с предпоследним тестом по первичным PNG/plan evidence, если они доступны.
5. Не менять frozen masks, thresholds, исходный plan или production defaults.

**Будущий кандидат:** после основной заливки выполнить одну непрерывную обводку контура, правильно сместив центральную линию внутрь области с учётом фактического renderer footprint, чтобы край кисти закрывал границу без выхода наружу. Это не реализовано и не подтверждено. До рассмотрения нужны offline geometry/raster validation, затем отдельное разрешение на live проверку; критерии — coverage≥99%, leakage=0 и exact CHALK по `pointCount_after - pointCount_before`. Длина контура и proxy points не заменяют измерение расхода.

## 8. Offline edge breakdown planner model и exploratory contour pass (2026-11-04)

### 8.1 Воспроизведение текущей planner raster model

По frozen mask `rectangle` (SHA-256 `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b`) и committed plan `fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1` воспроизведены 27 scanline centerlines с `y=55..185`, шагом 5. Target area — 44 653 logical pixels. Использована та же концепция OpenCV round-capped line model, что описана в `chalk_fill_fixed_radius_planner.py`.

В этой **planner model** осталось 304 uncovered target pixels (0.680805%):

| Область logical mask | Uncovered pixels |
|---|---:|
| Верхняя полоса, y=50..74 | 80 |
| Нижняя полоса, y=166..190 | 80 |
| Левая боковая полоса, y=75..165 и x≤94 | 72 |
| Правая боковая полоса, y=75..165 и x≥366 | 72 |
| Внутренняя область, y=75..165 и 95≤x≤365 | 0 |
| **Всего** | **304** |

Модельный leakage — 0. Это согласуется с гипотезой о краевой концентрации недопокрытия и подтверждает, что центральная часть в planner raster model закрыта. Однако это **не actual PNG pixel breakdown**: исходный corrected audit по фактическому `after.png` остаётся coverage=98.430600%, leakage=11. Координаты actual uncovered target pixels и 11 leakage pixels ещё не получены, поэтому фактическую причину нельзя считать установленной.

### 8.2 Exploratory contour-pass sweep

После неизменённого набора 27 scanlines смоделирован один замкнутый contour pass. Контур получался из той же frozen mask после erosion эллиптическим ядром с inward offset; затем он rasterized одной замкнутой линией шириной 10 px в OpenCV model.

| Inward offset | Coverage | Leakage | Uncovered | Offline gate |
|---:|---:|---:|---:|---|
| 5 px | 99.964168% | 32 | 16 | FAIL |
| 6 px | 99.516270% | 0 | 216 | PASS |
| 7 px | 99.372942% | 0 | 280 | PASS |
| 8 px | 99.328153% | 0 | 300 | PASS |

Для offset 6 один замкнутый contour содержит 64 вершины и имеет длину приблизительно 846.225 logical px в этой OpenCV approximation. Эта длина не является CHALK estimate. Результат показывает потенциальную геометрическую возможность закрыть краевой дефицит одной обводкой с корректным inward offset, но offset 5/6 резко меняет leakage; следовательно, подбор смещения должен быть привязан к фактическому footprint игрового renderer.

### 8.3 Статус и ограничения

- Edge concentration: подтверждена для воспроизведённой planner raster model; для actual PNG residuals — не подтверждена (E0).
- Contour pass: exploratory offline candidate, не реализован, не включён в frozen plan и не live-validated.
- Corrected actual PNG gate остаётся failed: coverage=98.430600%, leakage=11; capture REJECTED.
- Runtime binding и exact CHALK=1260 остаются подтверждёнными независимо от PNG quality gate.
- Не изменялись исходники, тесты, конфигурации, frozen mask/plan, acceptance thresholds и production defaults; live experiments не запускались.

**Следующий обязательный шаг:** получить координаты actual uncovered target pixels и 11 leakage pixels из неизменённых PNG, сопоставить с screen-transformed centerlines/renderer footprint, и только после этого продолжить contour candidate offline. Новый live preflight и 45-task matrix остаются заблокированными.
## Actual PNG residual diagnostic result — CI 41787492122

Committed-evidence replay diagnostic executed successfully in Preparation/G3 (804 passed, 82 subtests passed). Corrected audit still rejects capture: coverage=98.430600%, leakage=11.

Actual PNG pixel map:
- 1116 uncovered target pixels;
- top=244, bottom=239, left-middle=134, right-middle=499, interior/other=0;
- largest component area=870, bbox screen xywh=[460,63,33,178], right perimeter;
- additional components: area 142 bbox [88,90,2,122]; area 54 bbox [101,233,13,7]; area 41 bbox [101,64,13,6]; remaining components 6,1,1,1 pixels;
- nearest scanline centerline distances: <=2px=10, 2–5px=320, 5–10px=786, >10px=0;
- leakage coordinates xy: [116,63], [117,63], [92,78], [91,81], [90,83], [90,84], [89,85], [90,85], [90,218], [116,240], [117,240].

Pixel evidence confirms uncovered pixels confined to configured perimeter zones. Right perimeter is the largest failure region; leakage is sparse near opposite perimeter and rounded corners. This is consistent with endpoint/perimeter footprint mismatch, but does not establish game brush effective radius, cap geometry, or units. Actual engine rendering path and executor sampling must be inspected before selecting endpoint extension or contour offset.

Do not compare 1116 screen pixels directly with 304 logical pixels from planner OpenCV simulation. Capture remains rejected and 45-task matrix blocked. No live experiment or production change.
