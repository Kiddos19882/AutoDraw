# ENGINE-001 / V44-P1 — адаптивный RGB контуров с защитой локального контраста

**Дата:** 2026-11-16. **Статус:** PREREGISTERED / NOT_RUN. **Scope:** отдельный эксперимент, без изменения production, Stage6, executor, Monitor, Bridge или master.

## Основание
Пользователь запросил цветоадаптивную обводку и разрешил разработку/тестирование. V35-B является выбранной пользователем геометрией (410 тёмных линий). Native V37-P1 [CI43745869245](https://github.com/Kiddos19882/AutoDraw/actions/runs/43745869245): источник RGB на всех линиях уменьшил full RGB MAE 20.2112→11.9760, но линии лица/волос теряли контраст; 50% tint дал MAE14.8606. V37-P2-C — текущий контроль заливки.

## Гипотеза и ограничения
По исходной ROI 150×240 определить локальный цвет линии и два фона по нормали к траектории; выбирать оттенок исходного контура, при необходимости затемняя до фиксированного локального минимального contrast ratio. Для ближайших точек исходника разрешено измерять RGB, **но не footprint** — он проверяется исключительно native BoardPane/Egret. Не подбирать параметры после результата.

Фиксированные варианты для будущего native A/B/C:
- **A**: замороженный V37-P2-C, все 410 RGB [49,38,43].
- **B**: все 410 RGB из исходника, lower per-channel median (как V37-P1-B).
- **C**: тот же исходный RGB с порогом контраста 2.5:1 относительно двух локальных сторон, затемнение интерполяцией к [49,38,43], если не достигается — сохранить исходный V35-B тёмный контур и отметить unresolved.
Параметры: offset 2 логических px; точки для фоновых проб через нормаль к касательной; на границе ROI использовать только валидные координаты. Детали с недостоверной касательной/меньше двух валидных фоновых отсчётов сохраняют V35-B RGB. Не разделять существующий штрих на дополнительные цветовые сегменты в P1.

## Gates
A/B/C: неизменные ID, точки, ширина, порядок, 1945 заливок + 410 контуров, всего 2355 штрихов/5682 синтетические вершины **NOT CHALK**. В native проверить pixel-exact A против архивного V37-P2-C, alpha всех isolated/composite, границы цветов и внешнего силуэта ≤3 логических px, per-source-class ≥99% (не смягчать), full/warm MAE относительно A, читаемость лица/волос/кистей рук, переключения RGB, unresolved contours. Положительная RGB-диагностика без визуальной не означает production PASS. Новый actual CHALK только при run-bound E4. Отдельная независимая E5 требуется для production.

## Шаги
P1: изолированный pure color adapter + unit tests; E1/E2 без заявлений о native качестве. P2: при подтверждённом P1 использовать существующий Egret native_batch и baseline archive через отдельный prereg CI, сохранять raw PNG/report/hash. В случае невозможности сборки или CI честно выставить BLOCKED/NOT_RUN.

## Implementation audit — 2026-11-16

V44 P1 code created on branch `feature/image-geometry-optimization`: `tests/engine001_adaptive_color_outline_v44.py` (pure color proposal), `tests/test_engine001_adaptive_color_outline_v44.py` (guards), `tests/run_engine001_adaptive_color_outline_native_v44.py` (native A/B/C), `.github/workflows/engine001-adaptive-color-outline-native-v44.yml` (push/opt-in Windows runner). Corrective commit `cf5a819ee3e6604fd2d6cff47e120b748fe3a309` validates **all** report-linked SHA-256s in the immutable V37-P2 native archive before rendering and rejects bad baseline identity; commit `517ed1ede10e86eb85fd5c42cb24149fefa8aee2` adds tamper/count regression fixture. No changed acceptance rule. CI status not confirmed by connector, E2/E3 UNKNOWN; E4/E5/real game CHALK NOT_RUN. Main method limitations: source-background color is not actual painted Egret RGB; path-level RGB can hide detail when the line spans multiple color regions. Do not infer visual acceptance from computed contrast. Native comparison and face/hair/hand review remain required.
