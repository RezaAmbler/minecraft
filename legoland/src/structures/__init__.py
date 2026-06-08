"""Phase 4 — Structures.

Builds the MVP station complexes at their route positions: a generic platform+building
station for most stops, Tidmouth's engine shed (roundhouse) by its turntable, and Brendam's
dock pier. Each gets a distinct accent colour + lit marker for kid navigation.
"""
from __future__ import annotations

import importlib
import logging
import time

from .. import mcio
from . import builders

LOG = logging.getLogger("sodor.structures")


def resolve_placement(ctx, entry: dict):
    """(base_x, base_z, facing) for a `[[structures]]` entry — anchored to a station + offset,
    with `facing='toward_spawn'` resolved to the cardinal that turns the model toward spawn.
    Shared by the placement loop here and the datapack nameplate."""
    from ..rail import route
    ax, az = route.stations()[entry["anchor"]]
    ox, oz = entry.get("offset", [0, 0])
    bx, bz = ax + ox, az + oz
    facing = entry.get("facing", "south")
    if facing == "toward_spawn":
        sx = int(ctx.layout["world"]["spawn"]["x"])
        sz = int(ctx.layout["world"]["spawn"]["z"])
        dx, dz = sx - bx, sz - bz
        facing = ("east" if dx > 0 else "west") if abs(dx) >= abs(dz) else ("south" if dz > 0 else "north")
    return bx, bz, facing


def _place_registry(ctx, ed) -> None:
    """Stamp each `[[structures]]` schematic entry: build its model (source of truth), export
    the reusable .schem, then replay it into the world on a flattened foundation. Guards
    against burying the running line."""
    sea = int(ctx.layout["world"]["sea_level"])
    for entry in ctx.layout.get("structures", []):
        mod_name, fn_name = entry["builder"].split(":")
        mod = importlib.import_module(mod_name)
        bx, bz, facing = resolve_placement(ctx, entry)
        blocks = getattr(mod, fn_name)(facing)
        ry = ed.surface_y(bx, bz) or (sea + 6)

        xs = [bx + dx for dx, dy, dz, *_ in blocks]
        zs = [bz + dz for dx, dy, dz, *_ in blocks]
        x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
        if any("rail" in ed.name_at(x, y, z)
               for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) for y in (ry, ry + 1)):
            LOG.warning("registry %s footprint overlaps rail near (%d,%d) — skipping", entry["key"], bx, bz)
            continue

        for x in range(x0, x1 + 1):           # foundation + clear headroom
            for z in range(z0, z1 + 1):
                for yy in range(ry - 4, ry):
                    ed.set(x, yy, z, "stone")
                for yy in range(ry + 1, ry + 14):
                    ed.set(x, yy, z, "air")
        for dx, dy, dz, blk, props in blocks:
            ed.set(bx + dx, ry + dy, bz + dz, blk, props)

        if hasattr(mod, "export_schem"):
            mod.export_schem("schematics", entry.get("schem", entry["key"]))
        LOG.info("placed registry %s at (%d,%d) ry=%d facing=%s (%d blocks)",
                 entry["key"], bx, bz, ry, facing, len(blocks))


def _marker(ed, x, z, ry, accent):
    floor = ry + 1
    ed.set(x, ry, z, accent)
    for up in range(1, 9):
        ed.set(x, floor + up, z, accent)
    ed.set(x, floor + 9, z, "glowstone")


def run(ctx) -> None:
    from ..rail import route
    info = route.station_info()
    mvp = {loc["key"] for loc in ctx.layout.get("locations", []) if loc.get("mvp")}

    t0 = time.time()
    built = []
    with mcio.open_level(ctx) as level:
        ed = mcio.WorldEditor(level, ctx)
        for key, (x, z, axis) in info.items():
            if key not in mvp:
                continue
            ry = ed.surface_y(x, z) or (int(ctx.layout["world"]["sea_level"]) + 6)
            accent = builders.ACCENTS.get(key, "white_concrete")
            if key == "tidmouth":
                builders.build_roundhouse(ed, x, z, ry, axis)
                _marker(ed, x + (0 if axis == "ew" else 12), z + (12 if axis == "ew" else 0), ry, accent)
            elif key == "brendam_docks":
                builders.build_docks(ed, x, z, ry, axis)
            else:
                builders.build_station(ed, x, z, ry, axis, accent)
            built.append(key)
            level.save()
            level.purge()
            ed.invalidate_cache()
            LOG.info("built %s @ (%d,%d) ry=%d (%s)", key, x, z, ry, axis)
        _place_registry(ctx, ed)
        level.save()
    LOG.info("Phase 4 structures complete: %d stations + %d registry in %.1fs",
             len(built), len(ctx.layout.get("structures", [])), time.time() - t0)
