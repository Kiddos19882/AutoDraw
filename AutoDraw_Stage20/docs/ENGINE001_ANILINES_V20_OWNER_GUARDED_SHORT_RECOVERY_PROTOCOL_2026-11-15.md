# ENGINE001_ANILINES_V20_OWNER_GUARDED_SHORT_RECOVERY — предварительный протокол

**Задача:** ENGINE-001. **Дата регистрации:** 2026-11-15, ДО запуска V20 и получения новых результатов. **Статус:** PREREGISTERED / NOT_RUN. Работа только в отдельном experimental runner; ни V18-B, ни production pipeline не меняются.

## Входы и baseline

- Исходник `testImages/wV6VeZI9S1Y.png` 200×320: SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a` (97308 bytes).
- Настоящий V14 AniLines `line-output.png`: SHA256 `2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b`, [run 43653371987](https://github.com/Kiddos19882/AutoDraw/actions/runs/43653371987).
- Замороженный V18-B [run 43677851946](https://github.com/Kiddos19882/AutoDraw/actions/runs/43677851946) SHA `3b23cea2df90a8383d5b2fe51c324af7623e271c`, artifact `14147096853`. Переиспользовать проверяющую функцию `frozen_b` из V19 для source-mask и B-roi. `B-paths.json` проверяется по SHA, baseline 410 strokes / 1792 synthetic vertices.
- V19 [run 43681321799](https://github.com/Kiddos19882/AutoDraw/actions/runs/43681321799): 5943 source skeleton pixels; V18-B covered within 1 source px 5792, missing 151, 83 components; 101 возле узлов. Отдельный V20 не пересчитывает и не переопределяет этот frozen control.

## Гипотеза и фиксированный кандидат

**H1:** малые отсутствующие компоненты AniLines можно безопасно вернуть отдельными короткими width1 paths в однозначных цветовых областях. **H0:** ни один компонент не проходит color-owner gate либо выигрыш мал при неприемлемой цене. Отрицательный результат сохранять.

1. `skeletonize(AniLines grayscale <128)`; V19 exact missing = skeleton AND NOT 3×3 dilation(V18-B source-mask). Разбить missing на 8-connected components, отсортировать по минимальному (y,x). Не восстанавливать отсутствующие пиксели вне frozen AniLines или рисовать соединяющие мосты.
2. Кандидаты: только компоненты размера **2–9** (исключить одиночные точки, крупные и шум), строго простые цепочки 8-neighbor с ровно двумя degree-1 концами и degree<=2 у всех узлов. Детали с ветвлением/cycles отбрасывать. Если некоторые диагонали создают 8-connected triangles, не удалять их постфактум — отклонить. Маршрут содержит все точки компонента ровно один раз, соседние точки 8-connected; никаких RDP/shortcut и новых source координат.
3. Зафиксировать logical mapping (x*.75+155, y*.75), raster preview OpenCV LINE_8 width1; заранее проверить точное совпадение пикселей source-path raster с AniLines binary либо отклонить кандидат. Не выполнять brush fill и не утверждать native-Egret equivalence.
4. **Консервативный owner gate:** получить V19 frozen palette (логическая белая 460×240, исходник resize LANCZOS 150×240 в ROI x155..304, global MEDIANCUT 8, no dither). Для каждого результирующего логического пикселя, включая OpenCV LINE_8 между вершинами, все классы в его 3×3 окрестности внутри 460×240 обязаны совпасть с owner пикселя. Background (самый частый класс) запрещён. Если пиксель вне ROI, фон или другой класс поблизости — отклонить путь целиком. Этот conservative guard — proxy и не даёт гарантии игрового footprint/3 px; не разрешает смешанные color segments.
5. Выводить B контроль без изменений и **только добавочные маршруты**; каждому явно присвоить owner label и source/logical coordinates; цвет для контурного preview остаётся (49,38,43), а реальный owner цвет не объявляется. Писать все кандидаты и причины отклонения в числовой отчёт. При нуле разрешённых путей — E3 diagnostic PASS, **geometry improvement FAIL/NO_GAIN**.
6. Сравнение: число исходных/принятых/отброшенных компонент, число новых strokes/vertices/length, исходная и итоговая skeleton within1px, raster outside AniLines beyond1px, максимальная длина и owner-neighborhood violations=0 для принятых маршрутов. Базовый V18-B 410 paths / 1792 vertices не переписывать. Quota: до 100 новых strokes / 900 vertices; сверх — fail-closed. Baseline маска и SHA исходника immutable; output directory запрещает overwrite.

## Проверки и границы

Synthetic tests: 2/3/8px simple chain accepted in uniform non-background interior; singleton, cycle, branch, >9, foreign source pixel, palette boundary / background neighborhood, out-of-ROI and corrupted artifact rejected; deterministic route and unchanged V18. В CI authentic V14/V18 artifact SHA checks, five V19 baseline guards и SHA derived PNG/JSON. Только E2/E3 offline reproducibility, не художественный/семантический PASS. Базовые требования color-fill >=99% coverage, диагностический допуск 3 logical px, E4 exact `CHALK = post.pointCount-pre.pointCount` и E5 independent validation не менять. Не изменять Stage6, executor, Bridge, Monitor, production, `master`.
