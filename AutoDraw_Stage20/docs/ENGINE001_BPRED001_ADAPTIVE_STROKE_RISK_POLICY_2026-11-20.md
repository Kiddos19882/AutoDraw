# ENGINE-001 / BPRED-001 — принятое дополнение: адаптивная пригодность штриха

**Текущий диагностический факт 2026-11-20:** [результат S2v5](ENGINE001_BPRED001_S2V5_FALSE_SAFE_DIAGNOSTIC_RESULTS_2026-11-20.md) установил: S2v4 все 3 FP — один width7/111° штрих, три spatial copies, predicted alpha128 vs native21; H3 нарушает только width1 TP-retention79.1885%. Эти данные **не позволяют автоматически разрешить их как допустимые**, потому что реальный owner-source-over не измерен. До какого-либо `ADMISSIBLE` необходим [BPRED-S3 frozen E0](ENGINE001_BPRED001_S3_NATIVE_SOURCE_OVER_PREREG_2026-11-20.md) и отдельная future source-protected E0; hard gates unchanged.


**2026-11-20. DEC-042, ACCEPTED RESEARCH DIRECTION, NOT PRODUCTION RULE.** Пользователь разрешил дополнить [основной план BPRED](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md) **возможным применением адаптивных критериев**. Последовательность этапов **S0→S1→S2→S3→S4→S5→S6 НЕ меняется**. Прежние scientific E0, H1/H2/H3, исходы S2v4 и pixel-fidelity метрики не пересчитываются по новой политике; `S2v4 H1/H3 FAIL` остаётся.

## Разделить два независимых вида критерия

1. **Диагностика корректности Brush Prediction Engine:** на frozen actual Egret samples всегда фиксировать native alpha/RGBA, FP/FN/IoU/MAE, worst widths/angles/phase/position, pixel-level raw и модельный UNKNOWN; `FP=0` safety gate на source-independent native stress **не отменяется** для заявления о pixel-safe predictor. `CI PASS != scientific PASS != game-safe`.
2. **Приемлемость реального изменения конкретного рисунка:** это *потенциальный* второй уровень после S3 source-over/owner. Вполне возможны несовпадения M2/M5 footprint с native без повреждения изображения (в пределах исходной одноцветной области), но такой вывод требует **фактических цветов до/после**, а не просто нулевого/ненулевого FP альфы. Вводить новые per-stroke критерии только через отдельный E0 и независимую native verification, а не через словесное «3 FP допустимы».

## Консервативный трёхсостояний policy proposal (S2/S3 research)

Для source RGB планировщика с конкретной `owner`-палитрой, защищённой картой и соседними цветами применять `ADMISSIBLE_CANDIDATE`, `UNKNOWN`, `FORBIDDEN`:
- **Внутри допустимого одноцветного owner:** моделировать вероятную и неблагоприятную площадь отпечатка, uncertainty envelope на данной ширине/угле/фазе/position и проверять, остаётся ли *возможное изменение композиции* допустимым по текущей source policy; допускается экспериментально сравнить широкую кисть с меньшей. Отсутствующий upper bound означает `UNKNOWN`, не `ADMISSIBLE`.
- **У незашищённой границы:** оценить защищённый буфер, расстояние от физического/логического следа до чужих owners, worst-case spill и реальные source-over RGBA; при неуверенности — уменьшение кисти, изменение path или native-verification. Не считать нейтральным изменение чужого цвета, даже когда краска своей области полезна.
- **Защищённые детали, важные контуры, white/foreign владельцы:** `FORBIDDEN` при потенциальном изменении защищённого owner или невалидной calibration. **Protected foreign=0**, согласованный far leakage≤3 *logical* px, source-owner coverage≥99%, отсутствие ухудшения критичных деталей и исходная визуальная узнаваемость остаются hard gates до отдельного решения; никаких разрешённых `FP≤3` по умолчанию.

Никакого заведомого confident-negative от M4/M5, поскольку `UNKNOWN` включает предсказанный фон и неопределённые края. Показатель угла, диаметра, фазы и ширины — **условные признаки**, не эмпирическая гарантия. Убедиться, что карта разрешённого цвета, настоящая геометрия, backing3, CSS client и PNG логические пиксели не смешиваются. Устаревшая калибровка — fail-closed. Native Egret backstop при `UNKNOWN`, не автопередача в executor.

## Перед внедрением adaptive acceptance: отдельный будущий frozen E0

Заморозить **до** новой попытки: features (distance to source owner boundary/protected zones, width, angle, phase, real pre-RGBA); стратегию uncertainty (upper-bound или честный empirical quantile + abstention), правила `ADMISSIBLE/UNKNOWN/FORBIDDEN`, критерии риска per-color source-over, independent family split, penalties за отказ и coverage/no-trivial-UNKNOWN, hard quality gates. Строго логировать native per-pixel **actual consequences** на цвете, счётчики false-safe, false-reject, corrected-source coverage, abstention и harm. Объявлять `PASS` только если все gates выдержаны на заранее выделенных новых native scenarios; исторические S2v4 failures нельзя использовать как независимый acceptance-set после разработки на них. Для full E/F оценивать original protected-white и leakage отдельно.

**Неизменное:** сначала S2 диагностирует реальные 3 FP и H3 deficiency, затем S3 owner RGB source-over, S4 untouched independent BLIND, S5 global E/F, S6 сократить strokes при принятых quality gates. Реальный exact CHALK только связанный E4 `post.pointCount-pre.pointCount`; master, production defaults, game renderer, Stage6, Bridge не меняются. Пользовательское разрешение на адаптивность **не** является разрешением переводить unsafe predictor в production.
