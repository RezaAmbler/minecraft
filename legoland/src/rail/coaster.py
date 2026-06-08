"""Coaster planning — turn a ride's waypoint route into a rideable Cell list.

Shared by the rail layer (lays the track), the ride system (boarding cell + rig follow), and
the validator (checks the written geometry), so the plan cannot drift from what's built.

A coaster differs from Sodor's terrain-following branch line: its elevation is the RIDE's
profile (lift hill, drops) interpolated from the route waypoints' Y, then made vanilla-legal
with the proven helpers — every step clamped to <=1 block, curves flattened with their
neighbours, single-cell valleys removed — and finally lifted to sit on/above the terrain
(the layer adds stone supports/embankment beneath). Reuses grid.cell_shape etc. verbatim.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import grid
from .pathing import _fix_valleys, _nbr_idx, _slope_limit, _terrain_y


@dataclass(frozen=True)
class CoasterPlan:
    key: str
    name: str
    cells: list                 # list[grid.Cell]
    boarding_idx: int           # index into cells of the boarding/station cell
    xz: list                    # the 4-connected (x,z) path


def _nearest_idx(xz: list[tuple[int, int]], x: int, z: int) -> int:
    return min(range(len(xz)), key=lambda i: (xz[i][0] - x) ** 2 + (xz[i][1] - z) ** 2)


def coaster_profile(hf, xz, wp_xyz, corners, closed: bool = True) -> list[int]:
    """Y profile from the waypoints' Y, slope-limited / corner-flattened / de-valleyed, then
    raised so no cell sits below the terrain surface (supports are added by the layer)."""
    n = len(xz)
    pos = {p: i for i, p in enumerate(xz)}
    # keyed (index -> target y) from the route waypoints
    keyed: dict[int, float] = {}
    for x, y, z in wp_xyz:
        i = pos.get((int(x), int(z)))
        if i is None:
            i = _nearest_idx(xz, int(x), int(z))
        keyed.setdefault(i, float(y))
    ks = sorted(keyed)
    if not ks:
        ys = [_terrain_y(hf, x, z) for x, z in xz]
    else:
        ys = [None] * n
        # interpolate linearly between consecutive keyed indices (wrapping if closed)
        pairs = list(zip(ks, ks[1:]))
        if closed:
            pairs.append((ks[-1], ks[0]))
        for i0, i1 in pairs:
            y0, y1 = keyed[i0], keyed[i1]
            span = (i1 - i0) % n if closed else (i1 - i0)
            if span <= 0:
                ys[i0] = y0
                continue
            for s in range(span + 1):
                idx = (i0 + s) % n if closed else i0 + s
                ys[idx] = y0 + (y1 - y0) * (s / span)
        ys = [int(round(v)) if v is not None else _terrain_y(hf, *xz[i])
              for i, v in enumerate(ys)]

    # make it vanilla-legal: clamp steps, flatten curves, remove width-1 valleys
    for _ in range(200):
        changed = _slope_limit(ys, closed)
        for i in corners:
            p, nx = _nbr_idx(n, i, closed)
            for j in (p, i, nx):
                if j is not None and ys[j] != ys[i]:
                    ys[j] = ys[i]
                    changed = True
        changed |= _fix_valleys(ys, closed)
        if not changed:
            break

    # raise the whole loop so the rail never sits below the ground it crosses
    lift = max((_terrain_y(hf, x, z) - ys[i] for i, (x, z) in enumerate(xz)), default=0)
    if lift > 0:
        ys = [y + lift for y in ys]
    return ys


def plan_coaster(hf, ride: dict, layout_like: dict) -> CoasterPlan:
    """Resolve one coaster's `route` (list of [x,y,z]) into a connected, rideable Cell list."""
    cfg = grid.rail_cfg(layout_like)
    wp_xyz = [(int(x), int(y), int(z)) for x, y, z in ride["route"]]
    wp_xz = [(x, z) for x, _, z in wp_xyz]
    xz = grid.grid_path(wp_xz, closed=True, max_dev=cfg["max_deviation"])
    corners = grid.corner_indices(xz, closed=True)
    ys = coaster_profile(hf, xz, wp_xyz, corners, closed=True)
    rt = grid.plan_rail_types(xz, ys, corners, True, cfg)
    cells = grid.classify_cells(xz, ys, rt, closed=True)
    bx, _, bz = ride["boarding"]
    boarding_idx = _nearest_idx(xz, int(bx), int(bz))
    return CoasterPlan(key=ride["key"], name=ride["name"], cells=cells,
                       boarding_idx=boarding_idx, xz=xz)


def rail_tuning(transform_cfg: dict) -> dict:
    """Rail booster/deviation tuning, read from transform.toml [rail] (with sane defaults)."""
    return {"rail": transform_cfg.get("rail", {})}


def mvp_coasters(ride_cfg: dict) -> list[dict]:
    return [r for r in ride_cfg.get("rides", [])
            if r.get("kind") == "coaster" and r.get("mvp") and r.get("route")]
