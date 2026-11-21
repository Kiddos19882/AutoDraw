# ENGINE-001 / BPRED-S4-R1 / FC1 — реальный полный новый Egret-проход: E2/E3 PASS технически, качество FAIL/PARTIAL

**Дата:** 2026-11-21. **Задача:** FC1. **Протокол:** [FC1 frozen E0](ENGINE001_BPRED001_S4R1_FC1_FRESH_CHAIN_EGRET_PREREG_2026-11-21.md), Git blob `e026b0ef82f04ecb979e5366d5c582162c60052a`, зафиксирован **до реализации**, не изменялся. **Основной принцип:** [DEC-046](DECISIONS.md#dec-046-autodraw--главная-цель-узнаваемый-полный-рисунок-а-не-абсолютная-безопасность-штрихов) quality-first и [DEC-047](DECISIONS.md#dec-047-новые-сквозные-алгоритмы-проверяются-только-свежей-полной-цепочкой-без-наследования-старых-результатов) new full chain only.

## Версия и проверка

- Изменения: [FC1 research runner/test/native workflow code SHA `58869a0`](https://github.com/Kiddos19882/AutoDraw/commit/58869a0019d88fecbdb51e16e4139cd36707594e); [README E0 indexing `14e73c7`](https://github.com/Kiddos19882/AutoDraw/commit/14e73c72bf8f4194d9659605a2cf654fc5ddabcb); [Pillow no-explicit-mode `7cc5378`](https://github.com/Kiddos19882/AutoDraw/commit/7cc5378b98edf435deff5e12c2489a4d5d34ae15).
- **[Native FC1 CI44920332768](https://github.com/Kiddos19882/AutoDraw/actions/runs/44920332768)** exact SHA `7cc5378b98edf435deff5e12c2489a4d5d34ae15`: job completed **SUCCESS**: seven synthetic E2 regression tests, game+renderer+E0 Git blob SHA, original PNG SHA, Markdown index, Firefox159 true original Egret native **blank alpha0 + full fill + full fill/repair/new outline**. All final raw files validated SHA against report, **E3 technical PASS**. [AutoDraw validation run44920332767](https://github.com/Kiddos19882/AutoDraw/actions/runs/44920332767) on same SHA completed SUCCESS (only its covered jobs).
- **[FC1 raw artifact14713755860](https://github.com/Kiddos19882/AutoDraw/actions/runs/44920332768/artifacts/14713755860)**, 1,761,625 bytes, GitHub artifact ZIP SHA256 `ec3af7f0bc64659637046c076c51a0f773fe7069504fbbd199d552b8a97a338f`; separately downloaded with exact SHA256, ZIP CRC PASS, **14/14 report-listed files independently SHA256 PASS** (15 ZIP members including report).
- Key visual file `00_VISUAL_REVIEW_FRESH_CHAIN.png`, SHA256 `af83c8d35d648b41620c02891c0b39c787c044807cf792d1e4adf9febc038ba3`: four panels *original RGB / fresh game128 target / real native fill / real native final*. `05_ACTUAL_EGRET_FILL.png` SHA256 `947c8fa3b66780ce42e175230c1f4ad8e55dad17d4c647c698a2813597a70efd`; `06_ACTUAL_EGRET_FINAL.png` SHA256 `128538c55d4b4045409388eaec76e23151021a5cd01fa3f367e7cb952beeff86`.

## Происхождение — доказанный в коде input contract E1 + runtime SHA E3

Оригинал `testImages/wV6VeZI9S1Y.png` bytes SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a` (200×320 RGB) → **в этом запуске** RGBA/LANCZOS 150×240 → новый nearest-Lab по **игровым 128 swatches** из pinned engine blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388` → новые source RGB/owner edges → НОВЫЙ adaptive distance-aware horizontal/vertical brush planner → реальные Egret blank/fill → width1 repair только по текущим raw native alpha → свежий source-edge outline в конце → реальная финальная Egret RGBA/Png. Renderer Git blob `76d950e0a8911888a9df3b675b866519ecf7bba4`, Firefox159. **Никакие старые E/F/G32/V44/P4D artistic owner/region/mask/plan/PNG не были считаны или подмешаны в pipeline.** Старые Python modules используются только как fixed palette parser, pinned test renderer/native transport. Карта owner128 остаётся `PROVISIONAL_LAB_NEAREST_NOT_SOURCE_OWNER`, не ground truth; универсальность на других исходниках пока не доказана.

## Измерения, строго отличать объекты

| Метрика | Fresh native fill | Fresh final после repair+outline |
|---|---:|---:|
| Количество native source nonwhite logical candidate cell | 15,389 | 15,389 |
| Cell с хотя бы одним физическим alpha≥24 внутри соответствующего 3×3 | 15,272 | 15,389 |
| Cell с **нулём** ink alpha≥24 | 117 | 0 |
| Source white owner cell с каким-либо ink alpha≥24 | 1,996 | **3,505** |
| MAE RGB по конечному white-composited native в 150×240 относительно свежей game128 цели | 6.1553 | **33.5374** |
| MAE RGB относительно свежего original logical RGB | 8.3658 | **35.0377** |

**Важно:** «any ink 15389/15389» — только факт хотя бы одного backing pixel alpha≥24, **не** заполнение 100% площади, не полная корректность RGB и не native quality PASS. Точная alpha/цветовая структура видна на PNG; нет данных об игровом CHALK.

**Fresh stroke plan:** 10,479 fill, 70 repair из текущей native fill (не старый ремонт), 298 новых контурных; final **10,847 strokes** (НЕ CHALK); 10,781 ширина1, 49 ширина3, 14 ширина5, 3 ширина7, 0 ширина10. Цветов game128 предложено 53, edges provisional owner 18,264/36,000, original RGB source edges 9,219/36,000. Это показывает избыток width1/мелких областей — не повод гоняться за случайными процентами.

## Научный и визуальный вывод

**Технически E2/E3 PASS, полная цепочка реальна. Визуальное качество финала `FAIL/PARTIAL`; production NO_PROMOTION.** Контрастное тёмное исходно-цветонезависимое контурирование (единая самая тёмная игровая краска) после fill **сильно ухудшило** рисунок: детальные формы ещё узнаются, но финал чрезмерно исчерчен чёрными линиями; white-source ink повысился 1996→3505, native logical RGB MAE original 8.3658→35.0377. Заполнение **до** контура лучше узнаваемо, но многие маленькие белые отверстия/точки в тёмных областях остаются видимыми, хотя 3×3 any-ink число высокое. По непосредственному PNG E1 visual reading чёрная обводка — **существенный дефект**, достойный одной целевой коррекции; не требовать абсолютной safety новой теоремой.

Пользовательское отдельное визуальное принятие исходного output на момент подписания: **NOT_RUN/UNKNOWN**. Не подменять его численным RGB/нативным technical PASS.

**Предыдущие технические FAIL сохраняются:** [Markdown run44919716953](https://github.com/Kiddos19882/AutoDraw/actions/runs/44919716953) замороженный E0 отсутствовал в README index; [первый FC1 run44920079432](https://github.com/Kiddos19882/AutoDraw/actions/runs/44920079432) E2 7/7 PASS, native НЕ запускался из-за того же unindexed Markdown. README исправлен на 14e73c7; [Markdown CI44920259458](https://github.com/Kiddos19882/AutoDraw/actions/runs/44920259458) SUCCESS. Приёмочные пороги/исторические E0 и P4D18 native FAIL не пересмотрены.

## Следующий ровно один осмысленный шаг

Не открывать новый NG safety/admissibility поиск. Полученный опыт **исправляет уже обнаруженную существенную визуальную ошибку**, а не микро-погрешности: разработать **один отдельно замороженный FC2 исследовательский вариант с согласованной с локальным original/owner цветом обводки вместо глобальной чёрной**, заново прогнав *всю* цепь от оригинала (без FC1 архивов в input), сохранить side-by-side + native raw и сравнить только этот значимый визуальный эффект. Белые дырки заливки остаются следующей **отдельной** проблемой лишь если финальный рисунок FC2 действительно их демонстрирует. Не объявлять научный S4 PASS; H8/BLIND120/second50 sealed; formal S5/S6/E4/E5/exact CHALK NOT_RUN. Production/master/Stage6/Monitor/Bridge untouched.
