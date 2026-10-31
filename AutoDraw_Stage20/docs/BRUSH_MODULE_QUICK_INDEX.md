# Быстрый поиск по документации: модуль автоматических тестов кистей и CHALK

**Назначение:** точка входа для разработчика или ИИ-агента перед изучением и реализацией модуля автоматизированных экспериментов.  
**Рабочая ветка:** `feature/image-geometry-optimization`.  
**Корень приложения:** `AutoDraw_Stage20/`.  
**Главный документ концепции:** [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md).

> Этот файл — навигационный индекс, а не замена исходникам и подробной документации. Он помогает быстро найти нужный контекст. Перед изменением кода обязательно открыть фактический файл реализации в текущей ветке и проверить его актуальные вызовы/сигнатуры.

## 1. Быстрый старт: что читать в первую очередь

| Порядок | Документ / исходник | Зачем открывать |
|---:|---|---|
| 1 | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md) | Целевая архитектура, компоненты, полный жизненный цикл, матрица, checkpoints и критерии готовности |
| 2 | [TASKS.md](TASKS.md) | Текущие статусы INT-003—INT-009 и зависимости |
| 3 | [PROJECT_STATUS.md](PROJECT_STATUS.md) | Что подтверждено, что не завершено и какие действуют ограничения |
| 4 | [GAME_MONITOR_BRUSH_LAB_PLAN.md](../GAME_MONITOR_BRUSH_LAB_PLAN.md) | Подробный технический контекст Game Monitor, CHALK и лаборатории кистей |
| 5 | [source/game_monitor/README.md](../source/game_monitor/README.md) | Подключение, команды, snapshot и ограничения Game Monitor 0.2.0 |
| 6 | [MODULE_REFERENCE.md](MODULE_REFERENCE.md) | Быстрый поиск назначения основных программных модулей |
| 7 | [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) | Интерфейсы Stage6 и executor |
| 8 | [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md) | Интерфейсы модулей подготовки и лаборатории |
| 9 | [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) | Как вкладки и callbacks связаны с integrated_app и executor |
| 10 | [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) | Реальные прямые импорты и зависимости модулей |
| 11 | [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md) | Форматы профилей, калибровки, планов и отчётов |
| 12 | [WORK_LOG.md](WORK_LOG.md) и [DECISIONS.md](DECISIONS.md) | История технических выводов и принятых решений |

## 2. Карта компонентов: где искать код

| Компонент | Основной файл / каталог | Что искать |
|---|---|---|
| Точка интеграции приложения | `AutoDraw_Stage20/integrated_app.py` | Создание вкладок, передача callbacks и DrawingPlan, получение canvas area/size, связь Brush Test с Stage6 |
| UI лаборатории кистей | `AutoDraw_Stage20/source/preparation/brush_behavior_test_ui.py` | Сценарии, создание логических DrawingPlan 420×240 и передача теста |
| Преобразование координат Brush Test | `AutoDraw_Stage20/source/preparation/brush_coordinate_transform.py` | Явное преобразование logical_board_pixels в screen-local ROI с сохранением transform в generation metadata |
| Исполнитель мыши | `AutoDraw_Stage20/source/executor/drawing/mouse_executor.py` | MouseExecutor, ExecutorConfig, экранные координаты, движение мыши, отчёт исполнения |
| UI исполнителя | `AutoDraw_Stage20/source/executor/stage6_execute_plan.py` | Загрузка плана, preview, проверка размеров, запуск рабочего потока и передача в MouseExecutor |
| Game Monitor | `AutoDraw_Stage20/source/game_monitor/game_monitor.js` | Поиск BoardPane, snapshot, inspect, export, wrappers, stop/start |
| Документация Game Monitor | `AutoDraw_Stage20/source/game_monitor/README.md` | Команды Monitor, контекст iframe и ограничения |
| Ресурсная модель | `AutoDraw_Stage20/source/preparation/board_resource_model.py` | Калиброванная модель точек/ресурса; не путать с точным игровым счётчиком |
| Калибровка игровых точек | `AutoDraw_Stage20/source/preparation/engine_point_calibration.py`, `game_point_calibration.py` | Исторические/теоретические оценки и их ограничения |
| UI тестирования лимита | `AutoDraw_Stage20/source/preparation/paint_limit_test_ui.py` | Существующие сценарии тестирования ограничения ресурса |
| Модели геометрии | `AutoDraw_Stage20/source/geometry_models/` | Общие Point, Stroke, DrawingPlan |
| Профили и калибровка | `AutoDraw_Stage20/source/preparation/profile_manager.py` и связанные модули | ScreenArea, calibration settings, параметры ввода |
| Игровой bundle (только чтение) | `AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js` в `master` | Источник BoardPane; не изменять master |
| Статический анализ bundle | `AutoDraw_Stage20/tests/analyze_game_brush_engine.py` | Повторяемая статическая проверка игрового bundle |

Пути выше — навигационные указатели. Если файл переименован или перемещён, сначала проверьте дерево текущей ветки и обновите этот индекс.

## 3. Поиск по задаче: ключевые темы и точные документы

| Если нужно найти… | Сначала открыть | Затем проверить в коде |
|---|---|---|
| Целевую архитектуру и порядок реализации | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), разделы 3–4 и 10 | `integrated_app.py`, Brush Test UI, Stage6 |
| CHALK: точную формулу и delta | [GAME_MONITOR_BRUSH_LAB_PLAN.md](../GAME_MONITOR_BRUSH_LAB_PLAN.md), разделы о CHALK snapshot; [source/game_monitor/README.md](../source/game_monitor/README.md) | `game_monitor.js`, источник BoardPane в bundle |
| Почему нельзя использовать абсолютный pointCount как расход | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), раздел 2 | поля `max`/`less` в Monitor |
| Размер кисти и влияние на расход | [GAME_MONITOR_BRUSH_LAB_PLAN.md](../GAME_MONITOR_BRUSH_LAB_PLAN.md), разделы о движке и экспериментальной матрице | чтение `atom.radius`, установка ползунка, сценарии Brush Test |
| Logical 420×240 и экранный ROI | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), раздел 3.4; [GAME_MONITOR_BRUSH_LAB_PLAN.md](../GAME_MONITOR_BRUSH_LAB_PLAN.md), уточнение координат | `_get_brush_test_canvas_size()`, `_get_brush_test_canvas_area()`, `MouseExecutor._screen_point()` |
| Преобразование logical→screen | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), разделы 3.4 и 10 | `brush_coordinate_transform.py`, `_get_brush_test_canvas_size()`, `_transfer_brush_test_plan()`; live-проверка границ остаётся |
| Системное движение мыши и параметры скорости | [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) | `MouseExecutor`, `ExecutorConfig`, `point_step_px`, `point_delay_ms` |
| Loopback bridge и привязку событий | [GAME_MONITOR_BRUSH_LAB_PLAN.md](../GAME_MONITOR_BRUSH_LAB_PLAN.md), разделы архитектуры и протокола; [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), раздел 3 | существующий IPC/bridge код и места его запуска |
| Повторы, seed, матрицу и overlap | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), разделы 5–6 | генератор DrawingPlan и Brush Test UI |
| Сохранение JSON, manifest и export | [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), раздел 7; [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md) | сериализаторы, каталог экспериментальных данных, export Monitor |
| A/B/C overhead Monitor | [GAME_MONITOR_BRUSH_LAB_PLAN.md](../GAME_MONITOR_BRUSH_LAB_PLAN.md), разделы тестирования; [TASKS.md](TASKS.md), INT-003 | Monitor 0.1.2/0.2.0, тесты и CI |
| Unit-тесты и CI | [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md) | соответствующие `tests/` и workflow в `.github/workflows/` |
| Текущие блокеры и статусы | [TASKS.md](TASKS.md), [PROJECT_STATUS.md](PROJECT_STATUS.md) | актуальная ветка и последние commits |

## 4. Главные факты и ограничения, которые нельзя потерять

- Логическая доска игрового движка — **420×240**; экранный ROI — отдельная система координат.
- Logical→screen transform для Brush Test реализован на этапе передачи плана: logical 420×240 преобразуется в локальные пиксели ROI, обычные local/screen планы не затрагиваются. Используется отображение включительных границ логической доски в крайние пиксели ROI; его соответствие живому hit-test ещё нужно подтвердить.
- Точный ресурсный снимок: `pointCount = maxPoints - remainingPoints`.
- Расход опыта: `consumed = post.pointCount - pre.pointCount`, только если baseline/post валидны и относятся к одной сессии доски и одному лимиту.
- Baseline снимается после подтверждённого Clear; post — до следующего Clear.
- Радиус кисти не входит напрямую в формулу CHALK. Его влияние на покрытие и число необходимых траекторий проверяется экспериментально.
- Длина траектории, площадь следа, количество вызовов движения и количество игровых точек — разные величины; не подменять ими CHALK.
- Измеряемые штрихи должны идти через MouseExecutor/PyAutoGUI. Не вызывать из тестового контура игровые методы и не менять `atom.points`, `max`, `less`.
- Game Monitor 0.2.0 использует O(1) resource snapshot из `max/less`; полный обход `atom.points` — только явная диагностика.
- Статическая проверка и Node-тесты не заменяют live-проверку в iframe и A/B/C замеры.

## 5. Порядок работы при реализации

1. Проверить текущую ветку, HEAD и последние commits; не работать в `master`.
2. Прочитать этот индекс и разделы главного документа концепции, относящиеся к текущей задаче.
3. Открыть реальные исходники всех затрагиваемых callsites; сверить документацию с кодом.
4. Проверить зависимости и существующие тесты до изменения интерфейсов.
5. Сначала подтвердить live-геометрию уже реализованного logical→screen transform; затем двигаться к bridge/синхронизации, runner и recorder — в порядке актуального TASKS/ROADMAP.
6. Добавить unit-тесты на преобразование координат и регрессии обычных screen/local планов.
7. Обновить профиль/manifest и документацию, не смешивая точные измерения с оценками.
8. Не запускать полную CHALK-матрицу, пока не пройдены геометрические и live measurement gates.
9. После работы обновить TASKS, PROJECT_STATUS, WORK_LOG и CHANGELOG; не отмечать задачу DONE без критериев проверки.

## 6. Границы достоверности и статусы

- **Подтверждено статически:** формула чтения `max/less`, устройство Monitor 0.2.0, существующая основа Brush Test/MouseExecutor и реализация преобразования logical→screen.
- **Не подтверждено runtime:** доступность и точность `max/less` на живой доске, реальная установка радиуса во всех режимах, точность transform на живой игре, численный overhead Monitor.
- **Не завершено:** live A/B/C, loopback integration, полноценный batch runner, полная матрица, валидированная модель CHALK и подключение модели к оптимизатору.
- Статус задач смотреть в [TASKS.md](TASKS.md); не выводить его только из этого файла, поскольку статусы могут меняться.

## 7. Правило поддержки этого индекса

При добавлении, переименовании или переносе модулей:
- обновлять таблицу компонентов и поисковые темы;
- проверять относительные Markdown-ссылки;
- сверять упомянутые методы и поля с исходниками;
- сохранять в индексе только устойчивые точки входа, а подробности оставлять в специализированных документах;
- не копировать сюда целые разделы других документов.


## Дополнение: реализованное преобразование координат

`source/preparation/brush_coordinate_transform.py` содержит `transform_logical_brush_plan_to_screen()`. Brush Test теперь создаёт план в `logical_board_pixels` (420×240), а интеграционный слой преобразует его в `local_canvas_pixels` перед загрузкой в Stage6. Исходный план сохраняется с `generation.screen_transform`; runtime-план имеет размер экранного ROI. Для тестовых штрихов отключено дополнительное продление концов. Тесты: `source/preparation/tests/test_brush_coordinate_transform.py` и обновлённый `tests/test_unified_app.py`.


**Защита Stage6:** исходный logical_board_pixels JSON нельзя открывать напрямую через обычную загрузку DrawingPlan. Для него предусмотрена передача через Brush Test, где выполняется преобразование в экранный ROI. Stage6 отклоняет прямую загрузку такого исходника.
