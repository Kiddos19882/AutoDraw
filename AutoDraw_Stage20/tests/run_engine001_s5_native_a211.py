"""A21.1 prereg: frozen A21 strict/soft plans; original A20 pixel gates unchanged. Full native whole-stroke and interior vertex-block deletion until a complete pass accepts no deletion. No attempt cap; CI timeout remains. Local fixed point only, no production promotion."""
from run_engine001_s5_native_a16 import *
import math
import run_engine001_s5_native_a16 as base

from scipy.ndimage import distance_transform_edt

def bridge_ok(a,b,g,allowed):
    scale=g["scale"]
    d=math.hypot(a["x"]-b["x"],a["y"]-b["y"])/scale
    t=(np.arange(max(1,math.ceil(d*4)))+0.5)/max(1,math.ceil(d*4))
    xx=np.floor((a["x"]+(b["x"]-a["x"])*t-g["left"])/scale).astype(int)
    yy=np.floor((a["y"]+(b["y"]-a["y"])*t-g["top"])/scale).astype(int)
    valid=(xx>=0)&(yy>=0)&(xx<allowed.shape[1])&(yy<allowed.shape[0])
    inside=np.zeros(len(t),bool)
    inside[valid]=allowed[yy[valid],xx[valid]]
    return inside.mean()>=0.8

def join(paths,g,radius,allowed):
    remaining=[dict(p,points=list(p["points"])) for p in paths]
    result=[]
    while remaining:
        p=remaining.pop(0)
        while remaining:
            end=p["points"][-1]
            candidates=sorted((math.hypot(end["x"]-q["points"][-1 if rev else 0]["x"],end["y"]-q["points"][-1 if rev else 0]["y"])/g["scale"],i,rev) for i,q in enumerate(remaining) for rev in (False,True))
            choice=next(((i,rev) for d,i,rev in candidates if d<=radius and bridge_ok(end,remaining[i]["points"][-1 if rev else 0],g,allowed)),None)
            if choice is None: break
            i,rev=choice
            q=remaining.pop(i)["points"]
            if rev: q.reverse()
            p["points"].extend(q[1:] if p["points"][-1]==q[0] else q)
        result.append(p)
    return result

def simplify(p,scale,epsilon):
    pts=p["points"]
    xy=np.array([[q["x"],q["y"]] for q in pts],float)
    keep={0,len(pts)-1}
    stack=[(0,len(pts)-1)]
    while stack:
        a,b=stack.pop()
        if b<=a+1: continue
        v=xy[b]-xy[a]
        z=xy[a+1:b]-xy[a]
        t=np.clip(z@v/max(float(v@v),1e-30),0,1)
        dist=np.linalg.norm(z-t[:,None]*v,axis=1)
        i=int(np.argmax(dist))
        if dist[i]>epsilon*scale:
            k=a+1+i
            keep.add(k)
            stack.extend([(a,k),(k,b)])
    return dict(p,points=[pts[i] for i in sorted(keep)])

def contracts():
    g=dict(scale=1,left=0,top=0)
    p=lambda a,b: dict(points=[dict(x=a,y=1),dict(x=b,y=1)],width=1,colorRgb=0)
    allowed=np.ones((5,20),bool)
    assert len(join([p(0,6),p(8,14)],g,3,allowed))==1
    allowed[:,6:8]=False
    assert len(join([p(0,6),p(8,14)],g,3,allowed))==2
    assert len(simplify(dict(points=[dict(x=i,y=0) for i in range(10)]),1,.25)["points"])==2
    base.contracts()

def main(baseline, source):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    output = Path(os.environ["RUNNER_TEMP"]) / "s5-a211-diagonal"
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
        # Frozen A21 artifact, not regenerated approximation.
        archive=Path(os.environ["RUNNER_TEMP"])/"a20-baseline"
        old20=json.loads((archive/"a20-results.json").read_text("utf8"))
        key="r150-w2-e2.0-l20"
        assert old20["sha"]=="b5e9c3a29fa3f839ec2ee405cb053bced1463e12" and str(old20["run"])=="45562888542"
        assert old20["geometry"]==g and old20["target_sha256"]==digest(output/"dark-contour-only-target.png")
        record=old20["results"][key]
        plan=archive/(key+"-plan.json.gz")
        assert digest(plan)==record["plan_sha256"]
        with gzip.open(plan,"rt",encoding="utf8") as f: selected=json.load(f)
        assert len(selected)==21 and all(p["width"]==2 and length_source(p,g["scale"])>20 for p in selected)
        ref=native.render(driver,"baseline-proof",selected)
        assert digest(archive/(key+".png"))==record["rgba_sha256"]
        assert np.array_equal(ref,np.asarray(Image.open(archive/(key+".png")).convert("RGBA")))
        proposed=[("a20-control",selected,{})]
        prior=Path(os.environ["RUNNER_TEMP"])/"a21-baseline"
        old21=json.loads((prior/"a21-results.json").read_text("utf8"))
        assert old21["sha"]=="1d11b5b4a0bc4d79ad23d40ca74e5561b4a3c10f" and str(old21["run"])=="45565760896"
        assert old21["geometry"]==g and old21["target_sha256"]==old20["target_sha256"]
        trace=[]
        convergence={}
        base_masks=[(ref[:,465:915,3]>=t)&projected_mask for t in (24,128)]
        ref_out=[int((ref[:,:,3]>=t).sum())-int(m.sum()) for t,m in zip((24,128),base_masks)]
        for loss in (0.0,0.005):
            key=f"pruned-loss-{loss}"
            rec=old21["results"][key]
            plan=prior/(key+"-plan.json.gz")
            assert digest(plan)==rec["plan_sha256"]
            with gzip.open(plan,"rt",encoding="utf8") as f: current=json.load(f)
            start=native.render(driver,f"a21-loss-{loss}",current)
            assert digest(prior/(key+".png"))==rec["rgba_sha256"]
            assert np.array_equal(start,np.asarray(Image.open(prior/(key+".png")).convert("RGBA")))
            proposed.append((f"a21-loss-{loss}",current,{}))
            attempts=0
            rounds=0
            def evaluate(candidate,kind,i,k,block):
                nonlocal attempts
                attempts+=1
                rgba=native.render(driver,"scratch-trial",candidate)
                lost=[int((m & ~(rgba[:,465:915,3]>=t)).sum()) for t,m in zip((24,128),base_masks)]
                outside=[int((rgba[:,:,3]>=t).sum())-int(((rgba[:,465:915,3]>=t)&projected_mask).sum()) for t in (24,128)]
                ok=all(n<=loss*int(m.sum()) for n,m in zip(lost,base_masks)) and all(n<=o for n,o in zip(outside,ref_out))
                trace.append(dict(loss=loss,round=rounds,attempt=attempts,kind=kind,stroke=i,vertex=k,block=block,accepted=ok,lost=lost,outside=outside,vertices=sum(len(p["points"]) for p in candidate)))
                return ok
            while True:
                rounds+=1
                before=sum(len(p["points"]) for p in current)
                i=0
                while i<len(current):
                    candidate=current[:i]+current[i+1:]
                    if candidate and evaluate(candidate,"whole",i,0,0): current=candidate
                    else: i+=1
                for block in (16,8,4,2,1):
                    for i in range(len(current)):
                        k=1
                        while k<len(current[i]["points"])-1:
                            p=current[i]
                            q=dict(p,points=p["points"][:k]+p["points"][min(k+block,len(p["points"])-1):])
                            if length_source(q,g["scale"])>20 and length_source(q,g["scale"])<=length_source(p,g["scale"])+1e-8:
                                candidate=current[:i]+[q]+current[i+1:]
                                if evaluate(candidate,"vertices",i,k,block):
                                    current=candidate
                                    continue
                            k+=1
                after=sum(len(p["points"]) for p in current)
                native.binding.write_json(output/"pruning-trace.json",trace)
                print(f"A211 progress loss={loss} round={rounds} attempts={attempts} vertices={after}",flush=True)
                if after==before: break
                assert after<before
            convergence[str(loss)]=dict(rounds=rounds,attempts=attempts,status="LOCAL_FIXED_POINT")
            proposed.append((f"a211-loss-{loss}",current,{}))
        native.binding.write_json(output/"convergence.json",convergence)
        for ext in (".png",".json"):
            (output/("scratch-trial"+ext)).unlink(missing_ok=True)
        for name, paths, dropped in proposed:
            if not paths:
                results[name] = dict(status="NO_ELIGIBLE_STROKES", dropped=dropped)
                continue
            assert all(p["colorRgb"] == rgb and p["width"] in (1, 2, 3) for p in paths)
            assert all(length_source(p, g["scale"]) > 20 for p in paths)
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
            print("A211 " + json.dumps({name: dict(strokes=measure["strokes"],
                source_length_total_px=measure["source_length_total_px"],
                source_length_mean_px=measure["source_length_mean_px"],
                vertices=measure["vertices"], simulation_meter=sim["used"], coverage_percent=audit["128"]["coverage_percent"],
                outside_ink_percent=audit["128"]["outside_ink_percent"])}, ensure_ascii=False), flush=True)
        from PIL import ImageDraw
        names=["a20-control","a21-loss-0.0","a21-loss-0.005","a211-loss-0.0","a211-loss-0.005"]
        grid=Image.new("RGB",(450*5,780),"white")
        draw=ImageDraw.Draw(grid)
        for i,name in enumerate(names):
            frame=Image.open(output/(name+".png")).convert("RGBA").crop((465,0,915,720))
            panel=Image.new("RGBA",frame.size,"white")
            panel.alpha_composite(frame)
            grid.paste(panel.convert("RGB"),(450*i,60))
            m=results[name]
            draw.text((450*i+10,8),name,fill="black")
            draw.text((450*i+10,25),f'Strokes {m["strokes"]} | vertices {m["vertices"]} | coverage {m["native"]["128"]["coverage_percent"]:.3f}%',fill="black")
        grid.save(output/"native-comparison-all-five.png")
    report = dict(schema="ENGINE001_S5_A211_V1", run=os.environ["GITHUB_RUN_ID"],
        sha=os.environ["GITHUB_SHA"], baseline_sha=REFERENCE_SHA,
        baseline_control_sha=BASE_SHA, baseline_control_run=BASE_RUN,
        source_archive_sha=SOURCE_SHA, source_archive_run=SOURCE_RUN,
        source=src["source"], source_sha256=src["source_sha256"],
        prepared_sha256=digest(source / "rtv-prepared.png"),
        target_sha256=digest(output / "dark-contour-only-target.png"),
        geometry=g, source_radius_px=2, dark_color=winner, ranked_dark_colors=ranked,
        dark_contour_source_pixels=int(mask.sum()), full_contour_source_pixels=int(radius_mask.sum()),
        width_variants=[1, 2, 3], smoothing=False,
        min_source_stroke_length_exclusive=20,
        per_stroke_10_percent_native_spill_gate="NOT_RUN; scene-level diagnostic only",
        renderer="real Egret 5.4.1 BoardPane/WebGLRenderer",
        comparison="Frozen A21 strict/soft; original A20 gates; whole stroke and vertex deletion to local fixed point",
        results=results, exact_CHALK="NOT_RUN", live_E4="NOT_RUN", E5="NOT_RUN",
        user_visual_review="PENDING")
    native.binding.write_json(output / "a211-results.json", report)
    lines = ["# A21 isolated dark contour / actual Egret", "",
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
    (output / "A211_RESULT_TABLE.md").write_text("\n".join(lines) + "\n", encoding="utf8")

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
