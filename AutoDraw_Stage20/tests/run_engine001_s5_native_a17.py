"""A17 preregistration: same A16 RTV04 R2 target and native harness; no spill gate.
Compare frozen F1, joining nearest endpoints within 3/5/10/20 source px.
Keep all original path vertices, allow bridges outside mask, width1 unchanged.
Also test width2/3 on joined 10px routes. No production promotion.
Primary metrics: native alpha128 coverage >= A16 F1, fewer strokes; length and spill diagnostic.
"""
from run_engine001_s5_native_a16 import *
import math
import run_engine001_s5_native_a16 as base

def join(paths, scale, radius):
    remaining = [dict(p, points=list(p["points"])) for p in paths]
    result = []
    while remaining:
        p = remaining.pop(0)
        while remaining:
            end = p["points"][-1]
            def distance(q):
                return math.hypot(end["x"]-q["x"], end["y"]-q["y"])/scale
            d,i,rev = min((distance(q["points"][-1 if rev else 0]),i,rev)
                          for i,q in enumerate(remaining) for rev in (False,True))
            if d > radius:
                break
            q = remaining.pop(i)["points"]
            if rev:
                q.reverse()
            p["points"].extend(q[1:] if p["points"][-1]==q[0] else q)
        result.append(p)
    return result

def contracts():
    p=lambda a,b: dict(points=[dict(x=a,y=0),dict(x=b,y=0)],width=1,colorRgb=0)
    assert len(join([p(0,6),p(8,14)],1,3))==1
    assert len(join([p(0,6),p(8,14)],1,1))==2
    base.contracts()

def main(baseline, source):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    output = Path(os.environ["RUNNER_TEMP"]) / "s5-a17-diagonal"
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
        pp = free.proposals(target, g, proof, "f1", native.stroke, native.segment)
        paths, dropped = normalize(pp, rgb, g["scale"], "f1")
        assert len(paths)==275 and abs(metrics(paths,g)["source_length_total_px"]-10948.36860918064)<1e-6
        proposed = [("f1-control", paths, dropped)]
        for radius in (3,5,10,20):
            joined, _ = normalize(join(paths,g["scale"],radius),rgb,g["scale"],"joined")
            proposed.append((f"f1-join-r{radius}",joined,dropped))
            if radius==10:
                for width in (2,3):
                    proposed.append((f"f1-join-r10-w{width}",set_width(joined,width=width),dropped))
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
            print("A17 " + json.dumps({name: dict(strokes=measure["strokes"],
                source_length_total_px=measure["source_length_total_px"],
                source_length_mean_px=measure["source_length_mean_px"],
                coverage_percent=audit["128"]["coverage_percent"],
                outside_ink_percent=audit["128"]["outside_ink_percent"])}, ensure_ascii=False), flush=True)
        # Contact-sheet panels use the ORIGINAL native RGBA render; never draw simulated footprints.
        names = ["f1-control", "f1-join-r3", "f1-join-r5", "f1-join-r10", "f1-join-r20", "f1-join-r10-w2"]
        grid = Image.new("RGB", (450 * 3, 720 * 2), "white")
        for index, name in enumerate(names):
            if (output / (name + ".png")).exists():
                frame = Image.open(output / (name + ".png")).convert("RGBA")
                source_frame = frame.crop((465, 0, 915, 720))
                base = Image.new("RGBA", source_frame.size, "white")
                base.alpha_composite(source_frame)
                grid.paste(base.convert("RGB"), (index % 3 * 450, index // 3 * 720))
        grid.save(output / "native-comparison-6-scenes.png")
    report = dict(schema="ENGINE001_S5_A17_V1", run=os.environ["GITHUB_RUN_ID"],
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
        comparison="A16 F1 control; unrestricted endpoint bridges; spill diagnostic only",
        results=results, exact_CHALK="NOT_RUN", live_E4="NOT_RUN", E5="NOT_RUN",
        user_visual_review="PENDING")
    native.binding.write_json(output / "a17-results.json", report)
    lines = ["# A17 isolated dark contour / actual Egret", "",
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
    (output / "A17_RESULT_TABLE.md").write_text("\n".join(lines) + "\n", encoding="utf8")

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
