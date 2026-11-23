"""Per-image selection of authentic game swatches for the S5 source model."""
import numpy as np
from scipy.spatial.distance import cdist
from skimage.color import rgb2lab

from engine001_bpred_s4r1_rag3_hierarchy import _connected

SIZES = (5, 8, 10)
DEFAULT_SIZE = 8


def select_swatches(game, palette):
    """Minimize frequency-weighted squared Lab error with the dominant color fixed."""
    indices, counts = np.unique(game[game >= 0], return_counts=True)
    rgb = np.asarray(palette, dtype=np.uint8)[indices]
    colors, first, inverse = np.unique(rgb, axis=0, return_index=True, return_inverse=True)
    counts = np.bincount(inverse.ravel(), weights=counts, minlength=len(colors))
    distances = cdist(rgb2lab(colors), rgb2lab(colors), metric="sqeuclidean") if len(colors) else None
    variants = {}
    for size in SIZES:
        if len(colors) <= size:
            selected = list(range(len(colors)))
        else:
            selected = [int(counts.argmax())]

            def error(group):
                return distances[:, group].min(axis=1) @ counts

            while len(selected) < size:
                choices = (i for i in range(len(colors)) if i not in selected)
                selected.append(min(choices, key=lambda i: error(selected + [i])))
            while True:
                best = selected
                score = error(selected)
                for slot in range(1, size):
                    for i in range(len(colors)):
                        if i in selected:
                            continue
                        group = selected.copy()
                        group[slot] = i
                        cost = error(group)
                        if cost < score - 1e-8:
                            best, score = group, cost
                if best is selected:
                    break
                selected = best
        reduced = np.full_like(game, -1)
        if len(colors):
            chosen = indices[first[selected]]
            mapping = np.zeros(len(palette), dtype=game.dtype)
            mapping[indices] = chosen[distances[:, selected].argmin(axis=1)[inverse.ravel()]]
            visible = game >= 0
            reduced[visible] = mapping[game[visible]]
        variants[size] = reduced
    return variants


def paintable_regions(surface, game):
    visible = game >= 0
    labels = np.zeros(game.shape, np.int64)
    labels[visible] = surface[visible].astype(np.int64) * 128 + game[visible] + 1
    return _connected(labels)
