## 2026-11-05 — закреплены границы локального доступа и автоматизация live-тестов

**Объём:** только документация, ветка `feature/image-geometry-optimization`.

- В начале README и индекса документации добавлено заметное правило: локальная программа, игровая сессия и доска доступны только пользователю; локальный `git status` на ПК также может подтвердить только пользователь.
- В AI_WORK_GUIDE и EVIDENCE_AND_VALIDATION уточнено различие между удалённой проверкой GitHub и локальным состоянием ПК, а также требования к доказательствам live-тестов.
- В ENGINEERING_INVARIANTS приняты INV-010 (границы локального доступа) и INV-011 (максимальная автоматизация тестов с игровой доской).
- DEC-024 фиксирует постоянное решение: повторно использовать существующие средства автоматизации, создавать недостающие условия, автоматизировать сбор данных/точный CHALK/аудит/отчётность и минимизировать ручные шаги пользователя.

**Не выполнялось:** локальный `git status`, запуск AutoDraw, live-тесты с игровой доской. Код, тесты и workflow не менялись.


## 2026-11-05 — formal renderer acceptance tooling

- Reviewed the active multi-axis code, capture contract, historical horizontal baseline, same-run screenshots and the predeclared TASKS.md thresholds.
- Added fail-closed per-run evidence/geometry/pixel validation and a separate three-repeat series aggregator; added unit tests and CI wiring for the existing horizontal baseline audit.
- Kept vertical/diagonal live work blocked on actual user-screen captures. No live experiment, production renderer/planner/estimator/default, calibration profile, or executor behavior was changed.
- CI verification and post-run documentation sync remain pending.
