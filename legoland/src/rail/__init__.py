"""Phase 3 — Rail network (rideable).

Lays a 3-wide track bed (gravel) with rails + powered-rail boosters along the main loop and
both branches. Unlike the first pass, the geometry is genuinely vanilla-rideable: routes are
snapped to a 4-connected grid path and every cell's rail `shape` is derived from its immediate
neighbours (straight / curve / ascending) by `rail.grid`, so turns and grades actually connect
and a minecart can roll the whole loop. Branch junctions are lever-operated redstone switches
(`rail.switches`). A non-destructive stone apron marks the Tidmouth turntable beside the loop.
The engine ride (Phase 5) is the player in a real minecart on these rails — so the shapes here
must be correct, they are not decorative (see DECISIONS D16).
"""
from __future__ import annotations

import logging
import time

from .. import mcio
from ..terrain.heightfield import build_heightfield
from . import grid, route, switches

LOG = logging.getLogger("sodor.rail")
DIM = mcio.DIMENSION


def _terrain_y(hf, x, z):
    xi, zi = x - hf.west, z - hf.north
    if 0 <= xi < hf.size and 0 <= zi < hf.size and hf.land[zi, xi]:
        return int(hf.height[zi, xi])
    return hf.sea_level


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
        # centre: support + rail (+ clear headroom)
        ed.set(x, y - 1, z, "redstone_block" if c.powered else "gravel")
        props = {"shape": c.shape}
        if c.powered:
            props["powered"] = "true"
        ed.set(x, y, z, c.rail_type, props)
        for dy in range(1, 4):
            ed.set(x, y + dy, z, "air")
        ty = _terrain_y(hf, x, z)
        for yy in range(y - 2, ty - 1, -1):
            ed.set(x, yy, z, "stone")     # embankment over low ground
        # shoulders (3-wide bed) for straights/ascending
        for ox, oz in _shoulders(c.shape):
            sx, sz = x + ox, z + oz
            ed.set(sx, y - 1, sz, "gravel")
            for dy in range(0, 4):
                ed.set(sx, y + dy, sz, "air")
            sty = _terrain_y(hf, sx, sz)
            for yy in range(y - 2, sty - 1, -1):
                ed.set(sx, yy, sz, "stone")
        # cutting: clear terrain above the bed
        for yy in range(y + 4, ty + 3):
            ed.set(x, yy, z, "air")
        # curve: fill just the inside-corner floor (no air clearing -> can't sever the line)
        if c.shape in grid.CURVE_SHAPES:
            ox, oz = grid.curve_inside_offset(c.shape)
            ed.set(x + ox, y - 1, z + oz, "gravel")


def _turntable(ed, hf, x, z, y):
    """A stone apron marking the Tidmouth turntable, laid AROUND the running line (skips any
    cell already holding rail) so it never severs the loop. Rotation is a backlog item."""
    r = 5
    for dx in range(-r, r + 1):
        for dz in range(-r, r + 1):
            if dx * dx + dz * dz > r * r:
                continue
            bx, bz = x + dx, z + dz
            if "rail" in ed.name_at(bx, y, bz):
                continue                      # leave the loop rail (and its boosters) intact
            rim = dx * dx + dz * dz > (r - 1) * (r - 1)
            ed.set(bx, y - 1, bz, "stone_bricks" if rim else "smooth_stone")
            for dy in range(0, 4):
                ed.set(bx, y + dy, bz, "air")
    if "rail" not in ed.name_at(x, y, z):
        ed.set(x, y - 1, z, "iron_block")     # centre pivot marker
    LOG.info("turntable apron at (%d,%d) y=%d", x, z, y)


def run(ctx) -> None:
    hf = build_heightfield(ctx)
    t0 = time.time()
    net = grid.plan_network(hf, ctx.layout)

    with mcio.open_level(ctx) as level:
        ed = mcio.WorldEditor(level, ctx)

        _lay_track(ed, hf, net["main"])
        LOG.info("laid main loop: %d cells", len(net["main"]))
        level.save(); level.purge(); ed.invalidate_cache()

        for name, cells in net["branches"].items():
            _lay_track(ed, hf, cells[3:])     # first 3 cells are owned by the junction switch
            LOG.info("laid %s branch: %d cells", name, len(cells))
            level.save(); level.purge(); ed.invalidate_cache()

        for name, idx in net["jidx"].items():
            switches.stamp_junction(ed, name, net["main"][idx].y)
            LOG.info("lever switch stamped at %s junction", name)

        tx, tz = route.stations()["tidmouth"]
        ty = min(net["main"], key=lambda c: (c.x - tx) ** 2 + (c.z - tz) ** 2).y
        _turntable(ed, hf, tx, tz, ty)
        level.save()

    LOG.info("Phase 3 rail complete in %.1fs", time.time() - t0)
