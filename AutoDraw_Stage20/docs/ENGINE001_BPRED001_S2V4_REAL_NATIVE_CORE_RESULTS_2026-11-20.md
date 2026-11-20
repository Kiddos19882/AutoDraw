# ENGINE-001 / BPRED-S2v4 — результат новой native Egret проверки core

**Дата 2026-11-20. Исследование `ENGINE001_BPRED_S2V4_NEW_NATIVE_CORE_V1`: E2/E3 CI PASS, H1 FAIL, H2 PASS, H3 FAIL, safety FAIL.** Оригинальный [S2v4 E0](ENGINE001_BPRED001_S2V4_NEW_NATIVE_CORE_VALIDATION_PREREG_2026-11-20.md) закреплён до кода SHA `d7d5d0868749a1006b1d21c742ed3b0a69774ab5`. Кодовый SHA `2faf01de258da005edec5b4d59a6ca5d48d63e74`. Исходные thresholds/методика не менялись после исхода. [План](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), [DEC-041](DECISIONS.md), [возможное адаптивное решение](ENGINE001_BPRED001_ADAPTIVE_STROKE_RISK_POLICY_2026-11-20.md).

## Первичный experiment и артефакты

[CI44659022526](https://github.com/Kiddos19882/AutoDraw/actions/runs/44659022526) `pinned-original-egret-new-native-core` SUCCESS на SHA `2faf01de258da005edec5b4d59a6ca5d48d63e74`, Windows Firefox159.0, исходный game Egret5.4.1 blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`. Реально сгенерированы **120 первичных новых native сцен +10 byte-exact repeats + blank=131 PNG**, 360 физических ROI; углы22°/111°/241°, widths1..10, lengths9/23, независимые XY фазы (1/32,11/32)/(13/32,7/32), 3 пространственные копии; sample family не пересекается с S0 CALIBRATION или зарезервированным S0 BLIND. Повторы 10/10 pixel RGBA exact, blank alpha0, hashes 376 членов archive проверены CI.

[Архив raw14593824723](https://github.com/Kiddos19882/AutoDraw/actions/runs/44659022526/artifacts/14593824723) — исходные native PNG, планы source/runtime SHA, `CASE_ROWS_APPEND_ONLY.jsonl`, `FROZEN_NEW_SCENE_MANIFEST.json`, `WORST_NEW_NATIVE_CASES.json`, `REPLAY_CONTROLS.json`, `report.json`, `members_sha256` SHA. Исходные S2v3 guard tables закреплены, BLIND120+controls S0 **не использовались**. E2 14 S2v4 +16 S2v3+14 S2v1 PASS; [общая validation44659022505](https://github.com/Kiddos19882/AutoDraw/actions/runs/44659022505) 5 обязательных PASS, 3 optional SKIPPED.

| Физическая alpha24 маска на *новом* Egret | M2 area8 (alpha>=24) | M5 core (alpha>=128) |
|---|---:|---:|
| True positive (TP) | 402639 | **383505** |
| False positive (FP) | 2379 | **3** |
| Доля TP M2, оставшаяся M5 | 100% | **95.2479%** |
| H1: FP=0 | — | **FAIL** |
| H2: TP>=90% baseline | — | **PASS** |
| H3: TP>=80% по каждой width и >=85% по каждому angle | — | **FAIL** |

**Технический E3 PASS не означает H1/H3 PASS или безопасный алгоритм.** M5 `pixel_exact_safe=false`, `MODEL_ONLY`, production запрещён. Суммарные 3 FP — это **ошибки модели по физической альфе**, не подтверждённое изменение чужого owner цвета: S3 multi-color source-over/защита не измерены. Характер/координаты трёх FP, конкретная проваленная width/angle strata пока не зафиксированы в действующих docs: [следующий frozen E0 S2v5](ENGINE001_BPRED001_S2V5_FALSE_SAFE_DIAGNOSTIC_PREREG_2026-11-20.md) требует их извлечь из неизменного raw, **без изменения порога или результатов S2v4**.

[Значимые исходники](../tests/run_engine001_bpred_s2v4_native_core.py), [тесты](../tests/test_engine001_bpred_s2v4_native_core.py), [workflow](../../.github/workflows/engine001-bpred-s2v4-native-core.yml) — только `tests/` и research CI; ни один production/Stage6/Bridge/Monitor/CHALK/game renderer файл не менялся. P4D18 original E/F protected leakage FAIL, P4D19 DEFERRED; E4/E5/exact run-bound CHALK NOT_RUN.

**Следующий шаг по BPRED-S2** — S2v5 raw causal-localisation diagnostic, затем только новое E0 adaptive stroke-risk *feasibility* в рамках S2/S3; после проверки physical per-color source-over S3, reserved BLIND S4, original E/F whole planner S5, optimization S6. Никаких retroactive PASS и снижения прежних порогов.
