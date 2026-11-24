"""A6-Z1 research-only region consolidation on the current original and fresh swatches."""
from __future__ import annotations

from collections import Counter
import numpy as np
from skimage.color import rgb2lab
from engine001_bpred_s4r1_rag3_hierarchy import _connected, _lab_means, _boundary_stats
from engine001_bpred_s4r1_dg1_source_detail_atoms import _protected_original_dots

PRESETS = {"balanced": (12., 8., .25, 36., 100.),
           "strong": (24., 14., .50, 60., 300.)}
WHITE = np.array([255, 255, 255], np.uint8)


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def zone_labels(target):
    palette, inverse = np.unique(target.reshape(-1, 3), axis=0, return_inverse=True)
    index = inverse.reshape(target.shape[:2])
    fg = np.any(target != WHITE, axis=2)
    ids = _connected(np.where(fg, index + 1, 0))
    return palette, index, fg, ids


def region_counts(target):
    palette, index, fg, ids = zone_labels(target)
    n = int(ids.max())
    area = np.bincount(ids[fg], minlength=n + 1)
    owner = np.zeros(n + 1, np.int32)
    owner[ids[fg]] = index[fg]
    result = {}
    for k, rgb in enumerate(palette):
        if np.all(rgb == WHITE):
            continue
        sizes = area[1:][owner[1:] == k]
        result["#" + bytes(rgb).hex().upper()] = dict(
            zones=int(len(sizes)), pixels=int(sizes.sum()),
            singleton=int((sizes == 1).sum()), le4=int((sizes <= 4).sum()),
            le16=int((sizes <= 16).sum()), largest=int(sizes.max()) if len(sizes) else 0)
    return dict(zones=n, pixels=int(fg.sum()), colors=result,
                singleton=int((area[1:] == 1).sum()),
                le4=int((area[1:] <= 4).sum()), le16=int((area[1:] <= 16).sum())), ids


def quality(original, target):
    opaque = original[..., 3] == 255
    fg = np.any(target != WHITE, axis=2)
    lab = rgb2lab(original[..., :3])
    tlab = rgb2lab(target)
    total = kept = 0
    for a, b, ta, tb, u, v in (
        (lab[:, :-1], lab[:, 1:], tlab[:, :-1], tlab[:, 1:], opaque[:, :-1], opaque[:, 1:]),
        (lab[:-1], lab[1:], tlab[:-1], tlab[1:], opaque[:-1], opaque[1:])):
        strong = u & v & (np.linalg.norm(a-b, axis=2) >= 12.)
        total += int(strong.sum())
        kept += int((strong & (np.linalg.norm(ta-tb, axis=2) >= 12.)).sum())
    rgb_err = np.abs(original[..., :3].astype(np.int16)-target.astype(np.int16))
    d = np.linalg.norm(lab-tlab, axis=2)
    return dict(original_strong_edges=total, retained_strong_edges=kept,
                retained_fraction=kept/total if total else None,
                opaque_rgb_mae=float(rgb_err[opaque].mean()) if opaque.any() else None,
                foreground_mean_lab=float(d[fg].mean()) if fg.any() else None,
                foreground_mean_squared_lab=float(np.square(d[fg]).mean()) if fg.any() else None)


def consolidate(original, target, preset):
    require(preset in PRESETS, "unknown preset")
    require(original.ndim == 3 and original.shape[2] == 4 and original.dtype == np.uint8
            and target.shape == (*original.shape[:2], 3) and target.dtype == np.uint8
            and min(target.shape[:2]) > 0, "invalid source/target")
    max_mean, max_border, max_strong, max_swatch, max_loss = PRESETS[preset]
    palette, index, fg, ids = zone_labels(target)
    require(not np.any(fg & (original[..., 3] != 255)), "foreground alpha mismatch")
    lab = rgb2lab(original[..., :3])
    swatches = rgb2lab(palette.reshape(1, -1, 3)).reshape(-1, 3)
    protected = _protected_original_dots(lab, original[..., 3] == 255) & fg
    initial_cost = np.square(lab - swatches[index]).sum(axis=2)
    before, before_ids = region_counts(target)
    ledger = []
    while True:
        n = int(ids.max())
        counts, _, means = _lab_means(ids, lab)
        owner = np.zeros(n + 1, np.int32)
        owner[ids[fg]] = index[fg]
        blocked = np.bincount(ids[protected], minlength=n + 1) > 0
        base_sum = np.bincount(ids[fg], weights=initial_cost[fg], minlength=n+1)
        square_sum = np.bincount(ids[fg], weights=np.square(lab[fg]).sum(axis=1),
                                 minlength=n+1)
        pairs, lengths, border, strong = _boundary_stats(ids, lab)
        candidates = []
        for (u, v), length, distance, fraction in zip(pairs, lengths, border, strong):
            u, v = int(u), int(v)
            if (distance > max_border or fraction > max_strong
                    or np.linalg.norm(means[u]-means[v]) > max_mean
                    or np.linalg.norm(swatches[owner[u]]-swatches[owner[v]]) > max_swatch):
                continue
            for src, dst in ((u, v), (v, u)):
                if blocked[src] or owner[src] == owner[dst]:
                    continue
                new, old = swatches[owner[dst]], swatches[owner[src]]
                new_cost = square_sum[src] + counts[src] * (
                    np.dot(new, new) - 2*np.dot(means[src], new))
                old_cost = square_sum[src] + counts[src] * (
                    np.dot(old, old) - 2*np.dot(means[src], old))
                loss = float((new_cost-base_sum[src])/counts[src])
                if loss <= max_loss:
                    candidates.append((float(new_cost-old_cost), -int(length), src, dst,
                                       float(distance), float(fraction), loss))
        if not candidates:
            break
        # Disjoint region pairs guarantee each chosen source attaches to a
        # destination that does not change in this sweep. No new disjoint zones.
        remap = owner.copy()
        touched = set()
        merges = []
        for cost, length, src, dst, distance, fraction, loss in sorted(candidates):
            if src in touched or dst in touched:
                continue
            touched.update((src, dst))
            remap[src] = owner[dst]
            merges.append(dict(source=src, destination=dst, pixels=int(counts[src]),
                from_color=bytes(palette[owner[src]]).hex(), to_color=bytes(palette[owner[dst]]).hex(),
                cost_delta=cost, boundary_edges=-length, boundary_mean=distance,
                strong_fraction=fraction, baseline_mean_squared_lab_increase=loss))
        require(bool(merges), "nonprogressing candidate selection")
        index = np.where(fg, remap[ids], index)
        ids = _connected(np.where(fg, index+1, 0))
        require(int(ids.max()) <= n-len(merges), "region count did not decrease")
        ledger.append(dict(before=n, after=int(ids.max()), merges=merges))
    output = palette[index]
    require(np.array_equal(np.any(output != WHITE, axis=2), fg), "foreground changed")
    require(np.array_equal(output[protected], target[protected]), "protected dot changed")
    after, after_ids = region_counts(output)
    report = dict(preset=preset, thresholds=list(PRESETS[preset]), before=before, after=after,
        protected_dots=int(protected.sum()), changed_pixels=int(np.any(output != target, axis=2).sum()),
        sweeps=len(ledger), merges=sum(len(s["merges"]) for s in ledger),
        quality_before=quality(original, target), quality_after=quality(original, output))
    return output, before_ids, after_ids, protected, report, ledger
