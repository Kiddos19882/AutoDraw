# Документация AutoDraw — быстрый вход

**Рабочая ветка:** `feature/image-geometry-optimization`. **Актуальный evidence baseline ENGINE-001:** `177165361b0340515fe3bb74f4847ab3ec579ebc` (9/9 live E4, E5 PARTIAL; см. §21). Исторический baseline прежней системы документации — `a2d1f0a52d47`. Текущий remote HEAD проверять заново в каждом чате. Это вход в существующую систему документации, а не отдельный источник статуса. Полная предыдущая редакция индекса сохранена [здесь](README_HISTORY_THROUGH_2026-11-08.md).

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

