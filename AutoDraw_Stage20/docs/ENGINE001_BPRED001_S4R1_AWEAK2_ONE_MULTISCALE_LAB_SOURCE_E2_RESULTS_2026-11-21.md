# ENGINE-001 / BPRED-S4-R1 / AWEAK2 — автоматический двухмасштабный Lab-кандидат: ограниченный выигрыш, не продвигать

**2026-11-21. Research-only E2; GitHub Actions source-only technical PASS / scientific PARTIAL; NO production promotion.** [Frozen AWEAK2 E0](ENGINE001_BPRED001_S4R1_AWEAK2_AUTOMATIC_MULTISCALE_LAB_EDGE_PROPOSAL_PREREG_2026-11-21.md), Git blob `80a410cb5feb45dec3f7b36b0499e71120c8c512` заморожен до написания/запуска кандидата. Предыдущие истинные четыре человеческие визуально приблизительные A-разметки из коммита `75d0fb7` остаются тем же входом, не участвовали в построении кандидата. [AWEAK1 исходный measured baseline](ENGINE001_BPRED001_S4R1_AWEAK1_HUMAN_APPROX_REGIONAL_SOURCE_E2_RESULTS_2026-11-21.md) сохранён. `master`, настоящий original image preparation, Stage6, Bridge, Game Monitor, native и executor defaults не изменены.

## Первичные доказательства

- [CI44903477211](https://github.com/Kiddos19882/AutoDraw/actions/runs/44903477211), **точный код SHA `2d1ab8f55003c000e643103e44e042a0f18485da`**, completed SUCCESS: 7/7 новых synthetic AWEAK2 source/owner/core/immutability tests PASS, E0 blob SHA check PASS, четыре оригинала и четыре реальные A маски заново проверены AQA1 provenance reader, оригинальные `generic_source_maps` и исходный SLIC medoids исполнены без изменений, технический source-only отчет PASS, Markdown audit PASS. [Machine-readable artifact14706524050](https://github.com/Kiddos19882/AutoDraw/actions/runs/44903477211/artifacts/14706524050); provider-upload ZIP SHA256 `39fee990bcd91431f92bb046bfc76a580a25640f3f80e0b295824a67d867420b` (independent ZIP download/CRC **NOT_RUN**). E2 **source-only descriptive**; native E3/E4/E5/exact CHALK NOT_RUN.
- Заморожен ровно **один** автоматический кандидат, без sweep: original RGB→Lab; Gaussian sigmas 1,3 **source pixels**; скалярная норма трёх Sobel(Lab) каналов; p90 только положительного градиента на каждом масштабе, 1-px 4-neighbor dilation; `trial_protected = old_protected | additional_warning`, `trial_core = old_core & ~additional_warning`. Новый вывод **не** передаётся исполнителю и не считает core безопасным; `stroke_admission=FORBIDDEN`. Нет ручных ROI/индивидуальной настройки/дорисовки/нейромодели/проверки RGB-пиксельного равенства для визуально одинаковых цветов.

## Сводка всех 4 DEV: сколько нашли и чего лишились

| Показатель | Базовый original source | Автоматический AWEAK2 trial | Изменение/ограничение |
|---|---:|---:|---|
| K пикселей визуальных человеческих деталей/разных по восприятию областей | 272,644 | те же 272,644 | Только неточный proxy |
| K рядом с защищёнными source-точками (r0) | 125,356 = 45.98% | 141,208 = 51.79% | +15,852, **+5.81 процентного пункта** |
| K рядом с защищёнными source-точками (r2) | 193,374 = 70.93% | 204,610 = 75.05% | +11,236, **+4.12 п.п.** |
| K рядом с защищёнными source-точками (r5) | 239,637 = 87.89% | 244,754 = 89.77% | +5,117, **+1.88 п.п.** |
| protected original source, 4,231,639 пикселей | 845,517 | 959,370 | +113,853 = **+2.69% всего изображения**, цена консервативности |
| Гипотетический SLIC core | 2,607,794 | 2,542,762 | −65,032: **97.51% прежнего core остаётся**, но по прежнему НЕ SAFE |
| Человеческие визуально однородные I внутри hypothetical core | 11,910 | 11,593 | −317, **97.34% прежнего I∩core сохранено** |
| Из всех I новый trial защищает дополнительно | 0 до trial | 477/27,594 = **1.73% I** | Возможное избыточное исключение полезного интерьера |
| K попадает точно в hypothetical core | 96,911 | 89,423 | −7,488 proxy-conflicts, **не native false-safe** |

Исходные source-региональные core пиксели в AWEAK1 и в этом AWEAK2 run различились на **6 из ~2.608 млн** только для `ima56655ges.jpg` (59,119 против 59,125). В обоих CI базовый `engine001_bpred_s4r1_generic_source_maps.py` и AWEAK1 evaluator имеют одинаковые Git blob SHA1. Причина не выяснена, **межзапусковая полная детерминированность SLIC не доказана**. Результат AWEAK2 baseline→trial рассчитывается внутри **одного** CI исполнения, поэтому сопоставление A/B именно этого запуска корректно, но не обещать byte-identical reference source-core через отдельные runs.

## Показатели для конкретных оригиналов

| DEV original | K вблизи protected≤5 source px baseline → trial | Gain п.п. | I∩oldcore сохранено после trial | Исходный geometric core retained |
|---|---|---:|---:|---:|
| `6f6fff4105b941bf85b1fbd8519a.jpg` | 90.21% → **92.42%** | +2.21 | 99.66% | 96.60% |
| `ima56655ges.jpg` | 95.83% → **100.00%** | +4.17 | **80.93%** | **89.48%** |
| `EZAL3k9ddfs.jpg` | 78.18% → **79.36%** | **+1.18** | 97.82% | 98.19% |
| `images (1).png` | 99.38% → **99.80%** | +0.42 | 100.00% | 95.84% |

**Решение:** AWEAK2 оригинальная проверка технично PASS, но **не является достаточным автоматическим решением**: на наиболее сложном `EZAL3k9ddfs.jpg` прирост близости критических human-маркеров лишь 1.18 п.п., а на `ima56655ges.jpg` теряется примерно 19.07% ранее потенциально полезного `I∩core`, несмотря на более высокое совпадение с K. Нельзя объявлять улучшение качества только по росту площади protected или K proximity: source owner/semantic meaning и реальная кисть неизвестны. **NO_PROMOTION_TO_ACTIVE_ALGORITHM**; кандидата оставить как отдельный отклонённый/ограниченный исследовательский вариант для сравнения. Не подбирать другие sigma/p90/radius в этом E0 ради PASS.

## Что дальше (один шаг, без новой ручной работы)

Внутри уже принятого S4-R1 следующий ограниченный этап — автоматическое **согласование визуально однородных исходных цветовых регионов и важных контуров**, а не просто расширение edge mask. Начать с анализа оригинальных Lab source SLIC medoid region-adjacency/multiscale uncertainty и уже существующих NH1–NH4 **как информационных подсказок**, без дообучения и без окраски через подтверждённые границы, freeze отдельный E0 прежде чем сравнивать с этими же четырьмя A weak hints. Вход A никогда не должен превращаться в пер-рисуночную ручную production-маску. Для принятия штрихов нужен отдельный original Egret native S4 E3 и строгий S4 safety review. Не запускать heldout8/S0 BLIND120/second50 в этом research step.

**Итоговые статусы:** E0 prereg PASS; E2 technical PASS; scientific quality `PARTIAL_NEGATIVE_TRADEOFF`; AWEAK2 production decision `REJECT_NO_PROMOTION`; strict SEMREF1 `BLOCKED` (двух независимых reviewer GT не было; не требовать B для текущего exploratory route), strict S4 `BLOCKED`, S5/S6 `NOT_RUN`, native E3/E4/E5/exact game CHALK `NOT_RUN/UNKNOWN`, прежние S2/S3/P4D18/CR1 FAIL сохранены.
