# ENGINE-001 — корневая диагностика белых прорех P4D13 через Canvas2D и истинные пиксели

**Дата:** 2026-11-19. **Статус:** post-hoc **E1/E2 диагностический анализ** неизменяемых настоящих E3 PNG, а **НЕ** новая prereg P4D17 и не E4. Пользователь скорректировал задачу: выяснить **причину белых прорех**, а не максимизировать коэффициент совпадения математической маски кисти. Опорный оригинал: [P4D13 E3 CI44536042475](https://github.com/Kiddos19882/AutoDraw/actions/runs/44536042475) SHA `1f8b4dd13a0d74896643e6fc82c9a56d9ef65574`, frozen original wV6VeZI9S1Y PNG SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Все 39 raw archive files проверены SHA256 и CRC. Frozen Stage01-03 E/F и полный список stroke endpoints/widths/colorIndices использованы без модификации.

## Основной установленный механизм: геометрия + слишком слабый residual gate

`P4D13.full_source_state` считает source nonwhite logical клетку «докрашенной», когда **≥5/9** физических backing пикселей `alpha≥24` и RGB каждого близок к целевому (max-channel `≤32` после source-over-white). `residual_owner_runs` создаёт последующие `width1` штрихи **только** для logical клеток, не прошедших этот gate, а не для всех недокрашенных физ. подпикселей. Поэтому даже source interior physical alpha0 дырка перестаёт быть причиной исправления, если соседние 5 подпикселей уже корректны.

Из замороженных full native alpha 3× и source-owner index RGB:
- В source nonwhite interior (distance≥2 logical from source-white по той же маске P4D16) у E alpha0 physical **2444→95→95→95**, у F **2397→96→96→96** от initial Stage00 через три repair stages. Ни у одного из конечных alpha0 pixels alpha не появлялась в предыдущем проходе; фактическая alpha на всех пикселях монотонна для всех трёх переходов.
- 95 E zero-alpha physical holes принадлежат **89** logical source цветным клеткам, 96 F — **90** клеткам; **все 89/90** конечных logical клеток имеют `≥5/9` правильного цвета, поэтому остаточный planner **не запрашивает** их повторное покрытие.
- Для каждого из 95/96 нулевых физических пикселей был вычислен минимальный `signed_distance = distance(pixel_center, finite segment) - width/2` ко **всем 6228/6254 настоящим stroke segments** полного плана с round caps; применён source-derived Egret `δ=(+0.5,+0.5)` для widths1/3 и0 для прочих, масштабы logical→backing3×/board offset X0=155. **Ни один physical pixel center не находится внутри идеальной капсулы какого-либо штриха:** min signed distance **+0.166667 logical**, max +0.358981 logical (расстояния до ближайшего штриха). Следовательно, отсутствие альфы согласуется с геометрическими промежутками; **не требуется предполагать случайную ошибку/пропуск Canvas2D**. Ограничение: модель идеального капсула НЕ доказывает byte-perfect fractional pixel coverage Canvas; квадрат пикселя может касаться геометрии даже если центр снаружи.
- Реальный renderer P4D15 source Canvas→WebGL дал [30/30 идентичные crop RGBA](https://github.com/Kiddos19882/AutoDraw/actions/runs/44560216224), т.е. в этих фиксированных случаях дополнительный WebGL transfer не создаёт прорех. Egret [CanvasRenderer.ts](https://github.com/egret-labs/egret-core/blob/5913071f8e7c35ae223d44b1f681f814333bfcc3/src/egret/player/rendering/CanvasRenderer.ts) делает Canvas `stroke()`; [HTML Canvas spec](https://html.spec.whatwg.org/multipage/canvas.html#drawing-paths-to-the-canvas) определяет геометрию штриха, не универсальное бинарное покрытие ячеек. За пределами экспериментального Firefox backend обобщений нет.

## Второй большой источник визуальных дефектов: цвет уже есть, но он неправильный

Подсчёт по всем **небелым исходным** backing pixels source crop:
| Метрика final true Egret | E | F |
|---|---:|---:|
| source nonwhite physical backing | 124812 | 124767 |
| `alpha=0` — полная прозрачность | 122 | 122 |
| `alpha=1..23` — недостаточная видимая альфа | 155 | 163 |
| `alpha≥24` **но RGB не совпадает с owner допуском32** | **14103** | **14303** |
| Из неправильных RGB при `alpha=255` | 2526 | 2589 |
| Всего неправильных/непокрытых source-owner физических pixels | **14380** | **14588** |
| Original-white erroneously painted physical `alpha≥24` | 4415 | 4445 |

Это раздельная **наблюдаемая** диагностика: `alpha≥24/RGB wrong` **не** равно доказательству перерисовки именно чужим цветом — может быть AA, частичная альфа на белом фоне или перекрытие; `alpha=255/RGB wrong` исключает простую белую прозрачность, но не идентифицирует конкретный чужой штрих. Следующий эксперимент должен сохранить per-color render / order attribution, а не объявлять 14103/14303 перерисованными без run-bound цвета.

P4D16 [E3 CI44568765466](https://github.com/Kiddos19882/AutoDraw/actions/runs/44568765466) показал хорошее среднее IoU~98.85% у модели area8, но лишь9/150 exact alpha24 masks и **не изменил** P4D13 изображения: эта работа не ответила на вопрос отсутствующего физического покрытия. Впоследствии проведён настоящий post-hoc **per-pixel cause** выше.

## Минимальный следующий шаг

**Не увеличивать бездумно число проходов и не ослаблять protected gates.** На том же pinned P4D13 исходном плане разделить для каждой физической неуспешной позиции:
1. Вообще геометрически не достигалась ни одним owner-stroke → нужно source-owner-aware physical residual 7/9–9/9 с native replay, а не logical5/9.
2. Геометрически достигалась своим цветом, но оказалась неправильной → исследовать настоящий Canvas alpha и последовательность штрихов/замещение чужим owner per-color native attribution.
3. У исходно белого source появилась краска → отдельно строгая protected-white/foreign gate, preserve previously failed evidence. Не исправлять (1) ценой (3).

После отдельного **нового E0** на полный original E/F и закреплённые thresholds проверить в Egret real native **physical** owner density + protected original-white spill, real visual crop; лишь затем E4 live/E5 и точный run-bound CHALK. Frozen P4D13 owner 5/9 achievement сохранён, protected quality FAIL не переименовывать в PASS. Production/Stage6/Game Monitor/Bridge/master/CHALK estimator не менялись. Локальная аналитика и визуальные overlay masks переданы пользователю отдельно архивом.
