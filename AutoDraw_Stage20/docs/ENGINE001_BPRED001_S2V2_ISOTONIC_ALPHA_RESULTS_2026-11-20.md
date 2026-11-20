# ENGINE-001 / BPRED-S2v2 — отрицательный результат isotonic alpha residual

**Дата:** 2026-11-20. **Статус:** E2/CI PASS, science H1 FAIL / H2 FAIL / H3 PASS, MODEL_ONLY UNSAFE. Задача `BPRED-S2` продолжается; S3–S6 не начаты. Исходный [E0](ENGINE001_BPRED001_S2V2_ISOTONIC_ALPHA_RESIDUAL_PREREG_2026-11-20.md) заморожен до кода на SHA `cf8915e468f463c6e2999cb45bc30d531152ca55`, индекс на SHA `6ebe86142661966aa37a61ea60bbaad5ec29c641`. Никакого изменения критериев после результатов.

## 1. Первичные доказательства

- **Исследовательский SHA:** `4656b62eeb8196faaa66f9c10023a24d4c866a21`, ветка `feature/image-geometry-optimization`. [CI44652423011](https://github.com/Kiddos19882/AutoDraw/actions/runs/44652423011) job `source-native-residual-validation` **SUCCESS**, [artifact14591791460](https://github.com/Kiddos19882/AutoDraw/actions/runs/44652423011/artifacts/14591791460) (61 862 bytes, доступен на момент проверки). [Общая validation44652423039](https://github.com/Kiddos19882/AutoDraw/actions/runs/44652423039): 5/5 обязательных jobs PASS, 3 дополнительных SKIPPED; успех CI относится только к указанному SHA.
- Native source: 120 реальные сцены CALIBRATION × 3 физические ROI из [S1 E3 CI44646682797](https://github.com/Kiddos19882/AutoDraw/actions/runs/44646682797), parent S2v1 [CI44651134628](https://github.com/Kiddos19882/AutoDraw/actions/runs/44651134628). Source 363 member SHA снова верифицированы, исходный M2 результат перепроверен; **0 новых native renders**, **0 S0 BLIND scenes**.
- Модель `M3_ISOTONIC`: для каждой ширины1..10 отдельно обученная weighted PAVA таблица `f_w(alpha_M2)`, anchors0/255, три фиксированных leave-one-angle-out folds (held-out angles 7/73/166; training только две другие angle families), 120 валидационных CALIBRATION scenes. Все 30 таблиц, train counts, raw rows и FP/FN представлены в артефакте.
- E2 10 новых unit tests S2v2 + 14 regression S2v1 PASS, доп. исходные требования Markdown PASS. Источник original/renderer/engine неизменен.

## 2. Фактические результаты, критерии до теста

| Метрика | M2 AREA8 | M3 PAVA | Вердикт |
|---|---:|---:|---|
| Macro alpha MAE на ненулевом union | **2.4705090039** | 2.5061744360 | H1: **FAIL** (требовалось M3 ≤0.97×M2) |
| Macro IoU alpha≥24 | 0.9892986132 | **0.9899392162** | H3: **PASS** (допуск −0.002) |
| Физические FP alpha≥24 | 2167 | **1315** | Снижение есть, но H2 требует также FN bound |
| Физические FN alpha≥24 | **559** | 1237 | H2: **FAIL** (лимит M3 ≤1.25×559) |

**Важно:** M3 не рекомендуется заменять M2 даже при немного большем IoU. Ошибки физического альфа-слоя особенно критичны на границах original owner и protected white, поэтому результаты нельзя объявлять pixel-safe. Никакая production-модель не принята, P4D18 source E/F protected-quality **FAIL**, P4D19 prereg **DEFERRED**. E4 live, E5 independent/BLIND, exact game CHALK `post.pointCount-pre.pointCount` **NOT_RUN**.

## 3. Сохранение отрицательного результата и следующий шаг

Отрицательные H1/H2 сохраняются как независимые от технического CI PASS. S2v2 не изменял `P4D16` native renderer, production planners/Stage6/Bridge/Monitor, master и исходный E/F target. Восстановление зависимости от ранее известного `S2v1` не является независимым свидетельством на новых images.

**NEXT в BPRED-S2:** [отдельный E0 S2v3](ENGINE001_BPRED001_S2V3_RISK_AWARE_ALPHA_PREREG_2026-11-20.md) фиксирует анализ физических residual и fail-closed область положительных предсказаний; измерить на тех же CALIBRATION scene families с angle-heldout CV без BLIND, сохранить все errors/uncertain. Только если такие исследования дают надёжные основания, после S2 переходить к S3 source-over, но без production или S4 blind до принятой версии модели.
