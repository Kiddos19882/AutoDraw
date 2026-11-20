# ENGINE-001 / BPRED-S2v5 — три false-safe: точная локализация по native Egret

**2026-11-20. E2/CI diagnostic PASS, source E3 исходного S2v4 подтверждён, S2v4 H1 FAIL/H2 PASS/H3 FAIL НЕ изменены.** Frozen [E0 S2v5](ENGINE001_BPRED001_S2V5_FALSE_SAFE_DIAGNOSTIC_PREREG_2026-11-20.md) закреплён заранее в [commit ccd3cde6](https://github.com/Kiddos19882/AutoDraw/commit/ccd3cde6f4508c20622913da806611ebf8480c3b). Код/CI final SHA `9d2aee51575b81de36a05f2bfcc6c3b6e9209f12`, оригинал real native [S2v4 E3 run44659022526](https://github.com/Kiddos19882/AutoDraw/actions/runs/44659022526), original artifact14593824723. Итоговый read-only [CI44663535886](https://github.com/Kiddos19882/AutoDraw/actions/runs/44663535886) **SUCCESS**; [artifact14596516744](https://github.com/Kiddos19882/AutoDraw/actions/runs/44663535886/artifacts/14596516744) 8 230 bytes содержит исходные три FP, per-width/angle и все120 sample-strata.

## 1. Три физических FP принадлежат одному семейству

Все три ошибки `M5 predicted_alpha>=128 && real Egret_alpha<24` на **одной** исходной сцене `BPRED-S2V4-W07-A111-L23-PX01-PY11`, width7, angle111°, length23 logical, phase X=1/32,Y=11/32, в трёх disjoint translated copies. Их нельзя считать независимыми новыми семьями.

| Copy | Полная физическая координата (x,y) | predicted alpha | real Egret alpha | ideal capsule margin, logical |
|---:|---|---:|---:|---:|
| 0 | (195,83) | 128 | 21 | -0.00142260 |
| 1 | (537,323) | 128 | 21 | -0.00142260 |
| 2 | (879,563) | 128 | 21 | -0.00142260 |

Все три имеют один относительный ROI пиксель (102,44) и находятся на расстоянии **1 physical pixel** от соседнего реального alpha≥24. Отрицательный margin ≈−0.00142 logical к идеальной капсуле означает точку *чуть вне* её математической границы; это MODEL_ONLY диагностика, не доказанная причинность Canvas2D/WebGL. Измеренная alpha21 сама по себе может не быть полностью прозрачной; FP определяется **только прежним native порогом24**. Source-over owner damage не измерялся.

**Интерпретация E1/E2:** ошибки воспроизводятся при трансляции и локализованы у границы; возможно субпиксельное поведение/AA, но нельзя объяснить причинный механизм лишь тремя исходами. Нельзя принять случайное «FP≤3» или posthoc alpha>=129 как новую safety модель на этом же raw.

## 2. Нарушение H3 — только width1

S2v4 [pre-registered H3](ENGINE001_BPRED001_S2V4_NEW_NATIVE_CORE_VALIDATION_PREREG_2026-11-20.md) требовал сохранения TP ≥80% каждой width и ≥85% каждого angle. **Только кисть width1 нарушила критерий**: M2 TP **6876**, M5 TP **5445**, ratio **0.79188481675** (79.1885%, threshold80%). Все остальные width и все три angle-группы выдержали собственные H3 ограничения; это не пересчитывает оригинальный H3=FAIL. В сумме M2 TP402639/FP2379; M5 TP383505/FP3, original H1 FAIL/H2 PASS/H3 FAIL на неизменных 120 new native samples×3 copies.

## 3. Метод проверки / доказательность

- Research-only (ф) [run_engine001_bpred_s2v5_fp_diagnostic.py](../tests/run_engine001_bpred_s2v5_fp_diagnostic.py), (ф) [test_engine001_bpred_s2v5_fp_diagnostic.py](../tests/test_engine001_bpred_s2v5_fp_diagnostic.py), (ф) [engine001-bpred-s2v5-fp-diagnostic.yml](../../.github/workflows/engine001-bpred-s2v5-fp-diagnostic.yml). **14 synthetic E2 +14 S2v4 regression PASS**, 376/376 immutable original raw SHA reverified, 120/120 source family rows, 360 physical ROI, exact reconstruction global TP/FP and 3 local pixels, E0/algorithm blob SHA pinned, output data member SHA checked, 0 новых настоящих Egret рендеров. Original S0 BLIND 120 НЕ открывался.
- Первый [CI44663275087](https://github.com/Kiddos19882/AutoDraw/actions/runs/44663275087) SHA67027d5e **technical BLOCKED/FAIL до pixel audit**: Windows checkout CRLF нарушал runtime blob SHA, исходные Git blobs при проверке HEAD совпадали. Только CI workflow восстановил оригинальные byte-exact Git file bytes commit9d2aee; научные пороги, raw, code/source geometry и S2v5 frozen E0 **не менялись**. Final [CI44663535886](https://github.com/Kiddos19882/AutoDraw/actions/runs/44663535886) SUCCESS.
- S2v5 E2/CI **PASS означает доказанный аудит ошибки**, не S2 physical pixel safety, не owner-E/F image quality и не production. Исходный P4D18 protected original-white quality **FAIL**, P4D19 DEFERRED; E4 live/E5/exact run-bound CHALK `post.pointCount-pre.pointCount` NOT_RUN. `master`, Stage6, Bridge/Monitor, production painter/game renderer не изменялись.

## 4. Следующий шаг по исходной очередности

**S2 остаётся PARTIAL, M2/M4/M5 MODEL_ONLY и fail-closed при UNKNOWN**. Чтобы исследовать принятое [DEC-042](DECISIONS.md) разделение «FP модели» и «физический вред чужому цвету», следующий **BPRED-S3** изучает последовательную native RGB source-over и owner-цвет на real Egret, без premature adaptive acceptance. [S3 frozen E0](ENGINE001_BPRED001_S3_NATIVE_SOURCE_OVER_PREREG_2026-11-20.md) пререгистрирован до новых S3 код/тестов. Далее S4 independent BLIND, S5 global original E/F adaptive, S6 quality-preserving optimization. Исходные S2v4 H1/H3 и hard gates остаются FAIL/неизменными.
