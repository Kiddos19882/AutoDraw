# ENGINE-001 / BPRED-S3 — две реальные RGB-краски, ordered source-over (2026-11-20)

**Заключение:** E2/E3/архив технически PASS; предзарегистрированная научная **H1 FAIL**, **H2 PASS**, C1 **MODEL_ONLY_UNSAFE**. Frozen E0 [S3](ENGINE001_BPRED001_S3_NATIVE_SOURCE_OVER_PREREG_2026-11-20.md), существовавший до разработки: Git blob 61996b3253c794c5cd16ca989a70628b6609669f. Новая исследовательская реализация commits 7a40a209 (runner), b151371f (E2), 6dedf6dd (CI); проверен исходный GitHub SHA **6dedf6ddfde36db17f07fc0aa00dd463dc525ca8**.

## 1. Первичные данные и техническая проверка

- [GitHub Actions CI44683117471](https://github.com/Kiddos19882/AutoDraw/actions/runs/44683117471) завершился SUCCESS; 14 новых S3 unit + 14 S2v1 regression +14 S2v4 regression **42/42 E2 PASS**, исходный скрипт Egret и браузер Firefox159.0.1 Windows, BoardPane 460×240 logical / PNG 1380×720 physical.
- **80 первичных настоящих Egret PNG:** width1..10 × CROSSING/NEAR_PARALLEL_OVERLAP × A_ONLY/B_ONLY/A_THEN_B/B_THEN_A; **10 byte-exact replays PASS** и **1 blank alpha0 PASS**: всего 91 PNG. A=0x503D35, B=0xC54191 доказаны на изолированных нативных пикселях alpha255; source strokes и runtime transport раздельно хешированы. S0 BLIND не использовался.
- [Исходный архив S3 — artifact14604987986](https://github.com/Kiddos19882/AutoDraw/actions/runs/44683117471/artifacts/14604987986): ZIP содержит 295 файлов, 91 настоящих PNG, 40 сжатых карт C0/C1 errors, планы/manifest и raw rows. CI проверил 294/294 member SHA; независимая повторная ZIP CRC и 294/294 SHA **PASS** по скачанному архиву. report.json в списке member SHA не хеширует сам себя.
- Источники P4D3, gameEngine, game_renderer_reference и S2 M2 проверены Git blob SHA; production/Stage6/Bridge/master не изменены.

## 2. Предзарегистрированные исходы

| Gate | Замороженный критерий | Факт | Статус |
|---|---|---|---|
| H1 C0 actual isolated native RGBA source-over → true AB/BA | В каждой из 40 композиций max channel≤2/255 и mean≤1/255 | 10/40 выдержали; 30/40 нет; max=6/255, worst mean=0.1287/255 | **FAIL** |
| H2 native AB vs BA | Хотя бы 1 физический pixel RGB отличается при alpha≥24 в каждой из 20 пар | 20/20 PASS; суммарно 9514 order-different физических пикселей по 20 независимым сценам | **PASS** |
| H3 C1 original M2 area8 source-over | owner/RGB риск диагностический, не safety PASS | alpha24 TP71486 FP236 FN48; high-alpha128 false-safe0 на этой выборке, но high-alpha wrong RGB>2 **1420** | **MODEL_ONLY_UNSAFE** |

H1 несоответствие: 1994 RGBA-differing физических пикселя из 40 ordered cases, **все 1994 лежат внутри native overlap двух изолированных отпечатков** (outside overlap=0). Все 20 CROSSING композиций H1 FAIL; из 20 NEAR_PARALLEL 10 PASS/10 FAIL. Изменения по alpha каналу присутствуют лишь в 13 channel observations (11 × −1, 2 × +1). На RGB ошибки чаще −1/−2, максимальная абсолютная ошибка R=6, G=5, B=4. Эти наблюдения — E1/E2 posthoc forensic на raw, не пересмотр H1.

**Не доказана первопричина.** Данные совместимы с потерей точности/промежуточным premultiplied alpha, Canvas2D внутри GraphicsNode и/или WebGL texture conversion; по конечным PNG невозможно назвать виновную стадию. [WebGL спецификация](https://registry.khronos.org/webgl/specs/latest/1.0/) допускает потери при un-premultiply; [HTML Canvas 2D](https://www.w3.org/TR/2021/SPSD-2dcontext-20210128/) оговаривает lossy premultiplication. Гипотезы требуют нативной промежуточной Canvas instrumentation, а не новой posthoc H1 формулы.

## 3. Отрицательный вывод и один следующий шаг

Оригинальный H1 остаётся **FAIL**. Нет разрешения заменять max2 на max6, принимать RGB FP≤236, считать 0 high-alpha128 FP на обучающей сцене независимой безопасностью или заявлять source E/F owner protection. P4D18 protected quality FAIL сохраняется; E4/E5/live game/exact run-bound CHALK NOT_RUN. DEC-042 adaptive policy только будущий research proposal.

**NEXT по тому же BPRED-S3:** [S3v2 frozen E0](ENGINE001_BPRED001_S3V2_NATIVE_CANVAS_COMPOSITING_DIAGNOSTIC_PREREG_2026-11-20.md) — захват настоящей промежуточной Canvas2D stage против final WebGL в рамках того же исходного BoardPane, без обновления модели, критериев, геометрии или S0 BLIND. После подтверждения механизма — отдельное решение о продолжении S4 independent BLIND, затем S5 original E/F global и S6 оптимизация.