# ENGINE-001 / BPRED-S4-R1 / AWEAK3 — завершённое ограниченное испытание согласованности цветов SLIC

**Дата:** 2026-11-21. **Исходный HEAD:** `5b8638bda7298140a4aba0a59c32cd5ec48e4dd5`. **Предварительно зафиксированный E0:** [AWEAK3 SLIC coherence](ENGINE001_BPRED001_S4R1_AWEAK3_PERCEPTUAL_SLIC_COHERENCE_PREREG_2026-11-21.md), неизменный Git blob `0d899b80415967315f1a87219428a4a867af2adf`; до написания/исполнения экспериментального кандидата. Предыдущий [AWEAK2 отрицательный результат](ENGINE001_BPRED001_S4R1_AWEAK2_ONE_MULTISCALE_LAB_SOURCE_E2_RESULTS_2026-11-21.md) остаётся отрицательным. Вход — те же 4 оригинальных DEV файла и ровно 4 человеческих приблизительных A PNG+JSON из [user commit 75d0fb7](https://github.com/Kiddos19882/AutoDraw/commit/75d0fb7e14d352a719691666cd6a55777dc4a713) с AQA1 SHA/provenance, без новых ручных масок.

## Первичное подтверждение

[CI44904546459](https://github.com/Kiddos19882/AutoDraw/actions/runs/44904546459), **точный experimental SHA `ac5ecaee0ee16192ddb2ef1ba244bccbe3e8cfd1`**, completed **SUCCESS**, 7/7 новых synthetic unit/regression PASS; сверка E0 blob PASS, 8/8 зафиксированных A PNG/JSON+4/4 оригинальных DEV SHA через повторный исходный AQA1 preflight, 4 реальных source-only исследовательских расчёта и Markdown PASS. [Machine-readable artifact14707915031](https://github.com/Kiddos19882/AutoDraw/actions/runs/44904546459/artifacts/14707915031); provider-upload ZIP SHA256 `5fa789446fad8667d7b604e3c431ee184c447bbf773fb1835fb86a1ed8d660f8`, независимые download/CRC **NOT_RUN**. Никакой source image не генерировался с помощью image generation; исходный RGB, исходный `protected`, `UNKNOWN`, ранее запрещённые штрихи не менялись; `A` используется только как оценка после построения автоматической карты.

**Один фиксированный вариант без перебора:** у существующих P2 SLIC исходных регионов вычислены соседние пары по четырём направлениям и CIEDE2000 между оригинальными медоидами цветов; использован исторический `DELTA_E_STRONG=12`, только сильные SLIC-границы сохраняются в дополнительном SLIC source warning. Настоящие original Sobel/DeltaE source edges, белый, P2 color disagreement и оригинальная protected остаются в сохранённой защите. `trial_core` может расширить **только гипотетическую UNKNOWN область**, не источник игровых owner/permission. Существующие SHA source и старые экспериментальные FAIL не изменены.

## Результаты: явный обмен пользы на риск

| Исходные четырёх-DEV показатели | Базовый P2 source | AWEAK3 trial | Что это означает |
|---|---:|---:|---|
| Всего source пикселей | 4 231 639 | те же | Не logical/PNG backing game |
| Original protected пикселей | 845 517 | **845 517, без изменений** | Уже установленные запреты сохранены |
| P2 hypothetical geometric core | 2 607 788 | 3 167 901 | +560 113 = **+21,48%** от прежнего core |
| Отмеченные человеком приблизительные I внутри core | 11 910 | 18 431 | +6 521 = **+54,75% относительно прежнего I∩core** |
| I после квадратной эрозии2 source px внутри core | 8 195 | 12 923 | +4 728 = **+57,69% относительно прежнего** |
| Примерно важные K, совпавшие с core | 96 911 | 109 638 | **+12 727 новых пересечений = 4,67% всех K** — существенное предупреждение, *не доказанный foreign damage* |
| K рядом (≤2 source px) с hypothetical core | 156 555 | 163 237 | +6 682 = **+2,45% всех K** — warning с учётом неточного мазка |
| Всего уникальных соседних region-пар | 18 506 | 14 787 Lab-weak / 3 719 Lab-strong | Не owner128, не реальная палитра |
| Граница SLIC в исходных pixels | 608 479 | сильная SLIC граница183 043 | Даже слабые SLIC пары могут находиться у важных деталей |

### Результаты на каждом оригинале

| DEV original | Прирост hypothetical core pixels | Добавленные I∩core px (относительно исходного I∩core) | Добавленные K∩core px (доля всех K) |
|---|---:|---:|---:|
| `6f6fff4105b941bf85b1fbd8519a.jpg` | 140 773 | +168 (+18,88%) | +9 674 (5,16%) |
| `ima56655ges.jpg` | 69 178 | +1 246 (+83,68%) | +239 (8,30%) |
| `EZAL3k9ddfs.jpg` | 340 489 | +231 (+16,78%) | +2 537 (3,83%) |
| `images (1).png` | 9 673 | +4 876 (+59,80%) | +277 (1,71%) |

**Интерпретация:** полезное совпадение с воспринимаемыми внутренними областями растёт существенно, поэтому эффект не является «разницей на десятые доли процента» и подтверждает, что SLIC чрезмерно режет визуально близкие по цвету области. Одновременно **предупреждение по K меняется в худшую сторону**: новые потенциальные области заходят на 12 727 вручную отмеченных ориентиров. Эти ориентиры нельзя считать точным RGB/owner GT, но игнорировать такой риск ради увеличения площади нельзя. На наиболее трудном `EZAL3k9ddfs.jpg` особенно важен низкий абсолютный gain I=231 при приросте total core=340 489, поэтому автоматически расширять его покраску нельзя.

## Итоговое решение и жёсткое правило остановки

- **Engineering hypothesis: PARTIAL/PROMISING_CONFLICTED.** Исходные визуально близкие регионы стоит группировать согласованно с первичными контурами, но не терять важные детали. Один эксперимент завершён; **не повторять AWEAK3 со sweep DeltaE12/компактности SLIC/радиуса/цветовых каналов ради micro gains**.
- **AWEAK3 production adoption: REJECT/NO_PROMOTION.** Сохранить экспериментальную реализацию и JSON для сравнения, без включения в active image preparation, Stage6 executor или planners. Никакой кандидат не становится `ADMISSIBLE` до отдельного native original Egret risk E3 и строгой S4 decision.
- **Stop/next по прежнему BPRED-S0→S6:** завершить серию DEV micro-refinements. **НЕ повторять уже выполненный [S4-R0 native/source readiness E1](ENGINE001_BPRED001_S4R0_SOURCE_KNOWN_READINESS_E1_RESULTS_2026-11-20.md)**: существующий отчёт подтвердил original owner palette/координаты E/F и исторический native protected-white FAIL, но неполную semantic critical-mask и отсутствие independent false-safe bound. Один следующий ограниченный шаг — заранее спроектировать/зафиксировать минимальный **консервативный source-known owner+original-white+source contour+UNKNOWN** контракт поверх существующих P4D18/Egret source maps и кодовых точек повторного использования; только затем отдельный prospective native E3, если доказана валидность входа. Не открывать S0 BLIND120, H8/second50 и не запускать S5/S6 до принятого S4 допуска. При неполной source/critical safety связи оставить S4 BLOCKED и не устраивать бесконечную коррекцию по нескольким процентам.
- **Условия валидации неизменны:** строгое SEMREF1 двумя reviewer не выполнено, но для текущего инженерного анализа достаточно предоставленных A и новых ручных точных пиксельных масок **не просить**. Исходные canvas/owner/native failures и quality gates без коррекции; actual game CHALK только valid real run `post.pointCount-pre.pointCount`.

**Статусы:** E0 PASS (порядок prereg), E2 technical PASS (7/7 tests, 4 original DEV E2); научный `PARTIAL/CONFLICTED`; strict S4 `BLOCKED`; source owner128 `MISSING`, native E3/game E4/E5/exact run-bound CHALK `NOT_RUN`; H8/BLIND120/second50 sealed; production/master/Stage6/Bridge/Monitor/S5/S6 **UNCHANGED/NOT_RUN**. Дополнительные 6 пикселей межзапусковой SLIC разницы из AWEAK1/AWEAK2 не исследовались в этом одном эксперименте: cross-run determinism still UNKNOWN.
