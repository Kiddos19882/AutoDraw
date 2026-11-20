# ENGINE-001 / BPRED-S2v2 — frozen E0: монотонная residual-калибровка alpha

**2026-11-20. E0 FROZEN BEFORE NEW MODEL CODE/RESULT; TASK BPRED-S2 (продолжение).** Baseline HEAD `4d2c7991e8472ed41ee64632658c55c9cd43287b`; неизменённые [S2v1 E0](ENGINE001_BPRED001_S2_PHYSICAL_ALPHA_AA_CALIBRATION_PREREG_2026-11-20.md) и [итог S2v1](ENGINE001_BPRED001_S2V1_ALPHA_AA_RESULTS_2026-11-20.md) подтвердили физическую alpha M2 area8 и исходные 2167 FP/559 FN при alpha24. В соответствии с [BPRED-001](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md) и [DEC-041](DECISIONS.md) следующий эксперимент — **только S2** улучшение предсказания, без локального постремонта изображения, без RGB composition/owner S3 или BLIND S4.

## 1. Гипотеза и фиксированная математическая коррекция

- Базовая модель `M2_AREA8` = неизменённый `P4D16.predict_alpha(..., "area8")` с исследовательским gate-adapter для width1..10 из v1 (формулу не переписывать).
- `M3_ISOTONIC` — обучаемая **одномерная монотонная функция** `f_w(alpha_M2)` отдельно для каждой width1..10, без ввода нового источника или нейросети, без подбора углов/фаз/смещения. Для входных значений `1..254` в train собрать `count_w[a]` и `sum(native_alpha)[a]`, получить среднее native alpha при каждом наблюдённом уровне `a`, применить однозначный weighted PAVA (isotonic non-decreasing), ограничить [0,255], `f(0)=0`, `f(255)=255`; пропуски уровней заполнить линейной интерполяцией между соседними обученными levels и двумя фиксированными anchors; итог `np.rint` к uint8. Все train counts и knots сохранять в raw artifact. **Не использовать native pixels с `M2=0`** для обучения — при реальном inference неизвестные native footprints недоступны; этот код не может подглядеть в целевую маску. Не изменять координаты, geometry, P4D16 area8 или threshold24. При отсутствии intermediate levels вернуть identity `f(a)=a`, зафиксировать причину.
- Критический риск: M3 может улучшить MAE, но ухудшить FP/FN в узких линиях. Считать отдельно все ошибки и abstention; нулевые FP/FN необходимы для `pixel_exact_safe`, и это только calibration, не S4 acceptance. Не изменять H1/H2/H3 после результата.

## 2. Строгое разделение по angle family до обучения

Единственный source native: [S1 CI44646682797](https://github.com/Kiddos19882/AutoDraw/actions/runs/44646682797) artifact14589516497 SHA `f38f2dbf`; 120 **CALIBRATION** (width1..10, angle7/73/166°, lengths7/19, 2 independent XY phases, 3 disjoint native copies). Source M2v1 [CI44651134628](https://github.com/Kiddos19882/AutoDraw/actions/runs/44651134628) SHA `4d2c7991e8472ed41ee64632658c55c9cd43287b` archive14589809874. Обязателен SHA/provenance audit S1 363 членов и exact fixed S2v1 code references. **BLIND120 +10 replay-control + blank from S0 не открывать и не использовать.**

Leave-one-angle-out **ровно три фиксированных fold**, без случайности:
- **F7:** train angle73+166, validate angle7;
- **F73:** train angle7+166, validate angle73;
- **F166:** train angle7+73, validate angle166.

В каждом fold train 80 families ×3 copies и held-out 40 families×3 copies; все копии, фазы и related cases конкретной angle family остаются вместе, no leakage. Для одной width train8 scenes×3 locations, test4 scenes×3. Валидация по 120 total cases, **macro-average сначала 3 copies/scene** и затем 120 scenes. Не смотреть показатели F7/F73/F166 до фиксации реализации/гипотез. Исследование всего лишь internal CALIBRATION cross-val, **не** independent blind/S4.

## 3. Предзарегистрированные численные условия

Сравнивать честно `M2_AREA8` и `M3_ISOTONIC` **на тех же held-out scenes** от одного fold; считать `alphaMAE_union`, alpha1/alpha24 TP/FP/FN/IoU, per-width, per-angle/fold, phase, absolute copies, exact mask, heldout worst. `alphaMAE_union` = MAE по union native>0 или model>0, порог alpha24 прежний.

- **H1** `M3 alphaMAE_union macro ≤0.97 × M2` (улучшение минимум3%) во всех 120 held-out CALIBRATION family cases.
- **H2** `M3 FP_alpha24_total ≤0.90 × M2 FP_alpha24_total` **И** `M3 FN_alpha24_total ≤1.25 × M2 FN_alpha24_total`. Условия одновременно, иначе FAIL. FP/FN считаются по всем 360 физических ROI, без сравнения с owners.
- **H3** `M3 macro alpha24 IoU ≥ M2 macro alpha24 IoU −0.002`. Иначе FAIL.
- **Safety:** для M3 `pixel_exact_safe=false`, если есть ANY FP/FN alpha1/24; никакой новый confidence не присваивать по calibrations. Отдельно сообщать худший width/angle/phase, возможную деградацию, не выбирать только удачные results.

Все thresholds фиксированы **до** новой реализации/исходов, не подгонять `PAVA`, folds, anchors, thresholds или ширины после измерений. Технический E2/CI PASS не означает H1/H2/H3 science PASS; всегда сохранять отрицательные outcomes. При FAIL не выдавать M3 за улучшение и не переходить к production.

## 4. Evidence / файлы / границы

Только исследовательский evaluator и regression tests, isolated CI, frozen provenance, append-only per-case rows, 3 fold×10 width knot manifests, raw predictions/metrics with SHA and run ID, архив GitHub Actions (не перезаписывать v1). Новых native Egret render **0**, E3 относится к original S1 source pixels, повторный анализ CI текущего SHA; E4 live/E5 independent BLIND/CHALK exact NOT_RUN. Предыдущие S2v1 негативы, P4D18 protected FAIL и P4D19 DEFERRED сохранять.

**После результата:** если M3 не удовлетворяет H1/H2/H3, изучить закономерности residual как отдельную S2 версию; если удовлетворяет, не объявлять safe, а далее по плану рассмотреть uncertainty bound/native fallback до S3 compositing. S4 blind не использовать до окончательной фиксации модели. `master`, production planner, renderer, Stage6, Monitor, Bridge и CHALK estimator не менять.
