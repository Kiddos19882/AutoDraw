# INT-006 — результаты live follow-up V1–V5 (2026-11-02)

**Источник данных:** commit [e879a77](https://github.com/Kiddos19882/AutoDraw/commit/e879a77f63be7a7a68de3f09091eab7dba0d34a2) в ветке `feature/image-geometry-optimization`.

## 1. Приёмка серий

Выполнены пять отдельных block series, по 9 задач на фазу (P0/P1/P2 × 3 повтора), всего **45/45 live captures**. Все пять block journals имеют `status=completed`, каждая задача — `completed`.

| Фаза | Сценарий | Штрихов в DrawingPlan | Повторы |
|---|---|---:|---:|
| V1 | `int006_diagonals` | 6 | 3 на профиль |
| V2 | `int006_short_strokes_followup` | 5 | 3 на профиль |
| V3 | `int006_turns` | 3 | 3 на профиль |
| V4 | `int006_closed_contours` | 3 | 3 на профиль |
| V5 | `int006_intersections_spacing_sweep` | 16 | 3 на профиль |

Во всех сериях радиус кисти подтверждён Game Monitor как единственный наблюдаемый радиус **10**. Параметры профилей:

- **P0:** point_step=2 px, point_delay=10 ms.
- **P1:** point_step=4 px, point_delay=5 ms.
- **P2:** point_step=4 px, point_delay=10 ms.

## 2. Exact CHALK — повторы и средние

Расход в таблице — точный игровой delta `post.pointCount - pre.pointCount`, не оценка по PNG или шкале краски. Значения приведены в CHALK points.

| Фаза | P0: 2/10 (3 повтора; среднее) | P1: 4/5 (3 повтора; среднее) | P2: 4/10 (3 повтора; среднее) | Экономия P1 / P2 относительно P0 |
|---|---:|---:|---:|---:|
| V1 диагонали | 253 / 251 / 251; **251.67** | 132 / 132 / 130; **131.33** | 132 / 133 / 132; **132.33** | **47.8% / 47.4%** |
| V2 короткие штрихи | 39 / 40 / 38; **39.00** | 23 / 26 / 23; **24.00** | 25 / 23 / 23; **23.67** | **38.5% / 39.3%** |
| V3 повороты | 344 / 344 / 344; **344.00** | 176 / 175 / 175; **175.33** | 174 / 174 / 174; **174.00** | **49.0% / 49.4%** |
| V4 замкнутые контуры | 441 / 436 / 438; **438.33** | 229 / 229 / 229; **229.00** | 230 / 229 / 229; **229.33** | **47.8% / 47.7%** |
| V5 пересечения и spacing | 406 / 409 / 408; **407.67** | 216 / 220 / 212; **216.00** | 214 / 216 / 219; **216.33** | **47.0% / 46.9%** |

### Выводы по sampling

1. На этих пяти геометриях переход с point_step=2 на point_step=4 снизил расход CHALK на **38.5–49.4%**. Для V1/V3/V4/V5 снижение близко к 47–49%; V2 с короткими штрихами даёт меньший выигрыш — около 39%.
2. При point_step=4 замена delay=5 ms на delay=10 ms практически не меняла расход: средние P1/P2 различаются не более чем примерно на 1.4% внутри фазы. По этой выборке нет основания выбирать задержку как рычаг экономии CHALK.
3. Это сравнение относится к одинаковой геометрии внутри каждой фазы, radius=10 и трём повторам. Оно не устанавливает универсальный production profile и не проверяет влияние радиуса кисти в этих новых сериях.

## 3. Целостность Game Monitor

Для всех 45 manifests/reports подтверждены:

- `execution_status=completed`, число strokes соответствует контракту фазы;
- `chalk.status=exact`;
- `point_delta_matches_chalk=true`: сумма sampled per-stroke deltas совпала с exact pre/post delta;
- единственный наблюдаемый радиус равен 10;
- per-run dropped events, Monitor errors, Bridge send failures, collector sequence gaps и buffer-drop delta равны нулю.

Следовательно, все 45 измерений пригодны для сравнения суммарного CHALK между профилями. Это не означает, что визуальный quality gate уже пройден.

## 4. Capture и визуальные ограничения

- В новых captures курсор перед after-draw снимком находится в точке экрана **(856, 624)**. В manifest зафиксирована политика ухода ниже доски и полоски краски, исключая `board_area` и `paint_meter_area`, с отступом 32 px. Это подтверждает применение исправленного post-draw cursor placement в новой серии.
- `paint_meter_measurement.status=inconclusive` во всех сериях. Шкала краски остаётся только вспомогательной визуальной диагностикой и не заменяет точный Game Monitor counter.
- ROI visibility heuristic: V1 — все 6 ROI показывают изменение; V2 — все 5; V3 и V4 первые два штриха помечены `ambiguous_overlap`, третий — `visible_change_detected`; V5 все 16 помечены `ambiguous_overlap`. Это эвристика пересечения ROI, а не подтверждение отсутствия штрихов: Monitor подтвердил ожидаемые stroke counts и точный CHALK.
- Количественный pixel-level аудит новых 45 captures выполнен в CI run 41496555297; исходные и follow-up серии проанализированы раздельно по chalk_experiment_matrix.series_id. Подробные результаты — в разделе 6 ниже. Результаты исходного аудита не переносились на новые DrawingPlan.

## 5. Решения и следующие gates

- Принять 45/45 captures как валидную выборку для анализа exact CHALK и сравнения P0/P1/P2.
- Зафиксировать point_step=4 как сильного экспериментального кандидата по экономии CHALK, но **не менять production defaults** до визуальной проверки.
- Не использовать paint-meter estimate для расчёта расхода; источником факта остаётся `post.pointCount - pre.pointCount`.
- Pixel-level аудит новых 45 after-draw PNG завершён; все 297 новых stroke rows имеют coverage=1.0, sufficient path metrics и gap_count=0. Диагностика V5 подтверждает merge при spacing 8/12 и разделение при 16/20/24 logical px.
- Следующий gate — независимая validation CHALK-модели на полных DrawingPlan и проверка safety margin; только после неё проектировать INT-007.
- Влияние размера кисти этими follow-up сериями не измерялось: радиус был фиксирован на 10.

**Raw data не изменялись:** block journals, DrawingPlan JSON, experiment manifests, Game Monitor reports и PNG сохранены в commit [e879a77](https://github.com/Kiddos19882/AutoDraw/commit/e879a77f63be7a7a68de3f09091eab7dba0d34a2).


## 6. Pixel-level PNG audit новых follow-up captures

**CI run:** [41496555297 — success](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297). Анализатор обработал исходные и follow-up серии раздельно по chalk_experiment_matrix.series_id.

### 6.1 Целостность полного набора

- Discovered/analysed: **90/90** (45 исходных + 45 follow-up).
- Capture valid: **90**, invalid: **0**.
- Серий: **10**, по 9 captures в каждой; V1–V5 — по 18 captures на фазу (исходная + follow-up).
- Duplicate/missing/unexpected matrix cells: **0**.
- Batch failures: **0**.
- Выходной artifact autodraw-int006-png-analysis: 273 файла — summary, 549 per-stroke rows, 900 parallel-pair rows и диагностические overlays/masks. [Скачать artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297/artifacts/13165359929).

### 6.2 Follow-up stroke coverage

В новых 45 captures проанализировано **297 штрихов** (V1 54, V2 45, V3 27, V4 27, V5 144):

- coverage_fraction=1.0: 297/297.
- path_metrics_sufficient=true: 297/297.
- gap_count=0: 297/297.
- max_gap_logical=0.0: 297/297.
- V5 сохраняет evaluable path fraction не ниже 0.9074 (среднее 0.9719) даже с зонами пересечения; все 144 штриха остаются sufficient.
- V4: все 27 замкнутых контуров имеют closure_seam_covered=true, шов не разомкнут.

V2 follow-up больше не имеет недостаточных centerline path metrics: все 45 коротких штрихов sufficient. В исходной V2 серии 9 rows были insufficient — эти исторические результаты остаются отдельно обозначены.

### 6.3 Проверка cursor placement

Во всех 45 новых captures:

- cursor_detected_near_final_endpoint=false;
- cursor_exclusion_pixels=0;
- transform_warning=null.

То есть курсор, перемещённый ниже доски и paint-meter ROI, не попал в board capture и не потребовал cursor-mask exclusion. На диагностических overlays также не наблюдается paint-meter tooltip, перекрывающего доску. Остаётся стабильный остаток 47–48 unassigned ink pixels на снимок у нижнего края UI; он не пересекает planned stroke corridors и не влияет на path coverage/gap metrics.

### 6.4 V5 — фактическое разделение параллельных линий

Для целевых пар parallel_sXX_a/b получено по 9 наблюдений на spacing (3 повтора × 3 sampling profiles):

| Плановый axis separation | Touch/merge | Минимальная дистанция ink masks |
|---:|---:|---:|
| 8.0115 logical px | 9/9 | 2.3718 logical px |
| 12.0172 logical px | 9/9 | 3.9530 logical px |
| 16.0229 logical px | 0/9 | 6.3250 logical px |
| 20.0286 logical px | 0/9 | 11.8590 logical px |
| 24.0344 logical px | 0/9 | 14.2310 logical px |

В рамках этой геометрии и radius=10 **16 logical px — первое проверенное расстояние, на котором целевая пара не сливалась**. Результат одинаков для P0 (2/10), P1 (4/5) и P2 (4/10). Это эмпирическая граница данной V5 конфигурации, не универсальный порог для всех радиусов и форм.

### 6.5 Интерпретация и ограничения

- ROI visibility heuristic ambiguity V3/V4/V5 не равна отсутствию штрихов: pixel-level анализ смог оценить траектории, и все 297 новых rows имеют полное покрытие и нулевые gaps.
- Pixel audit остаётся диагностическим инструментом; exact расход CHALK по-прежнему определяется только Game Monitor post.pointCount - pre.pointCount.
- Порог ink mask и corridor влияют на ширину и расстояния; V5 merge result следует использовать как экспериментальную геометрию при radius=10, а не как универсальную формулу.
- Production executor defaults и CHALK estimator не менялись.
