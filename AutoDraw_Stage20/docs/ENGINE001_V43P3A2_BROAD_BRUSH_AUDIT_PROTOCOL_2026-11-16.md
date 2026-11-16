# ENGINE-001 / V43-P3a2 — source-only аудит размеров 4, 6, 10, 20, 30

**Дата:** 2026-11-16. **Статус:** PREREGISTERED, E2 NOT_RUN. **ID:** ENGINE001_V43P3A2_BROAD_BRUSH_SOURCE_AUDIT. Продолжение V43-P3, **не замена** уже замороженного V43-P3a (4/6).

## Гипотеза
Крупные source-color компоненты могут допускать ориентированные проходы с более широкой кистью, вплоть до 30 logical Egret lineStyle units; нужно проверить геометрическую возможность для размеров **4/6/10/20/30**, прежде чем пытаться реальную native-замену узких заливок. 30 — верхняя исследуемая ширина, не подтверждённый max GUI/production, не радиус и не равен диаметру фактического растрового следа.

## Неизменная основа
Image `testImages/wV6VeZI9S1Y.png` SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; ROI150x240 logical x155..304, class7 largest connected component area5005. Реиспользовать существующую функцию `oriented_source_candidates` из P3a и `largest_dark_component`; не переносить новую отдельную геометрическую реализацию. Все 1945 исходных paint strokes и 410 цветных V44-B контуров frozen, на P3a2 они вообще не рисуются и не удаляются.

## Пререгистрированный режим
Исследовать ширины **4,6,10,20,30**, фиксированное продольное дискретизирование 1 logical px, перпендикулярный шаг=width, минимальная длина 8 logical px, source-distance от границы >=width/2 +1 px. Не адаптировать шаг/порог по полученным результатам. Каждая линия вдоль главной PCA оси крупнейшей компоненты class7. Журналировать число линий, длину, sample center count, owner class, source-mask SHA, alpha unknown. Candidate с нулём линий — честный `NO_ELIGIBLE_PATHS`, не FAIL теста и не автоматическое уменьшение ширины. `safe_to_execute=False` у всех.

## Verification
P3a source geometry unit/regression tests, настоящий P3a2 CI E2 MODEL_ONLY. Никакие круглые/прямоугольные proxy footprints не дают native coverage PASS. Для настоящей кисти шириной 10/20/30 нужны отдельные Egret alpha24/128 footprint tests с поворотом, изгибом, краем и переходом цвета до использования в P3b. Порог внешнего/внутреннего crossing <=3 logical px и source per-class>=99% unchanged. Real CHALK строго `post.pointCount-pre.pointCount` при валидном run-bound E4. Следующий P3b — только после результатов P3a/P3a2 и явной замены исходных 2px проходов вместо наложения поверх них. Production не изменять.

## Follow-up evidence integration — 2026-11-16

Existing [ENGINE-001 V31 real Egret footprint experiment CI43693170456](https://github.com/Kiddos19882/AutoDraw/actions/runs/43693170456) already captured 30 genuine native WebGL BoardPane brush cases: widths1/3/10/20/30 × six trajectories (dot, horizontal, diagonal, elbow, polyline, ROI edge); V31 E3 SUCCESS for reference capture. For widths **10,20,30**, native alpha128 occupied source logical pixels outside the ideal swept capsule in **6/6 cases per width**; WebGL and CanvasRenderer differed in **30/30 cases**. This proves distance-transform/capsule/rectangle logic is **not a conservative native-ink safety certification**, and brush width30 must never be approved for complex color boundaries just from source-centerline distance. V31 was isolated reference strokes, not actual P3 paint candidate paths.

Added non-gating, high-resolution 0.25-logical-unit **source-centerline-only diagnostic** to independent P3a2 report (commit `2274e528921f141a2790b15ff6711913a6f7f39d`) and unit tests (commit `3b8c048e708038463bf119d93d5674f847266008`). This samples candidate centerlines between P3a route endpoints, reports source owner and distance-margin violations, and retains all candidate paths without posthoc filtering. Its label `SOURCE_CENTERLINE_ONLY_NOT_EGRET_FOOTPRINT` is mandatory: even 0 violations **cannot** imply actual native brush safe-to-execute. Original P3a width4/6 route counts, geometry, order and frozen protocol are unchanged; P3a2 CI checks this explicitly (commit `7265ea09691f2cc2d71362fab5bc817626e6214d`). No E2/P3a2 CI result confirmed yet via connector; no P3b, E4/CHALK, production changes.
