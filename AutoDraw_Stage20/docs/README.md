# Документация AutoDraw

**Статус:** основной индекс документации  
**Продукт:** AutoDraw 1.8.3  
**Корень приложения:** AutoDraw_Stage20/

Каталог содержит структурную документацию и файлы управления проектом. Документы описывают состав репозитория, назначение компонентов, конфигурацию, пользовательские данные, интерфейсы, форматы, сборку и порядок разработки.

Документация не является анализом поведения программы: не оцениваются корректность алгоритмов, производительность, качество результата или точность измерений.

## Навигация

| Документ | Назначение |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Общая структура приложения, подсистемы и связи |
| [COMPONENT_CATALOG.md](COMPONENT_CATALOG.md) | Каталог исходных модулей, тестов, утилит и CI |
| [MODULE_REFERENCE.md](MODULE_REFERENCE.md) | Структурный справочник модулей preparation, executor и Game Monitor |\n| [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md) | Справочник интерфейсов модулей preparation |
| [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) | Карта восьми вкладок, callback-связей и передачи данных в executor |
| [DATA_FORMATS_AND_MODELS.md](DATA_FORMATS_AND_MODELS.md) | Общие модели DrawingPlan, Stroke, Point и формат .autodraw |
| [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md) | Профили, палитры, планы, лабораторные и калибровочные результаты, экспорт Game Monitor |
| [CONFIGURATION_AND_DATA.md](CONFIGURATION_AND_DATA.md) | Каталоги данных, профили, форматы и переменные окружения |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Подготовка Windows-среды, запуск, тесты и сборка |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Текущее состояние проекта |
| [ROADMAP.md](ROADMAP.md) | План документирования и сопровождения |
| [TASKS.md](TASKS.md) | Реестр текущих задач |
| [DECISIONS.md](DECISIONS.md) | Журнал проектных решений |
| [WORK_LOG.md](WORK_LOG.md) | Журнал выполненных работ |
| [CHANGELOG.md](CHANGELOG.md) | История значимых изменений |

## Архивные и специализированные документы

- [README.md](../README.md) — точка входа приложения.
- [PROJECT_GUIDE.md](../PROJECT_GUIDE.md) — ранее созданный технический справочник.
- [MASTER_ROADMAP.md](../MASTER_ROADMAP.md) — исторический план разработки.
- [PROJECT_DOCUMENTATION.md](../PROJECT_DOCUMENTATION.md) — накопленная документация Stage20.
- [PROJECT_ANALYSIS_PLAN_10_STAGES.md](../PROJECT_ANALYSIS_PLAN_10_STAGES.md) — архивный аналитический план; этапы 7–10 отменены.
- [source/game_monitor/README.md](../source/game_monitor/README.md) — документация Game Monitor.

## Приоритет источников

1. Фактическое содержимое файлов текущей ветки.
2. Конфигурационные файлы, манифесты и сценарии запуска.
3. Сигнатуры и docstrings исходников для справочника API.
4. Тестовые файлы как источник названий тестовых точек, не как подтверждение поведения.
5. Документация соответствующей версии исходников.
6. Исторические отчёты.

При расхождении описания с текущим деревом репозитория обновляется документация. Изменения кода в рамках документирования не допускаются.
