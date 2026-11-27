"""A29 frozen A27 contour endpoint graph experiment (E0 in second-lane results).
Model-only proposals; real Egret validates contour and unchanged fill tail.
"""
import argparse
from collections import defaultdict
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

ARMS = (("corridor-r3", 3, False), ("corridor-r6", 6, False),
        ("corridor-r12", 12, False), ("native-center-r20", 20, True))
SCALE = 150 / 414
EXPECTED = {
    "stage1-contour-plan.json.gz": "874629745c7f711589383dd6e3074ba0e3baf243625a3746129e630f1e740985",
    "stage3-small-plan.json.gz": "08fd735c86bb8403fe797f8bdbcceab344e6a2635bd4b4bed391211480be6bb8",
    "stage1-contour.png": "45db3037fc1652407d06d2929538fc442b41a3b7360c63623e8ead6347e59b64",
    "stage3-small.png": "55a807d38b63d2f4c15db4876a53a3c88875a8ee3597d074de90c38f2ae2c877",
    "full-target.png": "f639ef6ea1c2a4a72ba102305c13f87abb7654d9dfcb63f9047c636732e696d0",
    "projected-target.png": "52a8a241005afc974496d30bbdca334122b129c9eb97ae4eb0a6609ed23ec625",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb_value(color):
    return np.array([(color >> 16) & 255, (color >> 8) & 255, color & 255])


def stitch(group, allowed, radius, scale, minimum):
    """Greedy global shortest-edge forest. No cycles, one edge per endpoint."""
    xy = np.array([(v["x"], v["y"]) for p in group
                   for v in (p["points"][0], p["points"][-1])])
    edges = []
    for a, b in cKDTree(xy).query_pairs(radius * scale):
        if a // 2 == b // 2:
            continue
        distance = float(np.linalg.norm(xy[a] - xy[b]))
        t = np.linspace(0, 1, max(2, math.ceil(distance * 12) + 1))
        q = np.floor((xy[a] + (xy[b] - xy[a]) * t[:, None]) * 3).astype(int)
        if not ((q[:, 0] >= 0) & (q[:, 0] < allowed.shape[1]) &
                (q[:, 1] >= 0) & (q[:, 1] < allowed.shape[0])).all():
            continue
        if allowed[q[:, 1], q[:, 0]].mean() >= minimum:
            edges.append((distance, a, b))
    parent = list(range(len(group)))
    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i
    links = {}
    length = 0.
    for d, a, b in sorted(edges):
        if a in links or b in links or root(a // 2) == root(b // 2):
            continue
        parent[root(a // 2)] = root(b // 2)
        links[a], links[b] = b, a
        length += d
    components = defaultdict(list)
    for i in range(len(group)):
        components[root(i)].append(i)
    result, membership = [], []
    for ids in sorted(components.values(), key=min):
        ends = [2*i+s for i in ids for s in (0, 1) if 2*i+s not in links]
        assert len(ends) == 2
        entry = min(ends)
        points, members = [], []
        while True:
            i, side = divmod(entry, 2)
            members.append(i)
            original = group[i]["points"]
            oriented = original if side == 0 else original[::-1]
            points.extend(oriented[1:] if points and points[-1] == oriented[0] else oriented)
            exit_endpoint = entry ^ 1
            if exit_endpoint not in links:
                break
            entry = links[exit_endpoint]
        assert sorted(members) == ids
        result.append(dict(group[ids[0]], points=points))
        membership.append([group[i]["strokeId"] for i in members])
    assert len(group) - len(result) == len(links) // 2
    return result, membership, length


def build(paths, raw, projected, radius, strict):
    canvas = np.full((720, 1380, 3), 255, np.uint8)
    canvas[:, 465:915] = projected
    result, membership, length = [], [], 0.
    for (color, width), group in itertools.groupby(paths, key=lambda p: (p["colorRgb"], p["width"])):
        group = list(group)
        rgb = rgb_value(color)
        if strict:
            allowed = (raw[:, :, 3] > 24) & np.all(raw[:, :, :3] == rgb, axis=2)
        else:
            allowed = distance_transform_edt(~np.all(canvas == rgb, axis=2)) <= 3 * SCALE * 3
        pp, mm, ll = stitch(group, allowed, radius, SCALE, 1.0 if strict else .8)
        result.extend(pp)
        membership.extend(mm)
        length += ll
    assert sorted(x for m in membership for x in m) == sorted(p["strokeId"] for p in paths)
    assert len({p["strokeId"] for p in result}) == len(result)
    return result, membership, length


def contracts():
    def st(i, a, b):
        return dict(strokeId=str(i), width=1, colorRgb=0,
                    points=[dict(x=a, y=1), dict(x=b, y=1)])
    group = [st(0, 1, 3), st(1, 5, 4), st(2, 6, 8)]
    mask = np.ones((12, 30), bool)
    pp, mm, d = stitch(group, mask, 1.1, 1, 1)
    assert len(pp) == 1 and len(mm[0]) == 3 and d == 2
    assert [v["x"] for v in pp[0]["points"]] == [1, 3, 4, 5, 6, 8]
    mask[:, 10:15] = False
    pp, mm, d = stitch(group, mask, 1.1, 1, 1)
    assert len(pp) > 1
    cyc = [st(0, 1, 3), st(1, 3, 5), st(2, 5, 1)]
    pp, mm, d = stitch(cyc, np.ones_like(mask), 0, 1, 1)
    assert len(pp) == 1 and d == 0 and len(mm[0]) == 3
    print("A29 contracts PASS: reversal, blocked bridge, zero-distance cycle prevention")


def read_baseline(folder):
    for name, expected in EXPECTED.items():
        assert sha(folder / name) == expected, name
    report = json.loads((folder / "a27-results.json").read_text("utf8"))
    assert (report["sha"], str(report["run"]), report["contour"]) == (
        "f33791afe82dee25d88c8fc0aef521b27c550861", "45704720111", "joined")
    def load(name):
        with gzip.open(folder / name, "rt", encoding="utf8") as f:
            return json.load(f)
    contour = load("stage1-contour-plan.json.gz")
    full = load("stage3-small-plan.json.gz")
    assert len(contour) == 1164 and len(full) == 3270 and contour == full[:1164]
    assert sum(len(p["points"]) for p in contour) == 66416
    assert sum(len(p["points"]) for p in full) == 72128
    assert all(p["width"] == 1 for p in contour)
    assert len(set(p["strokeId"] for p in full)) == len(full)
    def img(name, mode):
        return np.array(Image.open(folder / name).convert(mode))
    raw, end = img("stage1-contour.png", "RGBA"), img("stage3-small.png", "RGBA")
    target, projected = img("full-target.png", "RGB"), img("projected-target.png", "RGB")
    assert target.shape == (483, 414, 3) and projected.shape == (720, 450, 3)
    return contour, full, raw, end, target, projected


def difference(candidate, reference):
    return dict(rgba_changed=int(np.any(candidate != reference, axis=2).sum()),
                rgb_changed=int(np.any(candidate[:, :, :3] != reference[:, :, :3], axis=2).sum()),
                **{f"{kind}_alpha{threshold}": int(((reference[:, :, 3] > threshold) &
                    (candidate[:, :, 3] <= threshold)).sum() if kind == "lost" else
                    ((candidate[:, :, 3] > threshold) & (reference[:, :, 3] <= threshold)).sum())
                   for threshold in (24, 127) for kind in ("lost", "gained")})


def main(folder, model_only=False):
    paths, full, old, final, target, projected = read_baseline(folder)
    candidates = []
    for name, radius, strict in ARMS:
        pp, members, ll = build(paths, old, projected, radius, strict)
        stats = dict(strokes=len(pp), full_strokes=len(pp) + len(full) - len(paths),
                     vertices=sum(len(p["points"]) for p in pp), added_logical_length=ll)
        print(name, stats, flush=True)
        candidates.append((name, pp, members, stats))
    if model_only:
        return
    import run_engine001_s5_wv_full_native as native
    import run_engine001_s5_originals_native_transfer as transfer
    out = Path(os.environ["RUNNER_TEMP"]) / "s5-a29"
    out.mkdir(exist_ok=False)
    native.OUT = out
    geometry = transfer.layout(414, 483)
    assert np.array_equal(transfer.projected(target, geometry)[0], projected)
    results = {}
    def save_plan(label, pp):
        f = out / (label + "-plan.json.gz")
        with gzip.open(f, "wt", encoding="utf8") as stream:
            json.dump(pp, stream, separators=(",", ":"))
        return sha(f)
    with native.binding.native.p4b7.native_egret_session(Path.cwd()) as driver:
        driver.set_script_timeout(480)
        assert not native.render(driver, "blank", [])[:, :, 3].any()
        line = [native.stroke(native.segment(200, 100, 12, 0), 4, 0, 0)]
        control = native.render(driver, "reference-original", line)
        js = native.full_fixture()
        a = js.index("function renderComplexHoldoutColorProbe(")
        b = js.index("const board = makeTemporalBoard(", a)
        guard = js[a:b]
        anchor = " ||\n          stroke.points.length > 128"
        assert guard.count(anchor) == 1
        driver.execute_script(js[:a] + guard.replace(anchor, "") + js[b:])
        assert np.array_equal(control, native.render(driver, "reference-expanded", line))
        assert np.array_equal(old, native.render(driver, "baseline-contour", paths))
        assert np.array_equal(final, native.render(driver, "baseline-full", full))
        base_score = transfer.score("baseline-full", final, target, geometry, out)[0]
        grid = Image.new("RGB", (450 * 5, 760 * 2), "white")
        draw = ImageDraw.Draw(grid)
        def panel(index, row, label, raw):
            img = Image.new("RGBA", (450, 720), "white")
            img.alpha_composite(Image.fromarray(raw[:, 465:915], "RGBA"))
            grid.paste(img.convert("RGB"), (450 * index, 760 * row + 40))
            draw.text((450 * index + 5, 760 * row + 5), label, fill="black")
        panel(0, 0, "A27 contour 1164", old)
        panel(0, 1, "A27 full 3270", final)
        for i, (name, pp, members, stats) in enumerate(candidates, 1):
            combined = pp + full[len(paths):]
            assert combined[len(pp):] == full[len(paths):]
            r = native.render(driver, name + "-contour", pp)
            f = native.render(driver, name + "-full", combined)
            diff1, diff2 = difference(r, old), difference(f, final)
            score = transfer.score(name + "-full", f, target, geometry, out)[0]
            equivalent = len(pp) < len(paths) and diff1["rgba_changed"] == diff2["rgba_changed"] == 0
            results[name] = dict(**stats, contour_diff=diff1, full_diff=diff2, full_score=score,
                quality="PIXEL_IDENTICAL" if equivalent else "VISUAL_REVIEW_REQUIRED",
                contour_plan_sha256=save_plan(name + "-contour", pp),
                full_plan_sha256=save_plan(name + "-full", combined),
                contour_png_sha256=sha(out / (name + "-contour.png")),
                full_png_sha256=sha(out / (name + "-full.png")), membership=members)
            panel(i, 0, f"{name}: {len(pp)} strokes", r)
            panel(i, 1, f"{name}: {len(combined)} strokes", f)
            print(name, json.dumps({k: v for k, v in results[name].items() if k != "membership"}), flush=True)
            native.binding.write_json(out / "a29-results.json", dict(schema="ENGINE001_S5_A29_V1",
                sha=os.environ["GITHUB_SHA"], run=os.environ["GITHUB_RUN_ID"], baseline=EXPECTED,
                baseline_score=base_score, results=results, smooth=False,
                exact_CHALK="NOT_RUN", live_E4="NOT_RUN", E5="NOT_RUN", human_visual_review="PENDING"))
        grid.save(out / "comparison.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--contracts", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--model-only", action="store_true")
    args = parser.parse_args()
    if args.contracts:
        contracts()
    else:
        if args.baseline is None:
            parser.error("--baseline required")
        main(args.baseline, args.model_only)
