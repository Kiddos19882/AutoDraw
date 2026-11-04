# FILL-001-RS — статический sweep scanline spacing

**Статус:** ANALYZED — только OpenCV simulation; live validation NOT RUN  
**Experiment ID:** `FILL-001-RS-STATIC-SWEEP-V1`  
**Проверено:** 2026-11-04  
**Связи:** [временный план](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md), [harness design](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md), DEC-018.

## Методика

- Canvas 460×240; frozen shapes: rectangle, wide_irregular, narrow_irregular; radii: 1/5/10/20/30.
- Перебор: `scanline_row_step=1..radius`, `scanline_offset=0..step-1`.
- Всего 2 238 вариантов; 62 прошли gate.
- Неизменённый acceptance gate: coverage ≥99%, leakage=0.
- Выбор: максимальный прошедший row step; при равенстве — максимальное coverage, затем минимальные estimated points/path/strokes.
- Внутренний sampling не менялся: P1 `point_step_px=4`, `point_delay_ms=5`.

Frozen mask SHA-256 совпали с константами исходника:
- rectangle: `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b`
- wide_irregular: `ffff041d8fcaf53ce4f680ddbefb43a949dd72fdb10f44d6c95cf4832555d7db`
- narrow_irregular: `50d45794d9594b5b11f93ddfe407c47210eb315ae10f3d70e0b3978eff5764a3`

## Baseline reproduction

Rectangle/r10/step=1/offset=0 совпал с текущим frozen plan: 131 strokes, path 40 218 px, estimated points 10 237, coverage 100%, uncovered=0, leakage=0.

## Выбранные конфигурации 15 ячеек

| Shape | Radius | Step | Offset | Strokes | Path | Est. points | Coverage | Uncovered |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rectangle | 1 | 1 | 0 | 141 | 44 512 | 11 283 | 100,000% | 0 |
| rectangle | 5 | 2 | 1 | 68 | 21 096 | 5 368 | 99,682% | 142 |
| rectangle | 10 | 5 | 0 | 27 | 8 250 | 2 099 | 99,319% | 304 |
| rectangle | 20 | 8 | 4 | 16 | 4 736 | 1 200 | 99,180% | 366 |
| rectangle | 30 | 11 | 10 | 11 | 3 154 | 804 | 99,068% | 416 |
| wide_irregular | 1 | 1 | 0 | 151 | 45 008 | 11 468 | 100,000% | 0 |
| wide_irregular | 5 | 4 | 0 | 37 | 10 801 | 2 748 | 99,418% | 263 |
| wide_irregular | 10 | 7 | 1 | 21 | 6 030 | 1 535 | 99,041% | 433 |
| wide_irregular | 20 | 5 | 0 | 27 | 7 539 | 1 924 | 99,551% | 203 |
| wide_irregular | 30 | 10 | 0 | 13 | 3 498 | 891 | 99,136% | 390 |
| narrow_irregular | 1 | 1 | 0 | 221 | 44 658 | 11 471 | 100,000% | 0 |
| narrow_irregular | 5 | 3 | 1 | 72 | 14 139 | 3 631 | 99,133% | 389 |
| narrow_irregular | 10 | 5 | 0 | 43 | 8 245 | 2 120 | 99,173% | 371 |
| narrow_irregular | 20 | 5 | 0 | 41 | 7 474 | 1 925 | 99,385% | 276 |
| narrow_irregular | 30 | 5 | 0 | 39 | 6 724 | 1 731 | 99,285% | 321 |

## Общий кандидат r10 / step=5 / offset=0

| Shape | Strokes | Path | Est. points | Coverage | Uncovered | Leakage |
|---|---:|---:|---:|---:|---:|---:|
| rectangle | 27 | 8 250 | 2 099 | 99,319% | 304 | 0 |
| wide_irregular | 29 | 8 352 | 2 126 | 99,396% | 273 | 0 |
| narrow_irregular | 43 | 8 245 | 2 120 | 99,173% | 371 | 0 |

Для rectangle/r10 геометрические proxy-метрики снизились: strokes 131→27, path 40 218→8 250, estimated points 10 237→2 099 (около 79,5%). Это **не измерение экономии CHALK**.

## Реализация и ограничения

- Legacy planner без spacing-параметров сохраняет version 1 и прежнюю геометрию/signature.
- Новые планы получают отдельный `FILL001_RS_V1`, versioned plan signatures и spacing fields.
- RS manifest содержит 45 задач, но `execution_allowed=false`; запускать можно только одну выбранную задачу через существующий FILL-001 UI.
- Генератор manifest: `source/preparation/create_fill001_rs_manifest.py`; созданный файл открывается через «Открыть manifest…».
- CI воспроизводит полный sweep и сохраняет все 2 238 candidate records отдельным artifact.

OpenCV simulation не подтверждает поведение игрового renderer. Estimated sampling points/path/strokes не равны CHALK. Точный расход — только `pointCount_after - pointCount_before` в валидном live run. Предыдущие 5999 CHALK — расход до исчерпания квоты, не полная стоимость плана.

**Решение:** первый live preflight candidate — rectangle/r10/step=5/offset=0/P1(step=4, delay=5), 27 штрихов, coverage 99,319%, leakage=0 в симуляции. Это кандидат, не утверждённая настройка. До принятого live preflight FILL-001 45-cell matrix, INT-006 safety margin и INT-007 остаются BLOCKED.
