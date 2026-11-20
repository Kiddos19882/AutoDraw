# ENGINE-001 / BPRED-S3v2j — новые нативные сцены: скрытое влияние при alpha0 подтвердилось (2026-11-20)

**Результат:** E2/E3 CI **PASS**, научная H1 (точная последовательность оригинального Canvas) **PASS**, H2 физическая возможность изменить владельца при isolated top-owner alpha0 **DETECTED 21**, полная source-over H3 **FAIL 19/40 итоговых вариантов WebGL**, исходная безопасность planner/owner **NOT_VALIDATED / FAIL прежних gate**. Это независимая *новая выборка синтетических native Egret-сцен*, но не игровой E4, не S0 BLIND и не доказательство принятой production-модели.

Заранее зафиксированный [S3v2j E0](ENGINE001_BPRED001_S3V2J_NEW_NATIVE_ALPHA0_OWNER_INFLUENCE_PREREG_2026-11-20.md), Git blob `6801292e01a650a2b014ffe09256313ebe10562b`, появился **до нового исследовательского кода и E3**, его гипотезы и критерии не пересчитывались. Финальный [CI44721915503](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721915503) commit `ad1fa7fd66d4df563d729b7faae27651ca8279ea`, original Egret5.4.1, Firefox159.0, original BoardPane source game blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, reference renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`. [Raw artifact14621923148](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721915503/artifacts/14621923148).

## 1. Source, проверки и отрицательные технические попытки

Новый source set: **80** оригинальных Egret E3 разных сцен, widths1..10×CROSS_ROTATED/NEAR_SKEW×A_ONLY/B_ONLY/A_THEN_B/B_THEN_A; новая дробная фаза, углы и пары цветов не использованы в прежнем S3v2f. Original Canvas source main **80 PNG**, mask **80 PNG**, итоговый WebGL **91 PNG** (80 оригинальных+10 повторов exact на 162×162 ROI+blank alpha0), **200** реальных post-`stroke()` оригинальных Canvas PNG. Реальных вызовов на основном Canvas: 2 для одиночных A_ONLY/B_ONLY и 3 для двухцветных A_THEN_B/B_THEN_A во всех 20 парах width/relation; не задавались в условии допуска. Original game/methods не изменялись, original source transform и source node verified.

- Исходные immutable blob, E0 и настоящие методы: проверены в CI, original E2 **55/55** (10 S3v2j+9 S3v2i+10 S3v2h+12 S3v2f+14 S3) **PASS**, Markdown audit PASS. Отдельное исходное [AutoDraw validation](https://github.com/Kiddos19882/AutoDraw/actions/runs/44720836376) ещё относится к предшествующей commit стадии, не является S3v2j E3.
- Первоначальный S3v2j CI44721480176 SHA2444cd65 **CANCELLED** при новом коммите до scientific data. Затем [CI44721566531](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721566531) SHA67bbe6fe **FAIL E2**: тестовый fixture `A_THEN_B` по ошибке ожидал обратный порядок цветов. Исправлен только тест в коммите `ad1fa7fd`, оригинальные native source планы, E0 и acceptance остались прежними. Этот E2 FAIL сохранён.
- Final [CI44721915503](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721915503) native E3 SUCCESS, сохранены `FROZEN_S3V2J_MANIFEST.json`, 40 ordered owner rows, **все** выявленные изменённые 21 физические пиксельные occurrence, 80 source metadata, 200 original stroke snapshots. Независимо downloaded raw ZIP: **857 entries, ZIP CRC PASS, все 856/856 report-listed SHA256 PASS, без duplicate, соответствуют содержимому**. Source S0 BLIND не использован.

## 2. H1 — original native chronology, никакого выбора последующих штрихов

Зафиксированный first post-stroke original main Canvas соответствует независимому оригинальному A_ONLY/B_ONLY того же run для **40/40 ordered вариантов, 0 RGBA differing physical pixels**. Последний original `stroke()` снимок соответствует true main Canvas для **80/80 сцен, 0 RGBA differing pixels**. **H1 PASS**.

Original `Canvas→WebGL QH` с заранее прежней half-up unpremultiply проверен на всех80 новых original Egret scene: **0 физических RGB-различий и 0 alpha-различий**. Это подтверждает именно этап текстуры на новой выборке, но не право автоматически считать качественным owner source-over.

## 3. H2 — настоящее изменение чужого цвета при isolated alpha0

На всех **40 original two-owner ordered вариантах**, в зоне настоящих пикселей **нижнего owner с alpha>0**, где *самостоятельный верхний owner имеет alpha0*, обнаружено:

- **21** physical pixel occurrence, суммарно в **14** ordered сценах. Ширины 2:2, 3:3, 4:3, 6:2, 7:1, 8:7, 9:2, 10:1. На новых widths2..9 эффект также повторяется; прежние S3v2i ошибки были только width10.
- **20/21** lower-owner pixel alpha **255**, **1/21** lower-owner alpha **141**; в **каждом** isolated top owner RGBA `[0,0,0,0]`; итоговая alpha при ordered рисовании совпала с нижней (21/21).
- Реальное изменение только RGB: 20 случаев на 1 byte в одном/двух каналах и **1** случай на 2 byte в двух каналах (канальные суммы отрицательны на этой выборке). Дельты: `[-1,-1,0,0]` 6; `[0,0,-1,0]` 8; `[0,-1,0,0]` 4; `[-1,0,-1,0]` 2; `[-2,-2,0,0]` 1. Это *конкретная* микроскопическая RGB-потеря, не допускаемый в игре «незаметный» foreign damage.
- Пример: `BPRED-S3V2J-W02-NEAR_SKEW-A_THEN_B` физическая координата `(508,353)`, lower native RGBA `[165,215,66,255]`, top-alone `[0,0,0,0]`, native ordered `[164,214,66,255]`, дельта `[-1,-1,0,0]`.

**Frozen detection H2 = DETECTED (21>0).** Этого достаточно, чтобы опровергнуть на независимой новой выборке универсальное «isolated alpha0 гарантирует нулевое влияние поверх другого цвета». Это не устанавливает, какой именно sub-byte alpha/rasterization/premultiplied путь ответственен; не устанавливает допустимость ущерба чужому owner. Для безопасности такой случай остаётся **UNKNOWN/FORBIDDEN** при защищённом источнике.

## 4. H3 — оригинальная двухцветная композиция по-прежнему не готова

Невозмущённая прежняя source-over math `s3.source_over` с fixed H1 threshold max channel≤2/255 + mean channel≤1/255 проверена на сорока новых ordered variants:
- **True original Canvas 31/40 PASS**, **9 FAIL** (worst max channel 85/255).
- **Original model Canvas→WebGL с фиксированной QH 21/40 PASS**, **19 FAIL** (worst max channel 170/255).
- Исторические S3v2f two-owner H2 14/40 FAIL, S3v2g P2 integer model FAIL, исходный S3 C0 FAIL30/40 сохраняются без пересмотра критериев. Адаптивность DEC-042 не допускает произвольного игнорирования source owner RGB damage.

Настоящая хронология кисти и GL texture stage воспроизводятся; **полное RGB предсказание последовательного рисования нескольких owners ещё не прошло**. Результат 31/40 на Canvas не означает H3-PASS для итогового WebGL (21/40).

## 5. Незавершённое и следующий шаг

Source protected original full image E/F P4D18 **FAIL**, canvas/planner source-alpha safe model **не принят**, source-owner foreign0 и source coverage≥99%/far leakage≤3 logical px hard quality gates не менялись. E4 game, E5 independent, run-bound exact CHALK `post.pointCount-pre.pointCount` **NOT_RUN**. Production, original game/render engine, Stage6 executor, Monitor/Bridge, master без изменений.

**NEXT в S3:** до расчёта ещё одной модели **отдельно заморозить E0** на основании доказанных физических случаев: безопасная interval/uncertainty envelope возле границ кисти (owner source alpha0 в PNG не равен физически нулевому влиянию) и реальная composition после второго штриха. Требуется independent fresh native validation после калибровки, не использовать S0 BLIND и не разрешать owner damage «потому что малозаметно». Проведённые 80 новых S3v2j теперь diagnostic/calibration, не будущая независимая acceptance.
