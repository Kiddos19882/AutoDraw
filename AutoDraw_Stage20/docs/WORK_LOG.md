

## 2026-11-04 — создан единый реестр результатов тестирования

- Создан [TEST_RESULTS.md](TEST_RESULTS.md) как центральный индекс и сводка автоматических тестов, GitHub Actions, live CHALK/brush experiments, Game Monitor/Bridge, FILL-001 и offline geometry benchmarks.
- Реестр фиксирует точный метод CHALK, статусы PASS/FAIL/CANCELLED/SKIPPED/BLOCKED, commit/run/artifact references и ограничения доказательности.
- Первичные отчёты, manifests, raw JSON, PNG и CI artifacts сохранены; их не дублируем и не удаляем.
- В управляющие документы добавлены ссылки на реестр. Локальный git status недоступен через GitHub API; изменения выполняются в feature/image-geometry-optimization.
