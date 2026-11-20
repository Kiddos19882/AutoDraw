# ENGINE-001 / BPRED-S3v2d — полная нативная локализация RGB-расхождений Canvas2D → WebGL (2026-11-20)

**Итог: E2/E3 technical PASS; H1 на настоящем Canvas PARTIAL/FAIL 38/40, на итоговом WebGL старый H1 FAIL 10/40.** Результат НЕ означает безопасность пикселей, готовность S3 или автоматический допуск к S4. Исходный [frozen S3v2d E0](ENGINE001_BPRED001_S3V2D_MAIN_NODE_STAGE_PREREG_2026-11-20.md) blob `1eb60858facc4d208f238ca9bb1c39e2f937ca1b` зафиксирован до кода и нативного полного запуска. [Успешный CI44697386598](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598) code SHA `2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a`, [архив artifact14610824409](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598/artifacts/14610824409), original Firefox159.0, Egret5.4.1.

## 1. Почему потребовалось техническое исправление

Исторические S3v2 original [CI44684709364](https://github.com/Kiddos19882/AutoDraw/actions/runs/44684709364) technical FAIL (deBG-byte drift) и S3v2b [CI44686065270](https://github.com/Kiddos19882/AutoDraw/actions/runs/44686065270) technical BLOCKED (два разных Canvas вместо единственного) сохранены. [S3v2c доказал](ENGINE001_BPRED001_S3V2C_CANVAS_MULTICAPTURE_RESULTS_2026-11-20.md) реальный основной Canvas и маску в 8 сценах.

Первый полный S3v2d [CI44688742268](https://github.com/Kiddos19882/AutoDraw/actions/runs/44688742268) технически FAIL до первой сцены: `BLOCKED_BPRED_S3V2_MISSING_SCOPED_P4D15_REUSE_JS`. Причина: общая функция `run(...stage_version="v2d")` всё ещё требовала старое имя `engine001_bpred_s3v2_canvas_capture.js`, хотя S3v2d по отдельному frozen E0 обязан передавать `engine001_bpred_s3v2d_source_node_selector.js`. Изменён исключительно version-scoped входной контракт (ф) `tests/run_engine001_bpred_s3v2_native_canvas_stage.py` commit [5914e65d](https://github.com/Kiddos19882/AutoDraw/commit/5914e65d793ad337e013d037b9db8a74fcc28be6), 4 fail-closed regression tests (ф) `tests/test_engine001_bpred_s3v2_native_canvas_stage.py` commit [0132b1f6](https://github.com/Kiddos19882/AutoDraw/commit/0132b1f6ec99201246dab57d859c095e9877613e), Git blob pin оригинального runner в (ф) `.github/workflows/engine001-bpred-s3v2d-main-canvas-stage.yml` commit [2ba4241b](https://github.com/Kiddos19882/AutoDraw/commit/2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a). Старый S3v2b путь не менялся, пороги H1 не менялись.

## 2. Архив и воспроизводимость

На SHA `2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a`:
- E2 **43 PASS**: 10 S3v2b, 14 S3v2 (включая 4 новые), 5 S3v2c и 14 исходных S3; node-check и Markdown integrity PASS.
- E3 **80** genuine original main BoardPane Canvas PNG (1392×732, node -2/-2/464×244, transform [3,0,0,3,6,6]), **80** настоящих отдельно сохранённых mask Canvas PNG (1380×720), **91** original WebGL PNG (80 primary +10 replay +1 blank), 20 source pairs, 40 ordered AB/BA variants. Firefox159.0 pinned.
- Parent S3 run44683117471 SHA `6dedf6ddfde36db17f07fc0aa00dd463dc525ca8`: deBG-only nonce proof, все 91 final RGBA exact относительно parent; replay RGBA exact, blank alpha0. Не ретушировать ошибочные пиксели.
- Archive ZIP имеет **656** записей, 655 перечислены в `report.json.members_sha256` и проверены независимой CI SHA256-проверкой; [CI44697386598](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598) technical **SUCCESS**. S0 reserved BLIND **не использован**.

## 3. Научная проверка исходного H1, строго без ослабления

Сравнение straight-sRGB original frozen C0 source-over из настоящих изолированных A/B с результатом A_THEN_B/B_THEN_A. Исходные одинаковые для Canvas и WebGL критерии H1: **max-channel ≤2/255 и mean-channel ≤1/255 по каждой ordered variant**.

| Стадия | H1 PASS / 40 | H1 FAIL / 40 | Worst max-channel byte | Сумма различающихся pixel occurrences (40 variants) |
| --- | ---: | ---: | ---: | ---: |
| original Canvas2D intermediate | **38** | **2** | **4** | 1 325 |
| original WebGL final | **10** | **30** | **6** | 1 994 |

Два residual Canvas H1 FAIL: **W04/NEAR_PARALLEL_OVERLAP/B_THEN_A** max3, 15 different pixels, mean0.00649; **W10/NEAR_PARALLEL_OVERLAP/A_THEN_B** max4, 75 different pixels, mean0.01056. Порог не изменён; Canvas **не** назван perfect или accepted. Native final H1 original **FAIL30/40** воспроизведён, source S3 scientific FAIL сохранён.

## 4. Отдельный posthoc raw-pixel аудит (E1/E2 diagnostic, НЕ prereg safety)

После завершения CI открыт только его фактический архив и попарно сопоставлены `*_ALIGNED_MODEL_ONLY.png` и `*_REAL_WEBGL.png` для 80 основных сцен. Результат описательного анализа: **12 694 различных RGBA physical pixel occurrences**, и в **каждом** совпадает альфа; RGB различается во всех 12 694; **все** имеют настоящую промежуточную альфу 1..254, альфа0 и альфа255 пикселей среди изменившихся нет. Worst RGB difference across stages на малых alpha до **127** (это **не** исходная H1 source-over error; это прямой intermediate→final RGB difference). Следовательно доказано **stage RGB-only disparity on these 80 scenes**, не доказано, какой именно GPU/texture/rounding/premultiplication механизм его породил. RGB может заметно меняться при низкой alpha; простое `source-over` от сохранённых straight RGB в финальном канале не обязано совпадать с настоящим WebGL.

## 5. Границы и следующий невыполненный шаг

Source S3 C0 H1 FAIL30/40, owner model C1 unsafe (FP236, confident wrong RGB1420), prior S2v4 zero-FP FAIL, original E/F P4D18 protected-source quality FAIL сохраняются. Синтетические two-owner сцены не доказывают качество оригиналов E/F. **E4 live game / E5 independent / run-bound exact CHALK NOT_RUN**, production, Stage6 executor, Monitor, Bridge, master не менялись. DEC-042 adaptive consequences остаётся только research proposal, hard original quality gates прежние.

**NEXT в S3 (не S4):** до следующего расчётного эксперимента отдельно заморозить E0 для проверки RGB texture-stage quantization/alpha representation с отрицательными вариантами. Использовать этот истинный S3v2d raw только как диагностический источник, не S0 BLIND. Различать actual pre-Canvas RGB/alpha, transformed WebGL RGB при тождественной alpha и две residual Canvas H1 failures. Нельзя объявлять один механизм причиной до отдельной проверки. Далее по базовому плану S4 independent BLIND → S5 original E/F global adaptive → S6 безопасная оптимизация штрихов, только после доказанной пригодности.
