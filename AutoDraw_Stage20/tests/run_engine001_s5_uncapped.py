"""Offline stroke-quality baseline, rebuilt from an original with the S4.6 source contract."""
import argparse
import gzip
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

import engine001_bpred_s5r8_connected as connected
import run_engine001_bpred_s5r7_four_originals as reference


def run(root, relative, output):
    original = reference.original
    data = (root / relative).read_bytes()
    palette, provenance = original.palette.read_engine_palette(root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != original.dev.ENGINE_BLOB:
        raise ValueError("Engine palette digest mismatch")
    rgba = original.original_io.decode_original(data)["rgba"]
    ctr = original.ctr.build_ctr1(rgba, palette)
    manifest, packet = original.s46.export_quarantined(
        data, rgba, palette, ctr, str(relative), original.dev.ENGINE_BLOB)
    original.s46.verify_quarantined(manifest, packet, data)
    with np.load(io.BytesIO(packet), allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in ("original_rgba", "game_index", "paintable_id",
                                          "protected_original_dot", "source_edge")}
    plan = connected.build_candidates(arrays)
    metrics = reference.independent(plan, arrays)
    game = arrays["game_index"]
    h, w = game.shape
    visible = rgba[..., 3] == 255
    colors = np.asarray(palette, dtype=np.uint8)
    target = np.full((h,w,3), 255, np.uint8)
    target[visible] = colors[game[visible]]
    image = np.full_like(target, 255)
    painted = np.zeros((h,w), bool)
    output.mkdir(parents=True, exist_ok=False)
    Image.fromarray(rgba).save(output / "01-original.png")
    Image.fromarray(target).save(output / "02-prepared.png")
    phase_counts = {}
    for phase, filename in (("broad", "03-connected.png"), ("detail", "04-with-residuals.png")):
        for stroke in plan["proposals"]:
            if stroke["phase"] != phase:
                continue
            mask = connected.r7.source.swept_capsule_pixel_masks(
                stroke["points"], stroke["brush_value"], 1., 1., w, h)
            for x, y in mask["potential_cells"]:
                painted[y,x] = True
                image[y,x] = colors[stroke["color_index"]]
        phase_counts[phase] = dict(covered=int(painted.sum()),
                                   nonwhite=int((painted & (game != 6)).sum()))
        Image.fromarray(image).save(output / filename)
    if int(painted.sum()) != metrics["total"]:
        raise ValueError("Coverage mismatch")
    report = dict(schema=plan["schema"], input_sha256=original.sha(data),
                  source_manifest_sha256=original.sha(manifest), plan_sha256=plan["result_sha256"],
                  drawing_mode="normal", smooth=False, metrics=metrics, cumulative=phase_counts,
                  phase_strokes=plan["phase_strokes"], phase_trials=plan["phase_trials"],
                  missing=int((visible & ~painted).sum()), visible=int(visible.sum()),
                  rgb_matches_prepared=bool(np.array_equal(image,target)),
                  native_Egret="NOT_RUN", exact_CHALK="NOT_RUN")
    (output / "source-manifest.json").write_bytes(manifest)
    (output / "plan.json.gz").write_bytes(gzip.compress(original.canonical(plan), mtime=0))
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=Path(reference.original.dev.SOURCES[0]))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.root, args.source, args.output)
