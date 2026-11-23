"""Double-fresh R8 source-only experiment against signed R3–R7 baselines."""
import argparse
import gzip
import io
import platform
import sys
from pathlib import Path
from zipfile import crc32

import numpy as np

import engine001_bpred_s5r8_connected as r8
import run_engine001_bpred_s5r7_four_originals as prior


original = prior.original
FLOOR = (2726, 7501, 240845, 14877)


def run_source(index, relative, root, out, palette):
    data = (root / relative).read_bytes()
    expected = None
    for repeat in range(2):
        rgba = original.original_io.decode_original(data)["rgba"]
        ctr = original.ctr.build_ctr1(rgba, palette)
        manifest, packet = original.s46.export_quarantined(
            data, rgba, palette, ctr, relative, original.dev.ENGINE_BLOB)
        original.s46.verify_quarantined(manifest, packet, data)
        with np.load(io.BytesIO(packet), allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in ("original_rgba", "game_index", "paintable_id",
                                              "protected_original_dot", "source_edge")}
        plan = r8.build_candidates(arrays)
        original.verifier.validate_model(plan, arrays)
        metrics = prior.independent(plan, arrays)
        raw = original.canonical(plan)
        signature = [original.sha(manifest), original.sha(packet), original.sha(raw), metrics]
        if repeat:
            if signature != expected:
                raise ValueError("Double-fresh source or plan drift")
            continue
        expected = signature
        (out / "plan.json").write_bytes(raw)
        (out / "source_manifest.json").write_bytes(manifest)
        original.visual_report(arrays, palette, plan, out / "model.png")
        graphs = r8.r7.dual_graphs(arrays["paintable_id"], rgba[...,3] == 255)
        for axis, graph in zip((0,90), graphs):
            (out / f"graph_{axis}.json.gz").write_bytes(
                gzip.compress(original.canonical(graph),mtime=0))
        del graphs
    floor = FLOOR[index]
    return dict(source=relative, input_sha256=original.sha(data), signature=expected,
                metrics=metrics, nonwhite_min=floor, r3_total_min=prior.R3_TOTAL[index],
                nonwhite_pass=metrics["nonwhite"] >= floor,
                total_pass=metrics["total"] >= prior.R3_TOTAL[index],
                protected_pass=metrics["protected"] >= 120,
                gain10=10*metrics["nonwhite"] >= 11*floor, double_fresh=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    opts = parser.parse_args()
    opts.output.mkdir(parents=True, exist_ok=False)
    palette, provenance = original.palette.read_engine_palette(
        opts.root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != original.dev.ENGINE_BLOB:
        raise ValueError("Engine palette blob drift")
    rows = []
    for index, path in enumerate(original.dev.SOURCES):
        output = opts.output / str(index)
        output.mkdir()
        row = run_source(index, path, opts.root, output, palette)
        rows.append(row)
        print(path, row["metrics"], flush=True)
    passed = all(r["total_pass"] and r["nonwhite_pass"] and r["protected_pass"]
                 for r in rows) and sum(r["gain10"] for r in rows) >= 2
    result = dict(experiment=r8.VERSION, python=sys.version, environment=platform.platform(),
                  sources=rows, native_Egret="NOT_RUN", exact_CHALK="NOT_RUN",
                  status=("PASS" if passed else "FAIL") + "_CONNECTED_COVERAGE_FEASIBILITY")
    (opts.output / "results.json").write_bytes(original.canonical(result))
    ledger = {}
    for path in sorted(opts.output.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            ledger[str(path.relative_to(opts.output))] = [original.sha(data), crc32(data)]
    (opts.output / "checksums.json").write_bytes(original.canonical(ledger))


if __name__ == "__main__":
    main()
