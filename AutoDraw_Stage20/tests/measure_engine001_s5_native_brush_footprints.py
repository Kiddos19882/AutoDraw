"""Post-analyze archived P4D3/P4D4 Egret PNGs without rerendering the game."""
import argparse
import csv
import hashlib
import io
import json
import statistics
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

EXPECTED = {
    "p4d3": "690fab5a021efac16ffa6bf67e3c6cef3bc39d5e7eefc57b93a0cd87b2e7bb2d",
    "p4d4": "e28b065fbc6880f8180f110e3ae934a7f807055c77bc1e188256c09fcf67772a",
}
CENTERS = [(x, y) for y in (40, 120) for x in (58, 172, 286, 400)] + [(58, 200), (172, 200)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for study, expected_sha in EXPECTED.items():
        raw = (args.input_dir / (study + ".zip")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise ValueError(f"{study} ZIP SHA256 does not match frozen archive")
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if archive.testzip() is not None:
                raise ValueError(f"{study}: ZIP CRC failure")
            for width in range(1, 11):
                for angle in range(0, 360, 15):
                    prefix = f"primary/L34/W{width:02}/W{width:02}_A{angle:03}_L34"
                    plan = json.loads(archive.read(prefix + "_PLAN.json"))
                    alpha = np.asarray(Image.open(io.BytesIO(archive.read(prefix + "_R1.png"))).convert("RGBA"))[:, :, 3]
                    if alpha.shape != (720, 1380) or len(plan) < 10:
                        raise ValueError("Invalid native resolution or plan")
                    for copy, (cx, cy) in enumerate(CENTERS):
                        a, b = plan[copy]["points"]
                        dx, dy = b["x"] - a["x"], b["y"] - a["y"]
                        distance = float(np.hypot(dx, dy))
                        if abs(distance - 34) > 0.005 or plan[copy]["width"] != width:
                            raise ValueError("Mismatched native stroke geometry")
                        ux, uy = dx / distance, dy / distance
                        x0, y0 = (cx - 27) * 3, (cy - 27) * 3
                        patch = alpha[y0:y0 + 162, x0:x0 + 162]
                        yy, xx = np.indices(patch.shape)
                        t = ((xx + x0 + 0.5) / 3 - a["x"]) * ux + ((yy + y0 + 0.5) / 3 - a["y"]) * uy
                        core = (t >= 7) & (t < 27)
                        for threshold in (24, 128):
                            mask = core & (patch >= threshold)
                            bins = np.bincount(np.floor(t[mask] - 7).astype(int), minlength=20)[:20] / 9
                            rows.append(dict(study=study, width=width, angle=angle, copy=copy, alpha=threshold,
                                             core_area_logical_px2=round(int(mask.sum()) / 9, 6),
                                             effective_width_logical=round(int(mask.sum()) / 180, 6),
                                             min_slice_width_logical=round(float(bins.min()), 6),
                                             max_slice_width_logical=round(float(bins.max()), 6)))
    assert len(rows) == 9600
    core_path = args.output_dir / "brush_native_core_measurements.csv"
    with core_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = []
    for study in EXPECTED:
        for width in range(1, 11):
            for threshold in (24, 128):
                sample = [r for r in rows if r["study"] == study and r["width"] == width and r["alpha"] == threshold]
                vals = [r["effective_width_logical"] for r in sample]
                assert len(vals) == 240
                summary.append(dict(study=study, width=width, alpha=threshold, samples=len(vals),
                                    min=round(min(vals), 3), median=round(statistics.median(vals), 3),
                                    max=round(max(vals), 3), p05=round(float(np.quantile(vals, .05)), 3),
                                    p95=round(float(np.quantile(vals, .95)), 3),
                                    min_1logical_slice=round(min(r["min_slice_width_logical"] for r in sample), 3)))
    summary_path = args.output_dir / "brush_native_width_summary.csv"
    with summary_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    for path in (core_path, summary_path):
        print(path.name, hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
