"""Rail phase — lay the park's coasters as rideable vanilla rail.

Each coaster route (config/rides.toml) is snapped to a 4-connected grid path; every cell's
rail `shape` is derived from its neighbours (straight / curve / ascending) by `rail.grid`, so
turns and grades actually connect and a minecart rolls the whole loop. Powered-rail boosters
land only on straights/climbs (never on curves). The ride (rides phase) is the player in a
real minecart on these rails, so the shapes here are load-bearing, not decorative (DECISIONS
LD1 / Sodor D16). Phase 1 lays The Dragon at Castle Hill.
"""
from __future__ import annotations

import logging
import time

from .. import mcio
from ..terrain.heightfield import build_heightfield
from . import coaster, grid

LOG = logging.getLogger("legoland.rail")
DIM = mcio.DIMENSION


def _terrain_y(hf, x, z):
    ix, iz = x - hf.x0, z - hf.z0
    if 0 <= ix < hf.nx and 0 <= iz < hf.nz:
        return int(hf.ground[iz, ix])
    return 64


def _shoulders(shape):
    """Off-path bed cells beside the rail (never the connected neighbours, so clearing them
    can't sever the line). Curves keep just an inside-corner floor (added in `_lay_track`)."""
    if shape in grid.CURVE_SHAPES:
        return []
    if shape in ("east_west", "ascending_east", "ascending_west"):
        return [(0, 1), (0, -1)]
    return [(1, 0), (-1, 0)]   # north_south / ascending_north|south


def _lay_track(ed, hf, cells):
    for c in cells:
        x, y, z = c.x, c.y, c.z
        # centre: support + rail (+ clear headroom for the train)
        ed.set(x, y - 1, z, "redstone_block" if c.powered else "polished_andesite")
        props = {"shape": c.shape}
        if c.powered:
            props["powered"] = "true"
        ed.set(x, y, z, c.rail_type, props)
        for dy in range(1, 4):
            ed.set(x, y + dy, z, "air")
        ty = _terrain_y(hf, x, z)
        for yy in range(y - 2, ty - 1, -1):
            ed.set(x, yy, z, "stone")     # support column / embankment down to ground
        # shoulders (3-wide bed) for straights/ascending
        for ox, oz in _shoulders(c.shape):
            sx, sz = x + ox, z + oz
            ed.set(sx, y - 1, sz, "polished_andesite")
            for dy in range(0, 4):
                ed.set(sx, y + dy, sz, "air")
            sty = _terrain_y(hf, sx, sz)
            for yy in range(y - 2, sty - 1, -1):
                ed.set(sx, yy, sz, "stone")
        # cutting: clear terrain above the bed (so a buried section becomes a tunnel/cutting)
        for yy in range(y + 4, ty + 3):
            ed.set(x, yy, z, "air")
        # curve: fill just the inside-corner floor (no air clearing -> can't sever the line)
        if c.shape in grid.CURVE_SHAPES:
            ox, oz = grid.curve_inside_offset(c.shape)
            ed.set(x + ox, y - 1, z + oz, "polished_andesite")


def run(ctx) -> None:
    hf = build_heightfield(ctx)
    rides = coaster.mvp_coasters(ctx.rides)
    if not rides:
        LOG.warning("no MVP coasters with a route in rides.toml — nothing to lay")
        return
    t0 = time.time()
    with mcio.open_level(ctx) as level:
        ed = mcio.WorldEditor(level, ctx)
        for ride in rides:
            plan = coaster.plan_coaster(hf, ride, ctx.transform)
            _lay_track(ed, hf, plan.cells)
            powered = sum(1 for c in plan.cells if c.powered)
            LOG.info("laid %s: %d cells (%d boosters), boarding cell #%d at %s",
                     plan.name, len(plan.cells), powered, plan.boarding_idx,
                     plan.cells[plan.boarding_idx].xz)
            level.save(); level.purge(); ed.invalidate_cache()
    LOG.info("rail complete in %.1fs", time.time() - t0)
