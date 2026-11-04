# INT006R — live preflight и визуальный аудит

> **Исторический протокол выполнения.** Описанные ниже preflight/launch инструкции относятся к завершённой серии 2026-11-03. Они сохранены для воспроизводимости, но не являются разрешением на новый live run и не описывают текущий backlog. Результаты: `CHALK_INT006R_LIVE_RESULTS_2026-11-03.md` и `CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md`.


**Статус на дату создания:** HISTORICAL / SUPERSEDED. 45/45 captures завершены; raw-data audit PASS; официальный CLI analyzer PASS; ручной visual audit 45 пар PNG завершён. Текущие ограничения и применимость см. `TASKS.md` / `ROADMAP.md` и итоговые отчёты INT006R.  
**Фаза:** INT006R  
**Матрица:** D1–D5 × radius 1/10/30 × 3 повтора = 45 captures  
**Sampling:** P1 — point_step_px=4, point_delay_ms=5 ms  
**Рабочая ветка:** feature/image-geometry-optimization

## Текущий статус live серии — 2026-11-03

Live block выполнен и сохранён в commit `138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a`:
- series `chalk-20261103-030837-a20df5`;
- block `a8e0b9ec87984f60aa294910d366e987`;
- 45/45 tasks completed;
- exact CHALK и per-stroke delta совпадают; observed radius соответствует requested; dropped events, Monitor errors, Bridge failures и sequence gaps — 0.

Raw-data результаты: [CHALK_INT006R_LIVE_RESULTS_2026-11-03.md](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md).

Этот документ сохраняет инструкцию как воспроизводимый протокол. Следующие действия: запустить CLI analyzer на committed live journal/capture bundle, затем вручную проверить все 45 пар before/after PNG и заполнить таблицу visual audit. До этого visual quality gate не закрывать.

## 1. Обязательные условия до live запуска

Не запускать блок, пока не выполнены все пункты:

- [ ] Полный GitHub Actions workflow для актуального code HEAD завершился SUCCESS.
- [ ] Windows portable build и startup smoke-test завершились SUCCESS.
- [ ] Portable-приложение запущено на Windows; игра и доска доступны.
- [ ] Game Monitor Bridge подключён; heartbeat свежий, exact pointCount доступен.
- [ ] Профиль калибровки содержит board ROI, paint-meter ROI и координату Clear; профиль не помечен как требующий проверки.
- [ ] Расширенный slider кисти откалиброван по обеим крайним точкам диапазона 1–30; управление должно выполняться перетаскиванием.
- [ ] Эталон пустой доски сохранён и соответствует текущему разрешению/калибровке.
- [ ] Доска чистая, текущий рисунок можно удалить, нет другого активного CHALK block/journal.
- [ ] Для серии выбран новый уникальный series ID; старые manifests и журналы не переиспользуются.

Если хотя бы одна проверка не пройдена, live block не запускать. Не обходить preflight и fail-closed gates.

## 2. Запуск INT006R

1. Открыть вкладку Brush Test.
2. В разделе автоматического блока CHALK выбрать фазу INT006R.
3. Проверить, что серия использует новый ID.
4. Нажать «Запустить полный блок» и подтвердить, что текущую тестовую доску разрешено очищать.
5. Во время блока не менять радиус, sampling или настройки исполнителя вручную.
6. Дождаться завершения всех 45 задач либо остановить блок штатной кнопкой на безопасной границе.

Для каждой задачи UI берёт requested radius из durable journal. Ожидаемые значения — 1, 10 и 30. Перед запуском executor сверяет радиус из metadata с requested brush. P1 фиксирован на 4/5.

Блок автоматически останавливается при failed/inconclusive capture. Не редактировать journal вручную и не перескакивать через не принятую задачу. Перед recovery обязательно проверить игровую доску и состояние кисти.

## 3. Где искать результаты

Journal сохраняется в каталоге:

- `<output_dir>/chalk_test_blocks/chalk-block-INT006R-<series_id>-<block_id_prefix>.json`

Experiment manifests и связанные файлы сохраняются в подпапках `<output_dir>`. Для каждой принятой задачи должны присутствовать:

- `experiment.json`;
- `monitor_report.json`;
- `before_draw-board.png`;
- `after_draw-board.png`;
- остальные screenshot ROI и Monitor evidence, созданные штатным capture workflow.

Не перемещать отдельные файлы внутри capture bundle и не переименовывать experiment directories до анализа.

## 4. Запуск независимого analyzer

Из корня репозитория в PowerShell:

```powershell
$env:PYTHONPATH = "AutoDraw_Stage20;AutoDraw_Stage20/source/preparation;AutoDraw_Stage20/source/executor"

python AutoDraw_Stage20/source/preparation/chalk_int006r_validation.py `
  --journal "<output_dir>\chalk_test_blocks\<INT006R journal>.json" `
  --results-dir "<output_dir>" `
  --output "<output_dir>\int006r-analysis.json"
```

Ожидаемый data gate:

- `status=complete`;
- `accepted_count=45`;
- `missing_count=0`;
- `rejected=[]`;
- 15 групп scenario × radius, по 3 повтора;
- 45 уникальных experiment IDs и Monitor run IDs;
- точное равенство CHALK delta и суммы per-stroke DRAW_SAMPLE.pointDelta;
- валидные before/after board PNG для каждого capture.

Analyzer также рассчитывает mean, median, min/max и population SD по каждой ячейке, а для radius 1 и 30 — абсолютную и относительную разницу относительно radius 10 в рамках той же геометрии.

Код завершает работу с exit code 0 только при полном data gate. Неполный набор, неверный журнал, повторная ячейка или ошибка binding должны оставить отчёт incomplete/invalid.

## 5. Визуальный аудит — отдельный gate

Даже при `status=complete` поле `visual_quality_gate` остаётся `pending_manual_review`. Полнота данных и визуальная пригодность — разные критерии.

Проверить все 45 пар before/after board ROI, сгруппировав их по D1–D5 и радиусу:

| Геометрия | Radius 1 | Radius 10 | Radius 30 |
|---|---|---|---|
| D1 — смешанные линии | 3 повтора | 3 повтора | 3 повтора |
| D2 — пятиугольник | 3 повтора | 3 повтора | 3 повтора |
| D3 — пересечения | 3 повтора | 3 повтора | 3 повтора |
| D4 — короткие детали | 3 повтора | 3 повтора | 3 повтора |
| D5 — повторное покрытие | 3 повтора | 3 повтора | 3 повтора |

Для каждого capture проверить:

- все ожидаемые штрихи появились на доске;
- отсутствуют разрывы, исчезнувшие сегменты и неожиданные пропуски;
- пересечения не сливаются в неприемлемые пятна;
- короткие детали и точки различимы;
- повторное покрытие не приводит к неожиданному расширению/слиянию следа;
- толщина следа и форма концов соответствуют фактическому радиусу;
- before/after ROI имеют одинаковые размеры и одинаковую калибровочную геометрию.

Не считать визуальный результат успешным только по факту завершения executor. Не делать вывод о качестве по одному повтору.

## 6. Форма фиксации визуального аудита

| Геометрия | Радиус | Повторы проверены | Визуальный результат | Замечания |
|---|---:|---:|---|---|
| D1 | 1 | 0/3 | PENDING | |
| D1 | 10 | 0/3 | PENDING | |
| D1 | 30 | 0/3 | PENDING | |
| D2 | 1 | 0/3 | PENDING | |
| D2 | 10 | 0/3 | PENDING | |
| D2 | 30 | 0/3 | PENDING | |
| D3 | 1 | 0/3 | PENDING | |
| D3 | 10 | 0/3 | PENDING | |
| D3 | 30 | 0/3 | PENDING | |
| D4 | 1 | 0/3 | PENDING | |
| D4 | 10 | 0/3 | PENDING | |
| D4 | 30 | 0/3 | PENDING | |
| D5 | 1 | 0/3 | PENDING | |
| D5 | 10 | 0/3 | PENDING | |
| D5 | 30 | 0/3 | PENDING | |

Любой дефект, влияющий на видимость или непрерывность штриха, должен быть записан отдельно. До завершения визуального аудита INT006R не считать полностью закрытой.

## 7. Интерпретация результатов

- Сначала сравнить radius 1/10/30 внутри каждой геометрии, затем сравнить характер эффекта между D1–D5.
- Сопоставлять mean и разброс трёх повторов; единичное отличие не объявлять устойчивым эффектом.
- Если изменение между крайними радиусами превышает естественный разброс повторов или проявляется нелинейность, спроектировать дополнительную серию для радиусов 5/15/20/25 на затронутых геометриях.
- Не переносить выводы на кривые, заливки и произвольные полные рисунки без отдельной validation.
- Не вводить radius multiplier, safety margin или production estimator update автоматически по результатам INT006R.

Frozen INT-006 model, production estimator/defaults и master остаются неизменными.
