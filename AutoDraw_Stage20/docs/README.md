# Документация AutoDraw — быстрый вход

**Рабочая ветка:** `feature/image-geometry-optimization`. **Актуальный evidence baseline ENGINE-001:** `177165361b0340515fe3bb74f4847ab3ec579ebc` (9/9 live E4, E5 PARTIAL; см. §21). Исторический baseline прежней системы документации — `a2d1f0a52d47`. Текущий remote HEAD проверять заново в каждом чате. Это вход в существующую систему документации, а не отдельный источник статуса. Полная предыдущая редакция индекса сохранена [здесь](README_HISTORY_THROUGH_2026-11-08.md).

**Обязательное правило игровых кистей:** [GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md](GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md) — использовать реальный след BoardPane/Egret во всех brush-dependent тестах; модели не заменяют native quality.

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

