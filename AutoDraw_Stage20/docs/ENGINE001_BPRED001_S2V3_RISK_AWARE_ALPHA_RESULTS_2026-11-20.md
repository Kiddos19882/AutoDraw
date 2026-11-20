# ENGINE-001 / BPRED-S2v3 — native-sourced uncertainty guard, результаты

**2026-11-20. E2/CI PASS, H1/H2/H3 PASS, critical zero-FP safety FAIL; MODEL_ONLY.** Исследовательская ветка `feature/image-geometry-optimization`, окончательный test SHA `fe39bba16c8df21a8fa3f796da35323f240c7269`; исходный [E0 prereg](ENGINE001_BPRED001_S2V3_RISK_AWARE_ALPHA_PREREG_2026-11-20.md) фиксирован ранее на SHA `a812f70927641cb5b04bd8dfb0f8deed30b9899a` **до кода**. Предыдущая [S2v2 научная неудача](ENGINE001_BPRED001_S2V2_ISOTONIC_ALPHA_RESULTS_2026-11-20.md) сохранена, P4D18 full-original protected quality FAIL сохраняется. Не переименовывать «H1–H3 PASS» в «pixel-safe».

## 1. Проверенные первичные источники

- [CI44657226273](https://github.com/Kiddos19882/AutoDraw/actions/runs/44657226273) на `fe39bba16c8df21a8fa3f796da35323f240c7269`: обязательный `original-egret-alpha-residual-calibration-only` job **SUCCESS**; 16 новых synthetic unit E2 + 10 S2v2 + 14 S2v1 regression **PASS**, frozen prereg/source Git blobs verified, source native S1/S2v1/S2v2 archives and SHA verified, complete 120 scene families ×3 ROI, 30 per-width/held-out-angle quantile guards, ALL raw file SHA and final uploader PASS.
- [Сохранённый artifact14593881636](https://github.com/Kiddos19882/AutoDraw/actions/runs/44657226273/artifacts/14593881636) (43 228 bytes) содержит `report.json`, `CASE_ROWS_APPEND_ONLY.jsonl` (120 records, 3 locations each), `M4_FOLD_WIDTH_GUARDS.json` (30 train histograms/quantile tables), `WORST_MODEL_ONLY_CASES.json`. Исходные 363 S1 native files и parent S2v1/S2v2 source hashes проверены в CI; **0 новых native Egret рендеров и 0 S0 BLIND сцен**. Это офлайн анализ реально измеренных ранее Egret alpha.
- [Первый CI44657070988](https://github.com/Kiddos19882/AutoDraw/actions/runs/44657070988) на `487d071f`: **FAIL technical** 13/16 synthetic E2, три тестовые фикстуры не содержали `phase_x/y` (KeyError), до загрузки native datasets не дошёл. Исправлено **только metadata тестового fixture**, не формула, source sample или frozen E0; [general validation](https://github.com/Kiddos19882/AutoDraw/actions/runs/44657226342) на final SHA — обязательные jobs PASS.

## 2. M4 empirical quantile guard: что изменилось

M2 original `P4D16.area8` alpha0..255 **не изменена**. В каждом из трёх frozen held-out-angle folds на двух других углах TRAIN рассчитывается `q_width=quantile(abs(M2-native),0.995,method='higher')` среди всех pixels с `M2>0 OR native>0`; на test `M4 trusted_positive` только при `M2_alpha>=24+q_width`, остальные pixels `UNKNOWN`, включая предсказанный фон. Согласованные H1/H2/H3 проверены на 120 held-out CALIBRATION scenes, 360 correlated physical ROI.

| На той же CALIBRATION | M2 positive alpha≥24 | M4 trusted-positive |
|---|---:|---:|
| True positive (TP) | 346 712 | **341 139** |
| False positive (FP) | 2 167 | **63** |
| False negative (FN; включая UNKNOWN) | 559 | 6 132 |
| Доля TP M2, сохранённая M4 | — | **98.3926%** |
| Доля FP M2, оставшаяся M4 | — | **2.9072%** |

**H1: FP ≤10% M2 — PASS**, **H2: TP ≥90% M2 — PASS**, **H3: каждый угол FP≤10% и TP≥80% — PASS**. **Отдельный safety gate: FP=0 — FAIL**, поскольку имеется 63 FP. Поэтому **S2 ещё не готов** считать `trusted_positive` безошибочным: слово trusted означает лишь кандидатную оценку риска, не гарантию.

По 3 углам held-out `7°/73°/166°`: M4 FP `27/12/24`; сохраняемые TP по каждому углу около98.35–98.44%. По ширинам есть FP на 1/4/5/7/8/9/10; на2/3/6 калибровочный FP0 — **не доказательство** универсального поведения этих ширин. Все 3 copied positions имеют по **21 FP**; это равные счётчики, не отдельные независимые эксперименты. **18 unique scene families** содержат FP.

## 3. Диагностика причины — без постфактум «исправления»

Из frozen `predicted_alpha_error_bins` в сырых 120 записях S2v3: для **M2 без M4 guard** FP при `predicted alpha24..63` = **2106**; при `64..127` = **61**; при `128..255` = **0**. На этих же CALIBRATION ROI M2 при alpha≥128 дал `329883` правильных TP и **0 FP**, то есть приблизительно95.15% его TP. **Эта граница выведена постфактум из S2v3 CALIBRATION**, не было заранее зарегистрированной гипотезы для cutoff128, поэтому это только exploratory signal, не science PASS и не proof of safety. Отдельная независимая native E3 проверка на **новых** направлениях/фазах обязательна перед использованием cutoff как candidate gate; S0 BLIND120 сохраняем закрытой для S4.

Самая заметная структурная проблема: небольшой объём FP сосредоточен у физических краёв следа и воспроизводится при целочисленных перемещениях центров на копиях; строгого causal root-cause Canvas antialiasing это наблюдение **не доказывает**. Нужен source-faithful physical alpha/phase analysis, а не новая случайная repair-кисть. Residual и ошибки по каждому width/angle/phase/copy исходно сохранены, worst failures не удалены.

## 4. Ограничения и следующий шаг

**Политика:** любой `UNKNOWN` или не подтверждённая на независимой native dataset граница требует fail-closed/native replay, а не автоматического executor. При нулевом FP на CALIBRATION нельзя объявлять безопасность нового положения или иного Canvas renderer/browser. S3 owner-RGB composition, S4 independent blind, S5 global E/F и S6 optimization **NOT_RUN**; real E4, E5 и точный CHALK `post.pointCount-pre.pointCount` **NOT_RUN**; production/defaults/game/Stage6/Bridge/master нетронуты.

**NEXT строго внутри S2:** предварительно заморозить отдельную S2v4 native validation новых направлениях/фазах для конкретного candidate alpha≥128 и против M4, **не используя** S0 BLIND, затем выполнить тест настоящим Egret и сохранить любой FP, в т.ч. научные FAIL.
