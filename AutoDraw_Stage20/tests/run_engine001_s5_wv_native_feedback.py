"""Research-only: real Egret alpha-hole feedback on frozen S5 full wV source plan."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_s5_wv_full_native as base


def projected_target(target):
    rows = np.floor((np.arange(720) + .5) / 2.25).astype(int)
    cols = np.floor((np.arange(450) + .5) / 2.25).astype(int)
    return target[rows[:, None], cols], rows, cols


def diagnostic(native_rgba, prepared):
    crop = native_rgba[:720, 465:915]
    target, rows, cols = projected_target(prepared)
    fg = np.any(target != 255, axis=2)
    alpha = crop[:, :, 3]
    d = {
        "native_foreground_pixels": int(fg.sum()),
        "alpha0_missing": int((fg & (alpha == 0)).sum()),
        "alpha24_missing": int((fg & (alpha <= 24)).sum()),
        "alpha128_missing": int((fg & (alpha < 128)).sum()),
        "white_background_ink_alpha24": int(((~fg) & (alpha > 24)).sum()),
    }
    return d


def patches(native_rgba, prepared, method, first_id):
    crop = native_rgba[:720, 465:915]
    target, rows, cols = projected_target(prepared)
    missing = np.any(target != 255, axis=2) & (crop[:, :, 3] <= 24)
    yy, xx = np.nonzero(missing)
    if method == "source-centroid":
        src_index = rows[yy] * prepared.shape[1] + cols[xx]
        ids, inverse = np.unique(src_index, return_inverse=True)
        nx = np.bincount(inverse, weights=xx.astype(float), minlength=len(ids))
        ny = np.bincount(inverse, weights=yy.astype(float), minlength=len(ids))
        counts = np.bincount(inverse, minlength=len(ids))
        coords_x, coords_y = nx / counts, ny / counts
        source_y, source_x = np.divmod(ids, prepared.shape[1])
    elif method == "backing-points":
        coords_x, coords_y = xx.astype(float), yy.astype(float)
        source_x, source_y = cols[xx], rows[yy]
    else:
        raise ValueError(method)

    result = []
    for i, (x, y, sx, sy) in enumerate(zip(coords_x, coords_y, source_x, source_y)):
        color = int.from_bytes(bytes(prepared[int(sy), int(sx)]), "big")
        logical_x = (465 + float(x) + .5) / 3
        logical_y = (float(y) + .5) / 3
        # The real Egret single-point draw previously produced no ink.
        path = base.segment(logical_x, logical_y, .5, 0)
        result.append(base.stroke(path, 1, color, first_id + i))
    return result, int(missing.sum())


def main(method):
    # Baseline rebuild is fresh from original; unchanged predecessor checks its
    # source SHA, original source-plan digest, blank board and native control.
    base.main(extra_percent=20, strategy="global")
    out = base.OUT
    with gzip.open(out / "native-plan.json.gz", "rt") as f:
        initial_paths = json.load(f)
    prepared = np.asarray(Image.open(out / "source" / "02-prepared.png"))
    assert prepared.shape == (320, 200, 3) and len(initial_paths) == 8922
    initial = np.asarray(Image.open(out / "full.png"))
    assert initial.shape == base.binding.native.SHAPE
    baseline_diag = diagnostic(initial, prepared)
    # Frozen observation from archived real native global +20% at 6c5095a.
    assert baseline_diag["alpha0_missing"] == 2027
    assert baseline_diag["alpha24_missing"] == 2423

    history = [dict(phase="baseline", diagnostic=baseline_diag,
                    metrics=json.loads((out / "results.json").read_text())["metrics"]["full"],
                    cumulative_strokes=len(initial_paths))]
    all_paths = list(initial_paths)
    with base.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        blank = base.render(driver, "feedback-blank", [])
        assert not blank[:, :, 3].any()
        control = [base.stroke(base.segment(200, 100, 12, 0), 4, 0, 0)]
        unchanged = base.render(driver, "feedback-control-original", control)
        driver.execute_script(base.full_fixture())
        assert np.array_equal(unchanged, base.render(driver, "feedback-control-full", control))
        for n in (1, 2):
            last = initial if n == 1 else rgba
            extra, detected = patches(last, prepared, method, 1000000 * n)
            assert detected == diagnostic(last, prepared)["alpha24_missing"]
            assert len(extra) > 0, "No holes remain: stop, report this as successful instead."
            all_paths.extend(extra)
            with gzip.open(out / ("feedback-round%d-plan.json.gz" % n), "wt") as f:
                json.dump(all_paths, f, separators=(",", ":"))
            rgba = base.render(driver, "feedback-round%d" % n, all_paths)
            metrics = base.score("feedback-round%d" % n, rgba, prepared)
            diag = diagnostic(rgba, prepared)
            history.append(dict(phase="feedback-round%d" % n, diagnostic=diag,
                                metrics=metrics, added_strokes=len(extra),
                                detected_missing=detected,
                                cumulative_strokes=len(all_paths)))
    base.binding.write_json(out / "feedback-results.json", dict(
        sha=__import__("os").environ["GITHUB_SHA"], run=__import__("os").environ["GITHUB_RUN_ID"],
        method=method, tolerance_baseline_percent=20, mode="normal", smooth=False,
        source_plan_sha256="2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3",
        history=history, exact_CHALK="NOT_RUN"))
    print("FEEDBACK_RESULTS " + json.dumps(dict(method=method, history=history), separators=(",", ":")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", choices=("source-centroid", "backing-points"), required=True)
    main(parser.parse_args().method)
