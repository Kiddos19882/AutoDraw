# ENGINE-001 / BPRED-S4-R1 / NG2 — фактический original Egret E/F width1/3 native risk

**2026-11-21. Эксперимент завершён. Технический true Egret E3 PASS; строгий S4 — BLOCKED.** Frozen [NG2 prospective E0](ENGINE001_BPRED001_S4R1_NG2_ORIGINAL_EF_NATIVE_SINGLE_STROKE_RISK_PREREG_2026-11-21.md) Git blob `c9a5af70223c5eccbadb36e659c98d4ebdf2d186` создан ДО реализации и native выходов. Signed technical run: [CI44916234316](https://github.com/Kiddos19882/AutoDraw/actions/runs/44916234316) **SUCCESS** на точном код SHA `9cefbb66ca7a28047a3133db11077281adfac666`, 5/5 synthetic E2 PASS, настоящий исходный Windows Firefox159/BoardPane Egret 5.4.1 E3, 20 исходных отдельных одиночных штрихов +1 blank; source original game/renderer E0 pinned, архив P4D18 outer SHA/CRC/34 member SHA PASS; [raw NG2 artifact14712410260](https://github.com/Kiddos19882/AutoDraw/actions/runs/44916234316/artifacts/14712410260), GitHub размер 14 372 bytes, provider digest `cc7290fea99fd428a02d9d06f505eb2c95b3ecfac6ebbf2d8a228420550edbeb`. Отдельная независимая загрузка/outer ZIP CRC после CI **NOT_RUN**; сам CI проверил file SHA и 21 native scene/metadata.

## Неподвижные входы и методы

- Исходный P4D18 original E/F archive14557770111 SHA256 `b0700a6b2d7fcd03aa1af0e741e0e7eb700304b779c32eced67fe43582066079`, `ORIGINAL_RGB_LOGICAL.png` RGB150×240, `SOURCE_OWNER_INDEX.png` (L), `SOURCE_OWNER_RGB.png` RGB150×240 для E/F, game128 blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`; координаты source x155..304 logical в Egret, factor3 backing (RGBA720×1380). `source_known_egret_protection_contract` SKC1 неизменён, geometric UNKNOWN 1,919/1,921, `stroke_admission=FORBIDDEN`.
- Для E и F только 5 заранее указанных row-major квантильных исходных UNKNOWN-точек, ширины **1/3**, `x-0.025→x+0.025`, y целое, в одном штрихе на новом native blank; 2×5×2 = **20** настоящих независимых native сцен +1 blank. Никакого автоматического выбора новых пикселей по результату, перемещения ROI, нового обучения, полного изображения или повторного P4D18.
- Reuse (ф) `tests/run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native.py::_stroke`, (ф) `tests/run_engine001_b1r_p4d13_full_original_relaxed_finish.py::render`, (ф) `tests/run_engine001_b1r_p4b7_native_stroke_attribution.py::native_egret_session`. Исходная точка имеет owner из frozen source E/F; raw pixel actual RGBA и native alpha>=24 archived diagnostic gate, исходный owner-индекс и protected/Sobel+RGB strong контур для атрибуции. Это **настоящая Egret**, не OpenCV footprint. Existing production/executor/Monitor/Bridge/CHALK unchanged.

## Реальные измерения: пересечения физических пикселей, не живой game CHALK

В каждом native-run 1 width1 stroke оставил **9**, width3 — **73** original backing-пикселя alpha>=24; total 10×9+10×73=**820** ink *occurrences across independent scenes* (не 820 различных пикселей единого рисунка). В 10 сценах width1 все 90 occurrences принадлежали целевому исходному owner и ни разу не пересекали protected. В 10 сценах width3 все 730 occurrences принадлежали целевому owner; protected пересечения **310**.

| Показатель (sum of independent scenes) | E width1 ×5 | E width3 ×5 | F width1 ×5 | F width3 ×5 |
|---|---:|---:|---:|---:|
| Actual physical ink alpha>=24 | 45 | 365 | 45 | 365 |
| Owner совпадает с целью | 45 | 365 | 45 | 365 |
| Чужой nonwhite owner | **0** | **0** | **0** | **0** |
| Original-white source owner | **0** | **0** | **0** | **0** |
| Out-of-source physical crop | **0** | **0** | **0** | **0** |
| **SKC1 protected source intersection** | **0** | **142** | **0** | **168** |
| Original strong RGB contour intersection | 0 | 29 | 0 | 30 |

Ширина3 пересекла protected на **9 из 10** отдельных пробных сцен (E 4/5, F 5/5); ширина1 — 0/10. `protected=310` **не равно 310 испорченным RGB пикселям или foreign-owner harm**: эти пересечения оказались внутри **того же source owner**; важно не терять исходные важные контуры и учитывать будущие перекрытия чужих цветов/композитное накопление. `rgb_contour=59` — подмножество/пересечение с защитой, эти числа **не суммировать** с protected как независимую потерю. Метод не исследовал смешивание нескольких цветных слоёв и полную визуальную читаемость; успешный width1 в этой малой sample **не становится общим допуском** для всех width1/stroke/angles/images.

## Проверки, технические отрицательные результаты и протокол остановки

- [NG2 run44916234316](https://github.com/Kiddos19882/AutoDraw/actions/runs/44916234316) SHA `9cefbb66ca7a28047a3133db11077281adfac666`: E0 frozen Git blob/game/renderer hash PASS, 5 new E2 synthetic tests PASS, Markdown audit PASS (старое предупреждение по исторической ссылке сохранено, не новый FAIL), Node JS syntax PASS, P4D18 zip SHA/CRC/members PASS, Firefox159 native renderer 21 raw scenes with hashes, full report/run SHA binding, E3 **technical PASS**. Existing H8/BLIND120/second50 untouched, S5/S6/game E4/E5/exact CHALK NOT_RUN.
- Первая попытка [CI44915891972](https://github.com/Kiddos19882/AutoDraw/actions/runs/44915891972) SHA `d67f59f` **technical FAIL до реального Egret**: Windows worktree CRLF менял локальный E0 byte-hash, без изменения frozen Git-object; минимальное исправление Git `show HEAD:path` SHA `6d8513a`. Вторая попытка [CI44916071942](https://github.com/Kiddos19882/AutoDraw/actions/runs/44916071942) SHA `6d8513a` **technical FAIL до реального Egret**: ошибочное H×W ожидание квантилей synthetic test `(20,10)` (только ожидаемые y/x), исправлено одним test literal в `9cefbb6`. Оба неуспеха **сохраняются**, frozen E0, пять source positions rule, widths и source SHA никогда не переписывались по результату.
- **Scientific risk verdict:** `PARTIAL / OBSERVED_PROTECTED_OVERLAP` на width3: безопасность важных RGB-контуров и их читаемость **не доказана** даже при 0 foreign/white этих 20 однослойных проб. Original S3 hidden-alpha0 foreign owner, P4D18 full E/F protected-white2250/2261 and interior holes24/25 **FAIL остаются**. All SKC1 geometric core UNKNOWN and **0 admitted strokes**; strict S4 `BLOCKED`, не заявлять original image whole-paint PASS.

## Окончательное решение NG2 (STOP)

Одна ограниченная native E3 выборка **выполнена полностью**. **Не запускать** следом новые width/angle/phase/Lab/SLIC микросерии ради нуля по protected. Для дальнейшего движения по **старому S0→S6** нужен **один минимальный source/native owner-aware admissibility risk-gate дизайн** с независимым подтверждением непустого полезного покрытия/critical contour и фактической native footprint/мультицветного слоя. Пока нет такого доказательства, не открывать строгий S4 BLIND120, S5 или S6. Отдельный prospective E0 обязателен перед любым новым значимым E3. VIS1 признан пользователем визуально предварительно приемлемым, не окончательным рисунком. Данные NG2 не дают права менять production/Stage6/Bridge/Monitor/master, scientific zero-protected/owner thresholds или CHALK estimator.
