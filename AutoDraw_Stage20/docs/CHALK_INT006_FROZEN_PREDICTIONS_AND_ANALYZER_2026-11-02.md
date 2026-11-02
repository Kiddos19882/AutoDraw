# INT-006 — frozen predictions и независимый analyzer

**Model ID:** `chalk-int006-frozen-2026-11-02`, version 1; **radius:** 10; **phase:** `INT006`.  
**Software gate:** PASS — [CI run 41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663).  
**Live gate:** PASS — D1–D5 block 45/45 captures completed при radius=10. **Quantitative gate:** PENDING — требуется официальный запуск analyzer по полному набору.

## Frozen model

| Profile | point_step_px | point_delay_ms | intercept | slope |
|---|---:|---:|---:|---:|
| P0 | 2 | 10 | 1.765 | 0.2988 |
| P1 | 4 | 5 | 1.475 | 0.148865 |
| P2 | 4 | 10 | 1.440 | 0.149151 |

Для прямого штриха вне short lookup применяется (C=a+bL), где (L) — logical px. Для точных длин 1/2/3/5/8/10 используется lookup без интерполяции:

| L | P0 | P1 | P2 |
|---:|---:|---:|---:|
| 1 | 2.00 | 2.00 | 2.00 |
| 2 | 2.67 | 2.00 | 2.00 |
| 3 | 2.67 | 2.00 | 2.00 |
| 5 | 3.67 | 2.33 | 2.67 |
| 8 | 4.00 | 3.00 | 3.00 |
| 10 | 5.00 | 3.67 | 3.67 |

Неизвестная длина или неподдерживаемая геометрия не интерполируется автоматически. Кривые, заливки и классы вне D1–D5 остаются unsupported/UNKNOWN.

## Frozen artifact

`build_int006_prediction_artifact(series_id)` создаёт 15 записей: D1–D5 × P0/P1/P2. Каждая запись содержит model/version, profile, radius, geometry signature, полный DrawingPlan, stroke lengths/rules, per-stroke prediction и frozen total.

Artifact включается в INT006 block journal до первого live capture. SHA-256 вычисляется по канонической JSON-репрезентации. Каждая из 45 задач получает `prediction_id`; он записывается в `chalk_experiment_matrix` manifest metadata.

## Analyzer

Запуск из корня репозитория в PowerShell:

```powershell
$env:PYTHONPATH = "AutoDraw_Stage20\source\preparation"
python AutoDraw_Stage20\source\preparation\chalk_int006_validation.py --journal "<path-to-block-journal.json>" --results-dir "<path-to-brush_behavior_tests>" --output "<path-to-int006-analysis.json>"
```

Analyzer проверяет hash/содержимое artifact; 45 уникальных cells; series/phase/scenario/profile/repeat/order/task/block/experiment/run; completed accepted journal attempts; radius=10, executor parameters, prediction ID и geometry signature; exact pre/post CHALK, Monitor integrity и per-stroke breakdown. Считает residual = actual − predicted, MAE, RMSE, bias, MAPE, max absolute error, max underprediction, repeatability и per-stroke MAE/RMSE/bias.

Неполные, duplicate, unexpected, повреждённые или не связанные с journal captures отражаются в `rejected`/`missing_cells`. `status=complete` возможен только при 45 валидных captures без пропусков и rejected rows.

Положительный residual означает недооценку расхода. Максимальная наблюдённая недооценка — только provisional empirical guard выборки. Analyzer всегда выставляет `safety_margin_status=not_established` и `production_eligibility=not_validated`. Production estimator/defaults не менялись. Radius в INT-006 фиксирован; влияние размера кисти требует отдельного controlled experiment.


## Актуализация после live D1–D5 — 2026-11-03

- Block `chalk-20261102-232320-7cea27`: 45/45 tasks completed; одна завершённая попытка на каждую задачу.
- Все 45 experiment manifests и 45 `monitor_report.json` доступны в ветке. Предварительная проверка: exact CHALK, per-stroke delta sum, соответствие количества штрихов, нулевые dropped events/errors/Bridge failures/sequence gaps.
- Предварительные метрики сохранены в [CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md): 45 plan runs, MAE 1.408, RMSE 1.967, bias -0.875, MAPE 2.134%, max underprediction 1.82 CHALK. Per-stroke: 243 rows, MAE 0.439, RMSE 0.544.
- Analyzer изменён только в части journal experiment-directory binding: вместо сравнения абсолютных путей используется уникальное имя каталога эксперимента, чтобы Windows captures можно было проверять после переноса в CI workspace. Добавлен regression test.
- Workflow `.github/workflows/geometry-tests.yml` теперь запускает этот analyzer и сохраняет JSON report как artifact.
- **Официальная quantitative validation пока не закрыта:** требуется подтвердить CI, получить analyzer JSON, проверить SHA-256 frozen artifact и accepted/missing/rejected counters. До этого `safety_margin_status=not_established`, `production_eligibility=not_validated`.


## Hash and capture audit — 2026-11-03

The frozen prediction artifact SHA-256 was independently recomputed from canonical JSON and matches the journal value: `a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`. All 45 Monitor reports were re-read and checked for exact CHALK, stroke-level pointDelta sum, unique observed radius=10, and zero Monitor/Bridge integrity counters. The official analyzer JSON remains pending.


## Дополнительная проверка binding журнала — 2026-11-03

При статическом аудите analyzer обнаружено, что prediction ID проверялся в manifest metadata, но не сравнивался напрямую с `prediction_id` в соответствующей journal task. Это оставляло непроверенным одно звено цепочки frozen artifact → journal task → manifest.

Исправлено:
- analyzer теперь отклоняет запись с `journal_prediction_id_mismatch`, если task prediction ID не совпадает с вычисленным ID для scenario/profile;
- analyzer дополнительно сверяет `task.expected_strokes` с числом strokes в frozen prediction;
- добавлен regression test, который изменяет task prediction ID и ожидает fail-closed rejection.

Изменение не меняет frozen model, прогнозы, production estimator или executor defaults. После этого изменения нужен новый CI run; официальный report по 45 captures остаётся pending.
