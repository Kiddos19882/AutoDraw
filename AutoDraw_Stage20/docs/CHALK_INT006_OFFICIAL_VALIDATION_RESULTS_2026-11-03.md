# INT-006 — официальный отчёт независимой количественной validation CHALK

**Дата:** 2026-11-03  
**Репозиторий:** `Kiddos19882/AutoDraw`  
**Ветка:** `feature/image-geometry-optimization`  
**CI run:** [41532629748 — SUCCESS](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748)  
**Analyzer commit:** `dd64730e202ed6f6014fa2dd1a65c3100cc32018`  
**Series:** `chalk-20261102-232320-7cea27`  
**Block ID:** `1f93ddcac07445b78093744c7cbabcde`  
**Model:** `chalk-int006-frozen-2026-11-02`, version 1; radius=10  
**Artifact:** `autodraw-int006-chalk-validation`, ID `13182727663`

## 1. Итоговый gate

Официальный запуск `chalk_int006_validation.py` завершился успешно. Analyzer report:

| Проверка | Результат |
|---|---:|
| Expected captures | 45 |
| Accepted | **45** |
| Missing | **0** |
| Rejected | **0** |
| Complete scenario/profile groups | **15 / 15** |
| Repeats per group | 3 / 3 |
| Stroke-level rows | 243 |
| Frozen artifact SHA-256 | совпадает |

SHA-256 frozen prediction artifact:

`a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`

Analyzer report: `analysis.json` внутри CI artifact. Статусы в самом report: `status=complete`, `safety_margin_status=not_established`, `production_eligibility=not_validated`.

## 2. Общие метрики по 45 DrawingPlan captures

Residual = actual CHALK − predicted CHALK. Положительный residual означает недооценку расхода.

| Метрика | Официальный результат |
|---|---:|
| Фактический CHALK, сумма | 3910 |
| Frozen prediction, сумма | 3949.38 |
| MAE | **1.408 CHALK** |
| RMSE | **1.967 CHALK** |
| Bias | **−0.875 CHALK** |
| MAPE | **2.134%** |
| Maximum absolute error | **4.94 CHALK** |
| Maximum underprediction | **1.82 CHALK** |
| Underprediction / overprediction / exact | 15 / 28 / 2 |

Модель в среднем слегка завышает расход на этой выборке. Это не устраняет локальные случаи недооценки: максимальная недооценка 1.82 CHALK зафиксирована в D5/P2.

## 3. Сравнение sampling profiles

| Profile | Step / delay | Actual total | Predicted total | MAE | RMSE | Bias | MAPE | Max underprediction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | 2 / 10 ms | 1884 | 1925.25 | 2.882 | 3.189 | −2.750 | 3.484% | 0.99 |
| P1 | 4 / 5 ms | 1010 | 1011.81 | **0.657** | **0.838** | −0.121 | **1.178%** | **0.92** |
| P2 | 4 / 10 ms | 1016 | 1012.32 | 0.685 | 0.854 | +0.245 | 1.741% | 1.82 |

P1 имеет лучшие совокупные MAE/RMSE/MAPE и меньшую максимальную недооценку, чем P2. На данных D1–D5 это лучший исследовательский кандидат. Он не становится автоматически production default: серия покрывает только пять заданных DrawingPlan и radius=10.

### Фактическая экономия P1 относительно P0

| Geometry | P0 actual mean | P1 actual mean | Снижение расхода |
|---|---:|---:|---:|
| D1 mixed lines | 118.00 | 62.33 | 47.2% |
| D2 polygon | 134.00 | 70.67 | 47.3% |
| D3 intersections | 189.67 | 100.00 | 47.3% |
| D4 short details | 19.00 | 14.67 | 22.8% |
| D5 repeated coverage | 167.33 | 89.00 | 46.8% |
| **Итого по 15 captures каждого профиля** | **1884** | **1010** | **46.4%** |

Это прямое сравнение фактического CHALK в пределах одинаковых D1–D5 сценариев при radius=10. Результат подтверждает преимущество step=4 на этих сценариях, но не доказывает такое же снижение на иных рисунках или при других размерах кисти.

## 4. Метрики по каждой геометрии

| Geometry / profile | Actual mean | Frozen prediction | MAE | RMSE | Bias | Max underprediction | Repeat σ |
|---|---:|---:|---:|---:|---:|---:|---:|
| D1 / P0 | 118.00 | 120.30 | 2.30 | 2.30 | −2.30 | 0.00 | 0.00 |
| D1 / P1 | 62.33 | 62.32 | 0.44 | 0.47 | +0.01 | 0.68 | 0.47 |
| D1 / P2 | 62.67 | 62.29 | 0.57 | 0.60 | +0.38 | 0.71 | 0.47 |
| D2 / P0 | 134.00 | 135.79 | 1.79 | 1.97 | −1.79 | 0.00 | 0.82 |
| D2 / P1 | 70.67 | 70.63 | 0.46 | 0.47 | +0.04 | 0.37 | 0.47 |
| D2 / P2 | 71.33 | 70.58 | 0.75 | 0.89 | +0.75 | 1.42 | 0.47 |
| D3 / P0 | 189.67 | 193.71 | 4.04 | 4.07 | −4.04 | 0.00 | 0.47 |
| D3 / P1 | 100.00 | 100.08 | 1.31 | 1.42 | −0.08 | 0.92 | **1.41** |
| D3 / P2 | 99.67 | 100.05 | 0.38 | 0.61 | −0.38 | 0.00 | 0.47 |
| D4 / P0 | 19.00 | 20.01 | 1.67 | 1.92 | −1.01 | 0.99 | 1.63 |
| D4 / P1 | 14.67 | 15.00 | 0.33 | 0.58 | −0.33 | 0.00 | 0.47 |
| D4 / P2 | 15.00 | 15.34 | 0.78 | 0.88 | −0.34 | 0.66 | 0.82 |
| D5 / P0 | 167.33 | 171.94 | 4.61 | 4.63 | −4.61 | 0.00 | 0.47 |
| D5 / P1 | 89.00 | 89.24 | 0.75 | 0.85 | −0.24 | 0.76 | 0.82 |
| D5 / P2 | 90.00 | 89.18 | 0.94 | 1.16 | +0.82 | **1.82** | 0.82 |

D3/P1 имеет заметный разброс повторов (σ≈1.41 CHALK); D4 показывает повышенную относительную ошибку из-за малых абсолютных расходов. Это аргумент сохранять геометрическую сегментацию и не заменять модель одним средним процентом.

## 5. Per-stroke metrics

| Метрика | Результат |
|---|---:|
| Stroke rows | 243 |
| MAE | 0.439 CHALK/stroke |
| RMSE | 0.544 CHALK/stroke |
| Bias | −0.162 CHALK/stroke |
| Maximum absolute error | 1.645 CHALK/stroke |
| Maximum underprediction | 1.085 CHALK/stroke |

Для P1 per-stroke maximum underprediction составила около 0.80 CHALK; maximum absolute stroke error — 1.00 CHALK. Это данные конкретной серии, а не универсальная граница ошибки.

## 6. Целостность captures и связи

Официальный analyzer принял все 45 manifest records после проверки frozen artifact, journal task, completed accepted attempt, scenario/profile/repeat/order, prediction ID, normalized geometry, radius, executor configuration, experiment/run identity, exact CHALK и per-stroke Monitor breakdown.

Предварительный повторный аудит первичных данных дополнительно подтвердил по всем 45 Monitor reports:
- `chalk.status=exact`;
- `post_point_count - pre_point_count = consumed_points`;
- sampled point delta и сумма per-stroke `DRAW_SAMPLE.pointDelta` совпадают с CHALK delta;
- stroke group count соответствует DrawingPlan;
- observed brush radius единственный: 10;
- dropped events, Monitor errors, Bridge send failures и collector sequence gaps равны нулю;
- experiment ID report совпадает с journal attempt.

## 7. CI и исправление analyzer

Run [41530634729](https://github.com/Kiddos19882/AutoDraw/actions/runs/41530634729) первоначально выявил ошибку сравнения разных сериализаций геометрии: frozen artifact хранит пары координат, runtime manifest — point objects `{x, y}`, closed flag и metadata. Все 45 captures были отклонены как `geometry_signature_mismatch`, хотя capture integrity была подтверждена.

Исправление:
- manifest hash проверяется отдельно в его исходном runtime representation;
- runtime strokes нормализуются к frozen logical geometry;
- normalized plan сравнивается с frozen plan/signature;
- тестовые fixtures переведены на реальный runtime manifest shape.

Commits:
- fix: `8eba34f2ae402bbcf8af096f8b642a5cdcfb5eee`;
- regression test: `dd64730e202ed6f6014fa2dd1a65c3100cc32018`.

Повторный workflow [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) завершился SUCCESS. Preparation/G3: 669 passed, 82 subtests passed; Application integration, Executor regression, Game Monitor/bridge, Windows portable build/startup smoke-test, PNG audit и independent CHALK analyzer — success. Optional benchmarks skipped.

## 8. Решение по запасу и применимости

**Предварительный кандидат:** P1 (step=4, delay=5 ms) для поддерживаемых прямых штрихов и DrawingPlan-классов, покрытых D1–D5 при radius=10.

**Наблюдённая недооценка P1:** максимум 0.92 CHALK на целом DrawingPlan. Округлённый вверх эмпирический guard — 1 CHALK на DrawingPlan. Такой guard покрывает максимальную недооценку только в этих 15 P1 captures; он не является статистической гарантией и не покрывает неподдержанные типы геометрии.

**Статус safety margin остаётся NOT ESTABLISHED.** Малое число независимых DrawingPlan (пять) и три повтора на cell не дают основания объявлять универсальный доверительный предел. Analyzer намеренно оставляет `safety_margin_status=not_established` и `production_eligibility=not_validated`.

Production estimator, executor defaults, sampling defaults и master не менялись. Не использовать P1/1 CHALK guard как глобальное production правило до дополнительной проверки на полных реальных рисунках, кривых, контурах, коротких деталях, перекрытиях и других размерах кисти.

## 9. Следующие gates

1. Сохранить P1 как исследовательского кандидата, не переключая production defaults.
2. Отдельно расширить validation на полные реальные DrawingPlan и неподдержанные классы геометрии; radius matrix не заменяет проверку модели при разных радиусах.
3. На реальных рисунках проверить прогноз против точного pre/post `pointCount`, включая короткие детали, пересечения, повторное покрытие, кривые и заливки.
4. Только после расширенной validation и решения о запасе рассматривать INT-007 (интеграцию в preflight/resource estimator).
5. До этого unsupported geometry должна оставаться UNKNOWN; нельзя подставлять коэффициент прямой линии для кривой/заливки.

