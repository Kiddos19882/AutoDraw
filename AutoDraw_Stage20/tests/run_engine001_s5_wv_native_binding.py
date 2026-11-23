"""S5 bench binding of fresh eight-color wV source owners to native BoardPane ink."""
import gzip
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
import run_engine001_s5_uncapped as pipeline
import run_engine001_s5_lane_p2_native_turns as native

ROOT = Path("AutoDraw_Stage20")
OUT = Path(os.environ["RUNNER_TEMP"]) / "wv-native-binding"
PIN = "76d950e0a8911888a9df3b675b866519ecf7bba4"


def board_point(x, y):
    return {"x": 155 + .75 * (x + .5), "y": .75 * (y + .5)}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf8")


def run():
    OUT.mkdir()
    source = OUT / "source"
    pipeline.run(ROOT, pipeline.reference.original.dev.SOURCES[0], source, second_lane_audit=True)
    results = json.loads((source / "results.json").read_bytes())
    assert results["plan_sha256"] == "2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3"
    with gzip.open(source / "plan.json.gz") as f:
        strokes = json.load(f)["proposals"]
    with np.load(source / "zones.npz") as archive:
        owners = archive["paintable_id"]
    assert owners.shape == (320, 200)
    prepared = np.asarray(Image.open(source / "02-prepared.png"))
    native_js = ROOT / "tests/game_renderer_reference.js"
    pinned = os_pinned_source(native_js)
    # Only relax the test adapter's minimum sample count for the singleton probe.
    # The engine, redraw method and original API used for controls stay pinned.
    guard = "stroke.points.length < 2 ||"
    start = pinned.index("function renderComplexHoldoutColorProbe(")
    end = pinned.index("const board = makeTemporalBoard(", start)
    assert pinned[start:end].count(guard) == 1
    fixture = pinned[:start] + pinned[start:end].replace(guard, "stroke.points.length < 1 ||") + pinned[end:]
    native_dir = OUT / "native"
    native_dir.mkdir()
    shapes = {}
    for i, stroke in enumerate(strokes):
        points = stroke["points"]
        if stroke["color_index"] == 6:
            continue
        kind = "point" if len(points) == 1 else "line" if len(points) == 2 else "turn"
        if kind not in shapes:
            shapes[kind] = (i, stroke)
    assert set(shapes) == {"point", "turn", "line"}
    yy, xx = np.indices((720, 1380))
    sx = np.floor(((xx+.5)/3-155)/.75).astype(int)
    sy = np.floor((yy+.5)/3/.75).astype(int)
    board_owners = np.zeros_like(sx)
    within = (sx >= 0) & (sx < 200) & (sy >= 0) & (sy < 320)
    board_owners[within] = owners[sy[within],sx[within]]
    report = dict(sha=os.environ["GITHUB_SHA"], run=os.environ["GITHUB_RUN_ID"],
                  plan=results["plan_sha256"], fixture_blob=PIN, cases={})
    with native.p4b7.native_egret_session(Path.cwd()) as driver:
        def capture(key, paths):
            response = driver.execute_script(native.CMD, paths)
            rgba, meta = native.read_webgl_result(response, native_dir, key)
            assert meta["renderer"] == "real Egret 5.4.1 BoardPane/WebGLRenderer"
            assert meta["sceneDiagnostics"]["stageAttached"] and rgba.shape == native.SHAPE
            if paths:
                assert meta["mode"] == "normal" and meta["syntheticAcceptedVerticesNotChalk"] == sum(len(s["points"]) for s in paths)
            write_json(native_dir / (key+".json"), dict(meta=meta, paths=paths))
            return rgba

        assert not capture("blank", [])[:,:,3].any()
        for width in range(1,11):
            x, y = 24+13*width, 17+20*width
            pts = [board_point(x, y), board_point(x+20, y)]
            path = dict(strokeId="icon-0", width=width, points=pts, colorRgb=0x503d35)
            rgba = capture(f"width-{width:02d}", [path])
            ink = rgba[:,:,3] >= 128
            center_x = int(3*(pts[0]["x"]+pts[1]["x"])/2)
            rows = np.flatnonzero(ink[:,center_x])
            assert len(rows) > 0
            iy, ix = np.nonzero(ink)
            observed = [float((ix.min()+ix.max()+1)/6), float((iy.min()+iy.max()+1)/6)]
            expected = [(pts[0]["x"]+pts[1]["x"])/2,pts[0]["y"]]
            report["cases"][f"width-{width:02d}"] = dict(thickness_backing_px=len(rows),
                center_error_board_px=max(abs(a-b) for a,b in zip(observed,expected)))
            if width == 1:
                control, original = path, rgba
        driver.execute_script(fixture)
        assert np.array_equal(original, capture("adapter-control", [control]))
        for kind, (index, stroke) in shapes.items():
            pts = stroke["points"]
            x,y = map(int, pts[0])
            owner = stroke["paintable_id"]
            assert all(owners[int(py),int(px)] == owner for px,py in pts)
            rgb = int.from_bytes(bytes(prepared[y,x]), "big")
            path = dict(strokeId="icon-0", width=stroke["brush_value"], colorRgb=rgb,
                        points=[board_point(px,py) for px,py in pts])
            rgba = capture(kind, [path])
            ink = rgba[:,:,3] >= 128
            report["cases"][kind] = dict(source_stroke=index, owner=owner,
                width=path["width"], points=len(pts), alpha_nonzero=int((rgba[:,:,3]>0).sum()),
                alpha128=int(ink.sum()), outside_owner=int((ink & (board_owners!=owner)).sum()))
    write_json(OUT / "report.json", report)
    print("::notice title=wV native results::"+json.dumps(report["cases"],separators=(",",":")))


def os_pinned_source(path):
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    digest = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    assert digest == PIN
    return raw.decode("utf8")


if __name__ == "__main__":
    run()
