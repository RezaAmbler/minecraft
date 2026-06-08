"""Small custom tree models for the deterministic scatter (oak/birch lowland, spruce highland).

Each `build(name, facing)` returns [(dx,dy,dz,block,props)] with dy=0 the first trunk log (placed
one above the grass). Leaves are persistent so they never decay. Pure + deterministic.
"""
from __future__ import annotations


def _rot(x, z, facing):
    if facing == "north":
        return (-x, -z)
    if facing == "east":
        return (z, -x)
    if facing == "west":
        return (-z, x)
    return (x, z)


def _tree(log, leaf, trunk_h, layers, facing):
    """layers = [(dy, radius), ...] leaf disks; the central column is overridden by trunk."""
    cells: dict = {}
    for dy, r in layers:
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if dx * dx + dz * dz <= r * r + 1:
                    cells[(dx, dy, dz)] = (leaf, {"persistent": "true", "distance": "1"})
    for y in range(trunk_h):
        cells[(0, y, 0)] = (log, {"axis": "y"})
    out = []
    for (x, y, z), (blk, props) in cells.items():
        rx, rz = _rot(x, z, facing)
        out.append((rx, y, rz, blk, props))
    return out


_SPECIES = {
    "oak_small":    ("oak_log", "oak_leaves", 4, [(3, 2), (4, 2), (5, 1)]),
    "oak_large":    ("oak_log", "oak_leaves", 6, [(4, 2), (5, 3), (6, 2), (7, 1)]),
    "birch_small":  ("birch_log", "birch_leaves", 5, [(4, 1), (5, 2), (6, 1)]),
    "birch_large":  ("birch_log", "birch_leaves", 6, [(5, 2), (6, 2), (7, 1)]),
    "spruce_small": ("spruce_log", "spruce_leaves", 3, [(2, 2), (3, 1), (4, 1), (5, 0)]),
    "spruce_large": ("spruce_log", "spruce_leaves", 4, [(3, 3), (4, 2), (5, 2), (6, 1), (7, 0)]),
}

NAMES = list(_SPECIES)


def build(name, facing="south"):
    log, leaf, trunk_h, layers = _SPECIES[name]
    return _tree(log, leaf, trunk_h, layers, facing)
