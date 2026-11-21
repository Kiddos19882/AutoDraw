# ENGINE-001 / BPRED-S4-R1 / NG1 — готовность к независимому Egret E3 после SKC1

**2026-11-21. Анализ (E1) выполнен; НОВЫЙ Egret E3 = NOT_RUN; строгий S4 = BLOCKED.** Новые экспериментальные данные, нативные штрихи, acceptance thresholds, production или master не создавались/не менялись при этом аудите. Это **не повтор** S4-R0 проверки frozen P4D18 20 показателей. NG1 сопоставляет новую SKC1 карту с существующими рисками и критериями допуска, чтобы решить, можно ли сейчас обоснованно запускать independent S4 native validation. Основание: рабочая ветка `feature/image-geometry-optimization`, проверенный remote HEAD до анализа `f478fa9462567570abf0698607b48bbc68aaba2e`; последние 20 коммитов, доступные GitHub Actions, документация README/PROJECT_STATUS/TASKS/ROADMAP/AI_WORK_GUIDE и профильный код изучены. GitHub не подтверждает локальное состояние ПК/игры.

## Изученные действующие данные (новых измерений здесь нет)

1. [SKC1 signed E2](ENGINE001_BPRED001_S4R1_SKC1_ORIGINAL_EF_SOURCE_CONTRACT_E2_RESULTS_2026-11-21.md), [CI44913972626](https://github.com/Kiddos19882/AutoDraw/actions/runs/44913972626) исходный code SHA `877dc760259a509a2570e1a4bc70408f879caf1a`: 43/43 теста, настоящий P4D18 ZIP SHA/CRC/34 members PASS, source index/engine128/palette RGB E/F PASS. SKC1 `source_known_egret_protection_contract` в (ф) `tests/engine001_bpred_s4r1_generic_source_maps.py` **не** предсказывает отдельный игровой отпечаток и всегда возвращает `stroke_admission=FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION`.
2. [S4-R0 source/native readiness E1](ENGINE001_BPRED001_S4R0_SOURCE_KNOWN_READINESS_E1_RESULTS_2026-11-20.md) доказал исходную E/F геометрию и архивную native-целостность. [DEC-044](ENGINE001_BPRED001_S4_ELIGIBILITY_AND_VISUAL_SAFETY_DECISION_2026-11-20.md) прямо запрещает S4 BLIND без verified critical/owner/white protection и non-vacuous safety. `source_critical_rois()` — **три заранее заданных прямоугольника** (face/eyes/hands), НЕ полная разметка важного контура.
3. [P4D18 original native E/F](ENGINE001_B1R_P4D17_P4D18_NATIVE_FULL_REPAINT_RESULTS_2026-11-19.md) и read-only R0: E/F 2250/2261 physical painted pixels в protected original-white, 24/25 interior physical alpha0 holes, original-white contamination 4415/4445. Это исторические реальные source-native **FAIL качества**, не значение текущего SKC1.
4. [S3v2q true native owner](ENGINE001_BPRED001_S3V2Q_NATIVE_INCREMENTAL_MICROALPHA_OWNER_RESULTS_2026-11-20.md) показал foreign-owner RGB harm в 20 случаях; [S3v2r2](ENGINE001_BPRED001_S3V2R2_BOUNDED_REPEAT_CONTRAST_NATIVE_RESULTS_2026-11-20.md) показал 18 изменений owner в двух физических координатах. Следовательно исходный owner-index и исходный RGB-контур сами по себе не гарантируют safety per-stroke.
5. Reuse-first исходного native harness: (ф) `tests/run_engine001_b1r_p4d13_full_original_relaxed_finish.py::native_metrics/render`, (ф) `tests/run_engine001_b1r_p4d17_owner_physical_repair.py::physical_owner_score/score`, (ф) `tests/run_engine001_b1r_p4d18_physical_owner_edt_repair.py`, pinned Egret game bundle `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer `76d950e0a8911888a9df3b675b866519ecf7bba4`, исходный Firefox159, E/F logical crop x155..304, physical backing scale3. Возможность создания будущего native E3 harness **имеется**, но это не acceptance и не разрешение запуска S4 BLIND.

## Отдельная проверка полезности и невакуозности после SKC1 (арифметика из подписанного CI E2)

| Диагностическая величина | E_SOBEL90 | F_SOBEL90_LAB12 |
|---|---:|---:|
| Source logical full | 36 000 | 36 000 |
| Source white owner | 22 132 | 22 137 |
| Target nonwhite owner | 13 868 | 13 863 |
| Protected total SKC1 | 34 081 | 34 079 |
| Nonwhite protected = total protected − owner-white | 11 949 (**86.16%** nonwhite) | 11 942 (**86.14%** nonwhite) |
| Geometric core = remaining UNKNOWN | 1 919 (**13.84%** nonwhite) | 1 921 (**13.86%** nonwhite) |
| Verified independent safe stroke or admitted path | **0** | **0** |

Эти количества — **арифметический E1 вывод** по настоящим E2 SKC1 counts, не новое pixel-level испытание. `protected` включает source-white, поэтому **94.67% protected не означает 94.67% испорченного или незакрашенного изображения**. Ненулевая геометрическая зона в 13.84/13.86% nonwhite **целиком UNKNOWN**, а не verified safe для кисти. Ни `99% owner coverage`, ни protected foreign zero нельзя обосновать «покраской 0 штрихов»: это вакуозная безопасность при отсутствии полезной отрисовки. Цель — законченный визуально узнаваемый рисунок, не максимальный процент запрещённых пикселей.

## NG1 verdict и ограничения

| Гейт/вход | Статус NG1 |
|---|---|
| Archived source SHA/owner128/RGB/white и logical/physical привязка для E/F | **PASS E2 (наследуется от SKC1/R0; не новая проверка)** |
| Existing pinned true Egret/Firefox native harness | **AVAILABLE E1**, новая сессия NOT_RUN |
| Оригинальный white и RGB+owner edge diagnostic | **AVAILABLE**, но semantic critical completeness **UNKNOWN** |
| Независимая source semantic critical mask, действительно представляющая важные детали | **MISSING / BLOCKED**: 3 ROI + Sobel/Lab не являются ground truth |
| Пер-штриховые physical owner/white/contour false-safe и конечное native качество для нового SKC1 | **NOT_RUN / UNKNOWN**, исторические E/F FAIL сохраняются |
| Non-vacuous `ADMISSIBLE` с независимыми границами риска | **FAIL_NOT_READY**: zero admitted; all 1919/1921 core UNKNOWN |
| Сам независимый строгий BPRED-S4 BLIND120 | **BLOCKED** (не открывать); H8/second50 sealed |
| S5/S6, game E4/E5, exact run-bound CHALK | **NOT_RUN** |

**Решение:** входы уже подходят для подготовки **отдельного ограниченного исследовательского native Egret owner/white/contour диагностического протокола** на original E/F (с реальными native pre/post, fixed candidate strokes, original RGB/owner and blank; no S4 BLIND). Но входы **НЕ подходят для строгой S4 safety validation/admission**: исходный источник не даёт подтверждённой полной важной семантики, SKC1 не назначает ни одного SAFE штриха, а старое native качество FAIL. Не запускать строгий E3 только ради зелёного CI, не повторять уже завершённый R0/P4D18 и не маскировать 0 admitted как PASS.

**Один следующий шаг:** отдельно зафиксировать *prospective E0* для **одной конечной native Egret research-only проверки физической границы между known E/F owner и source-white/critical RGB contour на заранее определённых неизвестных пробах**, с настоящим original BoardPane/WebGL, immutable source SHA, blank/replay, per-stroke and final pixel RGB/alpha и заранее неизменными hard gates. Такая диагностика не является открытием S4 и не даёт права переносить SAMPLE-based «safe» на произвольные изображения. Если требуемую независимую семантическую безопасность подтвердить нельзя — итог `BLOCKED`, а не обход через ручные пиксельные метки или новые Lab/SLIC микропороги. После native evidence — отдельно решить исходную readiness. Production/Stage6/Bridge/Monitor/master и вся freeze-история остаются нетронутыми.
