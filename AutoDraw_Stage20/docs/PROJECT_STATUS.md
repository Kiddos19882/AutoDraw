# AutoDraw — текущее состояние

**Дата сверки:** 2026-11-08. **Ветка:** `feature/image-geometry-optimization`. **Исходный HEAD проверки:** `a2d1f0a52d47`. **Последний проверенный code/test + workflow SHA:** `16f0e1b6cce0` (FILL-001 screen ROI diagnostics).

**Актуальный основной [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) — SUCCESS** на `16f0e1b`; 952 preparation tests PASS, INT-006 PNG audit и остальные обязательные jobs PASS, optional benchmarks/Windows portable build SKIPPED. Более ранние [full CI 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) и [81-image screening 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) были SUCCESS на `5a55e9f`. Проверка GitHub не равна локальному `git status`, Windows runtime или реальному игровому запуску.

> Полная прежняя редакция, включая все исторические факты, промежуточные статусы и ссылки: [PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md](PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md). Снимок сохранён без изменения исходных байтов.

## Текущий активный приоритет — ENGINE-001

На основании пользовательского задания 2026-11-08 прежние и новые FILL/GEOM/PRR оптимизационные эксперименты **отложены** (их подтверждённые PASS/FAIL/BLOCKED не изменены). Текущая задача — статический разбор сохранённого игрового движка с приоритетом интерактивной доски, `PainterPopup/BoardPane/BlackBoardAtom/Painter` и Egret рендеринга. [Техническая документация](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) — `ENGINE-001 PARTIAL`, `E1 PASS` для проверенных методов BoardPane/BlackBoardAtom/Painter/PainterPopup/Atom (§12) и сквозной цепочки input → Egret frame → Canvas/WebGL/mask/screen (§13). Полный `main.min` получен (4 859 418 байт, SHA совпадает); сверка с Monitor/PRR и snapshot выполнена в [§14](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#14-финальная-сверка-источников-game-monitorbridge-prr-и-runtime-2026-11-08); исправлена неверная атрибуция client corners в старом snapshot (там `boardClientCorners=null`). В [ENGINE-001 accepted-only offline replay](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) 27 штрихов/1260 точек воспроизведены через actual BoardPane: Canvas2D/WebGL итоговые RGBA **0 отличий** между one-pass и accepted-only incremental; [browser CI job 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) SUCCESS на `8d5d088`. Само архивное измерение CHALK=1260 неизменно. Это E2/E3, не полный E4 temporal trace и не FILL-001 pixel acceptance; эти gates остаются PARTIAL/NOT_RUN.

[Отложенные варианты A–D, E1–E4 и инструмент Egret](ROADMAP.md#отложенная-программа-тестов-fill-001-geom-001-и-связанных-gates). Работа текущего этапа не запускает gameplay, не меняет production и не меняет отвергнутый FILL-001 capture.

**Full validation CI [42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) — SUCCESS** на code/test SHA `8d5d0880c2027bf5c699608578d338025d64c595`: preparation 952 passed / 24 warnings / 82 subtests; Egret browser reference, Game Monitor/Bridge, executor, app integration и INT-006 PNG audit — SUCCESS; optional algorithm benchmarks и Windows portable build — SKIPPED. Это E3, не E4 gameplay.

## Работоспособность подсистем и доказательства

| Направление | Подтверждено | Не закрыто |
|---|---|---|
| AutoDraw 1.8.3 | Integrated UI, preparation, Stage6 executor; regression/CI | Новое live качество на произвольных рисунках не проверено |
| Game Monitor / Bridge | Привязка run/session, exact `pointCount`, per-stroke telemetry в экспериментальных сериях; [API](GAME_MONITOR_BRIDGE_REFERENCE.md) | Нет доступа к текущему runtime пользователя |
| G1/G2/G3 + radius matrix | Live 12/12 + 18/18 + 27/27 + 21/21; подтверждён эффект sampling в заданных условиях | Не универсальный прогноз CHALK |
| INT-006 | [D1–D5 45/45, quantitative PASS](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md); P1 — лучший исследованный профиль | `safety_margin_status=not_established`; `production_eligibility=not_validated` |
| INT006R | [45 exact captures](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md) и [визуальный аудит](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md) | Radius 1: разрыв D2; radius 30: слияние деталей D4; перенос на fills не подтверждён |
| PRR renderer | [6/6 PASS_PER_RUN, aggregate PASS](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) | Не универсальная pixel-equivalence каждого будущего рисунка |
| FILL-001-RS | [Exact CHALK 1260 на 27 штрихах](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md), runtime binding PASS | **PNG FAIL**: coverage=98.430600% при ≥99%, leakage=11px при 0 |
| FILL-001 A–D offline | [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS, 3 frozen masks × 4 strategies; [artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597) | Только OpenCV: actual PNG 98.430600%/11px остаётся FAIL; 81-image strategy comparison не выполнен |
| FILL-001 actual ROI counterfactual | [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS: 1116 actual screen misses / 11 actual leaks, 6 PNG, JSON; [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007) | Inset6 recovers 734 in modeled union, 382 remain, inherited 11 leaks. Baseline model underpredicts missing by 700px; game contour NOT validated |
| Корпус 81 изображения | 31+50 unique SHA, 81 моно+цветных планов; [screening E3](TEST_RESULTS.md) | Similarity review не доказывает semantic independence; scanline ≠ frozen D1–D5 domain |
| INT-007 | Требования к estimator документированы | **BLOCKED:** safety margin/domain/quality gates не закрыты |

## Непреложные факты

- Точный игровой **CHALK = post.pointCount − pre.pointCount**, при валидной привязке run. Длина пути, площадь и N штрихов не заменяют этого измерения.
- На исправленных V1–V5 переход `point_step_px=2→4` уменьшал расход на 38.5–49.4% **только в исследованных сценариях**; [источник](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md).
- 81 цветной scanline-план: 942206 исходных штрихов, 395455 одиночных пикселей и 916312 переключений между цветами. Это offline counters, **не** CHALK/runtime time.
- Имеющиеся измерения CHALK повторно собирать с нуля не требуется. Необходимы отдельные доменные и quality gates, если планируется новый универсализированный вывод.

## Завершённая проверка новой документации

[Markdown CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) **SUCCESS**: 99/99 Markdown в едином индексе, 0 broken links в анализируемом синтаксисе, 0 duplicate DEC IDs, 9 intact historical snapshots по SHA, 5 unit tests PASS. [Основной CI 42420934884](https://github.com/Kiddos19882/AutoDraw/actions/runs/42420934884) также **SUCCESS** на `c7f2e363`. Это проверки конкретных SHA, не новый live runtime. [Manifest сохранности](HISTORY_SNAPSHOT_PROVENANCE.json).

## Новый экспериментальный offline baseline A–D (2026-11-08)

Новый FILL-001 A–D offline [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123): SUCCESS на workflow SHA `6d790cd`. 3 frozen mask × 4 strategy, 15 диагностических PNG + JSON ([artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597)). Для варианта C coverage rectangle=99.516%, wide=99.593%, narrow=99.381%, leakage=0 в OpenCV. Эффект не подтверждён на реальном PNG. Вариант D использует oracle residual и создаёт слишком много дополнительных штрихов.

Исходные masks, план FILL-001 и live capture не менялись. Stage6, CHALK estimator и production defaults не затронуты. 12/12 raster PNG согласованы с JSON при независимом пересчёте. FILL-001 live capture по-прежнему REJECTED: CHALK=1260 exact, coverage=98.430600%, leakage=11. Сравнение actual ROI с контуром уже выполнено (см. ниже); следующая задача — калибровка реальной геометрии границ и исправление источника утечки, затем фиксированная подвыборка 81 изображения.

## FILL-001 screen-ROI counterfactual — проверено 2026-11-08

[CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS (`16f0e1b`), [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Actual ROI target 71110 screen px: 1116 uncovered, 11 leaked. Hypothetical contour inset6 recovers 734, leaves 382, would yield 99.462804% coverage with 0 NEW model leakage, but existing 11 leakage remain, so this is not a game PASS. Отступ 5 (1092 recovered) создаёт 60 новых modeled leaks; offset 7/8 восстанавливают 335/157 pixels и дают coverage <99%. При сдвиге modeled mask на 1 screen px offset6 может породить 89 новых leaks (dilation). В исходном baseline модель считает незакрашенными 416 screen pixels против 1116 actual; 738 pixels модель считала окрашенными, а actual change-mask — нет. Причина renderer/rounding/coordinate discrepancy не установлена.

Проверены SHA frozen PNG и LF-canonical JSON; архив ZIP SHA-256 `19313debbcc350f0eeda3edf2cba9e65350690a850d5bb2d9d733bb03794d620`, 6 diagnostic PNG+JSON cross-checked. [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) сначала FAILED (Windows CRLF JSON vs LF hash); нормализация только JSON исправлена и покрыта тестом, [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS. Исходный live PNG не перестал быть FAIL; exact CHALK для дополнительного контура отсутствует.

**Следующий gate:** E1/E2 уточнить фактическое смещение/footprint экранных концов 27 scanlines и 11 leakage pixels, особенно left/right border; разработать и проверить отдельную boundary-aware candidate geometry до любого нового live preflight или расширения на 81 изображение.

**Уточнение 2026-11-08, ENGINE-001/FILL-001:** из frozen plan и архивного Monitor run проверены 19 одинаковых по X горизонтальных линий. У всех первая/последняя принятая X одинаковы, но предпоследние X отличаются; `smooth(drawLast=false)` даёт три конечных midpoint (384.708/386.208/387.708), разброс 3 logical px. Это **подтверждённая причина геометрической вариации конечной точки path**, но не подтверждённая причина всех правых misses: с идеальным cap у 18/19 оценок правый край мог быть дальше OpenCV. Реальный per-stroke PNG, frame фазировка и same-run transform не проверены. [Подробности §16](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md).

## Ближайший приоритет

Поддерживать [действующие задачи](TASKS.md) и [очерёдность](ROADMAP.md); сначала сохранить целостность документации, затем оценивать алгоритмы на одинаковых рисунках и разбирать FILL-001 perimeter mismatch. 95% protocol — отдельная цель, не препятствие для начала офлайн-сравнения.

**Источники:** [TEST_RESULTS](TEST_RESULTS.md) · [DECISIONS](DECISIONS.md) · [первичная история](PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md).
