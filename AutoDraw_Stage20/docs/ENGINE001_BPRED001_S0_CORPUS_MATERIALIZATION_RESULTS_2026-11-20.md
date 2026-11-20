# ENGINE-001 / BPRED-S0 — результат материализации native-корпуса (2026-11-20)

**Статус: BPRED-S0 COMPLETE (инвентаризация/целостность); BPRED-S1/S2 accuracy NOT_RUN.** [План BPRED](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), [frozen S0 E0](ENGINE001_BPRED001_S0_CORPUS_INVENTORY_AND_SPLIT_PREREG_2026-11-20.md), [DEC-041](DECISIONS.md). Ветка `feature/image-geometry-optimization`. Проверенный код SHA `5b6ed18a065740c3a99b3463129c36118fc6514c`, [финальный CI44644039555](https://github.com/Kiddos19882/AutoDraw/actions/runs/44644039555) **SUCCESS**.

## Проверенные реальные первичные данные

Исследовательский [artifact14586574667](https://github.com/Kiddos19882/AutoDraw/actions/runs/44644039555/artifacts/14586574667) (`engine001-bpred-s0-frozen-native-corpus-v1`, 19 758 215 байт) содержит **семь неизменённых исходных ZIP** из ранее завершённых real Egret CI, `historical_raw_member_manifest.json` со всеми проверенными SHA и ссылками на исходный SHA/run/artifact, `future_native_scene_plans.json` и `report.json`. GitHub Actions заново скачал архивы, проверил метаданные original run, hash оригинальной игры, renderer, исходного файла PNG и P4D3 runner; **ZIP CRC, полный список members и SHA256 каждого member**. Исходные raw архивы не перезаписаны.

| Источник | Оригинальный artifact | SHA256 members PASS | PNG, включая диагностику |
|---|---:|---:|---:|
| P4D3 | 14480461909 | 1686 | 1123 |
| P4D4 | 14482220143 | 1446 | 963 |
| P4D14 | 14544372165 | 334 | 172 |
| P4D15 | 14549505133 | 103 | 68 |
| P4D16 | 14554416035 | 319 | 166 |
| P4D13 | 14537095764 | 39 | 32 |
| P4D18 | 14557770111 | 34 | 26 |
| **Итого** | **7 ZIP** | **3961** | **2550** |

PNG count включает previews/heatmaps, а не только independent native scenes. Эти original native результаты относятся **к исходным** commit/CI; новое предсказание кисти не проверялось.

## Созданные планы и качество проверок

Исследовательские (ф) [run_engine001_bpred_s0_corpus_audit.py](../tests/run_engine001_bpred_s0_corpus_audit.py), (ф) [test_engine001_bpred_s0_corpus_audit.py](../tests/test_engine001_bpred_s0_corpus_audit.py), (ф) [engine001-bpred-s0-frozen-corpus.yml](../../.github/workflows/engine001-bpred-s0-frozen-corpus.yml) не связаны с production. **17/17 E2 tests PASS**: детерминированные IDs/plans/sha, непересечение calibration/blind families, XY phase, three isolated copies, widths1..10, replay, blank, fail-closed на bad sha, bad ZIP/DEFLATE/CRC, path traversal, extra members, неправильный исходный commit и overwrite. Markdown CI **PASS** (один прежний historical link warning без current error).

Будущий `BPRED001_CORPUS_V1`: **120 CALIBRATION** (angles7/73/166), **120 BLIND** (angles38/121/277), **11 CONTROL** (10 replay+blank), width1..10, lengths7/19, независимые fractional X/Y phases. **251 план подготовлен, 0 новых настоящих Egret сцен**: `native_png_sha256=null`, `capture_status=NOT_RUN`. Не выдавать опубликованные P4D3–16 за fresh blind, результаты P4D13/18 за качество новой модели или 2550 PNG за независимую выборку.

## Отрицательные попытки — сохранены

- [CI44643434621](https://github.com/Kiddos19882/AutoDraw/actions/runs/44643434621) SHA4befd710 **FAIL** (16/17 E2): synthetic corrupted ZIP вызывал zlib.error вместо fail-closed; исправлено.
- [CI44643646179](https://github.com/Kiddos19882/AutoDraw/actions/runs/44643646179) SHAfc798ba8: E2 и 3961 raw SHA PASS, но при workflow SUCCESS архив **не был загружен** из скрытого каталога. Исправлено обязательным upload `include-hidden-files:true`, `if-no-files-found:error`.
- [CI44643825015](https://github.com/Kiddos19882/AutoDraw/actions/runs/44643825015) SHAbc3c4ec5 — опубликован промежуточный архив; затем имя schema/IDs в коде приведено к frozen E0 **без изменения сцен/выборки**.
- **Итог:** [CI44644039555](https://github.com/Kiddos19882/AutoDraw/actions/runs/44644039555) SHA5b6ed18a E2/CI integrity/uploader **PASS**, финальный archive14586574667 подтверждён.

## Доказательность и следующий шаг

**E1 PASS**, **E2 17/17 PASS**, **CI artifact integrity PASS** на SHA5b6ed18a; **новые E3 Egret scene NOT_RUN**, BPRED M0/M1/M2 accuracy **NOT_MEASURED**, E4 live/E5/exact run-bound CHALK **NOT_RUN**. P4D18 original-white/protected quality **FAIL** остаётся, P4D19 DEFERRED. Нет изменений master, production renderer/planners, Stage6, Monitor, Bridge или CHALK estimator.

**NEXT один:** BPRED-S1 — отдельная E0 prereg с математическими гипотезами, метриками и native-критериями для M0/M1 source-faithful geometry на уже определённых frozen scenes. После разрешённого stage S1 разработки и тестов использовать только настоящий Egret для проверки следа, сохранить модели и raw отрицательные результаты.