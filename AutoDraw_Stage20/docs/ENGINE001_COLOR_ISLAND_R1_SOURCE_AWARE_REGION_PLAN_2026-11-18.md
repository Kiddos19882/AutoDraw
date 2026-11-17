# ENGINE-001 / COLOR-ISLAND-R1 — исходно-обоснованные цветовые области для круглой игровой кисти

**ID:** `ENGINE001_COLOR_ISLAND_R1_SOURCE_AWARE_REGIONS`. **Дата решения и плана:** 2026-11-18. **Статус:** PLAN_REGISTERED / NOT_RUN. **Направление:** после S5-P4 технического E3 PASS, но ухудшения fidelity, пользователь подтвердил приоритет: ликвидировать *ложные* мелкие цветовые островки и неверные акцентные цвета (например, яркий розовый около исходной тёмной массы), сохранив детали и узнаваемость. **Разрешённый текущий scope:** документация/план; отдельная реализация, CI, Egret и live-тесты на момент регистрации НЕ запускались.

## 1. Причина, baseline и границы применимости

- Исходник `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, logical ROI 150×240; любой алгоритм опирается на этот RGB, **не** на результат Recolorization-Pro, G32, S3/S4/P4c2 как источник «правильного» цвета.
- Frozen game32 baseline G32: 32 swatches Git blob `461b5f3725b9b79888ad36e807b3cf4c9e445e98`, фон index30, карта G index PNG SHA256 `b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637`; `components4=1284`, `singletons=779`, `area<=4 components=1097`, исходный mean ΔE00 `5.5314`, p95 `17.2715`. Все величины source MODEL_ONLY.
- P4a `ENGINE001_COLOR32_S2B_P4A_COMPONENT_ISLAND_PROTOCOL_2026-11-17.md`: исходный edge-protected компонентный merge ≤24px, extra mean ΔE00≤+2.0, но локальная коррекция меняла мало пикселей и не решала основную задачу. S2 SLIC/SAM2 уменьшал островки с1284 до368, но ухудшал mean ΔE00 до~8.58 и фон ~10.9% mismatch; S3/S4 также source quality FAIL. Следовательно **не** считать уменьшение островков доказательством качества.
- S5-P3/P4 полноценная RGB recolor-модель создаёт новый цвет, не предназначена для точного воспроизведения цветов исходника. S5-P4 [CI44190035785](https://github.com/Kiddos19882/AutoDraw/actions/runs/44190035785) E3 SUCCESS, но mean ΔE00 11.769, p95 25.858, nearwhite proxy 19416→0, оранжевый→оливковый. Эти результаты сохраняются как отрицательные, новую recolor-модель в R1 не использовать.
- P4c2 Native Egret [CI44119887018](https://github.com/Kiddos19882/AutoDraw/actions/runs/44119887018) paint-only FAIL, 14/17 классов ниже99%. Наряду с плохой картой была отдельная геометрическая проблема: нельзя объявить причину всех native артефактов одним только назначением цветов.

## 2. Цель и гипотеза

**Цель:** карта заливки, в которой каждая цветовая область поддержана исходным RGB, ложные мелкие акценты удалены, реальные микродетали и границы сохранены; только затем адаптация под игровой набор цветов и реальную круглую кисть.

**H0:** исходно-обоснованное объединение областей и контекстная проверка кандидатов палитры не позволяют одновременно сократить фрагментацию и удержать качество относительно G32. **H1:** при одинаковых входах и контролях R1 уменьшает *бесполезные* islands без ухудшения ошибок цвета, фона и защищённых деталей; не принимает любую карту только по количеству компонент.

**Ключевое правило:** не запрещать розовый как цвет глобально. Проверять локальную поддержку оттенка/насыщенности исходником, в том числе малые настоящие розовые детали; цвета около тёмных областей не признавать «невозможными» только по соседству.

## 3. Повторное использование и кандидаты

До новой реализации на текущем SHA сверить API, потребителей и тесты:
- `tests/run_engine001_palette32_region_study.py`: `read_source`, `nearest32`, `quality`, `topology`, `tiny_region_merge`;
- `tests/run_engine001_color32_s2_edge_protection.py`: `strong_edges`, `protected_merge`, границы оригинала;
- `tests/run_engine001_color32_s2b_p4a_component_islands.py`: `components_for`, `component_aware_h`, статистика островков и guards;
- `tests/run_engine001_color32_neural_s2.py`: original-first SLIC/region guidance. SAM2/OneFormer/BiRefNet только как опциональные абляции с настоящим проверенным checkpoint; R1 **не требует** нейросети.
- `docs/GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md` и `tests/game_renderer_reference.js` для следующего native шага. Source distance transform и морфология только MODEL_ONLY, не измерение реального следа кисти.
Если API несовместим — сначала тонкий test-only адаптер, а не второй производственный планировщик.

**Независимые сравнения в одном experiment/run:**
- `B0`: неизменная G32 map, baseline всех game32 метрик.
- `C0`: неизменный original-first S2/SLIC контроль, чтобы видеть эффекты готовой сегментации отдельно.
- `R1_RGB`: цельная карта source-RGB областей (каждая область получает устойчивый original-derived representative; unrestricted RGB, НЕ 32 цвета), без изменения оригинальных защищённых границ. Цель — проверить shape/regions до квантования.
- `R1_G32`: те же R1 области, каждой выбирают один существующий game32 swatch по **совокупной** original-RGB статистике области, с source-support/hue/chroma guard и контекстом соседей. Не брать локальные G32 метки как ground truth, но использовать их как frozen контроль.
- `R1_ABLATE_NO_CONTEXT`: тот же region mask и выбор игровой палитры без local source plausibility guard, для измерения конкретного вклада anti-false-accent логики.
- `R1_ABLATE_NO_CLEANUP`: исходная partition без объединения, при остальных одинаковых условиях. Параметры каждой версии фиксировать до первого измерения, после результатов не настраивать в том же ID.

## 4. Детерминированная последовательность, фиксируемая до реализации

1. **Original-first partition:** применить existing source-edge protected SLIC / connected components с жёсткой защитой значимых исходных границ. Белый фон определять из исходного RGB и проверять на ошибочные входы (не принимать BiRefNet foreground как ground truth). Сохранять необработанные region IDs и каждый промежуточный PNG.
2. **Критерий ложности:** для каждого маленького кандидата анализировать его original RGB gamut/median/CIELAB, связь с соседней областью, исходные gradient/edge, возможную support continuity с более крупной той же зоной и вклад в узнаваемые детали. Пиксель/островок не является ложным только из-за площади; реальный контрастный блик, глаз, узкая полоса остаются.
3. **Source-supported merge:** объединять только с пространственно соседней областью, если цвет/граница исходника разрешают замену; ограничивать ΔE00 ухудшение, не пересекать защищённый edge, не уничтожать тонкий контур. Цель: удалить ненужное дробление, не «замазать» детали. Рейтинг и tie-break детерминированы; запрещено менять исходный RGB или замороженные controls.
4. **Game32 projection only after source diagnosis:** назначать один из реальных 32 цветов по региональному распределению исходного RGB, не по одному пикселю. Для *насыщенного акцентного кандидата* проверять, есть ли в original region/близком source context сходный chroma/hue. Для нейтральных/почти серых original RGB hue ненадёжен — опираться на CIELAB distance и chroma отдельно. Если подходящего цвета нет, явно записать `UNREPRESENTABLE_BY_GAME32` / score и отклонить кандидат, **не** подменять его розовым и **не** выдавать неокрашенный регион за PASS. Универсальное исключение swatches запрещено.
5. **Brush-readiness MODEL_ONLY:** измерить число островков по площади (1/2/4/8/24), периметр, минимальные поперечные ширины и distance-to-boundary для нескольких допустимых кистей как диагностические характеристики. Не стирать участки, которые может покрыть адаптивная меньшая кисть или неизменный контур. Не подменять настоящую круглую кисть прямоугольным proxy.
6. **Native only after source + visual gate:** использовать существующий BoardPane/Egret renderer для реального следа штрихов, размеров 2/4/6/10/15/30 там, где подтверждены, и адаптивных траекторий (круговые/направленные/смешанные). Preserve original V44-B410 LAST. Настоящее E3 native качество, E4/E5 и exact CHALK — отдельные зарегистрированные шаги.

## 5. Предварительные acceptance gates / точная проверка

Сначала source-only R1_G32 vs **frozen B0** на идентичном оригинале и palette:
- strong-edge protected original pixels unchanged при component-level cleanup; no contours V44-B edits; никаких неизвестных palette IDs и подмены background без original evidence;
- 4-connected компоненты **≤963** (не менее 25% меньше B0=1284); отчёт отдельно по **маленьким и неподдержанным** островкам, изменениям в регионах лица/волос/одежды. Само снижение 25% НЕ достаточный PASS;
- mean original-source ΔE00 **≤6.5314** (B0+1.0), p95 **≤19.2715** (B0+2.0), original-vs-frozen-G32 white background disagreement **≤2% ROI**; эти значения заимствованы из исходных S3/S4 gates для **нового независимого кандидата**, не переписывают старые результаты;
- R1_RGB диагностируется отдельно по original RGB, color/edge/detail drift; **game32 пороги не применять к unrestricted-RGB как будто это эквивалентные карты**;
- `unsupported_accent_pixels` / components counted using **before-run deterministic definition** of source support; R1_G32 count/area не должны увеличиться vs B0. На синтетическом adversarial кейсе «тёмный source без розового + соседство» — 0 новых розовых компонент, при реальной малой розовой детали она обязана сохраняться; точный список порогов chroma/hue/region-size preregister *в коде+тестах до первого CI inference*, затем freeze; не подбирать по итоговому PNG;
- source visual gate: узнаваемость, лицо, волосы, поза, оранжевые детали, белый фон, небольшие настоящие блики и контуры. До пользовательского visual review — `SOURCE_CANDIDATE_VISUAL_PENDING` даже при числовом PASS; при ухудшении любой из этих критических характеристик — FAIL/REJECTED с отчётом, а не смена критериев;
- при невыполнении параметров, нехватке представимых игровых цветов, разногласии методов или нехватке evidence — `FAIL/BLOCKED` с сохранением original baseline, отчёта и отрицательных PNG. Никогда не переводить source tests в E3 native acceptance и не объявлять production-ready.

## 6. Проверки, evidence и порядок выполнения

**R1-0 (read-only inventory; первый шаг после плана):** на актуальном HEAD найти owners, API, тесты, зависимости, frozen manifests/hash и существующие анализаторы; проверить доступность оригинальных B0/G32 и edge masks; подготовить компактную dependency/diff оценку. Если source/palette/blob нет — BLOCKED, не реконструировать скрытно.

**R1-1 (новый эксперимент, отдельно разрешённая разработка):** реализовать минимальный source-only runner, детерминированные unit tests для ложного розового, настоящего розового, узких деталей, защищённой границы, нечёткой/нейтральной зоны, фона, отсутствия совместимого swatch, fail-closed input. Без production imports и без перезаписи frozen data.

**R1-2 (отдельное разрешённое тестирование):** выполнить единый CI runner R1_RGB/R1_G32 и контрольные абляции; сохранить original/B0/C0/R1 maps, label IDs, edge overlays, falsy-island localization, palette assignments, machine-readable reports, source and code SHA, PNG SHA256, run ID, versions; независимая проверка hashes и журнал отрицательных результатов.

**R1-3 (пользовательский visual gate):** показать original/B0/R1_RGB/R1_G32, особенно тёмные участки и бывшие розовые островки. Только при визуальном согласии — отдельный prereg native Egret brush replay с frozen acceptance: α24 per-owner≥99%, leakage≤3 logical pixels, original410 V44-B LAST, ≤3000 strokes /5900 vertices; дальше E4/E5/game run-bound `CHALK=post.pointCount-pre.pointCount`.

## 7. Инварианты и запреты

Не менять `master`, production defaults, Stage6, Game Monitor, Bridge, CHALK estimator; не менять original `wV6VeZI9S1Y`, frozen G32/S2/S3/S4/S5/P4a/P4c2 artifacts и thresholds; original V44-B **410 LAST/1792 vertices** неизменяем. 32-game-color ограничение остаётся для `R1_G32` (проверка будущей игровой пригодности), но `R1_RGB` visual-first разрешён **без 32-color quantization**. Это **разные выходы одного нового эксперимента**, не возвращение исторических критериев S5-P3/P4. P5 recolor-поиск не является следующим приоритетом.

**Статус при создании:** `PLAN_REGISTERED`; R1-0/R1-1/R1-2/R1-3 `NOT_RUN`. Это протокол и план, не утверждение о реализованном результате.
