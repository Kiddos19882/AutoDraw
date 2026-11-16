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
