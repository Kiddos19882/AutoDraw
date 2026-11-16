# ENGINE-001 / V43-P3 — ориентированная многоразмерная заливка, неизменная обводка V44-B

**Дата пререгистрации:** 2026-11-16. **Статус:** P3a PREREGISTERED / NOT_RUN; P3b не выполнялся. **Задача:** существующая ENGINE-001 / V43-P3; отдельный ID проверки `ENGINE001_V43P3_ORIENTED_REPLACEMENT`. Branch `feature/image-geometry-optimization`. Никаких изменений production, Stage6, Monitor, Bridge, master, frozen captures.

## Цель и причина изменения методики

Пользователь требует максимальную полезную ширину круглой кисти **в зависимости от места** и произвольное направление, контур отдельно последним. Непосредственный native baseline для дальнейших работ — **V44-B выбранный пользователем**, [CI43813812976](https://github.com/Kiddos19882/AutoDraw/actions/runs/43813812976), artifact14201581692 SHA256 `43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1`. Цветная обводка 410 оригинальных V35-B траекторий, source-median RGB V44-B; рисовать последней. Исходная заливка V37-P2-C: 1945 width2, всего 2355 stroke/5682 synthetic vertices NOT CHALK. Full RGB MAE V44-B=11.13399074, warm16.42272007.

V43-P2a no-op и P2b [CI43778700514](https://github.com/Kiddos19882/AutoDraw/actions/runs/43778700514) доказали: дополнительные широкие сегменты поверх горизонтальных не улучшают уже закрашенные пиксели. P3 ставит задачу **удалять заменённые узкие проходы**, а не только добавлять новые. Исторические отрицательные результаты неизменны.

## P3a: source-only направленные кандидаты, E1/E2 MODEL_ONLY

Повторно использовать `run_engine001_shape_adaptive_fill_v43p1.analyze_component`, `run_engine001_native_wide_interior_v43p2a.largest_dark_component`, `original_labels`, `cv2.distanceTransform`, `skeletonization`. Не реализовывать второй renderer или production brush planner.

Варианты пробного исследования: главная связная область класса7 (area5005, largest source blob), ориентация по PCA, для неё фиксированные размеры native Egret 4 и 6 **как гипотеза**, не подтверждённая гарантия. Истинное право применения определяется только PNG native Egret. Для вычисления кандидата: координаты в logical ROI460×240, x=155..304, исходная метка не меняется; выбрать главное направление PCA детерминированно, проецировать маску на него; построить параллельные линии с шагом выбранной ширины и оставить только центральные последовательности длиной>=8 logical px, где все дискретные точки имеют owner7 и Euclidean boundary distance>=width/2+1. Источник для выбора — только исходная маска, не результат B/C native рендера. На P3a выводить JSON-кандидаты с `safe_to_execute:false`, source SHA, bbox/component и ID, ориентацией и списком геометрий; **не удалять** исходные штрихи и не заявлять экономии/покрытия.

## P3b: отдельно замороженная замена + native Egret (только после P3a)

A — V44-B baseline pixel-exact. B — width4 oriented interior replacing source-owned redundant width2 lines. C — width6 interior + width2/тонкие линии вдоль skeleton/границ и исправление фактических native alpha gaps. До создания B/C определить точное правило для **удаления** исходных width2 paths (по покрытию всем native sweep footprint, а не по прямоугольнику), порядок, допуски, хеши и критерии. Нельзя переиспользовать dark V35-B RGB в A или смешивать цвет как новую переменную. Сохранить ID/точки/цвет RGB всех 410 исходных контуров V44-B, их порядок последним слоем. Нет поддержки изменения ширины внутри штриха без отдельного E3 доказательства. Если безопасная замена не получается, результат `NO_REPLACEMENT` и сохранение baseline, а не подмена наложением новых мазков.

## Frozen validation gates

- Native Egret BoardPane WebGL в существующем `native_batch`, alpha24/128 **по каждому цвету**, original source full/warm RGB MAE и зрительная оценка лица, волос, рук, одежды, пользовательский эталон V44-B.
- Покрытие каждого необходимого цветового класса >=99% — production gate, не менять; допуск наложения на соседний цвет <=3 logical px и выход за внешнюю границу <=3 logical px, не изменять.
- Native эксперимент capped <=3000 paths / <=5900 synthetic accepted vertices, отдельно считать количество путей, цветовые переключения, длину и геометрию; synthetic vertices **NOT** exact CHALK. Экономия должна быть подтверждена реально удалёнными штрихами.
- Fail-closed при неизвестной калибровке, owner leak, неидентичных исходных source RGB/outline, отсутствии pinned archive SHA, неполном рендере/отчёте. Все A/B/C raw PNG/JSON/hash сохранять, провалы тоже.
- E4 run-bound `CHALK=post.pointCount-pre.pointCount` и независимая validation E5 отсутствуют до отдельной проверки. CI E3 не заменяет E4.

**Следующий невыполненный шаг:** P3a deterministic source geometry unit tests и provenance; затем точная пререгистрация правила удаления линий для P3b. Никакой posthoc подгонки после просмотра B/C.
