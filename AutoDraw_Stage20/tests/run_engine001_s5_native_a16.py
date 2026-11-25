"""ENGINE-001 S5 A16: dominant one-color RTV contour, actual native Egret routes."""
import argparse
import collections
import gzip
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

import engine001_s5_a14_routes as routes
import engine001_s5_a14_free_angle as free
from run_engine001_s5_native_a14 import bands
from run_engine001_s5_native_a14_nodot_l5 import length_source

BASE_SHA = "5858e37586a832b91ba40bce0afd6249e9579b1e"
BASE_RUN = "45512562848"
SOURCE_SHA = "3fa893904b87701de47fb50e88b27bfe62996f57"
SOURCE_RUN = "45465036156"
REFERENCE_SHA = "70b13039e4518ce5a4eec57914667e146ee2f898"
ROUTES = ("b", "cfree", "d", "e", "f", "f1", "f2", "f3", "f4", "f6")
MIN_SOURCE_LENGTH = 5.0

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def dominant_dark(band):
    arr = np.asarray(band)
    if arr.dtype != np.uint8 or arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError("invalid source RGB contour band")
    colors, counts = np.unique(arr.reshape(-1, 3), axis=0, return_counts=True)
    candidates = []
    for rgb, count in zip(colors, counts):
        rgb = [int(x) for x in rgb]
        if rgb == [255, 255, 255]:
            continue
        light = sum(k * v for k, v in zip((2126, 7152, 722), rgb)) / 10000
        if light <= 128:
            candidates.append(dict(hex="#" + bytes(rgb).hex().upper(),
                                   rgb=rgb, luminance=light, pixels=int(count)))
    if not candidates:
        raise ValueError("no dark contour swatch with luminance <=128")
    candidates.sort(key=lambda c: (-c["pixels"], c["luminance"], c["hex"]))
    return candidates[0], candidates

def normalize(paths, rgb, scale, label):
    """No single-point marks or <=5 source px paths; preserve all bends."""
    output = []
    dropped = collections.Counter()
    for p in paths:
        if p["colorRgb"] != rgb:
            continue
        if len(p["points"]) < 2:
            dropped["dot"] += 1
            continue
        length = length_source(p, scale)
        if length <= MIN_SOURCE_LENGTH + 1e-9:
            dropped["short"] += 1
            continue
        if p["width"] not in (1, 2, 3):
            raise ValueError("unexpected brush width")
        output.append(dict(p, strokeId="icon-" + str(700000 + len(output))))
    if len({p["strokeId"] for p in output}) != len(output):
        raise ValueError("duplicate stroke IDs")
    return output, dict(dropped)

def set_width(paths, width=None, mixed=None):
    result = []
    for p in paths:
        l = p["_source_length"] if "_source_length" in p else None
        if mixed is not None:
            if l is None:
                raise ValueError("mixed width requires source length")
            w = (3 if l >= 18 else 2 if l >= 10 else 1) if mixed == "321" else (2 if l >= 10 else 1)
        else:
            w = width if width is not None else p["width"]
        q = {k: v for k, v in p.items() if k != "_source_length"}
        result.append(dict(q, width=w))
    return result

def metrics(paths, g):
    lengths = [length_source(p, g["scale"]) for p in paths]
    by_width = collections.Counter(int(p["width"]) for p in paths)
    total = math.fsum(lengths)
    return dict(strokes=len(paths), by_width={str(i): by_width[i] for i in (1, 2, 3)},
                vertices=sum(len(p["points"]) for p in paths),
                max_vertices=max((len(p["points"]) for p in paths), default=0),
                source_length_total_px=total,
                source_length_mean_px=total / len(paths) if paths else 0.0,
                source_length_min_px=min(lengths, default=0.0),
                source_length_max_px=max(lengths, default=0.0),
                logical_egret_length_total_px=total * g["scale"],
                logical_egret_length_mean_px=total * g["scale"] / len(paths) if paths else 0.0)

def native_audit(rgba, projected_mask):
    assert rgba.shape == (720, 1380, 4)
    cropped = rgba[:, 465:915, 3]
    result = {}
    for threshold in (24, 128):
        ink = cropped >= threshold
        inside = int((ink & projected_mask).sum())
        outside = int((ink & ~projected_mask).sum())
        full = int((rgba[:, :, 3] >= threshold).sum())
        result[str(threshold)] = dict(inside=inside, outside=outside,
            target_total=int(projected_mask.sum()), missing=int((projected_mask & ~ink).sum()),
            coverage_percent=100 * inside / int(projected_mask.sum()),
            outside_ink_percent=100 * outside / max(1, inside + outside),
            outside_board=full - int(ink.sum()),
            within_10_percent_scene_diagnostic=outside * 100 <= 10 * max(1, inside + outside))
    return result

def contracts():
    a = np.full((8, 8, 3), 255, dtype=np.uint8)
    a[1:7, 1:6] = [22, 32, 42]
    a[1:7, 6] = [80, 80, 80]
    winner, ranked = dominant_dark(a)
    assert winner["hex"] == "#16202A" and winner["pixels"] == 30
    a[:, :] = 255
    try:
        dominant_dark(a)
    except ValueError:
        pass
    else:
        raise AssertionError("missing fail-closed dark swatch")
    p = dict(points=[dict(x=0.0, y=0.0), dict(x=6.0, y=0.0)],
             width=1, colorRgb=0x16202A, strokeId="icon-0")
    filtered, dropped = normalize([p, dict(p, points=[p["points"][0]])], p["colorRgb"], 1, "test")
    assert len(filtered) == 1 and dropped == {"dot": 1}
    assert metrics(filtered, {"scale": 1})["source_length_total_px"] == 6
    p2 = dict(filtered[0], _source_length=19)
    assert set_width([p2], mixed="321")[0]["width"] == 3
    assert set_width([dict(p2, _source_length=11)], mixed="21")[0]["width"] == 2
    mask = np.zeros((720, 450), bool)
    mask[12:15, 12:15] = True
    rgba = np.zeros((720, 1380, 4), np.uint8)
    rgba[12:15, 477:480, 3] = 255
    assert native_audit(rgba, mask)["128"]["coverage_percent"] == 100
    routes.contracts()
    free.contracts()
    print("A16 source/route/length/native-audit contracts PASS", flush=True)

def main(baseline, source):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    output = Path(os.environ["RUNNER_TEMP"]) / "s5-a16-dark-contour"
    output.mkdir(parents=True, exist_ok=False)
    native.OUT = output
    old = json.loads((baseline / "a14-nodot-l5-results.json").read_text(encoding="utf8"))
    src = json.loads((source / "a14-nodot-results.json").read_text(encoding="utf8"))
    assert (old["sha"], str(old["run"]), old["case"], old["radius_source_px"]) == (BASE_SHA, BASE_RUN, "illustration", 2)
    assert (src["sha"], str(src["run"]), src["case"], src["radii_source_px"]) == (SOURCE_SHA, SOURCE_RUN, "illustration", [2])
    g = old["geometry"]
    assert g == src["geometry"]
    assert digest(native.binding.ROOT / src["source"]) == src["source_sha256"]
    prepared = np.asarray(Image.open(source / "rtv-prepared.png").convert("RGB"))
    band, radius_mask, edge = bands(prepared, 2)
    assert np.array_equal(band, np.asarray(Image.open(baseline / "r02-f4-target.png").convert("RGB")))
    winner, ranked = dominant_dark(band)
    rgb = int.from_bytes(bytes(winner["rgb"]), "big")
    mask = np.all(band == np.asarray(winner["rgb"], np.uint8), axis=2)
    target = np.where(mask[:, :, None], np.asarray(winner["rgb"], np.uint8), 255).astype(np.uint8)
    assert target.shape[:2] == (g["height"], g["width"])
    Image.fromarray(target).save(output / "dark-contour-only-target.png")
    Image.fromarray(band).save(output / "all-colors-original-contour-band.png")
    Image.fromarray(prepared).save(output / "rtv04-prepared.png")
    with gzip.open(baseline / "r02-f4-plan.json.gz", "rt", encoding="utf8") as file:
        frozen = json.load(file)
    control = old["results"]["r02-f4"]
    assert digest(baseline / "r02-f4-plan.json.gz") == control["plan_sha256"]
    assert len(frozen) == control["strokes"]
    assert all(p["width"] == 1 and length_source(p, g["scale"]) > 5 + 1e-9 for p in frozen)
    original_control, control_dropped = normalize(frozen, rgb, g["scale"], "baseline")
    assert not control_dropped and original_control
    results = {}
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver, "blank", [])[:, :, 3].any()
        reference = [native.stroke(native.segment(200, 100, 12, 0), 4, 0, 0)]
        first = native.render(driver, "reference-original", reference)
        js = native.full_fixture()
        a = js.index("function renderComplexHoldoutColorProbe(")
        z = js.index("const board = makeTemporalBoard(", a)
        guard = js[a:z]
        anchor = " ||\n          stroke.points.length > 128"
        assert guard.count(anchor) == 1
        driver.execute_script(js[:a] + guard.replace(anchor, "") + js[z:])
        assert np.array_equal(first, native.render(driver, "reference-expanded", reference))
        proof = physical.native_footprints(driver)
        native.binding.write_json(output / "egret-physical-footprints.json", proof)
        projected, _, _ = transfer.projected(target, g)
        projected_mask = np.all(projected == np.asarray(winner["rgb"], np.uint8), axis=2)
        assert projected_mask.any()
        proposed = [("baseline-f4-l5", original_control, control_dropped)]
        for variant in ROUTES:
            if variant.startswith("f") and variant != "f":
                pp = free.proposals(target, g, proof, variant, native.stroke, native.segment)
            else:
                pp = routes.plan(target, g, proof, variant, native.stroke, native.segment)
            paths, dropped = normalize(pp, rgb, g["scale"], variant)
            proposed.append(("route-" + variant, paths, dropped))
            if variant == "cfree":
                for w in (2, 3):
                    proposed.append((f"long-horizontal-w{w}", set_width(paths, width=w), dropped))
                augmented = [dict(p, _source_length=length_source(p, g["scale"])) for p in paths]
                for mixed in ("21", "321"):
                    proposed.append((f"long-horizontal-mix-{mixed}", set_width(augmented, mixed=mixed), dropped))
        for name, paths, dropped in proposed:
            if not paths:
                results[name] = dict(status="NO_ELIGIBLE_STROKES", dropped=dropped)
                continue
            assert all(p["colorRgb"] == rgb and p["width"] in (1, 2, 3) for p in paths)
            assert all(length_source(p, g["scale"]) > 5 + 1e-9 for p in paths)
            with gzip.open(output / (name + "-plan.json.gz"), "wt", encoding="utf8") as file:
                json.dump(paths, file, separators=(",", ":"))
            rgba = native.render(driver, name, paths)
            sim = json.loads((output / (name + ".json")).read_text(encoding="utf8")).get("paintCounter")
            assert sim is not None and sim["used"] == sum(len(p["points"]) for p in paths)
            measure = metrics(paths, g)
            audit = native_audit(rgba, projected_mask)
            results[name] = dict(status="NATIVE_RENDERED", **measure, dropped=dropped,
                native=audit, simulation_meter=sim["used"],
                plan_sha256=digest(output / (name + "-plan.json.gz")),
                rgba_sha256=digest(output / (name + ".png")))
            print("A16 " + json.dumps({name: dict(strokes=measure["strokes"],
                source_length_total_px=measure["source_length_total_px"],
                source_length_mean_px=measure["source_length_mean_px"],
                coverage_percent=audit["128"]["coverage_percent"],
                outside_ink_percent=audit["128"]["outside_ink_percent"])}, ensure_ascii=False), flush=True)
        # Contact-sheet panels use the ORIGINAL native RGBA render; never draw simulated footprints.
        names = ["baseline-f4-l5", "route-cfree", "route-e", "long-horizontal-w2", "long-horizontal-w3", "long-horizontal-mix-321"]
        grid = Image.new("RGB", (450 * 3, 720 * 2), "white")
        for index, name in enumerate(names):
            if (output / (name + ".png")).exists():
                frame = Image.open(output / (name + ".png")).convert("RGBA")
                source_frame = frame.crop((465, 0, 915, 720))
                base = Image.new("RGBA", source_frame.size, "white")
                base.alpha_composite(source_frame)
                grid.paste(base.convert("RGB"), (index % 3 * 450, index // 3 * 720))
        grid.save(output / "native-comparison-6-scenes.png")
    report = dict(schema="ENGINE001_S5_A16_V1", run=os.environ["GITHUB_RUN_ID"],
        sha=os.environ["GITHUB_SHA"], baseline_sha=REFERENCE_SHA,
        baseline_control_sha=BASE_SHA, baseline_control_run=BASE_RUN,
        source_archive_sha=SOURCE_SHA, source_archive_run=SOURCE_RUN,
        source=src["source"], source_sha256=src["source_sha256"],
        prepared_sha256=digest(source / "rtv-prepared.png"),
        target_sha256=digest(output / "dark-contour-only-target.png"),
        geometry=g, source_radius_px=2, dark_color=winner, ranked_dark_colors=ranked,
        dark_contour_source_pixels=int(mask.sum()), full_contour_source_pixels=int(radius_mask.sum()),
        width_variants=[1, 2, 3], smoothing=False,
        min_source_stroke_length_exclusive=MIN_SOURCE_LENGTH,
        per_stroke_10_percent_native_spill_gate="NOT_RUN; scene-level diagnostic only",
        renderer="real Egret 5.4.1 BoardPane/WebGLRenderer",
        comparison="A15.1 R2/T10 isolated color contour control (not full accepted image)",
        results=results, exact_CHALK="NOT_RUN", live_E4="NOT_RUN", E5="NOT_RUN",
        user_visual_review="PENDING")
    native.binding.write_json(output / "a16-results.json", report)
    lines = ["# A16 isolated dark contour / actual Egret", "",
        "Color: " + winner["hex"] + "; source contour pixels: " + str(int(mask.sum())), "",
        "| Variant | Strokes | Total length, source px | Mean length, source px | Total length, Egret logical px | Alpha128 coverage % | Alpha128 outside ink % |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for key, val in results.items():
        if val["status"] == "NATIVE_RENDERED":
            lines.append("| " + key + " | " + str(val["strokes"]) + " | " +
                f'{val["source_length_total_px"]:.2f} | {val["source_length_mean_px"]:.2f} | {val["logical_egret_length_total_px"]:.2f} | {val["native"]["128"]["coverage_percent"]:.2f} | {val["native"]["128"]["outside_ink_percent"]:.2f} |')
        else:
            lines.append("| " + key + " | NO_ELIGIBLE_STROKES | — | — | — | — | — |")
    lines += ["", "Only actual BoardPane/Egret RGBA supports native coverage. Source arc lengths are geometric plan metrics, not exact game CHALK.",
        "Simulation meter is not run-bound game CHALK. Each complete plan, native RGBA, and SHA is in this artifact."]
    (output / "A16_RESULT_TABLE.md").write_text("\n".join(lines) + "\n", encoding="utf8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.contracts:
        contracts()
    else:
        if args.baseline is None or args.source is None:
            parser.error("--baseline and --source required")
        main(args.baseline, args.source)
