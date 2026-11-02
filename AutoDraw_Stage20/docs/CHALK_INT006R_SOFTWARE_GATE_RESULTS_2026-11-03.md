# INT006R — результаты программного gate

**Дата:** 2026-11-03  
**Статус:** SOFTWARE GATE PASS  
**CI run:** [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975)  
**Проверенный code HEAD:** `28b56a97255b57b50072ba973533ce349c706bd1`  
**Рабочая ветка:** `feature/image-geometry-optimization`

## 1. Итог

Полный GitHub Actions workflow завершился `SUCCESS`. Реализация INT006R прошла regression suites, integration, Game Monitor/Bridge, pixel-level PNG audit существующих INT-006 captures и Windows portable build/startup smoke-test.

Это подтверждает программную готовность отдельной фазы INT006R. Это не подтверждает влияние радиуса на фактический CHALK: live captures INT006R ещё не запускались.

## 2. Результаты jobs

| Job | Результат |
|---|---|
| Preparation and G3 matrix tests | SUCCESS — 682 passed, 24 warnings, 82 subtests passed |
| Application integration tests | SUCCESS |
| Executor regression tests | SUCCESS |
| Game Monitor and bridge tests | SUCCESS |
| INT-006 pixel-level PNG geometry audit | SUCCESS |
| Windows portable build and startup smoke-test | SUCCESS |
| Optional algorithm benchmarks | SKIPPED (optional) |

## 3. Новые regression gates

- INT006R matrix metadata принимает только integer radius 1/10/30 и строго P1 (step=4, delay=5 ms).
- Block planner создаёт 45 уникальных ячеек D1–D5 × radius 1/10/30 × repeat 1/2/3.
- Journal validator отклоняет tampered radius, duplicate cells, неверный profile, неправильный task identity и frozen prediction artifact.
- Executor handoff сверяет radius metadata с requested brush и отвергает bool/float, unsupported radius, mismatched brush и profile P0.
- Независимый analyzer проверяет completed journal attempts, experiment/run binding, exact CHALK и per-stroke DRAW_SAMPLE pointDelta.
- Analyzer требует читаемые before/after board ROI PNG одинакового размера. Его положительный synthetic test подтвердил `status=complete` для корректного комплекта 45 captures.
- `visual_quality_gate` остаётся `pending_manual_review`: наличие корректных PNG не заменяет просмотр всех 45 пар изображений.

## 4. Ограничения результата

- INT006R live block: NOT RUN.
- Accepted live captures: 0/45.
- Radius × geometry effect: UNKNOWN.
- Visual quality gate: PENDING.
- Safety margin: NOT ESTABLISHED.
- Production eligibility: NOT VALIDATED.
- Frozen INT-006 model/artifact, production estimator, executor defaults и sampling defaults не изменялись.
- `master` не изменялся.

## 5. Следующий gate

1. Получить portable build из artifact текущего CI.
2. Выполнить локальный Windows preflight по [live preflight and visual audit guide](CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md).
3. Проверить Game Monitor heartbeat, exact pointCount, calibration slider 1–30 и blank-board reference.
4. Только после этого выполнить отдельный INT006R block на 45 captures.
5. Запустить независимый analyzer и отдельно завершить визуальный аудит before/after PNG.

**Вывод:** программная реализация INT006R прошла полный CI. Следующий шаг — локальный live preflight и контролируемый эксперимент; production integration не разрешена автоматически.
