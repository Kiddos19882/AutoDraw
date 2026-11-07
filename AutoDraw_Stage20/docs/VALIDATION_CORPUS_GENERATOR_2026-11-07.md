## 2026-11-08 — 81 images: дополнительный offline screening

Успешно выполнен [GitHub Actions 42416307401](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307401) (коммит `3fdffec`, [artifact 13591427560](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307401/artifacts/13591427560)). Анализатор `screen_candidate_corpus.py` сверяет реальные source SHA-256 с manifest и computes exact image-independent DrawingPlan geometry hashes без stroke names, pHash/dHash и image pixel features. Исходники обеих партий 31+50 присутствуют в репозитории. Exact duplicates 0, strict perceptual flagged pairs 0, 20 closest pair candidates требуют ручной проверки. Не делать выводов о semantic image family, статистической независимости, INT-006 domain eligibility либо 95% CHALK на основании этих признаков. Все raw results и ограничения — [TEST_RESULTS.md](TEST_RESULTS.md).

---

# Генератор кандидатного корпуса DrawingPlan и color scanline — 2026-11-07

**Статус:** IMPLEMENTED IN CODE / CI VALIDATION SUCCESS (51c731f; Windows build SKIPPED)  
**Инструмент:** source/preparation/generate_validation_corpus.py  
**Тесты:** source/preparation/tests/test_generate_validation_corpus.py

**Проверка CI (2026-11-07):** [GitHub Actions 42352776594](https://github.com/Kiddos19882/AutoDraw/actions/runs/42352776594) SUCCESS для code/test commit `51c731f`; Windows portable build/startup smoke-test и optional benchmarks SKIPPED. Это не является подтверждением локального запуска генератора на пользовательских изображениях или пригодности корпуса для 95% calibration/holdout.

## 0. Проверка при расширении repository testImages (2026-11-07)

Каталог `testImages/` увеличился до восьми поддерживаемых файлов в commit `0db0bcb`. Прежняя regression assertion на один уникальный исходник стала неактуальной. Test commit `098d5599` проверяет динамическое количество уникальных SHA-256, созданные .autodraw и color plans по каждому записи. Workflow commit `e984b68` добавил каталог в push triggers; [CI run 42387145503](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387145503) ещё проверяется на момент записи.

**Граница применимости:** Stage 8 scanline strokes имеют двухточечный `closed=false` формат и схематически соответствуют frozen INT-006 normalizer. Однако сам frozen INT-006 predictor проверялся на отдельной line-based domain, а не на всех generated scanline fill plans. Нельзя считать каждую строку scanline автоматическим valid CHALK observation или выдавать политику 95% для этих файлов. Fixtures `testImages` предназначены для offline smoke/inventory и не должны автоматически включаться в независимый production-like split.

### Фактический offline результат (2026-11-07)

Успешно выполнен [GitHub Actions 42387485762](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387485762) после исправления Linux import paths (`2fe37ef`); [artifact 13580167471](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387485762/artifacts/13580167471) содержит .autodraw, color scanline, manifest и N summary для всех восьми testImages. Уникальных SHA-256 — 8, дубликатов — 0; mono N 40–88, color N 172–295 при canvas 64×32. Подробные per-file результаты — [TEST_RESULTS.md](TEST_RESULTS.md). Первая попытка [42387397972](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387397972) FAILED из-за `PYTHONPATH`; эта попытка сохранена как отрицательный результат.

Валидационный статус остаётся `candidate_only_not_assessed`, а model eligibility — `not_assessed`. Это не production population, не замороженные N bands и не exact CHALK.

## Локальная offline-инвентаризация целевого корпуса на Windows

**Назначение:** получить реальные значения N, происхождение и предварительную диагностику формы DrawingPlan без открытия игры. Скрипт `AutoDraw_Stage20/run_validation_corpus_local.ps1` вызывает генератор, затем `audit_validation_corpus.py`, сохраняет новый каталог результатов без перезаписи.

**Действия пользователя:**

1. Подготовить папку с разнообразными **реально планируемыми** изображениями. Исходники не менять, одинаковые вариации одного рисунка не считать независимыми. Для предварительного инвентаризационного запуска достаточно 20–30 изображений разных типов; это не итоговая calibration/holdout выборка.
2. В PowerShell перейти в `AutoDraw_Stage20` (после синхронизации feature branch). При необходимости установить Python 3 и зависимости **в активный интерпретатор**:

```powershell
python -m pip install -r .\source\preparation\requirements.txt
```

3. Запустить, заменив входной путь и размеры холста на фактические настройки AutoDraw:

```powershell
.\run_validation_corpus_local.ps1 -InputFolder "D:\AutoDrawSamples" -CanvasWidth 646 -CanvasHeight 323
```

Используется профиль `data/palettes/profiles/Browser_palette.autodraw-palette.json` (можно переопределить `-PaletteFile`). По умолчанию результат пишется в новый `Documents/AutoDraw-Corpus-Runs/<run-id>`; при `-OutputRoot` путь должен отсутствовать.

4. Передать из созданной папки **два JSON**: `results/generated_validation_corpus_manifest.json` и `results/corpus_geometry_audit.json`. Также сообщить canvas width/height, фактический palette profile и возможные сообщения об ошибке. Raw images можно сохранить локально, их не требуется публиковать в GitHub; файлы могут содержать имена/хеши источников.

**Статус проверки:** [offline CI 42388237279](https://github.com/Kiddos19882/AutoDraw/actions/runs/42388237279) SUCCESS (8/8 schema valid); Windows runner [42388505263](https://github.com/Kiddos19882/AutoDraw/actions/runs/42388505263) FAILED из-за Python interpreter mismatch, исправлено `bb9bb2ee` и проверяется в [42388837703](https://github.com/Kiddos19882/AutoDraw/actions/runs/42388837703).

**Ограничения:** структурная валидность `closed=false`, двух конечных точек и N не означает поддержку геометрии frozen predictor. `predictor_domain_eligibility=not_assessed` остаётся до отдельного review. Ни изображения, ни эти результаты не используются автоматически как 19/59 calibration/holdout; точный игровой CHALK определяется только по разнице `pointCount` в валидном live capture.

## 1. Назначение

Генератор создаёт из набора исходных растровых изображений два независимых типа артефактов:

1. Portable-проект .autodraw со штатным Stage 12 processing result, бинарной маской, Stage 8 DrawingPlan и пересчитанным Stage 9 quality report.
2. Цветной autodraw_color_scanline_plan после штатного преобразования prepared image в заданную палитру CIELAB/CIEDE2000 и штатного color scanline planner.

Инструмент предназначен для воспроизводимой подготовки candidate corpus для офлайн-инвентаризации N и geometry families. Он не запускает executor, не взаимодействует с браузером/игрой и не измеряет CHALK.

## 2. Повторно используемые реализации

Генератор не реализует альтернативные алгоритмы преобразования:

- загрузка/EXIF orientation: image_processing.load_rgb_image();
- обработка, fit и бинарная маска: image_processing.process_image();
- монохромный DrawingPlan: stage8_optimizer.build_scanline_plan();
- portable archive: autodraw_project.create_project();
- проверка созданного проекта: autodraw_project.open_project();
- quantization: palette_quantization.quantize_image_to_palette();
- цветной план: color_scanline.build_color_scanline_plan();
- атомарное сохранение цветного плана: color_scanline.save_color_scanline_plan().

Для .autodraw качество пересчитывается существующей функцией внутри create_project; генератор не копирует внешний quality report как authoritative.

## 3. Запуск

Из корня AutoDraw_Stage20:

~~~powershell
python source/preparation/generate_validation_corpus.py --input "C:\path\to\source-images" --palette "data\palettes\profiles\palette-profile.json"
~~~

Если нужны только .autodraw и monochrome DrawingPlan:

~~~powershell
python source/preparation/generate_validation_corpus.py --input "C:\path\to\source-images" --skip-color-plans
~~~

Основные параметры:

- --canvas-width, --canvas-height: размер целевого холста (по умолчанию 646×323);
- --fit-mode: contain/cover/stretch;
- --row-step: шаг строк Stage 8 DrawingPlan;
- --color-row-step: шаг строк цветного плана;
- --threshold-mode, --threshold, --brightness, --contrast, --denoise-level: штатные Stage 12 настройки;
- --family: общая метка family, если она подтверждена оператором;
- --overwrite: явное разрешение перезаписать артефакты с теми же именами.

Без --palette цветные планы не создаются; для этого режима нужно явно передать --skip-color-plans.

## 4. Выходные данные

Для корня данных data/:

- data/projects/generated_validation_corpus/*.autodraw — проекты;
- data/results/color_scanline_plans/generated_validation_corpus/*.json — цветные планы;
- data/results/generated_validation_corpus_manifest.json — manifest корпуса, включая исходные SHA-256, family label и источник метки, plan IDs, N, hash планов, canvas, параметры и hash палитры.

Manifest сохраняет отдельно:

- drawing_plan_stroke_count — N для Stage 8 monochrome DrawingPlan;
- color_plan_stroke_count — N цветного scanline-плана.

Эти два N нельзя смешивать. Для INT-006 используется тот DrawingPlan, который реально поступает в frozen predictor / executor; перед назначением N bands требуется проверить согласованность именно с этим протоколом и его prediction artifact.

Дубликаты исходников с одинаковым SHA-256 не генерируются повторно и перечисляются в duplicates. Для одинакового содержимого задаётся один independence_group_id, поэтому копии одного изображения нельзя считать независимыми plan IDs.

## 5. Происхождение и статистические ограничения

Каждая запись помечена protocol_eligibility=candidate_only_not_assessed. Сам факт создания .autodraw и color plan не доказывает:

- что входные изображения представляют production population;
- что подпапка является достоверным geometry family;
- что разные изображения независимы по происхождению;
- что разные row-step/canvas/palette преобразования одного изображения являются независимыми DrawingPlan;
- что план входит в поддерживаемый line-based domain INT-006.

По умолчанию family label берётся из относительной подпапки input directory. Это только организационная метка источника, не автоматическая классификация геометрии. Для корневых файлов ставится unclassified. Метку можно задать через --family, но её происхождение сохраняется.

Генератор не создаёт split assignment, не отбирает 19/59 и не замораживает prediction artifact. Эти действия выполняются отдельно после проверки состава и происхождения корпуса. Не включать synthetic fixtures и тестовые шаблоны в production population без отдельного обоснования.

## 6. Проверки и ограничения

Генератор:

- проверяет расширения и доступность входных файлов;
- дедуплицирует точные копии по SHA-256;
- использует штатные validators/serializers;
- повторно открывает каждый .autodraw штатным reader;
- сохраняет manifest через временный файл и атомарную замену;
- отказывается перезаписывать существующие артефакты без --overwrite.

Текущие unit tests покрывают создание обоих форматов, открытие .autodraw, повторную загрузку цветного плана, дедупликацию и защиту от случайной перезаписи. Результат GitHub Actions должен быть зафиксирован отдельно; наличие тестового файла не означает, что tests/CI уже PASS.

## 7. Следующие шаги INT-006

1. Запустить генератор на доступном наборе исходных изображений и реальном профиле палитры.
2. Проверить происхождение каждого источника и family labels; исключить тестовые/синтетические изображения из production-like population либо явно выделить их в отдельную exploratory группу.
3. Сверить N с окончательным DrawingPlan, на котором работает frozen predictor.
4. Построить фактическое распределение N и geometry families; только затем зафиксировать low/medium/high bands.
5. Сформировать независимые calibration/holdout splits с защитой по source hash и independence group.
6. Заморозить manifest, canonical plan hashes, splits и protocol version до live capture.

Никакой CHALK reserve и production eligibility этот генератор не устанавливает.
