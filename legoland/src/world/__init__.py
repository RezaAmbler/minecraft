"""Phase 1 — World foundation.

Creates the world skeleton (amulet), writes the authoritative level.dat (nbtlib), and
builds a small safe spawn platform so the world is standable before terrain exists.
Strategy + DataVersion rationale: docs/DECISIONS.md D10/D11.
"""
from __future__ import annotations

import logging

from .. import mcio
from .level_dat import write_level_dat

LOG = logging.getLogger("sodor.world")

PLATFORM_HALF = 12  # 25x25 grass platform centred on spawn


def build_spawn_platform(ctx) -> None:
    """A small grass platform under spawn (overwritten later by the terrain phase)."""
    sp = ctx.transform["world"]["spawn"]
    sx, sy, sz = int(sp[0]), int(sp[1]), int(sp[2])
    top = sy - 1  # block the player stands on
    ver = mcio.version_id(ctx)
    grass = mcio.block("grass_block", {"snowy": _str("false")})
    dirt = mcio.block("dirt")
    stone = mcio.block("stone")
    count = 0
    with mcio.open_level(ctx) as level:
        for dx in range(-PLATFORM_HALF, PLATFORM_HALF + 1):
            for dz in range(-PLATFORM_HALF, PLATFORM_HALF + 1):
                x, z = sx + dx, sz + dz
                level.set_version_block(x, top, z, mcio.DIMENSION, ver, grass)
                level.set_version_block(x, top - 1, z, mcio.DIMENSION, ver, dirt)
                level.set_version_block(x, top - 2, z, mcio.DIMENSION, ver, stone)
                count += 3
    LOG.info("spawn platform: %d blocks around (%d, %d, %d)", count, sx, sy, sz)


def _str(value: str):
    import amulet_nbt
    return amulet_nbt.StringTag(value)


def _ring(cx: int, cz: int, r: int):
    if r == 0:
        yield (cx, cz)
        return
    for d in range(-r, r + 1):
        yield (cx + d, cz - r)
        yield (cx + d, cz + r)
    for d in range(-r + 1, r):
        yield (cx - r, cz + d)
        yield (cx + r, cz + d)


def _surface_feet_y(level, x: int, z: int, ver) -> int | None:
    """Topmost solid, standable column: returns feet-y (block+1) if 2 air above, else None."""
    for y in range(120, 55, -1):
        b = level.get_version_block(x, y, z, mcio.DIMENSION, ver)
        name = (b[0] if isinstance(b, tuple) else b)
        name = getattr(name, "base_name", "")
        if name and name not in ("air",):
            return (x, y, z, name)  # first non-air from top = surface
    return None


def find_ground_spawn(ctx) -> tuple[int, int, int]:
    """Scan the finished world for grass near the configured spawn (off the track)."""
    import amulet

    sp = ctx.transform["world"]["spawn"]
    sx, sz = int(sp[0]), int(sp[2])
    ver = mcio.version_id(ctx)
    level = amulet.load_level(str(ctx.world_dir))
    try:
        for r in range(0, 30):
            for x, z in _ring(sx, sz, r):
                surf = _surface_feet_y(level, x, z, ver)
                if surf and surf[3] == "grass_block":   # grass => natural ground, off the gravel track
                    return (surf[0], surf[1] + 1, surf[2])
        return (sx, 80, sz)
    finally:
        level.close()


def run(ctx) -> None:
    LOG.info("creating world skeleton at %s", ctx.world_dir)
    mcio.create_skeleton(ctx, overwrite=not ctx.resume)
    write_level_dat(ctx)
    build_spawn_platform(ctx)
    LOG.info("Phase 1 (world foundation) complete -> %s", ctx.world_dir)
