# AutoDraw — дорожная карта будущих работ

**Дата:** 2026-11-08 · **База сверки:** `a2d1f0a52d47` · **Ветка:** `feature/image-geometry-optimization`. Подробная прежняя редакция полностью сохранена: [ROADMAP_HISTORY_THROUGH_2026-11-08.md](ROADMAP_HISTORY_THROUGH_2026-11-08.md).

Этот файл задаёт **последовательность**, а не историю. Пункты выполнения и владельцы конкретных gate — [TASKS](TASKS.md); подтверждённые факты — [PROJECT_STATUS](PROJECT_STATUS.md) и [TEST_RESULTS](TEST_RESULTS.md).

## Этап 0. Быстрый достоверный вход в проект

Сократить актуальные управляющие файлы, собрать единый индекс всех Markdown, сохранить raw исторические snapshots и автоматизировать проверку ссылок/решений. Не удалять экспериментальные записи, ошибочные или неудачные попытки.

**Gate:** документация читается за 3–5 файлов, каждый значимый результат ведёт к исходному отчёту/commit/CI; проверен documentation CI.

## Этап 1. Офлайн-сравнение качества геометрии

Определить неизменный baseline на уже доступных изображениях. В FILL-001 воспроизвести perimeter-localized failure, сравнить scanline и outline-first / contour-correction без изменения production executor. Сопоставлять coverage, leakage, boundary errors, details, path length, strokes и expected operation count раздельно.

**Gate:** качество ≥99% coverage и leakage=0 для ранее заданных FILL-001 targets до новой live-проверки; offline simulation не утверждает runtime.

## Этап 2. Изучение фактического цветного execution pipeline

Отделить monochrome Stage8 scanlines от Stage6 color scanlines. Учитывать порядка 942206 source strokes, 395455 singletons и 916312 source color transitions на 81 изображении, но не приписывать эти числа одному рисунку и не превращать в CHALK. Проводить safety/overlap проверку перед попыткой сокращать цветовые переключения.

**Gate:** воспроизводимый сравнительный dataset, provenance и критерии качества, visual family independence отдельно.

## Этап 3. Оптимизация CHALK на основе уже выполненных опытов

Использовать измеренные G1–G3, V1–V5, D1–D5 и INT006R, не повторяя их без причины. При необходимости 95%-й policy заранее определить поддерживаемый domain и провести отдельную замороженную независимую validation (19/59 на профиль). Exact CHALK — только `post.pointCount-pre.pointCount`.

**Gate:** safety margin и применимость модели установлены для заявленного domain, а не для всех изображений по умолчанию.

## Этап 4. Интеграция resource preflight (INT-007)

Только после этапа 3 и других required quality gates: fail-closed UNKNOWN для неподдержанной геометрии, provenance модели, бюджетные предупреждения, regression, Windows startup и разрешённые live tests.

**Статус INT-007:** **BLOCKED**.

## Не смешивать уровни доказательств

CI/build, offline quality, real game `pointCount`, pixel equivalence и статистическая predictive coverage подтверждаются отдельно. История всех решений и неудач остаётся в [архиве дорожной карты](ROADMAP_HISTORY_THROUGH_2026-11-08.md) и специализированных отчётах.

## Совместимость старой ссылки на план калибровки

<a id="уточнённый-временный-план--автоматическое-определение-геометрии-доски-и-handoff-калибровки"></a>
Старый раздел перенесён в [полную дорожную карту до 2026-11-08](ROADMAP_HISTORY_THROUGH_2026-11-08.md#уточнённый-временный-план--автоматическое-определение-геометрии-доски-и-handoff-калибровки). Эта запись — навигация, а не возобновление закрытых задач.
