# ENGINE-001 / BPRED-S4 R0 — аудит исходных E/F: данные целостны, S4 BLIND заблокирован

**2026-11-20. Статус R0: E1 + read-only recalculation of frozen native E3; no new Egret execution, no R0 E2/CI and no E4/E5.** [Предварительно замороженный R0 E0](ENGINE001_BPRED001_S4R0_SOURCE_KNOWN_VISUAL_SAFETY_PREFLIGHT_PREREG_2026-11-20.md), коммит 21c5894c6580e6bb29d5db8842ef2f7ecfe3a3e7 до пересчёта этих показателей. [Decision DEC-044 and precise S4 rationale](ENGINE001_BPRED001_S4_ELIGIBILITY_AND_VISUAL_SAFETY_DECISION_2026-11-20.md). Начальный remote HEAD 3783f65fafd6a28b528bcf982068de63a989bd5e.

## Первичный архив и метод

Скачан без изменения [исходный P4D18 artifact14557770111](https://github.com/Kiddos19882/AutoDraw/actions/runs/44575816229/artifacts/14557770111), исходный code SHA 746639c1d0d3ac49be58e2a8379ff28c569bec4e, внешний SHA256 b0700a6b2d7fcd03aa1af0e741e0e7eb700304b779c32eced67fe43582066079 **совпал с digest GitHub**. ZIP **35 членов / CRC PASS / 34 из34 member SHA-256 PASS**. Исходный RGB image SHA256 07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a, оригинальный Egret game blob 46cc74de00b6cb5d207b1e1a2ffcd81613b6d388, renderer blob 76d950e0a8911888a9df3b675b866519ecf7bba4, Firefox159.

Архив содержит оба настоящих E/F источника: ORIGINAL_RGB_LOGICAL.png (RGB 150×240), SOURCE_OWNER_INDEX.png (L 150×240), SOURCE_OWNER_RGB.png (RGB 150×240), EDT_MARGIN_1P6_REAL_NATIVE.png (RGBA 1380×720), исходный stroke plan и прозрачный blank. Система палитры имеет 128 владельцев, но обе текущие карты содержат **32 использованных цвета**; каждый исходный owner-index однозначно связан с одним RGB. Координаты оригинала x=155..304 logical, physical backing scale3, native crop x=465..914. Этот crop не совпадает с S3 node-local ROI и не может подменяться им.

Независимый read-only пересчёт на сохранённых PNG использует те же проверяемые определения, что (ф) tests/run_engine001_b1r_p4d13_full_original_relaxed_finish.py, (ф) tests/run_engine001_b1r_p4d17_owner_physical_repair.py и (ф) tests/run_engine001_b1r_p4d18_physical_owner_edt_repair.py: actual native alpha>=24; RGB после alpha-composite поверх белого в диапазоне ±32 *только для воспроизведения исторической метрики*; 5/9,7/9,9/9 backing, EDT original-nonwhite interior logical distance>=2, leakage logical>3. Существующие правила alpha24/RGB32 **не становятся новыми визуальными safety thresholds**.

## Сверка original E/F с первичным отчётом

| Native/source property | E SOBEL90 | F SOBEL90 LAB12 |
|---|---:|---:|
| Logical nonwhite owner source | 13 868 | 13 863 |
| Original-white logical source | 22 132 | 22 137 |
| Correct logical original-owner ≥5/9 | 13 868 | 13 863 |
| Correct logical ≥7/9 | 11 585 | 11 490 |
| Correct logical 9/9 | 7 876 | 7 815 |
| Correct-owner physical pixels | 111 347 | 111 080 |
| Interior actual native alpha0 pixels | **24** | **25** |
| Original-white painted physical alpha≥24 | **4 415** | **4 445** |
| Protected-original-white painted physical alpha≥24 | **2 250** | **2 261** |
| Far >3 logical native paint alpha24 | 0 | 0 |
| Outside source rectangle native alpha24 | 7 | 7 |
| Stroke count, not game CHALK | 6 619 | 6 641 |

Все **20 проверенных показателей** (10 E и 10 F) **численно совпали** с архивным report.json. Нулевые расхождения с подписанным историческим отчётом означают целостность source/ROI и методики сравнения, **не PASS качества**: исходно-белые защищённые зоны в обоих вариантах повреждены, а внутренние физические прорехи остаются.

## Отдельная проверка критических масок

В исходном (ф) tests/run_engine001_b1r_p4b4_boundary_tolerance_sweep.py функция source_critical_rois() объединяет ровно три прямоугольные ROI из frozen (ф) tests/run_engine001_b1r_p1_fullrgb_edge_aware.py:

- female_face_eyes — logical (26,34,85,100);
- male_face_eyes — (72,14,123,92);
- hands — (31,125,115,165).

Объединение занимает **10 478 / 36 000 logical cells**, но представляет лишь прямоугольники, **не подтверждённые сегментированные границы глаз, рук или всех важных объектов**. Вне этих трёх областей находятся 6 846 E / 6 841 F исходных nonwhite логических ячеек; даже если вычесть четырехсвязные owner-границы, остается 2 131 E / 2 133 F ячейки, **которые нельзя автоматически считать безопасными**. Вычисленные source-owner adjacency boundaries E14 813 / F14 805 logical cells — только геометрия цветов, не независимая semantic contour validation.

## R0 readiness verdict

| Criterion | Status |
|---|---|
| R0-0 original frozen archive CRC/SHA, Egret and source | **PASS E1** |
| R0-1 original E/F owner-index↔RGB and physical coordinate binding | **PASS E1** |
| R0-2 original-white/protected/owner-edge map provenance | **PARTIAL** — source index and rectangles known; semantic completeness **UNKNOWN** |
| R0-3 archived native E/F baseline recounted independently | **PASS integrity**, original protected E/F quality **FAIL** |
| R0-4 complete calibrated native per-stroke false-safe risk with critical owner mapping | **NOT_READY** — no verified full semantic protection nor independent false-safe-bound |
| R0-5 strict independent S4 BLIND entry | **BLOCKED**; reserve S0 BLIND120 **untouched** |

**Итог:** исходные данные и измерения действительно готовы для дальнейшей работы; текущие маски и подтверждённая модель безопасности — нет. Ни 1–2 RGB за stroke, ни накопленные −8 RGB из S3v2r2 не могут быть общим автоматическим допуском. Исторический S2v4 M5 FP3/H1+H3 FAIL, S3v2q foreign20 и G3 88.65% FAIL, S3v2r2 foreign18-occurrence FAIL, original P4D18 E/F protected quality FAIL сохранены.

**Единственный следующий полезный шаг:** построить и проверить **консервативную карту protected owner + source-white + важных исходных RGB-контуров** с обязательным UNKNOWN вне доказанной безопасности, используя уже существующий source/preparation и native harness. Это отдельный prospective design/implementation шаг, не продолжение поисков Canvas rounding; до его E0/validation S4 BLIND нельзя открывать. После независимого принятия визуальной/owner safety будет возможно перейти к Egret spacing/holes/overdraw и whole-image S5. Ни production, ни master, Stage6, Bridge, Monitor не менялись. E4/E5/live CHALK НЕ запускались.

**Derived source-known R0 JSON SHA256:** db8e5df83e024dd08275b7ee96a98d2d3653c040acfb72606f29826846465366; доступен как производный файл текущей сессии, первичное неизменяемое доказательство — GitHub P4D18 ZIP. Отдельных R0 CI/E2 не запускалось.
