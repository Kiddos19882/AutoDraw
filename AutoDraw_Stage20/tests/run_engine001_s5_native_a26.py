"""A26 full multicolor contour reproduction of A16-A20. Same RTV04 R2, original route and parameter sweeps, light-to-dark, no zone fill, no A21 pruning. Native comparison only."""
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

def main(baseline, source, stage):
    import engine001_s5_native_brush_overlap as physical
    import run_engine001_s5_originals_native_transfer as transfer
    import run_engine001_s5_wv_full_native as native
    output = Path(os.environ["RUNNER_TEMP"]) / ("s5-a26-"+stage)
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
    colors=[c for c in np.unique(band.reshape(-1,3),axis=0) if np.any(c!=255)]
    colors.sort(key=lambda c:(-sum(int(v)*k for v,k in zip(c,(2126,7152,722))),tuple(map(int,c))))
    Image.fromarray(band).save(output/"all-colors-original-contour-band.png")
    Image.fromarray(prepared).save(output/"rtv04-prepared.png")
    with gzip.open(baseline / "r02-f4-plan.json.gz", "rt", encoding="utf8") as file:
        frozen = json.load(file)
    control = old["results"]["r02-f4"]
    assert digest(baseline / "r02-f4-plan.json.gz") == control["plan_sha256"]
    assert len(frozen) == control["strokes"]
    assert all(p["width"] == 1 and length_source(p, g["scale"]) > 5 + 1e-9 for p in frozen)
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
        from run_engine001_s5_native_a17 import join as unrestricted_join
        from run_engine001_s5_native_a19 import adaptive
        variants={}
        def add(name,paths):
            variants.setdefault(name,[]).extend(paths)
        add("a16-frozen-f4",frozen)
        for color in colors:
            rgb=int.from_bytes(bytes(color),"big")
            mask=np.all(band==color,axis=2)
            target=np.where(mask[:,:,None],color,255).astype(np.uint8)
            allowed=distance_transform_edt(~mask)<=3
            depth=distance_transform_edt(mask)
            for route in ROUTES:
                pp=(free.proposals if route.startswith("f") and route!="f" else routes.plan)(target,g,proof,route,native.stroke,native.segment)
                paths,_=normalize(pp,rgb,g["scale"],route)
                add("a16-route-"+route,paths)
                if route=="cfree":
                    for w in (2,3):add(f"a16-horizontal-w{w}",set_width(paths,width=w))
                    aug=[dict(p,_source_length=length_source(p,g["scale"])) for p in paths]
                    for mix in ("21","321"):add("a16-horizontal-mix-"+mix,set_width(aug,mixed=mix))
                if route=="f1": f1=paths
            for radius in (3,5,10,20):
                joined,_=normalize(unrestricted_join(f1,g["scale"],radius),rgb,g["scale"],"joined")
                add(f"a17-r{radius}-w1",joined)
                if radius==10:
                    for w in (2,3):add(f"a17-r{radius}-w{w}",set_width(joined,width=w))
            for radius in (20,30,40,50,75,100,150):
                joined,_=normalize(join(f1,g,radius,allowed),rgb,g["scale"],"joined")
                if radius<=50:
                    for eps in (0,.25,.5,1.0):
                        simple,_=normalize([simplify(p,g["scale"],eps) for p in joined],rgb,g["scale"],"simple") if eps else (joined,{})
                        for w in (1,2,3):add(f"a18-r{radius}-w{w}-e{eps}",set_width(simple,width=w))
                if radius==50:
                    for eps in (.5,1.0):
                        simple,_=normalize([simplify(p,g["scale"],eps) for p in joined],rgb,g["scale"],"simple")
                        for w in (1,2,3):add(f"a19-control-w{w}-e{eps}",set_width(simple,width=w))
                        for mode in ("whole","split"):
                            for t in (.6,.8):
                                mixed,_=normalize(adaptive(simple,g,depth,t,mode),rgb,g["scale"],"adaptive")
                                add(f"a19-{mode}-t{t}-e{eps}",mixed)
                if radius>=50:
                    for eps in (1.0,1.25,1.5,2.0):
                        simple,_=normalize([simplify(p,g["scale"],eps) for p in joined],rgb,g["scale"],"simple")
                        for w in (1,2,3):
                            wide=set_width(simple,width=w)
                            for minimum in (5,10,15,20):
                                add(f"a20-r{radius}-w{w}-e{eps}-l{minimum}",[p for p in wide if length_source(p,g["scale"])>minimum+1e-9])
        projected,_,_=transfer.projected(band,g)
        target_mask=np.any(projected!=255,axis=2)
        Image.fromarray(projected).save(output/"projected-target.png")
        combined={}
        from PIL import ImageDraw
        for name,paths in variants.items():
            if not name.startswith("a"+stage+"-"):continue
            paths=[dict(p,strokeId="icon-"+str(700000+i)) for i,p in enumerate(paths)]
            if not paths:
                combined[name]=dict(status="NO_ELIGIBLE_STROKES")
                continue
            assert all(p["width"] in (1,2,3) and length_source(p,g["scale"])>5 for p in paths)
            with gzip.open(output/(name+"-plan.json.gz"),"wt",encoding="utf8") as f:json.dump(paths,f)
            rgba=native.render(driver,name,paths)
            crop=rgba[:,465:915]
            correct=(crop[:,:,3]>=128)&np.all(crop[:,:,:3]==projected,axis=2)&target_mask
            combined[name]=dict(**metrics(paths,g),native=native_audit(rgba,target_mask),exact_rgb_core_percent=100*int(correct.sum())/int(target_mask.sum()),plan_sha256=digest(output/(name+"-plan.json.gz")),rgba_sha256=digest(output/(name+".png")))
            print("A26 "+name+" "+json.dumps(combined[name]),flush=True)
        # Native board crop, unchanged scale; paginate to avoid giant images.
        names=[n for n in combined if "strokes" in combined[n]]
        for start in range(0,len(names),12):
            subset=names[start:start+12]
            grid=Image.new("RGB",(450*4,760*((len(subset)+3)//4)),"white")
            draw=ImageDraw.Draw(grid)
            for i,name in enumerate(subset):
                frame=Image.open(output/(name+".png")).convert("RGBA").crop((465,0,915,720))
                panel=Image.new("RGBA",frame.size,"white");panel.alpha_composite(frame)
                xx=(i%4)*450;yy=(i//4)*760
                grid.paste(panel.convert("RGB"),(xx,yy+40))
                draw.text((xx+5,yy+5),name,fill="black")
            grid.save(output/f"comparison-{start//12:02d}.png")
    report=dict(schema="ENGINE001_S5_A26_V1",stage=stage,run=os.environ["GITHUB_RUN_ID"],sha=os.environ["GITHUB_SHA"],geometry=g,source_sha256=src["source_sha256"],source_radius_px=2,smoothing=False,widths=[1,2,3],min_source_length_exclusive=20,order="light to dark",white="excluded as existing contour background sentinel",results=results,combined=combined,exact_CHALK="NOT_RUN",live_E4="NOT_RUN",user_visual_review="PENDING")
    native.binding.write_json(output/"a26-results.json",report)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--stage",choices=("16","17","18","19","20"))
    args = parser.parse_args()
    if args.contracts:
        contracts()
    else:
        if args.baseline is None or args.source is None:
            parser.error("--baseline and --source required")
        main(args.baseline, args.source, args.stage)
