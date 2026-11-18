# ENGINE-001 / B1-R-P2C — оригинальные детали: независимая палитра исходных оттенков (prereg)

**ID:** `ENGINE001_B1R_P2C_SOURCE_INK_PALETTE_V1`. **Статус:** `PREREG/E0`, 2026-11-18, **до** первого P2C исполнения. Основание: DEC-034, [B1-R RGB-first](ENGINE001_B1R_RGB_FIRST_RESTART_PLAN_2026-11-18.md). Единица наблюдения — исходный пример `wV6VeZI9S1Y.png` (RGB 200×320, SHA-256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`); одна детерминированная реализация на один вариант; иные картинки — вне области выводов.

## Замороженная отправная точка и гипотеза

[B1-R-P2B](ENGINE001_B1R_P2B_RGB_RESIDUAL_INK_PREREG_2026-11-18.md), технический [CI44261071470](https://github.com/Kiddos19882/AutoDraw/actions/runs/44261071470) SHA `699c5a641db31ff6f9be4e82bf0d3397109091d0`: `K_DETAIL` при original-source маске 14 904/64 000 пикселей, flat-medoid 252 RGB, полный composite 13 517 RGB и логический LANCZOS 11 374 RGB, prereg source fidelity PASS, human visual PENDING. E1 read-only inventory уже заархивированного P2B ZIP: в этих 14 904 пикселях имеется **13 314** различных исходных RGB; это статистика *исторического контрольно-исходного изображения*, а не новый P2C кандидат. Успешные source-gates P2B не дают лицензии на game32 или новую кисть.

**Гипотеза:** неизменный original-derived `K_DETAIL` ink footprint можно сохранить, заменив только его чрезмерно разнообразные оригинальные RGB оттенки на небольшую source-medoid палитру, выбранную **из того же исходного ink-mask RGB**, а не из G32 или заранее существующей игровой палитры. Эксперимент определяет, достижима ли компрессия без утраты лиц/волос/контуров, но не обещает 32 цвета и не заменяет визуальный просмотр.

## Замороженный метод

В рабочем runner `tests/run_engine001_b1r_p2c_source_ink_palette.py` прочесть **только байты оригинального PNG** с pinned SHA. Reuse source-only функции из P1 `check_source/full_features/filter_original/logical_rgb`, из P2 `slic_labels/source_region_medoids/logical_region_map/delta_metrics/fixed_original_edge_recall`, из P2B `ink_residual/logical_composite`; запрещено запускать исторические `run()` и читать их outputs. Повторить независимо original full P1 `A_SOFT` (d5,color18,space2), SLIC `J_FINE` n=900/compactness=6 на оригинале, original-member RGB medoids, затем оригинальную маску `K_DETAIL` (outside DE00≥8 OR source dark L*≥5; inside ROI DE00≥4.5 OR source dark L*≥2.5; плюс original delta4≥4 с однопиксельной дилатацией). Получить flat full RGB, source original full RGB, mask и `K_DETAIL` reference full RGB **в том же P2C run**. P2B frozen PNG/labels/masks/JSON, G32/P4c1, V44-B410 и M1: лишь история, **никогда вход, target, seed или fallback**. Никаких нейросетевых recolor цветов и переноса старых контуров.

**Единственные варианты, заморожено до результата:**

| Вариант | Число source-ink оттенков | Исходные условия |
|---|---:|---|
| `C_096` | ≤96 | все K_DETAIL маскированные пиксели, CIELAB, SciPy kmeans2 |
| `C_192` | ≤192 | те же маска/база, только budget изменён |

Каждый `kmeans2`: `scipy.cluster.vq.kmeans2(source_mask_RGB_to_Lab_float64, k, iter=16, minit='++', missing='raise', seed=1729)`. Каждая выделенная группа выбирает один **реальный исходный RGB-цвет пикселя собственной маски**: минимальное квадратное CIELAB расстояние от пикселя до centroid, tie — первая позиция пикселя в original row-major. Цвет каждой выбранной source-mask точки становится RGB её cluster medoid; вне source-mask оставляем исходный full `J_FINE` flat medoid RGB **пиксель-в-пиксель**. Не применять алгоритмы фильтрации/диффузии, которые могут переместить линии или создать новые цвета. Пустая cluster группа, недостаточное число исходно-различимых RGB, NaN, и некорректное происхождение medoid → fail closed, **не** уменьшать бюджет молча. Настройки группирования одинаковы для обоих вариантов; повторный запуск под теми же фиксированными зависимостями должен выдавать идентичный результат.

**Различать цвета и координаты:** полный 200×320 RGB composite с точным набором source-member swatches должен содержать ≤ `flat_full_distinct+budget` RGB; discrete logical `NEAREST` также ≤ этой границы. Красивый предпросмотр для человека — full composite→150×240 `LANCZOS`: интерполяция даёт дополнительные RGB оттенки, поэтому его unique-color **не считать числом команд/игровых цветов**. При оценке fidelity к исходнику использовать именно LANCZOS предпросмотр на одинаковом логическом 150×240. Сохранить сравнения original RGB / 252-color flat / P2B full-source-ink control / C_096 / C_192 и ROI обеих лиц, рук и одежды; отдельный discrete nearest preview. Сжатая линия — **перекраска source residual MASK_ONLY**; это ещё **не** новая игровая contour geometry, не brush или 32-color output.

## Зафиксированные критерии до запуска

Для каждого варианта отдельные gates:
1. Подлинный SHA исходника и full/logical shape; ровно та же original-derived detail mask как в freshly-run `K_DETAIL`, вне неё output RGB **точь-в-точь** равен исходному flat medoid, для любого ink pixel assigned color принадлежит **реальным исходным masked RGB**. Ещё проверить per-cluster provenance и детерминированность. Все forbidden legacy input flags false, source-only.
2. `full_distinct_RGB ≤ flat_full_distinct_RGB+budget`, `nearest_logical_distinct_RGB≤full_distinct_RGB`; исходная J_FINE flat карта не меняется и сама обладает ≤900 уникальных RGB. Условия source map count считать на *полном* RGB, не на LANCZOS. Отдельно вывести фактическую компрессию masked distinct и full distinct относительно одно-run P2B K_DETAIL, без требования достижения ровно k.
3. Сравнение LANCZOS candidate против исходного original LANCZOS: mean CIEDE2000≤3.5, p95≤11.0; female-face/eyes mean≤4.0, male-face/eyes mean≤4.0, hands mean≤4.5. Кроме абсолютных, **оба лица** ухудшаются от same-run `K_DETAIL` baseline не более чем на +2.0 mean ΔE00. Исходные ROI — historical rectangles, **не** точные маски семантики.
4. Recall оригинального source logical top10% Sobel edges (base threshold неизменен) для LANCZOS candidate, принимая original source fixed-threshold×0.5 с neighbor 1 logical pixel, ≥0.90. Это исходно-визуальная математическая проверка, **не разрешённая утечка игрового красителя**.
5. Локально excess chroma mapped Lab chroma>original source logical Lab chroma+12 — ≤600 пикселей; никакого глобального запрета розового. Визуальный review отдельно обязан подтвердить глаза/рот/волосы/пальцы, контуры и отсутствие чуждых цветовых островков, искусственной мозаики/постеризации; численные PASS ≠ human PASS. Если gate провален — `SOURCE_GATE_FAIL`, сохранить все PNG/JSON/raw. Если все выполнены — `SOURCE_SCREEN_PASS_VISUAL_PENDING` и всё ещё **не** accepted game32.

## Протокол, доказательства, результаты

Зафиксированная среда CI: Ubuntu, Python3.11, NumPy2.2.6, SciPy1.15.3, scikit-image0.25.2, OpenCV headless4.11.0.86, Pillow11.3.0; `python -m unittest` на отдельных синтетических source-only fixtures, py_compile и docs audit, независимый CI P2C, ZIP GitHub artifact **включая** summary/comparison/все обрезки и отрицательные данные. Вывод: P2C provenance, budget, per-cluster medoid-source ledger, metrics, file SHA256, Github SHA/run ID, versions, исходные full/ROI PNG, логические LANCZOS и NEAREST PNG, сравнительная панель и readme для визуального ревью. Не перезаписывать frozen P2/P2B artifacts. При ошибке технический FAIL остаётся в истории; никакой подгонки критериев. Максимальная ожидаемая длительность одной CI job задаётся отдельным timeout ≤25min и checkout ≤5min.

**Граница:** palette32 projection, actual native Egret round brush, Stage6 executor, Monitor/Bridge, live E4, independent E5 и exact CHALK `post.pointCount-pre.pointCount` — **NOT_RUN**. Master/production неизменны. Итог визуального просмотра пользователя — `PENDING` до получения его оценки; E3 не объявлять визуальным PASS. До исполнения: P2C code/E2/E3 = `NOT_RUN`; после добавить outcome append-only в этот протокол и нужные status/tasks/results.

## Первый P2C run: frozen outcome (2026-11-18; append-only)

[CI44263770838](https://github.com/Kiddos19882/AutoDraw/actions/runs/44263770838), **exact SHA** `b20d9e8ead30fa7605d69f655ae3d7ab6c0890fb`: E2 11/11 deterministic synthetic regression PASS; E3 full original-only GitHub Actions job SUCCESS; Markdown audit PASS. [Artifact14408783882](https://github.com/Kiddos19882/AutoDraw/actions/runs/44263770838/artifacts/14408783882), independent downloaded ZIP SHA256 `f396ed07bb9fb46427350c57a4bf37aa47f5bbc49e89db25b72a3f9093b09e42`, CRC PASS, **26/26** member hashes exactly match frozen `report.json` (27 ZIP entries total incl report); report SHA256 `35d61dc3e51bafddcf7bcf118cd692160ab1c1befef3772be614202aac7e003a`. Python3.11.18/NumPy2.2.6/SciPy1.15.3/scikit-image0.25.2/OpenCV4.11/Pillow11.3.0. Only original pinned 200×320 RGB SHA `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, no G32/V44/M1 or frozen P2/P2B outputs used.

Same-run reference: source-only J_FINE **682** regions, **252** unique full RGB medoids; original `K_DETAIL` source residual geometry **14,904/64,000 pixels**, same-run uncompressed complete full RGB **13,517** colors and LANCZOS logical RGB **11,374** colors, mean original ΔE00 **0.748620**. P2C mask geometry unchanged; each compressed ink pixel obtains a real RGB source member from its own original source ink mask.

| Outcome | C_096 | C_192 |
|---|---:|---:|
| Source mask colors | 96 | 192 |
| Full uninterpolated RGB distinct | 347 | 443 |
| Logical NEAREST RGB distinct | 347 | 442 |
| Logical LANCZOS RGB distinct (*not* game swatches) | 10,778 | 11,068 |
| Source mean ΔE00 | 1.148854 | 1.036390 |
| Source p95 ΔE00 | 3.510995 | 3.038565 |
| Female face-eye ROI mean ΔE00 | 2.024609 | 1.754564 |
| Male face-eye ROI mean ΔE00 | 1.743704 | 1.514455 |
| Hands ROI mean ΔE00 | 1.708125 | 1.517662 |
| Source Sobel90 recall (1-logical-pixel neighborhood) | 1.000 | 1.000 |
| Source+12 chroma-excess pixels | 0 | 0 |
| All prereg source numerical gates | PASS | PASS |

**Both statuses strictly `SOURCE_SCREEN_PASS_VISUAL_PENDING`** (no user visual acceptance). Source medoid/geometry provenance confirmed by contracts and raw SHA. Assistant E1 inspection of original/flat/P2B/C_096/C_192 five-column PNG: original face structure/hair/clothes remain recognizable; C_192 changes colors less than C_096 but both visibly close to P2B. This inspection is **not** a user review, native Egret test, palette32 feasibility or run-bound CHALK measurement. Preserve independent P2/V1 and P2B/V1 results and failures unchanged. Next: user visually compare images in artifact ZIP; separately prereg original-first palette32 **only after** visual acceptance. No production promotion; palette32/native round brush/E4/E5/exact CHALK `NOT_RUN`.
