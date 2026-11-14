# ENGINE001_COMPLEX_STRUCTURE_V6 — предварительно зарегистрированный эксперимент

**ID:** `ENGINE001_COMPLEX_STRUCTURE_V6`. **Задача:** `ENGINE-001 / next complex-art architecture research`. **Статус:** PREREGISTERED / результаты NOT_RUN. **Дата:** 2026-11-14. **Область:** только исследовательские исходники и CI; production, executor, Monitor, Bridge, frozen V3/V4/V5 и `master` неизменны.

## Причина

V5 на исходном многоцветном изображении даёт 35.055% coverage (V3/V5), 36.760% (V4), все offline color gates FAIL; [CI 43600695050](https://github.com/Kiddos19882/AutoDraw/actions/runs/43600695050). Пользователь просмотрел полученный рисунок и сообщил: **без знания исходного изображения невозможно понять, что нарисовано**. Это пользовательский визуальный FAIL, но не независимый слепой тест и не новый live E4.

## Вопрос, гипотеза, ограничения

Вопрос: насколько ранняя глобальная квантовка и деление на независимые цветовые маски теряют линии и связность **до** генерации штрихов? Гипотеза H1: существенная часть исходных сильных границ / тонких деталей не представлена в границах V5 восьмиклассовой палитры; H0: различие несущественно, и основной источник потерь — планировщик. Проверять обе альтернативы, отрицательные результаты сохранять.

Вход только закреплённый файл (ф) `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, Git blob `d3cd95b846f036a3f8acecf75d2a237e46dcf13a`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, 200×320 RGB / 97308 bytes. Контроль: без изменений использовать `source_palette()` V5 и фактическую V5 геометрию `contain`, 460×240, 150×240 при x=155, и восемь MEDIANCUT классов. Этим файлом **нельзя** подтверждать независимую generalization, он уже seen. Второй held-out образец необходим до acceptance.

**Пререгистрированные переменные и методы:** исходный и палитровый RGB при одном logical scale, независимо извлечённые Canny edges (grayscale Gaussian sigma реализован `cv2.GaussianBlur(3×3, 0)`, thresholds 60/120, L2gradient=True) для исходного и палитрового изображения; 1 logical px допуск при сопоставлении через dilation 3×3 (без подгонки). ROI ограничена 150×240, без белого canvas. Отдельно считаем число и долю исходных edge pixels, поддержанных палитровыми edge pixels в пределах 1px; число edge-components >=12 px исходно и долю сохранённых компонент (>=50% пикселей в 1px окрестности palette edges); количество компонент, целиком потерянных. Считаем компоненты Canny через 8-connectivity. **Это E1/E2 диагностические proxy, не доказательство узнаваемости и не game quality.**

**Два статических диагностика** для выбора направления после результатов: (A) повторить точную V5 source palette и сравнить palette edge retention; (B) сохранить отдельную исходную границу как слой для последующего контура, не утверждая, что она уже drawable, безопасна по цвету или экономична по CHALK. Диагностика B — материал для будущего пути V6, **не** готовый production planner. Не менять цветовую палитру/threshold после просмотра outcome в рамках этого ID.

## Протокол и контроль

1. Проверить зафиксированный Git blob и исходный SHA; fail closed при неверном source.
2. Вызвать существующую V5 `source_palette()`, не копировать второй декодер изображения.
3. В фиксированной ROI вычислить два edge masks, метрики и 8-connected components; сохранить исходные intermediate PNG, masks, статистику и SHA256 всех derived artifacts.
4. Выполнить unit tests на blank/line/broken-line/zero-denominator/shape mismatch и прогнать через CI на branch SHA.
5. Оценка результатов: `DIAGNOSTIC_COMPLETE` только если source/hash/ROI, два edge masks, component summary и тесты проверены; иначе FAIL/BLOCKED. **Никакого численного порога узнаваемости не объявлено.** Численный edge recall не равен recognition PASS; пользовательское наблюдение сохраняется в статусе FAIL V5.
6. Сохранить raw V5/HOLDOUT outcomes без изменений, не подменять renderer quality/CHALK. Имеющиеся 99% coverage и симметричные 3 logical px не меняются.

**Ожидаемые outputs:** JSON с GitHub checkout SHA (или null локально), NumPy/OpenCV/Pillow version, source SHA/status, исходный crop и реконструированный palette crop, два binary edge PNG и `missing-v5-edges.png`, component stats. Все файлы derived, не исходные captures. GitHub workflow с явным checkout SHA, unit tests и artifacts. Вся статистика exploratory-only, интерпретация E3 не выше native/render pipeline и не выше E4.

## Следующий gate

По диагностике выбрать **один** минимальный experimental structure-aware path (сохранение связных линий и тонких цветовых областей), prereg нового ID до native результатов. Для признания практического улучшения обязательны native Egret итоговый рисунок и слепая визуальная оценка (без показа оригинала) на **новом** изображении, плюс per-color coverage/overpaint. Только затем E4 exact game CHALK и независимая E5. Нельзя выдавать улучшение edge recall за узнаваемое изображение.

## Дополнение к представлению артефактов — 2026-11-14

До доступных V6 measured outcomes добавлен исключительно **диагностический слой отображения**: `edge-retention-overlay.png` (RGB 150×240 ROI), с зелёными source-edge pixels, имеющими palette edge в пределах фиксированного 1 px, и красными source-edge pixels без соответствия. Основа — осветлённый исходный crop. Сохраняется SHA256 и проверяется форма/режим. Ни Canny параметры, ни edge matching, ни connected-component критерии, ни расчёт метрик не изменены. Visual overlay — средство интерпретации, **не** human recognition score и не new threshold. Исходное изображение визуально изучено непосредственно по закреплённому Git blob, но V6 на нём здесь не запускался.
