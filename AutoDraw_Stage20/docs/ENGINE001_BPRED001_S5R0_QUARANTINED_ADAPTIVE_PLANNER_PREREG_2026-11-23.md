# ENGINE-001 / BPRED-S5-R0 — исследовательский вход в S5 без допуска к игре (E0, 2026-11-23)

**Статус: PROSPECTIVE E0 / NOT_RUN.** Пользователь 2026-11-23 явно разрешил переход к S5. Это разрешение начать ограниченное исследование, **не** решение признать S4 картой достаточного качества, отменить DEC-049/DEC-050, выдавать gameplay strokes или запускать executor. Рабочая ветка `feature/image-geometry-optimization`; исходная точка [документированный S4.6 E2](ENGINE001_BPRED001_S4R1_S46_SOURCE_CONTRACT_E2_RESULTS_2026-11-23.md), код `86c5133c9c2cb2603cfaf1bdab872705a3b7de88`, документация HEAD до этого решения `d1886cf8ec47f393e2846795ede12b24be0dd55a`.

## Цель и границы

Проверить, можно ли строить *неисполняемые* адаптивные кандидатные пути кистей из **свежего полного оригинального RGB/alpha** через тот же S4.1–S4.6 контракт и определить, каких подтверждений не хватает для независимого S5 native входа. Это подготовка планировщика, а не оценка корректности/приёмка S4, не обещание полного рисунка. S5 согласно [единому плану](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md) отвечает за widths1–10, направления 360°, порядок реальных цветов, overlap, gap repair и full-scene coverage; S6 — отдельно strokes/CHALK.

**Действующий baseline:** S4.6 source packet E2 TECH PASS 11/11 и четыре original ×2 с raw hashes; `admissible_for_gameplay=false`, `source_owner_status=MISSING`, `native_calibration=UNVERIFIED`, `stroke_admission=FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE`. S4.5 критические детали глаз/волос PARTIAL; DG1 wV source color 131.668% > ART-C125 125% FAIL; original-source true strong-edge критерий >=75% для wV и EZAL остаётся; frozen scientific115% неизменен. **Ни одно из этих ограничений не превращается в PASS от разрешения пользователя.**

## Последовательность одного исследования

1. **S5-R0.1, E1 только чтение:** сверить текущий S4.6 API и producer, existing experimental planner, Egret stroke constructors, stroke constraints, existing full-scene visual/capture harness и границы logical/client/backing. Составить reuse-first перечень; не создавать параллельного executor.
2. **S5-R0.2, до кода отдельный фиксированный E0 кандидата:** один original-first исследовательский алгоритм геометрических *proposals* для 4 DEV, без старых художественных карт. Явно определить provenance, non-admissible input, метрики, deterministic run ×2, набор входных SHA, варианты ширины 1–10/углов и invalidation. Зависимости S4.6 и native ограничены read-only.
3. **S5-R0.3, только после E0 и статического аудита:** экспериментальные геометрические кандидатные траектории на полном оригинале с `status=MODEL_ONLY_NON_EXECUTABLE`. Адаптивная width выбирается по доступной территории одного game128 swatch/region, прогнозируемому физическому coverage и protected/foreign/white рискам; UNKNOWN отвергается, не трактуется как safe. Перекрытие своего цвета допускается. Подробности реальной кисти только через существующую модель и в будущем native Egret.
4. **S5-R0.4, отдельная валидация:** синтетические 1px точки/линии, границы 2 цветов, alpha, отверстия, узкие и широкие регионы; 4 целых DEV оригинала ×2; сравнивать bitmap coverage/leakage, missing original strong detail, original color и настоящие 4-connected source paintable, длину, число кандидатов/цветовых переключений раздельно. Сохранять FAIL и hashes. Результат не имеет статуса native E3 или CHALK.
5. **Только после отдельного source-owner/semantic acceptance и native coordinate/calibration evidence:** новый заранее зафиксированный E0 native replay через существующий Egret harness, затем отдельная оценка real E4; запрет автоматической передачи существующего S4.6 пакета executor остаётся.

## Вход, выход и fail-closed

Вход: полные оригинальные RGB/alpha и SHA, game128 из engine, оригинал-производный S4.6 source packet; любую прошлую карту, исправленный PNG и старые strokes запрещено использовать как вход. Неизвестный source owner, несоответствие SHA, размерности/coordinate space, недостаток исходной детали или unverified calibration ⇒ **`NOT_ADMISSIBLE`**. До native acceptance выход **только аналитический** (candidate count, proposed paths, physical risk estimates, uncovered/at-risk maps, hashes, rejection reasons), нельзя преобразовывать его в команды Stage6/Bridge/Monitor. Рискованная геометрия не может исправить плохую карту цвета/деталей; S4 acceptance gate остаётся открытым блокером.

## Gates и evidence

- **E0:** этот документ — гипотеза/протокол подготовки; S5 код, тесты и CI **NOT_RUN**.
- **E1:** инспекция source producer/consumers, повторное использование и разбор несоответствий — отдельно от автоматического S4 E2.
- **E2/E3:** только фактический прогон на конкретном SHA/CI run, не выводить их из E0.
- **E4/E5:** game run/независимая validation **NOT_RUN**; exact CHALK только `post.pointCount-pre.pointCount` с run binding.
- **Promotion:** исключительно после доказанного owner/critical-detail, выполнения действующих S4 quality gates и calibrated native replay. `master`, production Stage6, Bridge, Monitor, frozen protocols/thresholds не изменять.

**Первое непосредственно следующее действие:** S5-R0.1 read-only код/API и существующий planner/harness inventory; затем отдельный конкретный E0 реализации до разработки. Это **ограниченный переход к исследованию S5**, не открытие игрового S5.
