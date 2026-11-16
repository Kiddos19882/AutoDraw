# ENGINE-001 / V43-P4 — полная замена старой заливки адаптивной

**Пререгистрация:** 2026-11-16. **ID:** `ENGINE001_V43P4_FULL_ADAPTIVE_FILL_REPLACEMENT`. **Статус:** APPROVED PLAN / IMPLEMENTATION NOT_RUN. **Ветка:** `feature/image-geometry-optimization`. **Исходная точка плана:** `8273918226ff221dc94faf7a212e959a4c49fa49`. Пользователь прямо согласовал отказ от поштучной замены: **полностью исключить 1945 старых штрихов paint в новом варианте, создать адаптивную покраску с нуля, а найденные ошибки исправлять затем**.

## 1. Что уже проверено и почему сменили направление

- Исходный источник: `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; RGB200×320, рабочий ROI150×240, логическая доска460×240, x155..304, нативный backing1380×720. Frozen 8-color MEDIANCUT с пропуском классов0–3, обязательные классы4–7. Не изменять палитру, исходный crop и скейл для первоначального A/B сравнения.
- **A/эталон:** V37-P2-C `1945` width2 paint + **оригинальные 410 RGB-адаптированных цветных contour strokes V44-B LAST**, всего2355 strokes/5682 synthetic vertices NOT CHALK. [V44 CI43813812976](https://github.com/Kiddos19882/AutoDraw/actions/runs/43813812976), head `0a58bf36fa9cc3f72803563d4617622987812498`, E3 SUCCESS; B выбран пользователем как лучший визуальный, full RGB MAE11.13399074, warm MAE16.42272007. Контуры V44-B должны быть **побайтово одинаковыми в ID, RGB, width, points, порядке и layer**; **не путать** с исходной тёмной V35-B.
- [P3a3 CI43864508620](https://github.com/Kiddos19882/AutoDraw/actions/runs/43864508620) E3 real Egret изолированно: width4/6/10 прошли измерение 3 кандидатных strokes/ширину, width20/30 `NO_ELIGIBLE_PATHS` при старом генераторе; этот результат **не запрещает ширины20/30 в иных геометриях**, но не подтверждает их пригодность для P4.
- [P3b-P0 CI43878183627](https://github.com/Kiddos19882/AutoDraw/actions/runs/43878183627): E3 capture PASS, **0/18** полностью заменяемых старых линий; [P3b-P1 CI43882838806](https://github.com/Kiddos19882/AutoDraw/actions/runs/43882838806): E3 capture SUCCESS, width4/6/10 по12 старых штрихов, **0/36** полностью заменяемых. Текущая попытка подменять по одной линии не переносится в P4. Не использовать `P3b` как обязательную зависимость или posthoc менять её negative results.

## 2. Цель и сравниваемые варианты

**A (замороженный контроль):** полный оригинальный V44-B 2355 strokes. Реконструировать через существующие `run_engine001_boundary_shift_native_v39.verified_input`, `engine001_adaptive_color_outline_v44.adaptive_recolor(...,'B')` и `engine001_paint_then_detail_v35.native_strokes` / существующий V44 native runner. Входные архивы V35 и V37-P2-C брать только из GitHub Actions, проверять manifest SHA, source identity и пиксельное совпадение A с замороженным V44-B перед сравнением. Если A расходится: `BLOCKED_BASELINE_DRIFT`, остановить B.
**B0 (новая заливка):** удалить **все** оригинальные 1945 paint strokes (0 retained), генерировать новые strokes **из исходных цветовых масок**, обработать все необходимые классы4–7, затем неизменные 410 V44-B contours последним слоем. Ни единый штрих A paint не копировать/не оставлять как fallback; исправления B идут собственным новым adaptive planner.
**B1 (исправления):** отдельная версия того же экспериментального направления и новый зафиксированный набор corrections только после архивирования первого полного B0: закрытие дыр, коррекция чужих цветов и краёв, сохранение контуров. Не перезаписывать B0 и не подбирать его параметры после просмотра результатов.

## 3. Последовательность реализации B0 — обязательные контрольные точки

**P4.0 | Подготовка baseline (E1/E2):** взять frozen labels/source/контуры, воспроизвести A и проверить pixel exact replay. Записать input SHAs, Python/Node/renderer версии, class/component count, сам пакет frozen `A`. Этот этап допускает только read-only reuse существующих harness без нового рендерера.

**P4.1 | Новый компонентный planner (E1/E2 MODEL_ONLY):**
1. Для каждого класса4,5,6,7 получить связные компоненты собственной маски. Определить площадь, ширину через distance transform, локальное направление по PCA/медиальной оси и карту узких мест; учитывать компоненты и дырки независимо, но не терять ни одну обязательную исходную область. Не утверждать качество кисти по proxy-геометрии.
2. Проходы *от больших к меньшим* по **номинальным Egret width10,6,4,2** с фиксированной именно этой очередностью. Width10 применять лишь там, где условия ширины, сегмента и близости границы удовлетворяют модельным ограничителям; 6/4 — средние и узкие; 2 — источниковый adaptive-gap fallback, **не копия** старых горизонтальных A strokes. Width1 и 20/30 не включать в B0 автоматически: отдельный эксперимент/версия при необходимости и native footprint evidence для новых размеров и кривизны.
3. Для широких связных областей — параллельные полосы *вдоль локальной длинной оси* / bounded oriented sweeping, для сложных — рекурсивно разбивать на локальные зоны с новым направлением. Мелкие структуры — тонкие связные трассы по медиальной оси. Предотвращать лишние переключения цветов, не соединять несвязанные компоненты чужим цветом.
4. Внутренние центровые маршруты предлагать при запасе от чужого класса, предварительно проверять owner и ROI. **Не считать** circular/capsule/rectangle/DT-модель доказательством Egret; только последующий native footprint validation. Принудительно не расширять оригинальный цвет за3 логических px, не изменять допуск после FAIL.
5. Сгенерировать полную последовательность B0 с цветными группами/счётчиками; воспроизводимость: source hash, deterministic fixed order, random seed если используется, algorithm version. Явно подтвердить `original_paint_retained=0`, `detail_410_exact=True`, `detail_last=True`, каждый paint stroke относится только к классу4–7; никакого пути в Stage6.
6. Сохранить planner JSON, source-only candidate masks, selection diagnostics, ошибки и `safe_to_execute=False` до E3. Ресурсные preflight caps: максимум3000 total strokes и5900 synthetic vertices (ранее принят лимит native harness, **не CHALK**). При превышении **BLOCKED_RESOURCE** с исходным отчётом; не скрывать лишние strokes и не изменять gate.

**P4.2 | Первый полноценный native B0 (E3):** Windows CI reuse **архивного BoardPane/Egret WebGL** и `native_batch`, тот же движок и scale для A/B. Сначала native render baseline A; затем **весь B0**; сохранять раздельные color4/5/6/7 RGBA и composite, raw PNG, JSON, SHA256, route IDs, source masks/foreground, positive/negative outcomes. Не подменять Egret Pillow/OpenCV или SVG. 410 цветных контуров обязательно последними. Запуск B0 даже с низким качеством документировать как FAIL, а не незаметно исправлять перед архивированием.

**P4.3 | Объективная оценка + визуальное предъявление (E3):** coverage для каждого требуемого цвета4–7 на native alpha24 и128, пропущенные компоненты, внутренние чужие цвета, внешний силуэт, по отдельности превышение **3 логических px**. Рендеринг сохраняет и сравнивает оригинальную RGB MAE full и warm ROI, детальные crops лица/волос/рук/одежды, места контура, изломы и полосы, длину путей, число штрихов, число synthetic vertices и переключений цветов. Сопоставить A/B рядом и дать пользователю оценить узнаваемость; числовая MAE не заменяет решение по восприятию.

## 4. Как исправляем ошибки ПОСЛЕ первого полного B0 (B1, B2, ...)

Создать **новый frozen correction experiment ID до каждого** коррекционного набора, сохраняя исходный B0 PNG и JSON и полный negative evidence:
- **holes/coverage:** по native B0 alpha каждого цвета выделять недокрашенные компоненты, тонкие детали, провалы возле контуров; планировать новые width2/4/6 (или новые native-verified widths), не возвращать старый paint.
- **foreign color/leakage:** выявлять actual native пиксели другого класса/за силуэтом, убирать или менять только конкретные новые мазки, проводить отдельно native проверку и сравнение whole image, отслеживать последствия удаления.
- **recognizability:** оценить силуэт, лицо, руки и важные линии пользователя; не улучшать только CHALK/MAE ценой читаемости. Не менять 410 исходных V44-B контуров ради скрытия пробелов.
- Поправки не могут менять исходные acceptance thresholds, P4-B0 архивы, source SHA, B0 ID или A. Если correction меняет методику — новый ID/версия.

## 5. Фиксированные критерии и границы доказательств

- **Full-image native quality gate:** required source classes4,5,6,7 по **>=99%** каждый (не среднее); crossing за чужой цвет **<=3 logical px**, внешний выход **<=3 logical px**, контуры/мелкие детали визуально не хуже эталона V44-B. На E3 это нативный offline рисунок, **не** E4 live game.
- **Ресурс:** <=3000 native harness strokes, <=5900 synthetic vertices; дополнительно сравнить A2355/5682 и B0; если ресурсы не сократились, честно указать `NO_RESOURCE_SAVINGS` и не называть результат оптимизацией, даже если B0 красивее. Экономию не заявлять в units CHALK.
- **Production promotion BLOCKED** до независимой E5 и реального run-bound E4: exact `CHALK = post.pointCount - pre.pointCount` только при идентифицируемых `pre/post/run`. Нужны fail-closed калибровка logical/CSS/desktop/PNG, safety margin и отдельное решение на перенос. Не менять production CHALK estimator и Stage6 defaults в P4.
- **Обязательное evidence:** experiment ID, workflow run + head SHA, выбранный исходник SHA, версия widths/order/записи параметров, кадры before/after, raw PNG+JSON+hashes, пропущенные/неудачные цвета, размеры, ошибки и причины отклонения. Статусы E0–E5 строго по [EVIDENCE_AND_VALIDATION](EVIDENCE_AND_VALIDATION.md).

## 6. Восстановление инфраструктуры и план коммитов

Переиспользовать: `tests/run_engine001_native_color_boundary_audit_v38.py` (labels), `tests/run_engine001_native_wide_interior_v43p2a.py` (components), `tests/run_engine001_v43p3_oriented_source.py` (source direction as reference, не использовать старые routes), `tests/engine001_adaptive_color_outline_v44.py` (detail RGB), `tests/run_engine001_adaptive_color_outline_native_v44.py` (baseline), `tests/run_engine001_complex_holdout_v5.py::native_batch` и `tests/game_renderer_reference.js` (true Egret). Минимум новых файлов: **один planner**, **один native runner**, **один regression test module**, **один GitHub workflow**, и существующая документация. Не создавать альтернативную систему и не копировать renderer.

Этапы коммитов после текущего документирования: (1) deterministic planner+unit E2; (2) native A baseline fidelity E3; (3) full B0 native A/B E3 + артефакты; (4) review/defect map и отдельный протокол B1. Проверка Markdown: `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20` через разрешённый CI. После каждого шага обновлять только необходимые `PROJECT_STATUS`, `TASKS`, `TEST_RESULTS`, `WORK_LOG`, `CHANGELOG`.

**Следующий невыполненный шаг:** реализация deterministic multi-color full-replacement B0 planner с unit-тестами; это разрешение только на экспериментальные исходники/CI, **не** на production или E4 game execution.


## Addendum 2026-11-17 — независимая предварительная оценка сложности source masks (E1, НЕ prereg B0)

Исходный пользовательский PNG `wV6VeZI9S1Y` проверен локально по SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; Pillow RGB resize 150×240 LANCZOS + MEDIANCUT8 без dithering воспроизвёл ожидаемую frozen palette. **Это диагностическое исследование после пререгистрации, не кандидат B0 и не результат утверждённых P4.0/P4.1/P4.2.**

| Source owner | Source pixels | 8-connected components | Single-pixel components | Crude horizontal proxy strokes |
|---|---:|---:|---:|---:|
| 4 | 3932 | 628 | 256 | 2152 |
| 5 | 4774 | 452 | 216 | 1905 |
| 6 | 2339 | 409 | 187 | 1139 |
| 7 | 5494 | 86 | 31 | 738 |
| **Total** | **16539** | **1575** | **690** | **5934** |

**Как воспроизведён proxy (не Egret):** для каждого source owner отдельно бинарная mask 240×150, OpenCV 8-connected; для width10→6→4 брались строки `distanceTransform(mask) >= width/2+1` длиной не меньше `max(3,width//2)`, после каждого выбранного хода помечали как покрытые пиксели моделью `cv2.line(..., thickness=width)`. Остаток проходили строками width2, обновляя модельную маску. Итог: **5934 paint paths + 410 frozen detail = 6344 total**, `2*5934 + (5682-2*1945) = 13660` synthetic vertices **NOT CHALK**. Это не проверка leakage и не реальная игровая кисть; модель могла ошибочно засчитать покрытие или потерять качество, поэтому никаких positive coverage assertions.

Результат **модельно превышает** оба исходных cap (3000 strokes/5900 synthetic vertices). При сохранении 410 detail и 1792 их frozen synthetic vertices верхний допустимый размер новой покраски **min(3000-410, floor((5900-1792)/2)) = 2054 двухточечных paint strokes**; если план содержит больше двух точек, фактический лимит ещё строже. Ни threshold, ни игровые лимиты не менялись. Для P4.1 требуется реально source-oriented/local-anisotropy grouping, экономное покрытие фрагментированных цветов и ограниченное разрешённое пересечение до3 логических px; исходные color blobs не разрешается тихо выкидывать ради cap. При недостатке бюджета — `BLOCKED_RESOURCE`, а не частичная заливка, объявленная успешной. P4 B0 planner всё ещё NOT_RUN, native Egret/E4/E5 NOT_RUN. Никаких экспериментальных файлов в production не добавлено.


## P4.1 implementation checkpoint — 2026-11-17 (E1/local partial, E2 CI UNKNOWN)

Implemented **only** the new source candidate selector in (ф) [`tests/run_engine001_full_adaptive_fill_v43p4.py`](../tests/run_engine001_full_adaptive_fill_v43p4.py), regression (ф) [`tests/test_engine001_full_adaptive_fill_v43p4.py`](../tests/test_engine001_full_adaptive_fill_v43p4.py) and isolated (ф) [`engine001-v43p4-full-adaptive-source.yml`](../../.github/workflows/engine001-v43p4-full-adaptive-source.yml). Commits: `d6ebbc7f`, `bf42a47c`, `c7c119e2`. **This is not yet a native B0 or baseline A replay.**

Deterministic source labels are reused through `original_labels` and V43-P1 component analytics. For each required owner4–7, eight fixed oriented sweeping angles (0,30,45,60,90,120,135,150 degrees) generate independent line candidates. Select **width10→6→4→2**, greedy on yet-uncovered own-class pixels with fixed minimum new pixels12/8/6/1 and simulated centerline-owner constraint. Strict preflight checks maximum total3000 strokes /5900 synthetic vertices including **410 expected** detail and1792 expected detail vertices. Full source-only model stroke footprints have distance≤3 logical pixels from *their owner* under OpenCV rasterization; **this does not prove true Egret leakage**. Does not copy any original1945 paint strokes. Emits only model candidate JSON, `safe_to_execute=False`, `details_exact_verified=False`, `native_E3=NOT_RUN`, `exact_CHALK=null`. Reuse of frozen actual 410 RGB V44-B details / exact source A native replay **still required** before combining a full B0 candidate.

Local preliminary Python evaluation (isolated substitutes for imported GitHub helper modules, **not** full project E2 integration): authentic source SHA verified, 955 new 2-point paint paths, plus410 frozen detail **not rendered** =1365 projected strokes; 3702 synthetic vertices **NOT CHALK**. Per-class source **OpenCV-model-only** proxy: owner4 3926/3932=99.8474%, owner5 4761/4774=99.7277%, owner6 2316/2339=99.0167%, owner7 5477/5494=99.6906%. Width usage by source class (10/6/4/2): 4=0/2/4/271, 5=2/12/16/260, 6=0/3/4/214, 7=33/22/8/104. Three isolated regression methods (determinism, four-owner/no-old-paint/ordering/budget, fail-closed invalid/cap) passed individually with import substitutes; no GitHub runner test result confirmed. The source model's claimed >99% **must not** be written as Egret quality acceptance.

**Current status:** P4.1 experimental code **implemented, E1**, E2 GitHub Actions **UNKNOWN** pending actual completed job/artifact, P4.0 frozen A **BLOCKED_NOT_VERIFIED**, P4.2/E3/E4/E5 **NOT_RUN**. Real B0 should be archived at first actual Egret comparison, and B1 fixes only thereafter. Do not modify this protocol's original predeclared thresholds based on this result.
