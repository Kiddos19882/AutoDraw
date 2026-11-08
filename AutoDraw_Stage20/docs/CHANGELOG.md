# AutoDraw — значимые изменения

Записывать только изменения интерфейсов, форматов, возможностей и значимые изменения сопровождения. Ход проверки каждой задачи — [WORK_LOG](WORK_LOG.md). Полная прежняя редакция без изменений: [CHANGELOG_HISTORY_THROUGH_2026-11-08.md](CHANGELOG_HISTORY_THROUGH_2026-11-08.md).

## 2026-11-08 — сохранённый game PNG против модельной контурной коррекции

- Добавлен изолированный (ф) `source/preparation/chalk_fill_screen_residual_comparison.py` с pinning actual evidence SHA, идентичным capture-audit screen transform, counterfactual overlays offset5–8, baseline-model discrepancy и ±1px sensitivity. Добавлены tests и CI artifact; никакой executor integration.
- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS на `16f0e1b`, [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Первый [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) FAILED из-за LF/CRLF JSON checkout, исправлен через канонический SHA только JSON без ослабления проверки PNG; сохранён в WORK_LOG.
- Actual live FILL-001 quality FAIL не изменён; contour model и sampling proxy не являются измеренным CHALK.

---

## 2026-11-08 — экспериментальный анализ FILL-001 A–D

- Изолированный (ф) `source/preparation/chalk_fill_strategy_comparison.py`: плотные/редкие scanline, связный contour, модельная oracle-коррекция residual; reuse frozen FILL masks и current OpenCV painter; **not executor ready**.
- Unit tests и GitHub Actions выгрузка 15 PNG/JSON. [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS, [artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597). CHALK estimator, Stage6 и production settings не изменены.

---

## 2026-11-08 — проверяемый актуальный слой и сохранённая история

- `docs/README.md` — полная навигация по 99 Markdown; текущие `PROJECT_STATUS/TASKS/ROADMAP/TEST_RESULTS` отделены от истории; архивы девяти старых редакций имеют проверяемые SHA-1 Git blob.
- Второе решение `DEC-016` перенумеровано в `DEC-027` с traceable mapping; методология в `AI_WORK_GUIDE` ускоряет выбор профильных источников.
- Введён Markdown integrity workflow и 5 unit tests: [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS; ноль найденных нарушений локальных ссылок, индексирования и уникальности решений. Внешние GitHub URLs, runtime и semantic correctness этот CI не проверяет.
- Исходный код приложения, CHALK predictor и первичные экспериментальные файлы не изменялись.

---

## 2026-11-08 — документация: быстрый актуальный контекст

- Текущие [PROJECT_STATUS](PROJECT_STATUS.md), [TASKS](TASKS.md), [ROADMAP](ROADMAP.md) отделены от полной исторической записи: исторические версии сохранены Git blob-for-blob.
- [TEST_RESULTS](TEST_RESULTS.md) преобразован в реестр доказательств G1–G3, INT-006/R, FILL-001-RS, renderer/PRR и 81-image offline corpus; сохранены все прежние подробные измерения.
- Не изменены форматы .autodraw, исходники algorithms/executor, Game Monitor, CHALK profiles, пользовательские данные или production settings.

## 2026-11-08 — последние подтверждённые функциональные изменения до документационной реорганизации

- В `screen_candidate_corpus.py` и tests добавлена проверка source images/geometry/color source summaries для 81 plans; [offline CI 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) SUCCESS на `5a55e9f`.
- [AutoDraw validation 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) SUCCESS на `5a55e9f`. Успех автоматических проверок не подтверждает live CHALK или FILL-001 PNG PASS.

Все предыдущие даты, тесты, неудачные прогоны и SHA доступны в [истории CHANGELOG](CHANGELOG_HISTORY_THROUGH_2026-11-08.md).
