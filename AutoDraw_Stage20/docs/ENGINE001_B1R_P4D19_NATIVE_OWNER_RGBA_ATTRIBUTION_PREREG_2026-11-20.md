# ENGINE-001 B1-R P4D19 — native attribution оставшихся физических дефектов E/F

**E0 / prereg до реализации и новых запусков, 2026-11-20.** Experiment ID: `ENGINE001_B1R_P4D19_NATIVE_OWNER_RGBA_ATTRIBUTION_V1`. Task: `ENGINE-001`. Baseline remote HEAD at freeze: `fb680de708da13cacc409d598839004170d75c56`. This document is an experimental protocol, **NOT** a result, a quality PASS or permission to change production. E1 design only; E2/E3/E4/E5 **NOT_RUN** at freeze.

## Цель и проверяемые гипотезы

После [P4D18](ENGINE001_B1R_P4D17_P4D18_NATIVE_FULL_REPAINT_RESULTS_2026-11-19.md) лучшие native E/F содержат **24/25** alpha0 внутренних source-nonwhite backing-пикселей при полном original logical 5/9. Исходно белая и protected окраска не ухудшились относительно P4D13, но остаются E4415/F4445 и E2250/F2261 физических alpha24 соответственно (**качество FAIL**). Неверный RGB у уже окрашенных backing-пикселей и влияние перекрывающих owner цветов не атрибутированы. Одна только геометрия круглой кисти не доказывает причину неверного цвета.

**H1 (диагностика):** для воспроизводимого подмножества wrong-RGB и source-white-ink физ. пикселей реальный native redraw с исключением одного owner выявит зависимость финального RGBA от этого owner; число однозначно атрибутированных, смешанных и неразобранных случаев измеряется отдельно. **H2 (остаточные прорехи):** remaining alpha0 воспроизводится в frozen full-scene replay; последовательные prefix-сцены различат никогда не покрытые физические позиции от неоднозначных/невоспроизведённых. **H3 (ограничение):** owner-only scene показывает возможное влияние цвета, но не доказывает его *последнюю* или единственную причинную роль в исходной композиции. Для причинного вывода об удалённом owner нужен full-minus-owner native replay с сохранением исходного порядка остальных штрихов. Несовпадение результатов не исправлять догадками.

## Замороженные исходные данные и окружение

- Исходный `wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; original-only B1-R `E_SOBEL90` и `F_SOBEL90_LAB12`, палитра игры 128 индексов, `C_192_D_COMPONENT24`. **G32/V44 запрещены** как активные входы.
- Parent P4D18 code SHA `746639c1d0d3ac49be58e2a8379ff28c569bec4e`; frozen native ZIP [artifact14557770111](https://github.com/Kiddos19882/AutoDraw/actions/runs/44575816229/artifacts/14557770111), existing independently verified CRC + 34/34 member SHA. Использовать для каждого E/F `EDT_MARGIN_1P6_PLAN.json`, `EDT_MARGIN_1P6_REAL_NATIVE.png`, source owner index/RGB и соответствующий `report.json`; **не реконструировать** plan по картинке и не перезаписывать parent.
- Parent E/F по **6619/6641** истинных original Egret strokes; scale 3 physical/logical, 150×240 source logical, BoardPane X0=155 logical, true RGBA canvas 1380×720. Egret 5.4.1, Firefox **159.0** pinned. Game Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`; renderer Git blob `76d950e0a8911888a9df3b675b866519ecf7bba4`. Fail-closed при несовпадении любых hashes/source/browser/scale.
- Reuse `tests/run_engine001_b1r_p4d18_physical_owner_edt_repair.py` (frozen source, physical masks, real plans), `tests/run_engine001_b1r_p4d17_owner_physical_repair.py` (owner-correct backing metrics), `tests/run_engine001_b1r_p4d13_full_original_relaxed_finish.py` (native render) и `tests/run_engine001_b1r_p4b7_native_stroke_attribution.py` (native session and attribution semantics). P4B7 `normalized_subset` **ограничен colorIndex115**, поэтому без явной адаптации не применять его как универсальную функцию для E/F. Test-only wrapper обязан восстановить побайтово pinned renderer.

## Фиксированная выборка и native arms

Прежде чем смотреть на новые native outcomes, автоматически сформировать один deterministic sample manifest из неизменённого P4D18 RGBA + source owner: физические (backing) координаты, sample category, source owner, source logical x/y, актуальные RGBA, список индексов потенциально пересекающих штрихов и hash списка. Порог original owner-correct **alpha≥24 и max-channel RGB difference≤32**, original logical gate **5/9**; additional density 7/9 и 9/9 — отдельные метрики. Защита white/foreign и far>3logical без изменений. Категории:

1. **HOLE:** все source-nonwhite *interior* alpha0 физических пикселей, ожидается E24/F25, без отбора под желаемый результат.
2. **WRONG_RGB:** максимум32 alpha≥24 / wrong source-owner RGB на метод: до16 из frozen critical face/eyes x40..63,y45..68 и до16 вне него; детерминированное разнообразие по owner, RGB delta, физ. координатам, стабильная сортировка с зафиксированным seed или без случайности.
3. **WHITE_SPILL:** максимум24 alpha≥24 original-white на метод: до12 protected face и до12 других source-white, детерминированно по физ. координатам/цветам. Если группа короче лимита, report actual count; не заменять отобранные образцы после native просмотра.

Перечень реальных BoardPane native scenes (test-only, **максимум43**, если все 8 candidate owners доступны для E и F): **BLANK**×1; **FULL_P4D18**×2; **PREFIX_1_OF_5..4_OF_5**×4 на метод (8); **OWNER_ONLY** и **FULL_MINUS_OWNER** для до8 заранее отобранных source owner на метод (до32). Owner list до native прогонов получить детерминированно из геометрического *предфильтра* вокруг samples (включая strokes того же owner). Предфильтр с консервативной bbox+2 logical margin служит только отбору, **НЕ доказательству реального отпечатка**. Указать coverage кандидатных owner и все owner, не попавшие в budget. Оба owner arms сохраняют исходные полные координаты, brush widths1..10, RGB, относительный порядок штрихов; `FULL_MINUS_OWNER` удаляет **все** strokes только выбранного owner. Никаких повторных красок и добавленных исправляющих штрихов в P4D19.

**Абсолютное условие валидности:** каждый вновь полученный FULL native RGBA должен совпасть попиксельно со своим архивным P4D18 `EDT_MARGIN_1P6_REAL_NATIVE.png`, а BLANK иметь alpha=0. Иначе **BLOCKED**, никакой owner attribution и сравнения качества. Каждая scene записывается с реальным PNG, plan/index list, SHA, browser/version, status и metadata. Ограничение по сценам — обязательное; непокрытые гипотезы `PARTIAL`, не выдумывать PASS. Сцены разных методов изолированы; итоговый список 8 owner фиксируется **перед первым owner native replay**. Prefix snapshots — только дискретная временная диагностика: четыре точки не доказывают, что RGB между ними был монотонным.

## Алгоритм анализа и границы доказательства

Для каждого sample сохранять RGBA/alpha и composited-over-white RGB в base, четырёх prefix, owner-only и full-minus-owner; сравнивать bytewise на тех же физических координатах. Явно разделить:

- alpha0/alpha1..23 (реальный пробел/слабый AA) и alpha≥24 с правильным/неправильным RGB;
- изменение **финального** RGBA после удаления owner (native counterfactual dependence) и наличие alpha у отдельного owner-only штриха (possible contributor);
- source original-white/protected pixel, source owner correct-color vs foreign owner candidate; pixel alpha255 wrong RGB не объявлять ошибкой одного owner без отдельного native evidence;
- mixed/ambiguous/untested, возможный AA, порядок compositing и coverage candidate budget; если owner-only и ablation не дают однозначной причины, статус **UNATTRIBUTED**, не `PASS`.

Отдельно из полного native E/F считать исходный owner correct physical, alpha0 interior, 5/9,7/9,9/9, white ink, protected white, owner-sensitive foreign и far>3; сравнить base с архивом **без модификации** исходных thresholds. Карты с наложением для лица, рук, heterogeneous borders и full image — только диагностические; оригинал RGB всегда показывать рядом. Сохранить отрицательные и неполные случаи. Full original quality остаётся **FAIL** пока protected foreign0 не измерен и не соблюдён; no E4/E5/CHALK claims.

## Тесты, критерии завершения, архив

- **E1:** прочитать и сверить конкретные текущие исходники, pinned blob/hash, полный вход P4D18; отсутствие расхождений source/implementation и отсутствие повторной реализации Egret.
- **E2:** synthetic tests для deterministic sample membership; alpha/RGB categories; owner-only/full-minus-owner preserve order/stroke count/colors; prefix boundaries; constrained 43-scene budget; invalid hash/shape/duplicate sample/no archive => fail closed; read-only parent evidence; renderer restoration.
- **E3:** один новый изолированный GitHub workflow на закреплённом SHA (либо корректное расширение существующего research harness), реальный Egret source/BoardPane/WebGL Firefox159.0, parent archive SHA/CRC, baseline 2/2 exact RGBA, blank, scenes+JSON/PNG+manifest; все запуски/ошибки/sampled owners и unknowns включить в report. Один archive ZIP, внешняя независимая проверка целостности, сравнение с оригиналом; CI success **не равен** image quality PASS.
- **E4 live game, E5 independent quality validation, exact run-bound CHALK:** **NOT_RUN** в P4D19. Никаких production/executor/Bridge/Game Monitor/CHALK-default/master changes.

**Успех P4D19** — воспроизводимая и честно ограниченная причинная диагностическая таблица с native доказательствами и точным baseline, включая unresolved cases, **а не** визуальное 100% или меньшее число штрихов. Только затем отдельный E0 для **P4D20**: минимальные source-aware boundary/foreign/AA repairs на определённых настоящим рендерером причинах и последующая проверка original-white/protected0. Будущая оптимизация количества stroke/CHALK возможна лишь после quality gates, на frozen accepted картине, не подменяя CHALK числом strokes.
