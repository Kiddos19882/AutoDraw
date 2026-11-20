# ENGINE-001 / BPRED-S3v2g — целочисленный Canvas2D source-over: отрицательный результат (2026-11-20)

**Итог: E2/CI PASS; frozen scientific H1-P2 FAIL и H2-P2 FAIL.** Это результат только **offline E2** по уже просмотренному настоящему архиву Egret S3v2f; не новая нативная E3 проверка, не независимая S4 и не игровой E4. Протокол [S3v2g frozen E0](ENGINE001_BPRED001_S3V2G_CANVAS_INTEGER_SOURCE_OVER_PREREG_2026-11-20.md) Git blob `9dd47155d284f63c81cbb525ad757b137c287f11` заморожен до кода и расчётов. Source native [CI44710870514](https://github.com/Kiddos19882/AutoDraw/actions/runs/44710870514), source SHA `819b7fd20272e5ac87ead72ce0610687fa51cbf4`, raw artifact14617442073, original source Git blobs pinned.

## Воспроизводимость и технический первый отказ

Сначала [CI44712864253](https://github.com/Kiddos19882/AutoDraw/actions/runs/44712864253) original S3v2g code SHA `ef40d0a8cf6b6dc3df82cb2ad0e51285df9a5200` **FAIL technical** before computation at `BLOCKED_BPRED_S3V2G_SOURCE_MANIFEST_DRIFT`. Проблема проверки: исходный manifest создан Firefox/Windows Python, а Linux Python повторно вычислял координаты через `math.cos/sin` и требовал побитного совпадения `float` разных платформ, несмотря на 655/655 архивных SHA PASS. Зафиксировано как проблема *метода проверки*, не новой физики и не результат научного опыта.

Только research verifier (ф) `tests/run_engine001_bpred_s3v2g_canvas_integer_source_over.py` изменён коммитом `09446a0b7ed1d7ed45af4714e91f4f0f7631cdfa`: больше не перегенерируются trig floats в другой системе. Вместо этого проверяются original native manifest `experiment/E0/code`, 80 ID × варианты, frozen source/runtime plan SHA, все записанные исходные `SOURCE_PLAN.json`/`RUNTIME_PLAN.json` плюс неизменные **655/655 SHA256 ZIP members and CRC**. Никакого source pixel fallback, relaxed threshold или удаления случаев.

Финальный [CI44713169889](https://github.com/Kiddos19882/AutoDraw/actions/runs/44713169889) SHA `09446a0b7ed1d7ed45af4714e91f4f0f7631cdfa` technical **SUCCESS**. E2 10 новых S3v2g +12 S3v2f +14 S3 original **36/36 PASS**, Markdown audit PASS, original source archive656 ZIP entries CRC+655/655 SHA, frozen 20 owner pairs/40 ordered variants; [artifact14618675900](https://github.com/Kiddos19882/AutoDraw/actions/runs/44713169889/artifacts/14618675900). Самостоятельно загруженный S3v2g ZIP: CRC PASS, **2/2 output-member SHA** PASS, 20 results +40 input provenance rows.

## Frozen D1/D2: native Canvas и финальный WebGL

Исходный `P0` — без изменений original `s3.source_over` (straight sRGB double float64, rounding once). Заморожены до расчёта `P1` floor/floor, `P2` nearest-even/nearest-even и `P3` ceil/ceil с integer premultiply, ordered source-over и half-up unpremultiply; не адаптировать правила к данным. Одинаковые исходные H1 численные критерии по ROI: `max_channel_byte≤2` и `mean_channel_byte≤1`. Следующее QH Canvas→WebGL преобразование для D2 само по себе уже прошло prospective S3v2f и **не переобучалось**.

| Модель смешивания | Точный исходный Canvas /40 | После QH, точный WebGL /40 |
|---|---:|---:|
| P0 — исходный float source-over | **23** | **14** |
| P1 — integer floor | 0 | 0 |
| P2 — integer nearest-even | **18** | **8** |
| P3 — integer ceil | 0 | 0 |

Предварительно зафиксированные **H1-P2** требует **≥30/40** original Canvas, **FAIL** при18. **H2-P2** требует **≥30/40** WebGL, **FAIL** при8. Даже прежняя P0 точнее, поэтому P2/P1/P3 **отклонены как замена source-over**, никакого production promotion.

## D3: source representability и её пределы

Из 40 отдельных original Canvas owner-ROI (20 пар × A_ONLY/B_ONLY) проверены **8 295 полупрозрачных физических пикселей** (alpha1..254). По замороженной таблице обратимости `c=floor(255*p/a+0.5)`, `p∈[0,a]`:

- `UNKNOWN` на этом наборе: **0 из 8 295** пикселей.
- Не имеющих допустимого `p` каналов: **0**; имеющих несколько `p`: **0**.

Это доказывает лишь **единственность целочисленного p внутри выбранной модели полувверх** для исследованных JPEG-independent PNG-значений и альфы; не доказывает, что реальный внутренний Firefox Canvas использовал именно эти `p` до compositing, и не снимает требования выяснить точный путь stroke, маски, blend и readback. Сильные ошибки остаются при однозначной обратимости — проблема не решается одним округлением.

## Причина отрицательного вывода и следующий этап внутри S3

На новых original S3v2f 80 сценах QH **точно воспроизводит** переход уже отрисованного Canvas в WebGL (H1 PASS0 RGB ошибочных). Но простая попытка воспроизвести **само смешивание** из двух независимых PNG (P1/P2/P3) даёт FAIL. Сюда могут входить промежуточная альфа, порядок raster stroke, антиалиасинг, пересечение одного graphics path и его compositing; точный механизм пока **UNKNOWN**. Нельзя переписать исторический S3 H1 FAIL30/40, S3v2f H2 FAIL26/40 или выдавать P0/P2 за прошедший gate.

**NEXT строго S3:** прежде очередного приближения математикой зафиксировать отдельный E0 **S3v2h direct Canvas stroke-step observation**: реальный Egret/Firefox CanvasRenderer intermediate *после первого и второго фактического stroke*, исходный owner A/B и final Canvas/WebGL, с инструментированием `CanvasRenderingContext2D.stroke` вокруг original native calls и fail-closed provenance. Сопоставить, равен ли first-step screenshot настоящему isolated Canvas и что именно меняется в местах перекрытия, не допуская подгонки по новому нативному набору. Только после этого выбирать новую математическую модель и последующую независимую проверку.

S0 reserved BLIND **не использован**, P4D18 full original E/F protected-white/source-owner quality **FAIL**, E4 live/E5 independent/exact run-bound CHALK **NOT_RUN**. Stage6 executor, original engine, game renderer, Bridge, Monitor, production, master **не изменялись**.
