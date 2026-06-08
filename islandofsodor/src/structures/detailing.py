"""Per-station detailing distribution (detailing pass).

Stamps the reusable `props` per MVP station, sized by station type (small halts get less, main
stations get the full set), and engraves the platform name sign. Runs inside `structures.run()`
after the station builders, BEFORE rail — so the corridor guard reads the rail *plan*
(`grid.plan_network` + `switches.exit_cells`), not the world, and keeps every prop off the
running line and off the switch lever/stand (junctions stay operable). Reproducible: fixed kits,
no randomness, mtime=0 schems.
"""
from __future__ import annotations

import logging

from . import builders, props
from ..rail import grid, route, switches
from ..terrain.heightfield import build_heightfield

LOG = logging.getLogger("sodor.detailing")

_VEC_CARD = {(0, 1): "south", (0, -1): "north", (1, 0): "east", (-1, 0): "west"}

# per-station-type kits: (prop, side, t, d, facing). side offsets perpendicular to the track
# ("+P"/"-P"); t runs along the track. facing "toward_track" auto-resolves to face the centre.
_BASE = [
    ("name_board", "+P", -5, 3, "toward_track"),
    ("bench", "+P", 7, 3, "toward_track"),
    ("bench", "+P", -9, 3, "toward_track"),
    ("planter", "+P", 4, 4, "toward_track"),
    ("planter", "+P", -2, 4, "toward_track"),
    ("picket_fence", "-P", 0, 3, "toward_track"),
]
_KITS = {
    "branch_end": _BASE,
    "station": _BASE + [("canopy", "+P", 0, 4, "toward_track"),
                        ("water_tower", "-P", 12, 5, "toward_track")],
    "junction": _BASE + [("canopy", "+P", 10, 4, "toward_track"),
                        ("signal_box", "-P", -12, 4, "toward_track"),
                        ("footbridge", "across", 0, 0, "across"),
                        ("water_tower", "-P", 13, 5, "toward_track"),
                        ("phone_box", "+P", 11, 3, "toward_track")],
    "terminus": _BASE + [("canopy", "+P", 10, 4, "toward_track"),
                        ("water_tower", "-P", 13, 5, "toward_track"),
                        ("coal_stage", "-P", -13, 5, "toward_track"),
                        ("phone_box", "+P", 11, 3, "toward_track"),
                        ("signal_box", "-P", 2, 5, "toward_track")],
    "docks": [("name_board", "+P", -5, 3, "toward_track")],
}


def forbidden_cells(ctx, hf):
    """Rail corridor (cells + shoulders dilated by `clearance`) + every switch cell — props and
    trees must avoid these. Built from the rail PLAN (rail isn't laid yet when this runs)."""
    clr = max(1, int(ctx.layout.get("detailing", {}).get("clearance", 1)))
    net = grid.plan_network(hf, ctx.layout)
    rail = {(c.x, c.z) for c in net["main"]}
    for b in net["branches"].values():
        rail.update((c.x, c.z) for c in b)
    forb = set()
    for cx, cz in rail:
        for dx in range(-clr, clr + 1):
            for dz in range(-clr, clr + 1):
                forb.add((cx + dx, cz + dz))
    for name in switches.JUNCTIONS:
        for sx, sz in switches.exit_cells(name).values():
            for dx in range(-1, 2):
                for dz in range(-1, 2):
                    forb.add((sx + dx, sz + dz))
    return forb


def _place(x, z, axis, side, t, d):
    A, P = builders._axes(axis)
    sgn = 1 if side[0] == "+" else -1
    off, along = (P, A) if side[1] == "P" else (A, P)
    bx = x + along[0] * t + off[0] * sgn * d
    bz = z + along[1] * t + off[1] * sgn * d
    return bx, bz, (-off[0] * sgn, -off[1] * sgn)   # face vector toward the centre line


def run_detailing(ctx, ed) -> None:
    hf = build_heightfield(ctx)
    forb = forbidden_cells(ctx, hf)
    locs = {loc["key"]: loc for loc in ctx.layout.get("locations", [])}
    mvp = {k for k, loc in locs.items() if loc.get("mvp")}
    info = route.station_info()
    sea = int(ctx.layout["world"]["sea_level"])
    sign_mode = ctx.layout.get("detailing", {}).get("signs", "block_entity")
    exported, placed = set(), 0

    for key, (x, z, axis) in info.items():
        if key not in mvp:
            continue
        for prop, side, t, d, facing in _KITS.get(locs[key].get("type"), _BASE):
            if prop == "footbridge":
                bx, bz, pfacing = x, z, ("south" if axis == "ew" else "east")
            else:
                bx, bz, fvec = _place(x, z, axis, side, t, d)
                pfacing = _VEC_CARD[fvec] if facing == "toward_track" else facing
            blocks = props.build(prop, pfacing)

            # corridor guard: a non-bridge prop's track-blocking footprint must miss the corridor
            low = {(bx + dx, bz + dz) for dx, dy, dz, *_ in blocks if dy <= 3}
            if prop != "footbridge" and (low & forb):
                LOG.warning("skip %s at %s (near corridor)", prop, key)
                continue

            base = ed.surface_y(bx, bz) or (sea + 6)
            H = max(dy for _, dy, _, _, _ in blocks) + 3
            xs = [bx + dx for dx, _, dz, *_ in blocks]
            zs = [bz + dz for dx, _, dz, *_ in blocks]
            for fx in range(min(xs), max(xs) + 1):       # foundation + headroom (skip rail cols)
                for fz in range(min(zs), max(zs) + 1):
                    if (fx, fz) in forb:
                        continue
                    for yy in range(base - 4, base):
                        ed.set(fx, yy, fz, "stone")
                    for yy in range(base + 1, base + 1 + H):
                        ed.set(fx, yy, fz, "air")
            for dx, dy, dz, blk, p in blocks:
                ed.set(bx + dx, base + dy, bz + dz, blk, p)

            if prop == "name_board" and sign_mode == "block_entity":
                sdx, sdz = props._rot(0, 1, pfacing)      # the cell just in front of the backing
                ed.set_sign(bx + sdx, base + 2, bz + sdz, [locs[key]["name"]],
                            facing=pfacing, wall=True)
            placed += 1
            if prop not in exported:
                props.export_schem(prop)
                exported.add(prop)
        ed.invalidate_cache()
    LOG.info("detailing: placed %d props + signs across %d stations", placed, len(mvp))
