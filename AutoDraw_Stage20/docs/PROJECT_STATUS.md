# AutoDraw — текущее состояние

**Дата сверки:** 2026-11-08. **Ветка:** `feature/image-geometry-optimization`. **Исходный HEAD проверки:** `a2d1f0a52d47`. **Последний проверенный code SHA:** `5a55e9f45b34`.

**Основной [CI 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) — SUCCESS**, [81-image screening 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) — SUCCESS, оба на `5a55e9f`. Проверка GitHub не равна локальному `git status`, Windows runtime или реальному игровому запуску.

> Полная прежняя редакция, включая все исторические факты, промежуточные статусы и ссылки: [PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md](PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md). Снимок сохранён без изменения исходных байтов.

## Работоспособность подсистем и доказательства

| Направление | Подтверждено | Не закрыто |
|---|---|---|
| AutoDraw 1.8.3 | Integrated UI, preparation, Stage6 executor; regression/CI | Новое live качество на произвольных рисунках не проверено |
| Game Monitor / Bridge | Привязка run/session, exact `pointCount`, per-stroke telemetry в экспериментальных сериях; [API](GAME_MONITOR_BRIDGE_REFERENCE.md) | Нет доступа к текущему runtime пользователя |
| G1/G2/G3 + radius matrix | Live 12/12 + 18/18 + 27/27 + 21/21; подтверждён эффект sampling в заданных условиях | Не универсальный прогноз CHALK |
| INT-006 | [D1–D5 45/45, quantitative PASS](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md); P1 — лучший исследованный профиль | `safety_margin_status=not_established`; `production_eligibility=not_validated` |
| INT006R | [45 exact captures](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md) и [визуальный аудит](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md) | Radius 1: разрыв D2; radius 30: слияние деталей D4; перенос на fills не подтверждён |
| PRR renderer | [6/6 PASS_PER_RUN, aggregate PASS](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) | Не универсальная pixel-equivalence каждого будущего рисунка |
| FILL-001-RS | [Exact CHALK 1260 на 27 штрихах](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md), runtime binding PASS | **PNG FAIL**: coverage=98.430600% при ≥99%, leakage=11px при 0 |
| Корпус 81 изображения | 31+50 unique SHA, 81 моно+цветных планов; [screening E3](TEST_RESULTS.md) | Similarity review не доказывает semantic independence; scanline ≠ frozen D1–D5 domain |
| INT-007 | Требования к estimator документированы | **BLOCKED:** safety margin/domain/quality gates не закрыты |

## Непреложные факты

- Точный игровой **CHALK = post.pointCount − pre.pointCount**, при валидной привязке run. Длина пути, площадь и N штрихов не заменяют этого измерения.
- На исправленных V1–V5 переход `point_step_px=2→4` уменьшал расход на 38.5–49.4% **только в исследованных сценариях**; [источник](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md).
- 81 цветной scanline-план: 942206 исходных штрихов, 395455 одиночных пикселей и 916312 переключений между цветами. Это offline counters, **не** CHALK/runtime time.
- Имеющиеся измерения CHALK повторно собирать с нуля не требуется. Необходимы отдельные доменные и quality gates, если планируется новый универсализированный вывод.

## Ближайший приоритет

Поддерживать [действующие задачи](TASKS.md) и [очерёдность](ROADMAP.md); сначала сохранить целостность документации, затем оценивать алгоритмы на одинаковых рисунках и разбирать FILL-001 perimeter mismatch. 95% protocol — отдельная цель, не препятствие для начала офлайн-сравнения.

**Источники:** [TEST_RESULTS](TEST_RESULTS.md) · [DECISIONS](DECISIONS.md) · [первичная история](PROJECT_STATUS_HISTORY_THROUGH_2026-11-08.md).
