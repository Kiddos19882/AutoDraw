# ENGINE-001 / B1-R-P1 — независимый original-RGB edge-aware эксперимент

**Experiment ID:** `ENGINE001_B1R_P1_FULLRGB_EDGE_AWARE_A`. **PREREG, 2026-11-18 — ДО нового запуска B1-R.** Parent ENGINE-001 / B1-R, решение [DEC-034](DECISIONS.md), [новый план](ENGINE001_B1R_RGB_FIRST_RESTART_PLAN_2026-11-18.md). Статус E0; никакого B1-R E2/E3/visual PASS ещё нет. Применение: только `testImages/wV6VeZI9S1Y.png`, original 200×320 RGB SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, выход 150×240. Никаких других изображений/доменов пока не валидируем.

## Изоляция от истории — жёсткое правило

**Единственный исполняемый вход — байты оригинального RGB.** Запрещены любые G32/P4c1, M1 protected union, B1_CHROMA12_SPATIAL, V44-B410, сохранённые старые штрихи, старые RGB детали и их производные — в качестве исходной цветовой карты, маски защиты, целевого контура, seed, fallback либо исходных цветов. Исторические ссылки сохраняются **в документах**, но не читаются тестовым кандидатом. Palette32, исходный `read_source`-downscale-first и прежние P0 `inputs()/run()` с M1/V44 не использовать. Разрешено переиспользовать только математические действия bilateral и оригинальный `strong_edges` (в новый full-resolution вход, без G32). Результирующий контур — **НОВЫЙ source-derived математический edge preview**, не игровой native stroke plan, не финальный контур, не V44.

## Замороженные до измерения параметры

Исходник: full RGB 320×200, не downscale. ROI для оценки важных частей указаны в исходных пикселях изображения (x0,y0,x1,y1), без G32-derived geometry: female-face/eyes `(35,45,113,133)`, male-face/eyes `(96,19,164,123)`, hands `(41,167,153,220)`, blouse `(32,123,140,196)`. Эти прямоугольники — приоритетные обзорные зоны, **не** результат обнаружения нейросетью и не точная маска глаз/рта; в настоящем P2 необходима отдельная семантическая проверка. Считать y вниз, x вправо, Python slices правые/нижние границы исключаются. Фон и силуэт приоритетны по RGB edge strength вне зон тоже.

На original RGB full 320×200 вычислить `delta4` как max CIEDE2000 между четырьмя исходными соседями, и `sobel` по исходной luminance. Защитить source-Sobel90 и `delta4>=12` **по всему полю**; внутри ROI дополнительно `delta4>=6`, расширить защищённые пиксели в ROI на 1 original pixel (binary dilation). Защита вычисляется только один раз **до фильтра** и не зависит от кандидата. Downscale с LANCZOS до 150×240; пиксели логической маски, полученные `BOX(full_protect_uint8)>0`, восстанавливать из эталонного original ROI точь-в-точь. Ранний source full protected сохранять побайтно ещё до уменьшения.

**Варианты:** original RGB no filter — независимый контроль, не кандидат; `A_SOFT`: `cv2.bilateralFilter(original,d=5,sigmaColor=18,sigmaSpace=2.0)`, `A_MID`: `cv2.bilateralFilter(original,d=7,sigmaColor=28,sigmaSpace=3.0)`. RGB всех вариантов привязан к оригиналу (никакого nearest32). Фильтровать **до** защиты/scale, затем восстановить protected originals. Два заранее установленных уровня нельзя настраивать после изображения. Оригинальный PNG и обе версии сохранять и на 320×200, и на 150×240.

**Новый contour preview:** из одного original full RGB взять `(sobel>=Sobel90 AND delta4>=6)`, бинарная `skimage.morphology.thin`, отбрасывать независимые 8-связные компоненты площадью <3 full pixels **кроме** пересечений ROI с `delta4>=12`; это даёт одну неизменную новую геометрию для A_SOFT/A_MID. Stroke-preview оттенки выбирать из самого original source как самого тёмного RGB пикселя соседства 3×3 по original grayscale, без выдуманного/палитрового цвета; alpha=185. Перенос на logical ROI `NEAREST`, прозрачный source-over на RGB после фильтра. Это **не native Egret contour**, и способ цвета — исследовательский proxy для визуального сравнения, не production.

## Замороженные gates и отчёт

Для каждого A на source logical150×240 (36,000 pixels) и full 200×320:
- защита **full original mask** и logical BOX-mask = точно исходные RGB без сдвига;
- средняя CIEDE2000 к original ROI <=2.0, p95<=7.0;
- anchored grayscale Sobel strong-edge overlap >=0.90 при original full source90 threshold и сравнении на logical source90 threshold;
- mean ROI ΔE00 для female/male face-eyes/hands <=2.0 каждый (не заменяет глаз/рот);
- чужая насыщенность: число logical pixels, где mapped Lab chroma > source Lab chroma+12, <=60; **не** глобальный запрет розового;
- flat-region neighbor RGB roughness reduction >=1% относительно original ROI на неизменной маске `original sobel <= median(positive original sobel)`. Если отсутствие реального сглаживания — FAIL, даже при малой ΔE;
- контур source-derived geometry exactly same for both A; не заменяет existing native V44;
- никаких game32, native brush, точного CHALK и заявлений об узнаваемости.

`SOURCE_SCREEN_PASS_VISUAL_PENDING` только когда все численные gates выполнены. При провале — `SOURCE_GATE_FAIL`, сохранить все PNG/отчёты. В обоих случаях окончательное принятие требует визуального сравнения лиц, волос, рук, одежды; E3/metrics не доказывают узнаваемость. Изображение с новым source-derived контуром — *предпросмотр*: не native E3.

Выход: оригинал, `A_SOFT`, `A_MID` full/logical, full protected/edge, новый outline RGBA, обе сцены RGB+новый outline, единая сравнительная панель PNG и `report.json` с source SHA, точным SHA каждого файла, Python/OpenCV/skimage/Pillow версиями, provenance `candidate_source=original_RGB`, `legacy_G32_used_as_candidate=false`, `legacy_V44_used_as_candidate=false`; без перезаписи старых артефактов. Test-only script, синтетические tests, dedicated bounded CI. В качестве самого первого наблюдения допускается именно отрицательный источник: если A визуально почти не отличается, B1-R-P1 не объявлять успехом по отсутствию искажений. Далее B1-R-P2 — согласованные цветовые области и новый контур, только если RGB-этап достаточно читается.

**Исторические controls:** P0 [CI44229576245](https://github.com/Kiddos19882/AutoDraw/actions/runs/44229576245) E3 source-only PASS, **не** заменяет этот prereg; B1 [CI44230985963](https://github.com/Kiddos19882/AutoDraw/actions/runs/44230985963) four source quality FAIL; B4 [CI44236852882](https://github.com/Kiddos19882/AutoDraw/actions/runs/44236852882) real native full artwork quality FAIL. Старые thresholds не пересчитывать, не объявлять их улучшением.

**Источник SHA — коррекция опечатки (append-only 2026-11-18):** первичная регистрация выше ошибочно содержала 62-символьный SHA256 (пропущены два символа `6c`). Исходный PNG на GitHub неизменен, blob `d3cd95b846f036a3f8acecf75d2a237e46dcf13a`, размер 97308 bytes; точный SHA256 исходного файла `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a` (64 символа), идентичен успешному P0. Исправление касается только записи source provenance; методы bilateral, ROI/protected, source-gates и всё остальное prereg **не менялись**. Первоначальный CI44243911088 FAIL на fail-closed source-SHA оставлен в истории.
