"""Binary mask skeletonization and skeleton graph tracing."""
from __future__ import annotations

import numpy as np


class SkeletonizationError(ValueError):
    """Raised when a mask or skeleton graph cannot be processed."""


def thin_binary_mask(mask: np.ndarray) -> np.ndarray:
    """Zhang-Suen parallel thinning, implemented without opencv-contrib."""
    image = (np.asarray(mask) > 0).astype(np.uint8)
    if image.ndim != 2:
        raise SkeletonizationError("Маска скелетонизации должна быть двумерной.")
    if min(image.shape) < 3:
        return image

    max_iterations = max(image.shape) + 1
    for _iteration in range(max_iterations):
        changed = False
        for phase in (0, 1):
            p2 = np.roll(image, 1, axis=0)
            p3 = np.roll(p2, -1, axis=1)
            p4 = np.roll(image, -1, axis=1)
            p5 = np.roll(np.roll(image, -1, axis=0), -1, axis=1)
            p6 = np.roll(image, -1, axis=0)
            p7 = np.roll(p6, 1, axis=1)
            p8 = np.roll(image, 1, axis=1)
            p9 = np.roll(p2, 1, axis=1)

            neighbor_count = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            ring = (p2, p3, p4, p5, p6, p7, p8, p9, p2)
            transitions = np.zeros(image.shape, dtype=np.uint8)
            for before, after in zip(ring, ring[1:]):
                transitions += ((before == 0) & (after == 1)).astype(np.uint8)

            candidate = (
                (image == 1)
                & (neighbor_count >= 2)
                & (neighbor_count <= 6)
                & (transitions == 1)
            )
            if phase == 0:
                candidate &= (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                candidate &= (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)

            # Rolling arrays wrap around; border pixels are never removed.
            candidate[0, :] = False
            candidate[-1, :] = False
            candidate[:, 0] = False
            candidate[:, -1] = False
            if bool(np.any(candidate)):
                image[candidate] = 0
                changed = True
        if not changed:
            break
    return image


def trace_skeleton_paths(skeleton: np.ndarray) -> list[tuple[list[tuple[float, float]], bool]]:
    """Trace every skeleton edge once; junctions terminate separate open paths."""
    skeleton = np.asarray(skeleton)
    if skeleton.ndim != 2:
        raise SkeletonizationError("Скелет должен быть двумерной матрицей.")
    ys, xs = np.where(skeleton > 0)
    nodes = {(int(x), int(y)) for x, y in zip(xs, ys)}
    if not nodes:
        return []

    adjacency: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for x, y in nodes:
        neighbors = []
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                other = (x + dx, y + dy)
                if other in nodes:
                    # Suppress a diagonal shortcut when an orthogonal pixel already
                    # connects this pair; it reduces false junctions in thick corners.
                    if dx and dy and ((x + dx, y) in nodes or (x, y + dy) in nodes):
                        continue
                    neighbors.append(other)
        adjacency[(x, y)] = sorted(neighbors, key=lambda p: (p[1], p[0]))

    def edge_key(a: tuple[int, int], b: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        return (a, b) if a <= b else (b, a)

    visited: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    paths: list[tuple[list[tuple[float, float]], bool]] = []

    # Isolated one-pixel components have no graph edges, but still represent a
    # drawable mark and must not disappear from a skeleton plan.
    isolated = sorted(
        (node for node in nodes if not adjacency[node]),
        key=lambda p: (p[1], p[0]),
    )
    paths.extend(([(float(x), float(y))], False) for x, y in isolated)

    starts = sorted(
        (node for node in nodes if len(adjacency[node]) != 2),
        key=lambda p: (p[1], p[0]),
    )
    for start in starts:
        for neighbor in adjacency[start]:
            key = edge_key(start, neighbor)
            if key in visited:
                continue
            visited.add(key)
            path = [start, neighbor]
            previous, current = start, neighbor
            while len(adjacency[current]) == 2:
                candidates = [node for node in adjacency[current] if node != previous]
                if not candidates:
                    break
                nxt = candidates[0]
                next_key = edge_key(current, nxt)
                if next_key in visited:
                    break
                visited.add(next_key)
                path.append(nxt)
                previous, current = current, nxt
            paths.append(([(float(x), float(y)) for x, y in path], False))

    # Pure loops contain no endpoint or junction; walk each remaining cycle once.
    for start in sorted(nodes, key=lambda p: (p[1], p[0])):
        for neighbor in adjacency[start]:
            key = edge_key(start, neighbor)
            if key in visited:
                continue
            visited.add(key)
            path = [start, neighbor]
            previous, current = start, neighbor
            while True:
                candidates = [node for node in adjacency[current] if node != previous]
                if not candidates:
                    break
                nxt = candidates[0]
                next_key = edge_key(current, nxt)
                if next_key in visited:
                    break
                visited.add(next_key)
                path.append(nxt)
                previous, current = current, nxt
                if current == start:
                    break
            is_closed = len(path) >= 4 and path[-1] == path[0]
            if is_closed:
                path.pop()
            paths.append(([(float(x), float(y)) for x, y in path], is_closed))
    return paths


