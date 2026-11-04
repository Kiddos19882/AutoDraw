# Документация AutoDraw

**Статус:** основной индекс документации  
**Продукт:** AutoDraw 1.8.3  
**Корень приложения:** AutoDraw_Stage20/

Каталог содержит структурную документацию, файлы управления проектом и специализированные протоколы/отчёты CHALK. Структурные справочники описывают состав репозитория, компоненты, конфигурацию, данные, интерфейсы и сборку. Экспериментальные документы отдельно фиксируют методики и результаты измерений; их выводы ограничены указанными сценариями и не подменяют текущий статус проекта.

**Текущая точка продолжения:** статусы и gates определяются только [PROJECT_STATUS.md](PROJECT_STATUS.md), [TASKS.md](TASKS.md) и [ROADMAP.md](ROADMAP.md). Исторические планы и отчёты сохраняются для доказательной цепочки; отметка HISTORICAL/SUPERSEDED означает, что их старые TODO не являются текущим backlog.

> **Приоритетный ориентир для ИИ — FILL-001-RS:** при периметр-доминантных пропусках сначала рассматривать offline-кандидат «редкая внутренняя заливка + один связный обход контура + локальные внутренние коррекции», а не глобальное уплотнение горизонтальных проходов. Это гипотеза, не доказанный выигрыш CHALK. [Обязательный вывод и критерии сравнения в TASKS.md](TASKS.md#ключевой-технический-вывод-для-fill-001-rs--связный-контур-вместо-глобального-уплотнения-scanline). ИИ должен прочитать его до продолжения FILL-001-RS.

## Система управления знаниями для ИИ

Эти документы образуют постоянный регламент работы с проектом. Их следует читать в начале каждой новой задачи; они не привязаны к текущему этапу разработки.

- [AI_WORK_GUIDE.md](AI_WORK_GUIDE.md) — обязательный порядок начала, выполнения, проверки и передачи работы ИИ.
- [KNOWLEDGE_ARCHITECTURE.md](KNOWLEDGE_ARCHITECTURE.md) — роли документов, источники истины, жизненный цикл и синхронизация знаний.
- [EVIDENCE_AND_VALIDATION.md](EVIDENCE_AND_VALIDATION.md) — уровни доказательности для кода, тестов, CI, runtime и экспериментов.
- [ENGINEERING_INVARIANTS.md](ENGINEERING_INVARIANTS.md) — реестр критических свойств и правила их проверки.
- [EXPERIMENT_STANDARD.md](EXPERIMENT_STANDARD.md) — единая методика проектирования, проведения и анализа экспериментов.

Постоянная система не дублирует текущий статус, roadmap или результаты исследований. Пересматривать её следует только при изменении постоянных правил проекта.

## Измерения CHALK

- [Итоговые результаты G3 — матрица расхода CHALK](CHALK_G3_RESULTS_2026-11-02.md) — 27/27 принятых captures, девять конфигураций sampling, влияние шага/задержки и ограничения модели.
- [Предварительная сегментированная модель CHALK](CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md) — G1/G2/G3/radius matrix; раздельные оценки прямых, коротких штрихов, sampling и повторного покрытия; не production-модель.
- [Визуальный аудит G3 step=4](CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md) — просмотр всех шести PNG для delay=5/10; длинные горизонтальные линии визуально непрерывны, универсальный default не утверждён.
- [Результаты матрицы расхода CHALK по радиусам кисти](CHALK_RADIUS_MATRIX_RESULTS.md) — 21 эксперимент, семь радиусов, три независимых блока.
- [Результаты G1 матрицы CHALK по геометрии](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md) — 12 live-прогонов, точные per-stroke значения и обнаруженная проблема repeat metadata.
- [План измерения CHALK по геометрии и режиму ввода](../CHALK_GEOMETRY_MATRIX_PLAN.md) — следующие серии G1–G3, 57 экспериментов с последовательными gates.
- [Архитектура автоматических блоков CHALK](CHALK_TEST_BLOCKS_DESIGN.md) — пакетный запуск всех сценариев и повторов, критерии принятия, журналирование и восстановление.

- [INT-006 — официальная независимая validation CHALK](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md) — 45/45 accepted, метрики ошибки модели, ограничения и статус safety margin.
- [INT006R — live validation радиуса и геометрии](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md) — 45 captures, точный CHALK и сравнение радиусов 1/10/30.
- [INT006R — ручной визуальный аудит](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md) — просмотр 45 пар PNG и выявленные ограничения коротких деталей/контуров.
- [FILL-001 — план эффективности заливки](CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md) — три формы областей, пять радиусов, 45 captures.
- [FILL-001 — технический дизайн harness](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md) — fixed-radius planner, frozen masks, 45-cell matrix, capture validation, отдельный UI/runner и analyzer.
- [FILL-001 — разбор пользовательского Windows live preflight](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md) — история двух live attempts; полный run-level/per-stroke CHALK=5999, quota exhaustion на трёх последних strokes, rejected capture и открытый quantitative PNG audit.
- [FILL-001-RS — replay исходного live preflight](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) — исходные PNG/evidence, runtime binding, corrected PNG audit (coverage=98.430600%, leakage=11), SHA-256 входов и незакрытая диагностика остаточного расхождения.
- [FILL-001 — временный план дальнейших работ и этап FILL-001-RS](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md) — software/runtime gates, quota-exhausted preflight, отдельное исследование расстояния между scanline-проходами, versioned candidate и live preflight gate; исходные frozen plans и 45-cell matrix сохраняются.
- [FILL-001-RS — результаты статического sweep scanline spacing](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md) — exhaustive 2 238 candidates, 15 frozen shape/radius cells, выбранные spacing configs, OpenCV metrics и ограничения до live validation.
- [FILL-001 — аудит интеграции AutoDraw](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md) — исторический снимок до появления отдельной вкладки и UI/runner handoff.
- [FILL-001 matrix/analyzer](../source/preparation/chalk_fill_matrix.py) — экспериментальный manifest schema v2, frozen P1 metadata и fail-closed validation 45 captures.
- [FILL-001 Game Monitor capture adapter](../source/preparation/chalk_fill_capture_adapter.py) — сборка capture из Monitor events, exact per-stroke CHALK и PNG evidence audit; software regression gate подтверждён CI, live evidence pending.


## Действующий план CHALK и история статуса

- [План дальнейших действий по модели CHALK](CHALK_NEXT_STEPS_PLAN_2026-11-02.md) — исторический план раннего этапа; текущие задачи и gates определяются `ROADMAP.md` и FILL-001 plan/design.
- [INT-006 — план независимой validation CHALK](CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md) — новые DrawingPlan, замороженные прогнозы P0/P1/P2, повторения, критерии приёмки и расчёт ошибок.
- [INT-006 — предварительные результаты D1–D5](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md) — предварительный разбор 45 live captures, точные CHALK delta, run-level/per-stroke метрики и оставшиеся gates.
- [INT-006 — аудит готовности harness](CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md) — подтверждённые пробелы D1–D5 в matrix/block/UI/executor/analyzer и gates до live validation.
- [INT-006 — протокол выполнения](CHALK_INT006_EXECUTION_PROTOCOL_2026-11-02.md) — профили P0/P1/P2, сценарии V1–V5, acceptance gates, независимая validation и аудит готовности лаборатории.
- [INT-006 — отдельные live follow-up серии V1/V3/V4](CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md) — повторные captures исправленной геометрии, cursor-free closure validation и 9 captures на фазу.
- [INT-006 — отдельные live follow-up серии V2/V5](CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md) — координаты новых сценариев, 9 captures на серию, критерии приёмки и инструкция ручного live-прогона.
- [INT-006 — результаты live-матрицы V1–V5](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md) — 45/45 captures, exact/per-stroke CHALK, сравнение sampling profiles, первичная holdout-проверка модели и открытые quality gates.
- [INT-006 — результаты follow-up V1–V5](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md) — 45/45 новых captures после исправления геометрии/сценариев, raw repeat CHALK, сравнение P0/P1/P2 и следующие pixel-level/validation gates.
- [INT006R — live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md) — 45 captures D1–D5 × radius 1/10/30, exact CHALK и raw-data integrity audit; ручной visual audit завершён; ограничения D2/radius=1 и D4/radius=30 зафиксированы в отдельном отчёте.
- [Игровой движок — стоимость точки, ширина кисти и source trace](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) — точный CHALK counter, статическая трассировка и runtime renderer evidence (разделы 14–15); pixel equivalence ещё не подтверждена.
- [Runtime renderer snapshot 2026-11-04](../data/runtime/renderer_snapshot_2026-11-04.json) — пользовательский JSON, подтверждающий WebGL backend, stage/canvas scale и BoardPane transform для одной игровой сессии.
- [Исторический снимок PROJECT_STATUS](PROJECT_STATUS_HISTORY_2026-11-02.md) — полный статус до консолидации 2 ноября; только для аудита, не текущий backlog.

## Данные и очистка

- [Инвентаризация данных и кандидаты на безопасную очистку](DATA_CLEANUP_INVENTORY_2026-11-01.md) — назначение накопленных результатов, что можно удалить условно, что требует миграции/архивации и какие первичные данные сохранять.

## Инвентаризация и обслуживание документации

- [Инвентаризация документации](DOCUMENTATION_INVENTORY_2026-11-03.md) — 72 Markdown-файла, классификация действующих и архивных материалов, выявленные несогласованности и правила сохранения/удаления.

## Файлы игрового движка

Копия игровых assets находится в `AutoDraw_Stage20/gameEngine/` (п):

- [main.min_653f95bc.js](../gameEngine/main.min_653f95bc.js) (ф) — основной игровой bundle;
- [mergeEngine_df2e5bc5.js](../gameEngine/mergeEngine_df2e5bc5.js) (ф) — bundle движка;
- [manifest.json](../gameEngine/manifest.json) (ф) — манифест, перечисляющий runtime paths `js/mergeEngine_df2e5bc5.js` и `js/main.min_653f95bc.js`.

Файлы добавлены в commit [d3322fe](https://github.com/Kiddos19882/AutoDraw/commit/d3322fe35c808bde079c79545cc839636b7cda2a) ветки `feature/image-geometry-optimization`. В репозитории они физически лежат непосредственно в `gameEngine/`, а не во вложенном `gameEngine/js/`.

Пользователь подтвердил, что все три файла скачаны непосредственно с сайта запущенной игры в один момент; достоверность происхождения по его подтверждению — 100%. Рассматривать их как единый набор. Сверка с `master/fileGameEngine/main.min_570122a1.js` не требуется. Статический разбор `mergeEngine_df2e5bc5.js` показывает `egret.Capabilities.engineVersion="5.4.1"`; детали и ограничения приведены в [анализе стоимости точки и ширины кисти](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md).

## Справочники подсистем

- [Game Monitor и Bridge — техническая справка](GAME_MONITOR_BRIDGE_REFERENCE.md) — фактический API Game Monitor 0.2.1, Browser Bridge, WebSocket collector, методы RunRecorder, протокол сообщений, JSON-схемы и ограничения интерпретации.

## Навигация

| Документ | Назначение |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Общая структура приложения, подсистемы и связи |
| [COMPONENT_CATALOG.md](COMPONENT_CATALOG.md) | Каталог исходных модулей, тестов, утилит и CI |
| [MODULE_REFERENCE.md](MODULE_REFERENCE.md) | Структурный справочник модулей preparation, executor и Game Monitor |
| [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md) | Справочник интерфейсов модулей preparation |
| [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) | Справочник интерфейсов Stage 1–6, MouseExecutor, цветного исполнения и моделей |
| [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) | Карта прямых импортов production-модулей и общих адаптеров |
| [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md) | Тестовые наборы, диагностические скрипты, benchmark и GitHub Actions |
| [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) | Карта девяти вкладок (FILL-001 — № 8, калибровка — № 9), callback-связей и передачи данных в executor |
| [DATA_FORMATS_AND_MODELS.md](DATA_FORMATS_AND_MODELS.md) | Общие модели DrawingPlan, Stroke, Point и формат .autodraw |
| [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md) | Профили, палитры, планы, лабораторные и калибровочные результаты, экспорт Game Monitor |
| [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md) | Целевая архитектура автоматизированной лаборатории кистей, CHALK-экспериментов и сбора данных |
| [BRUSH_MODULE_QUICK_INDEX.md](BRUSH_MODULE_QUICK_INDEX.md) | Быстрый поиск по документации и исходникам для реализации модуля автоматических тестов кистей |
| [CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md) | Frozen predictions, 45-cell journal и независимый analyzer INT-006 |
| [CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md) | Официальный analyzer report: 45/45 accepted, метрики по профилям и geometry, safety-margin ограничения |
| [CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md) | План и текущий статус реализации INT006R: D1–D5 × radius 1/10/30 × 3 повтора при P1 |
| [CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md](CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md) | Windows preflight, запуск 45 captures, CLI analyzer и отдельный визуальный audit gate |
| [CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md) | Полный CI PASS INT006R: 682 tests, integration, bridge, PNG audit и Windows portable build |
| [chalk_int006r_validation.py](../source/preparation/chalk_int006r_validation.py) | Независимый analyzer INT006R: exact CHALK, journal binding и статистика по геометрии/радиусу |
| [CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md) | Локальная проверка portable-сборки на Windows 10 перед live validation |
| [FILE_STORAGE_CATALOG.md](FILE_STORAGE_CATALOG.md) | Каталог пользовательских файлов, runtime-планов, отчётов, проектов и экспериментальных данных |
| [CONFIGURATION_AND_DATA.md](CONFIGURATION_AND_DATA.md) | Каталоги данных, профили, форматы и переменные окружения |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Подготовка Windows-среды, запуск, тесты и сборка |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Текущее состояние проекта |
| [ROADMAP.md](ROADMAP.md) | План документирования и сопровождения |
| [TASKS.md](TASKS.md) | Реестр текущих задач |
| [DECISIONS.md](DECISIONS.md) | Журнал проектных решений |
| [WORK_LOG.md](WORK_LOG.md) | Журнал выполненных работ |
| [CHANGELOG.md](CHANGELOG.md) | История значимых изменений |

## Архивные и специализированные документы

- [README.md](../README.md) — точка входа приложения.
- [PROJECT_GUIDE.md](../PROJECT_GUIDE.md) — ранее созданный технический справочник; архивный, статусы устарели.
- [MASTER_ROADMAP.md](../MASTER_ROADMAP.md) — исторический план разработки; не использовать как действующий roadmap.
- [PROJECT_DOCUMENTATION.md](../PROJECT_DOCUMENTATION.md) — накопленная документация Stage20; архив, не расширять параллельно с docs.
- [PROJECT_ANALYSIS_PLAN_10_STAGES.md](../PROJECT_ANALYSIS_PLAN_10_STAGES.md) — архивный аналитический план; этапы 7–10 отменены.
- [source/game_monitor/README.md](../source/game_monitor/README.md) — документация Game Monitor.

## Приоритет источников

1. Фактическое содержимое файлов текущей ветки.
2. Конфигурационные файлы, манифесты и сценарии запуска.
3. Сигнатуры и docstrings исходников для справочника API.
4. Тестовые файлы как источник названий тестовых точек, не как подтверждение поведения.
5. Документация соответствующей версии исходников.
6. Исторические отчёты.

При расхождении описания с текущим деревом репозитория обновляется документация. Изменения кода в рамках документирования не допускаются.


## Единый реестр тестирования

[TEST_RESULTS.md](TEST_RESULTS.md) — центральная сводка результатов тестов и экспериментов.
