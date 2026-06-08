"""Shared rail elevation profiling: turn a 4-connected (x,z) grid path into a Y profile.

Used by BOTH the rail-bed laying (Phase 3) and the engine ride system (Phase 5) so the
engine follows exactly where the track is. The profile is corner-aware: cells flagged in
`flat_idx` (curves + junctions) are forced flat with their immediate neighbours, every step
is slope-limited to <=1 block, and single-cell valleys are removed — together these are the
preconditions that let `grid.cell_shape` emit valid curve/ascending rail (a curve cannot
ascend; an ascending cell cannot sit at the bottom of a one-cell dip).
"""
from __future__ import annotations


def _terrain_y(hf, x: int, z: int) -> int:
    xi, zi = x - hf.west, z - hf.north
    if 0 <= xi < hf.size and 0 <= zi < hf.size and hf.land[zi, xi]:
        return int(hf.height[zi, xi])
    return hf.sea_level + 1  # over water/off-map -> causeway just above sea


def _nbr_idx(n: int, i: int, closed: bool):
    """(prev, next) indices for cell i — wrap if closed, else None at the open ends."""
    if closed:
        return (i - 1) % n, (i + 1) % n
    return (i - 1 if i > 0 else None), (i + 1 if i < n - 1 else None)


def _slope_limit(ys: list[int], closed: bool) -> bool:
    """Clamp every connected step to <=1 block (forward then backward). Returns changed?"""
    n = len(ys)
    changed = False
    order = list(range(1, n)) + ([0] if closed else [])
    for i in order:
        p = i - 1 if i > 0 else n - 1
        d = ys[i] - ys[p]
        if d > 1:
            ys[i] = ys[p] + 1; changed = True
        elif d < -1:
            ys[i] = ys[p] - 1; changed = True
    order = list(range(n - 2, -1, -1)) + ([n - 1] if closed else [])
    for i in order:
        nx = i + 1 if i < n - 1 else 0
        d = ys[i] - ys[nx]
        if d > 1:
            ys[i] = ys[nx] + 1; changed = True
        elif d < -1:
            ys[i] = ys[nx] - 1; changed = True
    return changed


def _fix_valleys(ys: list[int], closed: bool) -> bool:
    """Raise any single-cell strict minimum (a width-1 valley) — an ascending rail cannot
    sit there (it would have to climb toward both neighbours). Returns changed?"""
    n = len(ys)
    changed = False
    for i in range(n):
        p, nx = _nbr_idx(n, i, closed)
        if p is None or nx is None:
            continue
        if ys[i] < ys[p] and ys[i] < ys[nx]:
            ys[i] = min(ys[p], ys[nx]); changed = True
    return changed


def compute_profile(hf, path, flat_idx=frozenset(), closed: bool = False,
                    window: int = 24, anchors: dict | None = None) -> list[int]:
    """Smooth + slope-limit the rail height; flatten `flat_idx` neighbourhoods; de-valley.

    `anchors` pins specific cell indices to a fixed Y (used to tie a branch's first cells to
    the main-line junction height so the tee connects level). Post-conditions (asserted):
    anchors hold, every flagged cell is flat with its neighbours, every step is <=1 block,
    and no cell is a width-1 valley. Raises AssertionError (with the offending index) if the
    gentle-terrain fixed point is not reached — a loud build failure beats a silently broken
    slope in-game.
    """
    n = len(path)
    if n == 0:
        return []
    anchors = anchors or {}
    base = [max(_terrain_y(hf, x, z), hf.sea_level + 2) for x, z in path]

    # moving-average smoothing (wrap on a closed loop)
    sm = []
    for i in range(n):
        if closed:
            vals = [base[(i + d) % n] for d in range(-window, window + 1)]
        else:
            lo, hi = max(0, i - window), min(n, i + window + 1)
            vals = base[lo:hi]
        sm.append(sum(vals) / len(vals))
    ys = [int(round(v)) for v in sm]
    for idx, val in anchors.items():
        ys[idx] = val

    for _ in range(200):
        changed = _slope_limit(ys, closed)
        for i in flat_idx:
            p, nx = _nbr_idx(n, i, closed)
            for j in (p, i, nx):
                if j is not None and ys[j] != ys[i]:
                    ys[j] = ys[i]; changed = True
        changed |= _fix_valleys(ys, closed)
        for idx, val in anchors.items():
            if ys[idx] != val:
                ys[idx] = val; changed = True
        if not changed:
            break

    # post-conditions
    for idx, val in anchors.items():
        if ys[idx] != val:
            raise AssertionError(f"rail Y anchor not held at cell {idx} {path[idx]}")
    for i in range(n):
        p, nx = _nbr_idx(n, i, closed)
        if p is not None and abs(ys[i] - ys[p]) > 1:
            raise AssertionError(f"rail Y step >1 at cell {i} {path[i]} ({ys[p]}->{ys[i]})")
    for i in flat_idx:
        p, nx = _nbr_idx(n, i, closed)
        for j in (p, nx):
            if j is not None and ys[j] != ys[i]:
                raise AssertionError(f"flat/corner cell {i} {path[i]} not level with neighbour")
    return ys


def line_path_xyz(hf, xz_path, flat_idx=frozenset(), closed: bool = False):
    """Convenience: the (x, y, z) path (no rail shapes) — used for the engine board point."""
    ys = compute_profile(hf, xz_path, flat_idx, closed)
    return [(x, ys[i], z) for i, (x, z) in enumerate(xz_path)]
