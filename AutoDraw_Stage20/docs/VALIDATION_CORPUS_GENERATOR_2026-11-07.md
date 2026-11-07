# Генератор кандидатного корпуса DrawingPlan и color scanline — 2026-11-07

**Статус:** IMPLEMENTED IN CODE / CI VALIDATION PENDING  
**Инструмент:** source/preparation/generate_validation_corpus.py  
**Тесты:** source/preparation/tests/test_generate_validation_corpus.py

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
