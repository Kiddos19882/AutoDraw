# ENGINE-001 / BPRED-S4-R1 / RAG2 — signed 4-DEV source E2: numeric 2/4, geometry not yet S5-ready

**Дата:** 2026-11-22. **Задача:** S4.2+S4.3, [DEC-048](DECISIONS.md#dec-048-s42s43-совместная-сегментация-связных-областей-и-выбор-игровых-цветов). [RAG2 immutable prospective E0](ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG2_SPLIT_GUARD_PREREG_2026-11-22.md) Git blob `c5e6564829b4ed641b31cba83da4a66c79caa5dd`, заморожен на [commit f42ddf5](https://github.com/Kiddos19882/AutoDraw/commit/f42ddf56b0c7f45bd7c18d30d90c51a4654472c6) **до реализации**. [RAG1 отрицательный отчёт](ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG1_E2_RESULTS_2026-11-22.md) неизменен. Этот отчёт описывает **source-only E2** и визуальные карты; ни native Egret, ни game/CHALK не выполнялись.

## Commit/CI и происхождение

- [RAG2 research implementation](https://github.com/Kiddos19882/AutoDraw/commit/de6f960e528ca5510cef555eaf65fc6beb4985b8): original-only SLIC → 4-connected split по новой source-derived palette-nearest гипотезе внутри каждого SLIC → real source Lab RAG guard и однократное условное recolor → 4-connected region IDs, color map, atlas/manifest; 8 synthetic E2 tests и isolated workflow.
- [Первая техническая CI44978612932](https://github.com/Kiddos19882/AutoDraw/actions/runs/44978612932) SHA `de6f960` **FAIL** в пяти тестах из-за Python `b[0] |= contrast` с tuple target; DEV этап **SKIPPED**, это не качество алгоритма. [Fix SHA a0fa870](https://github.com/Kiddos19882/AutoDraw/commit/a0fa870c533e93d0cc890d4c861bd6e5b3b26e5d) только заменил эту tuple/NumPy view assignment на явные view, без изменения E0, численных параметров или алгоритма.
- **[Final RAG2 CI44978720269](https://github.com/Kiddos19882/AutoDraw/actions/runs/44978720269)** exact code SHA `a0fa870c533e93d0cc890d4c861bd6e5b3b26e5d`, **completed SUCCESS**: frozen Git blob E0, engine blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, all 8/8 synthetic tests, 4/4 original-only DEV source runs, report/manifests SHA verification and artifact upload PASS. Это E2 **технический**, не image quality native PASS.
- [Raw four-DEV artifact14737290385](https://github.com/Kiddos19882/AutoDraw/actions/runs/44978720269/artifacts/14737290385), GitHub ZIP bytes **5,292,024**, SHA256 `51e5acf9a132b12923b930d039f59e1249ff53dbb15dc5eea60df271815fbfdc`. Независимо скачан в рабочую среду, outer ZIP SHA256 / ZIP CRC **PASS**, **28/28** manifest-declared originals/PNG raw SHA256 перепроверены **PASS**, 33 ZIP entries. Исходные изображения в папках сохранены как байты оригинала; все производные maps/превью вычислены только из текущего источника и pinned game128. Изменённые/старые FC1/RAG1/E/F/G32/V44/P4D artistic data не читались и не использовались для настройки.
- DEV как в заранее принятом E0: 4 originals `wV6VeZI9S1Y.png`, `Sanrio_Characters_Hello_Kitty_Image026.webp`, `EZAL3k9ddfs.jpg`, `images (1).png`; sealed H8/BLIND120/second50/images2_50_second не открывались.

## Итоги: прескрин численно PASS ровно 2/4

Показатели вычислены **по исходным пикселям**, внутри одного и того же прогона source original vs fresh nearest128 vs fresh RAG2. Это не GAME/Canvas RGBA/CHALK.

| DEV original | RGB MAE fresh nearest128 → RAG2 | Singleton игровых 8-connected компонентов | Уменьшение singleton | Исходные SLIC → начальные split → финальные геометрические регионы | Frozen E0 numeric |
|---|---:|---:|---:|---:|---|
| `wV6VeZI9S1Y.png` | **4.876 → 4.761** | 6,277 → 5,334 | **15.02%** | 365 → 12,366 → **10,888** | PASS numeric |
| `Sanrio_Characters_Hello_Kitty_Image026.webp` | 9.797 → 9.783 | 2,670 → 2,530 | 5.24% | 396 → 4,957 → **4,729** | FAIL numeric |
| `EZAL3k9ddfs.jpg` | **22.197 → 22.152** | 41,419 → 32,610 | **21.27%** | 1,783 → 101,062 → **79,787** | PASS numeric |
| `images (1).png` | 1.867 → 1.867 | 4,366 → 4,223 | 3.28% | 1,826 → 6,759 → **6,608** | FAIL numeric |

**Frozen RAG2 E0 numeric warning criterion (>=2/4, >=15% singleton decrease and <=15% RGB MAE increase): `PASS 2/4`.** Тонкие контуры, глаза, волосы, одежда на полноразмерной палитровой RAG2-картинке в основном остаются визуально узнаваемыми, в отличие от чрезмерно сглаженного RAG1. Но **геометрическая карта остаётся слишком раздробленной**, особенно в исходных фотографических/подробных сценах; тонкие color split компоненты численно близки к pixelwise nearest. Это **не** подтверждённая общая source semantics или художественное S4 quality gate.

### Почему нельзя считать RAG2 завершённым S4.2+S4.3

RAG1 оставлял слишком мало регионов и уничтожал исходные внутренние детали. RAG2 исправил **потерю деталей на входе**, разделяя внутри SLIC по исходно-квантованному swatch; без source-aware hierarchy такая операция создаёт много подрегионов (например, 79,787 финальных). Даже если RGB MAE и число singleton улучшаются, сам region-ID/adjacency остаётся перегруженным для будущего эффективного S5 заполнения. Пока нет согласованных крупных поверхностей **плюс** отдельных важных detail-layer/contour без множества бесполезных islands. Качественные контуры S4.4 и новый полный Egret native не были проверены, их нельзя выводить из 2/4.

**Research status:** `PARTIAL / PROMISING_NUMERIC_ONLY / NOT_PROMOTED_TO_S4_MAP`. **Technical:** `E2 PASS`. **E3 game/native Egret RAG2:** `NOT_RUN`. **E4 actual live:** `NOT_RUN`. **E5 independent:** `NOT_RUN`. Exact run-bound CHALK `NOT_RUN`; formal BPRED-S4 `BLOCKED`, engineering research S5 handoff `NOT_READY`. Historic RAG1 `FAIL/NO_PROMOTION`, AWEAK3 `PARTIAL/CONFLICTED`, FC1 quality FAIL untouched.

## Решение и один следующий шаг по существующему плану

**STOP frozen RAG2** после одного candidate и одного DEV batch. Не подбирать `area=3`, source-Lab12, RGB-cost1.0 или SLIC параметры «пока проходят все 4»: это нарушит замороженный E0 и вновь создаст бесконечную микрокоррекцию. **Следующее S4.2+S4.3 — только новый отдельно frozen архитектурный шаг:** выразить **иерархию из основных связных исходных областей и защищённых цветовых/контурных detail subregions**, где S4 хранит геометрию поверхности отдельно от игровых swatches и от мелких важных деталей. Перед новым кодом: E0 с приоритетом отсутствия массовых искусственных component IDs при сохранении original detail, и одним bounded DEV visual review. Это не возврат к RAG1, не удаление всех island<3 и не изменение FC1 PNG.

Сохранять стратегию DEC-047 whole-original/fresh-only; старый RAG2 output — только зафиксированная история сравнения *после* новых результатов, не вход следующего алгоритма. S4.4, S4.5, S4.6 и S5/S6 не объявлять начатыми. Production/master/Stage6/Bridge/Monitor не изменены, sealed heldout и научные thresholds сохранены.
