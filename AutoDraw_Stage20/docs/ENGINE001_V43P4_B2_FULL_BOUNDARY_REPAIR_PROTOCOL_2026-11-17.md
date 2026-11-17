# ENGINE-001 / V43-P4 B2-FULL — новая адаптивная заливка с пограничными микромазками

**Пререгистрация:** 2026-11-17, ДО создания полного B2-FULL планировщика и native-рендера. **ID:** ENGINE001_V43P4_B2_FULL_ADAPTIVE_BOUNDARY_REPAIR. **Статус:** REGISTERED / IMPLEMENTATION NOT_RUN. Отдельный эксперимент, не исправление frozen B0/B1.

## Доказательства и гипотеза

Исходный PNG wV6VeZI9S1Y.png SHA256 07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a, logical ROI 150×240, board 460×240, MEDIANCUT8 owners4–7.

- Контроль A — пользовательский V44-B: 1945 старых paint strokes + 410 точных цветных контуров последними, 2355 strokes/5682 synthetic vertices NOT CHALK, [native V44-B CI43813812976](https://github.com/Kiddos19882/AutoDraw/actions/runs/43813812976).
- Замороженный B0 [CI43983619222](https://github.com/Kiddos19882/AutoDraw/actions/runs/43983619222): 955 новых paint +410 contours, native coverage alpha24 83.10/87.60/80.46/94.75%, RGB MAE19.93 vs A11.13, excessive within3px foreign pixels — QUALITY FAIL.
- Замороженный B1 [CI43986256204](https://github.com/Kiddos19882/AutoDraw/actions/runs/43986256204): 105 новых paint, native alpha24 coverage 3.58/20.61/6.15/81.01%, too much missing fill — QUALITY FAIL.
- Изолированный [B2 micro Egret CI43987609480](https://github.com/Kiddos19882/AutoDraw/actions/runs/43987609480): на 12 разнесённых исходных singleton пикселях короткая линия длиной0.25 логического px и шириной2 или4 закрасила 12/12 целевых 3×3 backing-плиток на alpha24 и128; foreign ink alpha24 ширина2=237, ширина4=955, превышений >3logicalpx0, ZIP SHA256 99af82b2142303bd82bcc6de66d482745c08331b3e3d7a3f89d24f4e1ab56bfc. Это не доказательство для всех 690 singletons.

**Гипотеза E0:** широкие ориентированные проходы для внутренних цветовых зон плюс *короткие изолированные width2 микромазки* для остаточных owner pixels могут улучшить покрытие без длинных boundary-bleeding width2 маршрутов B0. Проверить на полном Egret и визуально; модельная геометрия — не фактическая игровая кисть.

## Зафиксированный метод первого B2-FULL до тестов

1. Источник только frozen original MEDIANCUT8. Не копировать НИ ОДИН старый paint из A, B0 или B1; генерировать новые ID p4-b2-OWNER-ORDINAL. RGB каждого paint owner из неизменного V44-B A mode: c4=15921900, c5=14466476, c6=11174513,c7=5191999. 410 оригинальных RGB V44-B detail ID, points, width, color и order LAST побайтово сохраняются. Классы строго4→7, вся логическая и PNG геометрия как A.
2. **Широкие внутренние проходы:** переиспользовать ТОЛЬКО функцию генерации исходных candidate geometry V43-P4 для widths10→6→4, восемь frozen angles (0,30,45,60,90,120,135,150), изначальные пороги MIN_NEW12/8/6, выбор максимальной ещё не покрытой площади собственной original source mask с фиксированным candidate-index tie-break. НЕ копировать B0 stroke JSON, его решения для width2 или уже просмотренные PNG для выбора координат.
3. **Пограничный микроремонт:** для каждого остаточного пикселя source класса4–7 создать candidate с двумя НЕ одинаковыми точками, разделёнными0.25 logical px внутри данного owner pixel: попеременно horizontal (x+0.125,y)→(x+0.375,y) и vertical (x,y+0.125)→(x,y+0.375) по стабильному порядку (owner,y,x). Номинальный width2; не соединять разные компоненты длинной линией. Ранжировать candidates по наибольшему числу оставшихся own source pixels, которые они покрывают в **MODEL_ONLY OpenCV footprint**, стабильный tie-break (y,x,orientation). После каждого кандидата пересчитать модельный uncovered set; минимальный положительный gain1. Все MODEL_ONLY foreign required pixels и near-border classes записывать как диагностику, но ни одну модель не считать native coverage.
4. **Строгий resource fail-closed:** ни один кандидат не передавать Egret при более чем3000 TOTAL strokes или5900 synthetic vertices, включая frozen410 detail с1792 vertices; при two-point paint верхняя граница2054 новых paint strokes. Если resource exceeded, вернуть BLOCKED_RESOURCE с фактическим attempted count и unmapped source masks; **НЕ обрезать** лишние строки и не заявлять частичный рисунок как прошедший quality. Персональные source-only компоненты с нулевым покрытием сохранять как отрицательный результат. Выход содержит source SHA, labels SHA, fixed parameters, все generated paint IDs, per-color widths/missing pixels, resource metrics, safe_to_execute=False, E3=NOT_RUN.
5. Пороговое решение не перенастраивать по результату. После первого source-only B2-E2 сначала проверка детерминизма (повторный JSON SHA), resource cap, original0 paint, original410 detail required and full owner accounting. Если source-only blocker — сохранить исходный результат и планировать новый B3 вместо незаметного изменения B2.

## Первый полный native E3 только после resource E2 PASS

Использовать существующие real-Egret native_batch и frozen source V44-B A pixel RGBA exact. Новый opt-in метод под B2 IDs/widths — не изменение V35/V36/B0/B1 defaults. Один Windows CI: проверить original source A/B0/B1 SHA, A replay **перед** B2, затем B2 full composite + color4/5/6/7/100 RGBA 1380×720, alpha24/128 per-class recall, foreign overlap включая <=3px, foreign/exterior >3px, full/warm RGB MAE vs original A, визуальные cropped face/hair/hands/clothing, original410 contours LAST, color switches, total strokes/vertices, все PNG/JSON SHA и negative evidence. Не пересобирать и не перезаписывать B0/B1.

**Гейты неизменны:** каждая required class4–7 >=99% на alpha24 и128, foreign/exterior >3logicalpx отсутствуют, узнаваемость и детали не хуже пользовательского V44-B, full/warm MAE без регрессии против A, лимит3000/5900. CI execution SUCCESS != quality PASS. При FAIL следующая коррекция только отдельно зарегистрированный B3. Никакой E4/live или game exact CHALK без run-bound post.pointCount - pre.pointCount; E5 отдельно. Никаких изменений master, Stage6, Monitor, Bridge или production.

## Порядок работы

(1) Отдельные source planner + unit E2/CI, сохранение source-only результатов даже при BLOCKED_RESOURCE. (2) Только если E2 и cap выполнены — отдельный opt-in Egret native A/B2. (3) Визуальный просмотр и quality assessment с frozen B0/B1 evidence. Источники для reuse: tests/run_engine001_full_adaptive_fill_v43p4.py::candidates_for_width, tests/run_engine001_v43p4_b2_singleton_native.py, V44-B frozen archive validator and native_batch, исходные metrics; НЕ переписывать старые реализации.


## First implementation, before CI result — 2026-11-17

Created standalone (ф) [B2-FULL source planner](../tests/run_engine001_v43p4_b2_full_source.py), commit `f2efa30f`, (ф) [source regression](../tests/test_engine001_v43p4_b2_full_source.py), commit `1a6da790`, and (ф) [source-only CI resource gate](../../.github/workflows/engine001-v43p4-b2-full-source.yml), commit `0f619a59`. Source output under distinct ID has hard resource check and `native_allowed=false`; on cap crossing reports `BLOCKED_RESOURCE`, first rejected route, projected stroke/vertex count and remaining source class pixels, never silently crops or sends partial result to Egret. This is E1 implementation; actual E2 CI PENDING/UNKNOWN. No full-image B2 E3, E4/E5/CHALK.
