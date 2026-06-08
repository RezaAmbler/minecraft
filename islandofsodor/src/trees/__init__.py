"""Phase: deterministic scattered trees (lush English-countryside scatter).

Runs AFTER rail (so the exclusion mask can use the laid corridor) and writes small custom tree
models onto plantable grass only. Placement is a SEEDED jittered grid — a single
`np.random.default_rng(seed)` consumed in fixed order — so every rebuild produces the identical
forest (byte-reproducible). Exclusions: non-grass (sand/rock/snow/water), the rail corridor +
an overhang ring (no leaves over the track), switch cells, station/dock footprints, and the
spawn statue/welcome plaza.
"""
from __future__ import annotations

import logging
import time

import numpy as np

from .. import mcio
from ..rail import grid, route, switches
from ..terrain.heightfield import build_heightfield, GRASS
from . import species

LOG = logging.getLogger("sodor.trees")

_RAIL_CLEAR = 4   # keep tree leaves this far from any rail cell (no overhang)


def _exclusion(ctx, hf) -> set:
    net = grid.plan_network(hf, ctx.layout)
    forb: set = set()

    def dilate(cx, cz, r):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                forb.add((cx + dx, cz + dz))

    for c in net["main"]:
        dilate(c.x, c.z, _RAIL_CLEAR)
    for b in net["branches"].values():
        for c in b:
            dilate(c.x, c.z, _RAIL_CLEAR)
    for name in switches.JUNCTIONS:
        for sx, sz in switches.exit_cells(name).values():
            dilate(sx, sz, _RAIL_CLEAR)
    mvp = {loc["key"] for loc in ctx.layout.get("locations", []) if loc.get("mvp")}
    for key, (x, z, axis) in route.station_info().items():
        if key in mvp:
            dilate(x, z, 20 if key == "brendam_docks" else 16)
    sp = ctx.layout["world"]["spawn"]
    dilate(int(sp["x"]), int(sp["z"]) - 18, 14)   # statue + welcome plaza north of spawn
    return forb


def _sample(ctx, hf, forb):
    """Seeded jittered-grid scatter -> list of (x, z, y, species_name, facing)."""
    cfg = ctx.layout.get("trees", {})
    step = int(cfg.get("grid_step", 7))
    keep = float(cfg.get("keep", 0.5))
    jit = int(cfg.get("jitter", 2))
    spruce_min = int(cfg.get("spruce_min_y", 84))
    rng = np.random.default_rng(int(cfg.get("seed", ctx.layout["world"]["seed"])))
    rock_y = 104  # heightfield ROCK_Y — no trees on bare stone/snow (already excluded by surf)

    trees = []
    n = hf.size // step
    half = step // 2
    for gi in range(n):
        for gj in range(n):
            r_keep = rng.random()
            jx = int(rng.integers(-jit, jit + 1))
            jz = int(rng.integers(-jit, jit + 1))
            r_sp = rng.random()
            r_size = rng.random()
            r_face = int(rng.integers(0, 4))
            if r_keep > keep:
                continue
            xi = gi * step + half + jx
            zi = gj * step + half + jz
            if not (0 <= xi < hf.size and 0 <= zi < hf.size):
                continue
            if not (hf.land[zi, xi] and hf.surf[zi, xi] == GRASS):
                continue
            x, z = hf.west + xi, hf.north + zi
            if (x, z) in forb:
                continue
            h = int(hf.height[zi, xi])
            if h >= rock_y:
                continue
            sp = "spruce" if h >= spruce_min else ("oak" if r_sp < 0.6 else "birch")
            size = "large" if r_size < 0.5 else "small"
            face = ("south", "north", "east", "west")[r_face]
            trees.append((x, z, h, f"{sp}_{size}", face))
    return trees


def plan(ctx):
    """Deterministic tree list (used by both the writer and the validator)."""
    hf = build_heightfield(ctx)
    return _sample(ctx, hf, _exclusion(ctx, hf))


def run(ctx) -> None:
    t0 = time.time()
    trees = plan(ctx)
    LOG.info("scattering %d trees…", len(trees))
    with mcio.open_level(ctx) as level:
        ed = mcio.WorldEditor(level, ctx)
        for i, (x, z, h, name, face) in enumerate(trees):
            base = h + 1
            if "rail" in ed.name_at(x, base, z):   # belt-and-suspenders: never bury rail
                continue
            for dx, dy, dz, blk, props in species.build(name, face):
                ed.set(x + dx, base + dy, z + dz, blk, props)
            if (i + 1) % 400 == 0:
                level.save(); level.purge(); ed.invalidate_cache()
        level.save()
    LOG.info("Phase trees complete: %d trees in %.1fs", len(trees), time.time() - t0)
