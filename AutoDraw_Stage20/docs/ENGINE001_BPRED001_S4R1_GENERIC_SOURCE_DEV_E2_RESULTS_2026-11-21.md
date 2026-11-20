# ENGINE-001 / BPRED-S4-R1 — первые универсальные исходные карты: E2 source-only, безопасность штрихов ещё не подтверждена

**2026-11-21. Итог:** исходный корпус проверен; 16/16 технических unit PASS; исходные карты на 23 DEV/KNOWN_CONTROL построены; **семантическая пригодность и игровые owner labels не доказаны, строгий S4 BLOCKED**. Результат по заранее замороженному [FIRST S4-R1 E0](ENGINE001_BPRED001_S4R1_AUTOMATIC_MULTIMAGE_PROTECTION_PREREG_2026-11-21.md), Git blob `5211c8ce5bb8b7b0106f7adf5c4c779a92f7a688` в [исходном плане S0→S6](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md) / DEC-045. Отдельного нового E0 для настоящей кисти и BLIND120 нет. Это не native E3 и не независимая visual validation.

## 1. Версии, CI, первичные данные

- Remote branch `feature/image-geometry-optimization`; **последний проверенный исходный E2+artifact code SHA `e675be71669acb5e49400ff32bca25a0b28f90df`**; workflow (ф) `.github/workflows/engine001-bpred-s4r1-generic-source-maps.yml`; версия модулей `ENGINE001_BPRED_S4R1_GENERIC_SOURCE_MAP_V1` и `ENGINE001_BPRED_S4R1_CORPUS_INTEGRITY_E2_V1`.
- [Первый E2 run44821960221](https://github.com/Kiddos19882/AutoDraw/actions/runs/44821960221) **FAIL 14/16**: численный FP шум Sobel на однотонном RGB дал ложную карту edges и перекрыл interiors; сохранено как исходный отрицательный результат. Исправление только `sobel<=1e-12 →0` для вычислительного нуля, НЕ новый visual/protected acceptance threshold, commit `24fe1f41da133cc9067d365bbf193df55269ab60`.
- [Повторный E2 run44822144592](https://github.com/Kiddos19882/AutoDraw/actions/runs/44822144592) **16/16 PASS, corpus31 SHA/decode PASS, 23 DEV карты PASS**, но архив **NOT_UPLOADED** из-за скрытого каталога вывода. Эту неполноту сохранения первичного артефакта не считать подтверждением полного provenance.
- **[Финальный E2 run44822358823](https://github.com/Kiddos19882/AutoDraw/actions/runs/44822358823) PASS**, source/CI SHA `e675be71669acb5e49400ff32bca25a0b28f90df`, **16/16 unit PASS**, Markdown audit PASS на том SHA, исходные 31 files проверены. Только workflow artifact-upload включил `include-hidden-files: true`, а отсутствие архива стало CI error.
- **[Первичный сохранённый artifact14672611890](https://github.com/Kiddos19882/AutoDraw/actions/runs/44822358823/artifacts/14672611890)**, GitHub digest SHA256 `0e37487048791bda9ca2cf5df5bd2171584d9fb04d6051f59173f86fab64a507`. ZIP скачан отдельно, внешний SHA256 сравнен побайтово с GitHub **PASS**, ZIP **94 члена / CRC PASS**: `corpus_integrity.json` + `dev_maps/dev_summary.json` + **92 PNG** (23 файла × 4 карты). Внутри нет H карты/PNG. Расширенные member SHA не подписаны отдельно; целостность внешнего ZIP подтверждена digest GitHub и ZIP CRC.

## 2. Собственно E2 доказательства

**Исходный автоматический adapter**, (ф) `tests/engine001_bpred_s4r1_generic_source_maps.py`: вход RGB/RGBA произвольных H×W до заявленного предела16 млн пикселей; EXIF orientation с сохранением original RGB/alpha; original Lab/DeltaE00/Sobel как reuse математической схемы P1, 4-connected source-owner adjacency **только при явном owner-index/palette**, original exact-white evidence, прозрачность отдельно, protected source geometry + UNKNOWN, без ручных face/eyes/hands ROI, без фиксированного crop/320×200/owner6. Координаты image-space letterbox и обратное преобразование заданы отдельно, **не** заявлена игровая калибровка. Это E2 математические карты, не true game footprint и не semantic AI model.

**Source-only integrity**, (ф) `tests/run_engine001_bpred_s4r1_corpus_integrity.py`: все **31/31** из (п) `data/generated_autodraw_plan/images_31_first` в точности совпали с frozen E0 по Git blob SHA1, byte size, decoded RGBA и вычисленному raw SHA256, EXIF и альфа сохранены. **8 KNOWN_CONTROL,15 DEV,8 LOCKED_HELDOUT**. В исходных файлах форматы decoded `23 RGB /7 RGBA /1 P`; у 7 файлов реальная alpha не полностью255 (5 KNOWN,1 DEV,1 H); все EXIF orientation=1. Первичный dHash64≤4 **одновременно** pHash63≤6 screening не дал совпадений между locked H и DEV/KNOWN (0) и внутри H (0); это **PASS_PRE_SCREEN_ONLY**, а НЕ доказательство независимости: crop/resize/re-encode и смысловая/жанровая схожесть остаются UNKNOWN. H ни для настройки, ни для source-масок не использовалась. Отдельный резерв (п) `images2_50_second` не участвовал.
 
**DEV/контрольные источники:** все **23/23** получили четыре математические карты `source_edge`, `geometric_detail_evidence`, `protected`, `unknown`, детерминированный SHA/provenance и числовой отчёт (все source original bytes неизменны). Вместе **17 187 107** original image pixels, из них геометрически protected **5 670 022**, `unknown` **11 517 085**, source_edges **1 243 303**. Этот «unknown» **нельзя** превращать в SAFE; коридор неизвестной семантики остаётся. Метрики учитывают источники с разными разрешениями, поэтому не являются ни image quality, ни следом игровой кисти.

**Главное ограничение:** на всех 23 DEV/KNOWN image inputs `owner_status=MISSING`, `candidate_interior=0`, `stroke_admission=FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION`, semantic protection status `UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL`. Это корректный fail-closed исход без выдуманной owner segmentation, **но R1 usefulness/semantically safe admission сейчас NOT_READY**. Нельзя говорить, что «получили универсальную карту владельцев» или что all-UNKNOWN прошёл quality. Для настоящего B1-R E/F уже имеются старые source-owner maps, однако их нельзя без новой source/provenance привязки подставлять другим файлам.

## 3. Критерии E0 и статус

| Проверка | Результат | Граница применимости |
|---|---|---|
| Frozen E0 blob before code | **PASS** | SHA из Git и исходного workflow |
| 16 generic RGB/alpha/owner/provenance/letterbox regressions | **PASS E2** | Synthetic/test source, не реальный Egret |
| 31 original file identities and decodability | **PASS E2** | SHA/size/decoded alpha, не semantic content |
| Near-duplicate pre-screen 8 H vs 23 DEV/control | **PASS_SCREEN_ONLY** | Не исключает перепакованных/обрезанных вариантов |
| 23 automatic source-edge/protected/UNKNOWN maps | **PASS_SOURCE_ONLY** | 92 PNG; owner labels MISSING |
| S4-R1 useful owner-bound candidate, semantic-detail protected recall | **NOT_READY / UNKNOWN** | Zero candidate on all 23; нет независимой semantic ground truth |
| True original Egret owner/protected false-safe, physical coverage/leakage | **NOT_RUN** | E3 требует отдельного E0 и validation |
| Strict S4 BLIND120, S5/S6, E4/E5/game exact CHALK | **BLOCKED / NOT_RUN** | Старые S2/S3 и original E/F failure неизменны |

**Не менять старые научные результаты:** S2v4 H1/H3, S3v2q lower-owner20/G3 usefulness88.65%, S3v2r2 18 событий owner изменения/−8 RGB после восьми проходов, P4D18 E/F original-white protected paint E2250/F2261 и alpha0 holes E24/F25 остаются FAIL. Ни визуальная поправка RGB±2, ни коэффициенты native brush/CHALK не менялись; G32/V44 не использовались как generative seed.

## 4. Один следующий невыполненный шаг по плану

**S4-R1 owner/semantic handoff на DEV:** найти и точно привязать **существующий B1-R original→palette/owner preparation API** к универсальному source-array adapter так, чтобы `owner_index`, palette и исходные RGB были согласованы автоматически **для каждого нового изображения**, с реальной проверкой соответствия координат, исходных хешей и неопределённости, не переносить E/F handwritten ROI или owner6. Для критичных семантических деталей, если оригинальные edge evidence недостаточны, отдельно обосновать frozen pretrained semantic helper и его UNKNOWN abstention; **не добавлять ad-hoc ручные маски**. В следующей prospective R1 E0-версии/диагностике оценить usefulness и protected false-safe на источниках DEV; затем заморозить код/пороги до единственной H evaluation. Строгий S4 пока блокирован, а зарезервированные S0 BLIND120 и H output не раскрыты. Старый научный pixel-safe FAIL не перезаписывать новым исследованием.
