# ENGINE-001 / BPRED-S4-R1 / SKC1 — настоящий original Egret E/F source-known контракт, E2

**Дата: 2026-11-21. Измерение завершено. Статус: технический E2 PASS; научная безопасность S4 BLOCKED.** Frozen prospective [SKC1 E0](ENGINE001_BPRED001_S4R1_SKC1_ORIGINAL_EGRET_SOURCE_KNOWN_CONTRACT_PREREG_2026-11-21.md) Git blob `8e58aa5c2f64695e29aa87301c63b47aa5d8f5e4` создан ДО кода/тестов; [S4-R0 E1](ENGINE001_BPRED001_S4R0_SOURCE_KNOWN_READINESS_E1_RESULTS_2026-11-20.md) повторно не запускался. Code + CI commit [877dc76](https://github.com/Kiddos19882/AutoDraw/commit/877dc760259a509a2570e1a4bc70408f879caf1a), [CI #44913972626](https://github.com/Kiddos19882/AutoDraw/actions/runs/44913972626) **SUCCESS**, все обязательные steps включая source-only E/F и upload PASS; [артефакт #14710524600](https://github.com/Kiddos19882/AutoDraw/actions/runs/44913972626/artifacts/14710524600), (ф) `skc1_original_ef_source_contract.json` внутри. Отменённый по concurrency первый CI `44913933185` SHA `2573c838` не является test FAIL; на этом коммите также исправлено только несовпадение полей P4D18/P4D17 до финального CI.

## Подтверждённые источники и процедура

- Исходный [P4D18 native E/F artifact #14557770111](https://github.com/Kiddos19882/AutoDraw/actions/runs/44575816229/artifacts/14557770111) был заново загружен в GitHub Actions runner; SHA256 внешнего ZIP `b0700a6b2d7fcd03aa1af0e741e0e7eb700304b779c32eced67fe43582066079` **совпал** с замороженным; ZIP CRC PASS и все 34 `members_sha256` PASS, исходные original RGB, source-owner index/RGB и нативный P4D18 `report.json` сохранены. Не выполнялась новая браузерная игра и не создавалась новая траектория кисти.
- Повторно использован закреплённый SHA source game engine и существующий `read_engine_palette` P3B: 128 разных RGB свотчей; для обеих карт `source_owner_rgb == game128[source_owner_index]` побайтово. Оригинальное `ORIGINAL_RGB_LOGICAL.png` проверено как RGB **150×240**, каждый метод `SOURCE_OWNER_INDEX.png` L 150×240 и `SOURCE_OWNER_RGB.png` RGB 150×240. Original RGB не приравнивался к palette RGB. Никакого G32/V44 или nearest-Lab provisional owner как trusted-source.
- Existing `generic_source_maps` оставлен неизменным по базовому пути; добавлен research-only (ф) `tests/engine001_bpred_s4r1_generic_source_maps.py::source_known_egret_protection_contract` с документированным source/owner/engine SHA, source white, 4-connected `max RGB channel diff >=32` **только из старого CR1 diagnostic** и прежними Lab/Sobel + alpha + owner-edges. Это НЕ новый perceptual/native gate.
- (ф) `tests/test_engine001_bpred_s4r1_generic_source_maps.py` — **43/43 E2 PASS**, 7 новых SKC1 синтетических и 36 ранее существовавших tests, включая fail-closed плохие owner/RGB, палитру/протокол, source/hash, alpha и white. Существующий DEV/KNOWN source-corpus job завершился SUCCESS, locked heldout8 не открывались для карт. Markdown audit PASS (в логе сохранено прежнее предупреждение по исторической ссылке, не новый FAIL).

## Реальные source-only измерения по архивным E/F

Обе карты имеют **36 000 логических клеток**, режим без alpha-прозрачности; число защищённых и UNKNOWN — разбиение, **не** изображённое качество и **не** прогноз рисования.

| Показатель | E_SOBEL90 | F_SOBEL90_LAB12 |
|---|---:|---:|
| Original owner 4-neighbor edge pixels | 14 813 | 14 805 |
| Original RGB strong-contrast CR1 endpoints | 11 739 | 11 739 |
| Existing original Lab/Sobel edges | 9 219 | 9 219 |
| Original exact-white pixels | 11 163 | 11 163 |
| Explicit source-owner white pixels | 22 132 | 22 137 |
| Protected union | **34 081** | **34 079** |
| UNKNOWN complement | **1 919** | **1 921** |
| Geometric candidate interior (весь UNKNOWN) | **1 919** | **1 921** |
| Stroke admission | **FORBIDDEN** | **FORBIDDEN** |

Protected занимает **94,67%** / **94,66%** исходного логического поля; UNKNOWN/геометрический interior **5,33%** / **5,34%**. Эти числа НЕ оценка покрытия рисунка: защитные категории пересекаются, а подавляющая часть protected — в том числе исходный белый фон и края; нельзя суммировать строки. Абсолютно **0** исходно разрешённых штрихов — преднамеренное сохранение fail-closed, не полезный stencil для production.

## Предел результата и зафиксированные отрицательные evidence

**PASS E2:** реальные E/F архивные данные, owner→palette binding, исходные RGB/owner/white/alpha карты, 7 новых synthetic fail-closed тестов, полная сверка архивных hashes и документации. **PARTIAL/BLOCKED scientific:** нет независимо подтверждённой полноты важных семантических деталей; owner-index — лишь известная метка source E/F, не native безопасный `owner` всех современных изображений; 1 919/1 921 потенциальных внутренних ячеек всё ещё `UNKNOWN`, usefulness/false-safe/native footprints не измерены. Прежние нативные защищённые исходно-белые E2250/F2261, alpha0 holes E24/F25 **FAIL** остаются, их не маскирует source E2. `strict S4=BLOCKED`; S0 BLIND120/H8/second50 не открывались, S5/S6/new E3/E4/E5/exact CHALK NOT_RUN; no production/master/Stage6/Monitor/Bridge/CHALK estimator modifications. VIS1 пользователь визуально предварительно одобрил, **не** конечное игровое качество.

**Решение/STOP:** SKC1 research source binding зафиксирован как технически готовый, без promotion в planner/executor и без дальнейших процентов/пороговых sweeps. **Следующий один шаг по прежнему S0→S6 плану:** отдельно оценить наличие независимого owner/critical/white native E3 eligibility и заморозить prospective E0 для одного ограниченного **настоящего оригинального Egret** visual/owner/white/contour теста, только если исходная семантическая безопасность подтверждаема; иначе явно `BLOCKED` и устранить source-owner/critical evidence gap без переизобретения источника карт. Никакого автоматического S4 PASS, S5/S6 и live CHALK до настоящих gates.
