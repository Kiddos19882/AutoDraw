# ENGINE-001 / V25 — визуальный обзор узнаваемости AniLines и V18/V20

**Дата:** 2026-11-15. **Статус:** EXPLORATORY / E1+визуальный обзор одного примера, без независимого рейтинга и без E4. **Задача:** ENGINE-001 (смена приоритета на узнаваемость исходного изображения). **Baseline commit при начале:** `0070f44504db8b115b7885e16cc8abc9c5d0d15e` на `feature/image-geometry-optimization`. Пользователь согласовал приоритет узнаваемости над техническими прокси. **Это ретроспективное сравнение уже готовых frozen артефактов, а НЕ заранее зарегистрированный experiment с распознавательным PASS.**

## Имеющиеся первичные контрольные результаты

Вход `wV6VeZI9S1Y.png`: исходная картинка 200×320 и её корректно масштабированный ROI 150×240 на логической доске 460×240 в (155,0). Пять сравниваемых колонок: original RGB, сырые `V14 line-output.png`, `V18-A-roi.png`, `V18-B-roi.png`, `V20 v20-three-panel.png` справа. Все изображения — **offline-представления исходного/контуров**, а не итоговое игровое полноцветное рисование.

Данные взяты без перезаписи из:
- [V14 real AniLines CI 43653371987](https://github.com/Kiddos19882/AutoDraw/actions/runs/43653371987), artifact **14136459858**, `line-output.png` SHA256 `2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b`; `source.png` SHA256 `a526e7e22984705f05751d91b55eaa8107026f5e17a529dae1cdc1f3c2a99f17`.
- [V18-A/B CI 43677851946](https://github.com/Kiddos19882/AutoDraw/actions/runs/43677851946), artifact **14147096853**, `A-roi.png` SHA256 `a65316ebc344dd3218e3e98fc1505bd3c5e167c9f61b0c13ffa5751e018eb662`, `B-roi.png` SHA256 `e2c604a31556b0414a451e36d6b7d2aa66cf01c65a36c4a31d3f9d601a3f1adf`.
- [V20 43682497864](https://github.com/Kiddos19882/AutoDraw/actions/runs/43682497864), artifact **14148846836**, `v20-three-panel.png` SHA256 `8329081964a60399e8ed626384f5671f8e3e80ab716519810c33f4aa926804a5`. Initial V20 [43682273860](https://github.com/Kiddos19882/AutoDraw/actions/runs/43682273860) also passed. V18-B 5792/5943 vs V20 5812/5943 **source skeleton within1px** — this is not recognizability.

## Reproducible visual sheet, bounded observation

The independently created **derived** visual bundle `engine001_v25_visual_review.zip` (local analysis artifact, not source-of-truth repo file), SHA256 `38f8c9b92c0567847e77d2e1a7141f34dc1c1ce06ab6a8f4b6f8e253bdfa6804`, contains `build_review.py`, `visual_review_manifest.json`, `visual_compare_full.png`, `visual_compare_faces.png`, `visual_diff_V18B_to_V20.png`. Derived hashes: full `5d02f128deb6d328d3a0b3c844ffacf3a1118ac7873eadec051aecdd5c033e0e`, faces `f762f7447cc7a8e3e59b04e2edb9dd20f02cf5cde1607255d22d04810ac29a20`, B→V20 difference `7583e81b84328ef3f884793e42913cf1433bbf9984cb84a45bc683a0c3334a68`. These files are **user-facing conversation artifacts** and are not claimed to be checked into GitHub. Archive provenance remains the original GitHub Actions links above.

Observation procedure: same 150×240 ROI and exact same cropping (faces upper ROI 150×125), enlarged by nearest-neighbor only for inspection; V14 raw 200×320 → 150×240 with NEAREST for alignment; source original 200×320 → 150×240 with LANCZOS. V18-A/B source previews kept unchanged. V20 rightmost 150×240 crop of original 450×240 three-panel. Python/Numpy exact per-pixel RGB comparison of V18-B preview and V20 preview finds **17/36,000 pixels changed** (bbox x 59..115, y 27..226); not native/game or painted coverage. Manual face/outline assessment below was made after looking at the existing outputs; **not blinded, no aggregate numerical ranking, no human-observer panel**.

## Visual findings, not acceptance test

| Criterion | Raw V14 AniLines | V18-A/B reconstructed thin contours | V20 versus V18-B |
|---|---|---|---|
| Number/identity of figures | Two interacting characters and main pose still readable | Both characters/pose still readable | No observable meaningful change |
| Face/expression | Several eye/mouth/hair details retained; lines densely overlap around both faces | Contours cleaner/less dense but some expressive face details become weaker/disconnected | No visible restoration of an eye, mouth or other salient distinctive feature |
| Silhouette/overlap | Dress, hair, shoulders and hand pose visible but crossings crowded | Major outfit and hair shapes retained, hands/overlaps still ambiguous | 17 changed logical pixels do not resolve silhouette/hand ambiguity |
| Colored recognition | No: original distinctive blonde/orange + dark attire are not reproduced in line-only preview | No: monochrome diagnostic only | No: monochrome diagnostic only |
| In-game actual painting | NOT_RUN | NOT_RUN | NOT_RUN |

**Interpretation:** morphological skeleton support improvement is not a perceptual similarity score. V18-B→V20 changes are tiny and **show no compelling salient-feature improvement on this single input**. The major recognizable difference from the original is the missing color/shape segmentation and expressive facial/hand details, not last 20 source skeleton vertices. AniLines may be a promising line extraction stage, but current evidence cannot rank final colored AutoDraw renders. Do **not** assert full-color performance or automatic recognizability PASS.

## Decision and next concrete task

**Stop spending the next experimental iteration on 1–9px skeleton recovery as the primary objective.** Retain V18/V20 immutable baseline and V21–V24 E3 safety findings as guard rails. Next ENGINE-001 experiment should first generate or locate a **genuine comparable full-color offline drawing-plan preview** for the pinned complex source using the *existing* Stage20 preparation + color planner/renderer (do not fake original colors by pasting source image behind outline; record exactly what planner actually paints). If the current pipeline cannot consume AniLines contours plus color fills, explicitly mark **BLOCKED** and document the minimal missing adapter, rather than claiming colored quality.

Prioritize *recognizable facial features, distinct silhouette, separating the two figures, clothing color blocks, and hand/eye contours*. Visual acceptance can be a transparent checklist with no blind independent reviewer required. Carry original and output side-by-side same ROI/scale, per-run source SHA, actual generated plan and PNG; if a change is imperceptible, prefer no regression/cost increase. Keep original constraints for leakage max3 logical px, >=99% quality coverage where applicable, and game exact CHALK bound to run, not forecasts. **Only a real game execution with Monitor artifacts is E4 and produces exact CHALK.**

**Next step:** audit existing color preview pipeline and produce comparable actual color-plan PNG before writing any new geometry filter. No production/Stage6/Bridge/Monitor changes in this retrospective review.
