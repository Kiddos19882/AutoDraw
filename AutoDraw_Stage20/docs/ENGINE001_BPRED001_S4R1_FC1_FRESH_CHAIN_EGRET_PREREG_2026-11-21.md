# ENGINE-001 / BPRED-S4-R1 / FC1 — полный независимый original-first исследовательский Egret-проход (E0)

**Дата:** 2026-11-21. **Тип:** заранее зафиксированный ограниченный research-only протокол до реализации и native-измерения. **Задача:** FC1, исполнение DEC-046/DEC-047 внутри существующего S4-R1, без открытия формального S4 BLIND/S5/S6.

## Цель и проверяемое предположение

Из **байтов оригинального файла** в *текущем запуске* построить все промежуточные карты и все штрихи новым полным конвейером, получить полный PNG именно из настоящего Egret BoardPane/WebGL, показать пользователю исходник, свежую игровую квантованную цель, итог и диагностические проблемные места. Допустить визуальные ошибки в исследовательском preview и не блокировать прогресс новыми safety-теоремами. Гипотеза: даже простая последовательная независимая RGB→owner128→геометрия адаптивной заливки→контур→native-feedback repair уже даёт оцениваемый полный рисунок.

## Строгая независимость данных (главный пользовательский критерий)

**Обязателен весь новый алгоритм в одном воспроизводимом прогоне:** `original raw bytes → normalized RGB/alpha → fresh logical RGB/alpha → fresh source analysis / owner palette proposal → fresh regions/contours → fresh adaptive width1..10 stroke planner → current-run native Egret fill → repair from this current-run native RGBA → current-run native Egret final → comparison`.

**Вход в алгоритм разрешён только:** оригинальный PNG непосредственно из `testImages/wV6VeZI9S1Y.png`; SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; неизменяемый реальный игровой bundle `gameEngine/main.min_653f95bc.js` Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388` **только для 128 игровых swatches и API**; native renderer `tests/game_renderer_reference.js` blob `76d950e0a8911888a9df3b675b866519ecf7bba4`, Firefox159 **только как измерительный прибор**; чистые статeless source-помощники декодирования/оригинальной RGB/Lab анализа и native transport без загрузки прежних результатов. Logical Egret test crop 150×240 / physical scale3 и source X=155 — только калибровка тестового стенда, не шаблон других картинок.

**Категорически не участвуют в вычислениях, отборе, метриках нового результата и native repair:** какие-либо старые `E/F`, `G32/V44`, `P3D/P4D*/P4C*` карты/контуры/маски/индексы, прошлые штрихи, подгонки, сегментации, результаты экспериментов, старые распечатки файлов, изображения из прошлых артефактов и старые результаты качества/погрешности. Нельзя незаметно подменить fresh-карту существующей archived owner-index или взять старые protected masks. Старые данные допускаются **лишь как отдельный baseline после создания и фиксации нового результата**; исходные game128 swatches и физика native Egret — свойства среды, а не данные старого метода. Не использовать old ROI face/eyes/hands.

## Зафиксированная проба FC1

- **Вход:** один known DEV original `wV6VeZI9S1Y.png`, 200×320 RGB (форма/sha перепроверить реально). Другие изображения не подмешивать, H8/BLIND120/second50 sealed.
- **Подготовка:** явный original EXIF decode; RGBA; пропорциональная RGB/alpha LANCZOS projection в тестовые 150×240; прозрачные owner `-1` исключаются, opaque current DEV first.
- **Цвет:** свежая ближайшая в CIELAB из реальных 128 игровых swatches гипотеза; не 32 фиксированных старых цвета, не старые E/F owner. RGB/alpha оригинала неизменны, output color target явно помечается `PROVISIONAL`.
- **Контур и заливка:** свежие границы из current source RGB и current owner adjacency; самостоятельно сгенерированные контуры поверх краски; планирование по маскам каждого текущего owner на основе distance transform и residual heuristic, ширины из 1..10 с горизонтальными/вертикальными линиями и width1 остатками; модель кисти — только эвристика выбора штрихов, результат качества — реальный Egret.
- **Реальный native:** один blank alpha0; одна полная `fill-only` Egret сцена; один финальный Egret `fill+feedback width1 repair+outline` из current RGBA. Только этот runtime может оценивать реальную кисть. Если нет нативной сцены, статус `BLOCKED` или `MODEL_ONLY`, не fake PASS.
- **Результаты:** save raw full original/reference/owner/edge/mask previews, ordered stroke plan JSON, owner palette hash/source bytes SHA, native fill/final backing PNG, 4-panel visual comparison, missing/white/leakage diagnostics, per-file SHA256 и manifest/report, output ZIP через GitHub Actions, original source git SHA, code SHA, Firefox browser version, engine+renderer blob.
- **Стоп:** ровно один FC1 проход без перебора десятков порогов; если native fails — сохранить технический failure и исправить только прямую причину; если рисунок плох — показать его и назвать крупные визуальные недостатки, не скрывать под safety-gate.
- **Метки:** `RESEARCH_ONLY / SCIENCE_NOT_VALIDATED`, strict S4 `BLOCKED`, formal S5/S6 `NOT_RUN`, game live E4/E5/exact CHALK `NOT_RUN`. Теоретические RGB/FN/FP не заменяют качество. Никакого production/executor/Monitor/Bridge/master.

## Проверки

E1 код-ревью границ input/output и запрещённых imports/read-зависимостей, E2 synthetic regression: fresh source changes derived maps/strokes, no old-index path, bounds/width 1–10, black/white/alpha, deterministic plan, no output overwrite, provenance native checks. E3 CI настоящего Egret на оригинале с blank, raw backing и sha; CI SUCCESS только по выполненным jobs. **Визуальное принятие пользователя — отдельно**, без изменения frozen методики. Если в первом проходе осмысленного рисунка нет, scientific result `FAIL/PARTIAL`, не подгонять критерии после результата.
