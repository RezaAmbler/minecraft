"""Structures phase — build Castle Hill's structures BEFORE the rail is laid.

Phase 1 places the medieval castle (so The Dragon coaster tunnels through it — the indoor
dark-ride section), a static dragon show-scene beside the track, and the coaster station at
the boarding point. Structures run before rail so the rail layer carves its corridor last and
the line is never buried (DECISIONS LD1 / Sodor D16). Block models come from `castle.py`.
"""
from __future__ import annotations

import logging
import time

from .. import mcio
from ..rail import coaster
from ..terrain.heightfield import build_heightfield, ground_at
from . import castle

LOG = logging.getLogger("legoland.structures")


def _flatten(ed, x0, x1, z0, z1, top_y, clear=22, found=6):
    """Grass pad at top_y with a stone foundation below and headroom cleared above."""
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            ed.set(x, top_y, z, "grass_block", {"snowy": "false"})
            for yy in range(top_y - 1, top_y - found, -1):
                ed.set(x, yy, z, "stone")
            for yy in range(top_y + 1, top_y + clear):
                ed.set(x, yy, z, "air")


def _stamp(ed, blocks, ox, oy, oz):
    for dx, dy, dz, blk, props in blocks:
        ed.set(ox + dx, oy + dy, oz + dz, blk, props)


def _cell_near(plan, x, z):
    return min(plan.cells, key=lambda c: (c.x - x) ** 2 + (c.z - z) ** 2)


def run(ctx) -> None:
    hf = build_heightfield(ctx)
    rides = coaster.mvp_coasters(ctx.rides)
    if not rides:
        LOG.warning("no MVP coaster route — skipping Castle Hill structures")
        return
    dragon_ride = rides[0]
    plan = coaster.plan_coaster(hf, dragon_ride, ctx.transform)
    board = plan.cells[plan.boarding_idx]

    # Castle origin: centred on the coaster's NE segment so the tunnel band (dx 2..14) wraps
    # the eastern track and the gatehouse (west) faces the station. dy band 1..5 must contain
    # the rail Y there, so anchor origin_y so band top (origin_y+5) >= local rail max.
    cox, coz = 84, -110
    east_cell = _cell_near(plan, cox + 12, coz)         # rail in the tunnel band
    co_y = east_cell.y - 1                               # band dy 1..5 -> rail at origin_y+1..+5
    fx0, fx1, fz0, fz1 = (cox + castle.CASTLE_FOOTPRINT[0], cox + castle.CASTLE_FOOTPRINT[1],
                          coz + castle.CASTLE_FOOTPRINT[2], coz + castle.CASTLE_FOOTPRINT[3])

    t0 = time.time()
    with mcio.open_level(ctx) as level:
        ed = mcio.WorldEditor(level, ctx)

        # Castle (flatten pad first so towers/walls sit on a level foundation)
        _flatten(ed, fx0, fx1, fz0, fz1, co_y, clear=26, found=8)
        _stamp(ed, castle.castle_blocks(), cox, co_y, coz)
        LOG.info("castle stamped at (%d,%d) origin_y=%d (%d blocks)",
                 cox, coz, co_y, len(castle.castle_blocks()))

        # Dragon show-scene: just WEST of the eastern track, at rail eye-level, body -> track.
        dcell = _cell_near(plan, cox + 12, coz - 2)
        dragon_w = castle.DRAGON_FOOTPRINT[1] - castle.DRAGON_FOOTPRINT[0]
        dox, doy, doz = dcell.x - dragon_w, dcell.y, dcell.z
        _stamp(ed, castle.dragon_blocks(), dox, doy, doz)
        LOG.info("dragon stamped at (%d,%d) y=%d (%d blocks)", dox, doz, doy, len(castle.dragon_blocks()))

        # Station at the boarding cell: platform flush with the rail, north of the track.
        sox, soy, soz = board.x, board.y - 1, board.z
        sfx0, sfx1 = sox + castle.STATION_FOOTPRINT[0], sox + castle.STATION_FOOTPRINT[1]
        sfz0, sfz1 = soz + castle.STATION_FOOTPRINT[2], soz + castle.STATION_FOOTPRINT[3]
        _flatten(ed, sfx0, sfx1, sfz0, sfz1, soy, clear=12, found=6)
        _stamp(ed, castle.station_blocks(), sox, soy, soz)
        LOG.info("station stamped at boarding (%d,%d) origin_y=%d (%d blocks)",
                 sox, soz, soy, len(castle.station_blocks()))

        level.save()
    LOG.info("structures complete in %.1fs", time.time() - t0)
