"""Rideable rail geometry (P3.7): 4-connected grid paths + neighbour-derived rail shapes.

The previous generator interpolated waypoints diagonally and wrote every cell as a flat
`east_west`/`north_south` straight, so most cells were diagonally offset (disconnected) and
no turn or grade ever connected. This module instead:

  * snaps each route to a strictly 4-connected grid path (one cardinal step per cell) as an
    axis-aligned staircase — long straights with batched corners, good for minecart momentum;
  * derives every cell's rail `shape` from its IMMEDIATE neighbours (straight / curve /
    ascending), the way Minecraft expects, so turns and grades actually connect;
  * plans rail TYPES so only plain `rail` ever curves and boosters land on straights/climbs.

The laying phase and the validator both call `plan_network`/`classify_cells`, so the written
geometry and the checked geometry cannot drift.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import route, switches
from .pathing import _nbr_idx, compute_profile

# direction unit vectors (layout.toml: +X=east, +Z=south)
VEC_TO_DIR = {(0, -1): "n", (0, 1): "s", (1, 0): "e", (-1, 0): "w"}
_OPP = {"n": "s", "s": "n", "e": "w", "w": "e"}
ASCEND = {"n": "ascending_north", "s": "ascending_south",
          "e": "ascending_east", "w": "ascending_west"}
CURVE = {
    frozenset(("n", "e")): "north_east",
    frozenset(("n", "w")): "north_west",
    frozenset(("s", "e")): "south_east",
    frozenset(("s", "w")): "south_west",
}
STRAIGHT = {"e": "east_west", "w": "east_west", "n": "north_south", "s": "north_south"}
CURVE_SHAPES = set(CURVE.values())
ASCEND_SHAPES = set(ASCEND.values())
DIR_TO_VEC = {d: v for v, d in VEC_TO_DIR.items()}


def curve_inside_offset(shape: str) -> tuple[int, int]:
    """The diagonal cell on the inside of a curve (sum of its two connection vectors)."""
    dirs = [d for fs, name in CURVE.items() if name == shape for d in fs]
    return (sum(DIR_TO_VEC[d][0] for d in dirs), sum(DIR_TO_VEC[d][1] for d in dirs))


class RailGeometryError(Exception):
    """Raised when geometry cannot be realised as connected vanilla rail — fails the build."""


@dataclass(frozen=True)
class Cell:
    x: int
    y: int
    z: int
    shape: str
    rail_type: str        # "rail" | "powered_rail"
    powered: bool

    @property
    def xz(self):
        return (self.x, self.z)


def _dir(a, b):
    """Cardinal from a to b, or None if not a unit cardinal step (e.g. a == b)."""
    return VEC_TO_DIR.get((b[0] - a[0], b[1] - a[1]))


# --------------------------------------------------------------------------- #
# 4-connected staircase path
# --------------------------------------------------------------------------- #
def _segment_cells(p0, p1, max_dev: int, flip: bool):
    """Axis-aligned staircase from p0 to p1 (excludes p0, includes p1); one cardinal/cell."""
    x0, z0 = p0
    x1, z1 = p1
    dx, dz = x1 - x0, z1 - z0
    out: list[tuple[int, int]] = []
    if dx == 0 and dz == 0:
        return out
    if abs(dx) >= abs(dz):
        amaj, amin = abs(dx), abs(dz)
        smaj, smin = (1 if dx > 0 else -1, 0), (0, 1 if dz > 0 else -1)
    else:
        amaj, amin = abs(dz), abs(dx)
        smaj, smin = (0, 1 if dz > 0 else -1), (1 if dx > 0 else -1, 0)
    k = 1 if amin == 0 else min(amin, max(1, math.ceil(amin / max_dev)))

    cx, cz = x0, z0
    done_maj = done_min = 0
    for li in range(k):
        maj_len = round(amaj * (li + 1) / k) - done_maj
        min_len = round(amin * (li + 1) / k) - done_min
        done_maj += maj_len
        done_min += min_len
        major_first = (li % 2 == 0) != flip
        seq = ([(smaj, maj_len), (smin, min_len)] if major_first
               else [(smin, min_len), (smaj, maj_len)])
        for (vx, vz), length in seq:
            for _ in range(length):
                cx += vx
                cz += vz
                out.append((cx, cz))
    return out


def grid_path(waypoints, closed: bool = False, max_dev: int = 24) -> list[tuple[int, int]]:
    pts = [tuple(p) for p in waypoints]
    if not pts:
        return []
    legs = list(zip(pts, pts[1:]))
    if closed and pts[0] != pts[-1]:
        legs.append((pts[-1], pts[0]))
    path = [pts[0]]
    flip = False
    for a, b in legs:
        path.extend(_segment_cells(a, b, max_dev, flip))
        flip = not flip
    out = [path[0]]
    for p in path[1:]:
        if p != out[-1]:
            out.append(p)
    if closed and len(out) > 1 and out[0] == out[-1]:
        out.pop()
    for a, b in zip(out, out[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            raise RailGeometryError(f"non-4-connected step {a}->{b}")
    if closed and len(out) > 1:
        a, b = out[-1], out[0]
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            raise RailGeometryError(f"closed loop not 4-connected {a}->{b}")
    return out


def corner_indices(path, closed: bool = False) -> set[int]:
    n = len(path)
    corners = set()
    for i in range(n):
        p, nx = _nbr_idx(n, i, closed)
        if p is None or nx is None:
            continue
        din, dout = _dir(path[p], path[i]), _dir(path[i], path[nx])
        if din and dout and din != dout:
            corners.add(i)
    return corners


# --------------------------------------------------------------------------- #
# neighbour-derived shape
# --------------------------------------------------------------------------- #
def cell_shape(prev, cur, nxt, yp: int, yc: int, yn: int, rail_type: str = "rail") -> str:
    """The authoritative prev/next -> rail shape mapping (straight / curve / ascending)."""
    din, dout = _dir(prev, cur), _dir(cur, nxt)
    if din is None:
        din = dout
    if dout is None:
        dout = din
    if din is None:
        return "north_south"  # isolated cell (shouldn't happen)
    if din == dout:  # collinear straight — slope takes priority
        if yn - yc == 1:
            return ASCEND[dout]            # rises toward the next cell
        if yp - yc == 1:
            return ASCEND[_OPP[din]]       # rises toward the previous cell
        return STRAIGHT[dout]
    # perpendicular neighbours -> curve (plain rail only)
    if rail_type != "rail":
        raise RailGeometryError(f"{rail_type} cannot curve at {cur} ({din}->{dout})")
    return CURVE[frozenset((_OPP[din], dout))]


def classify_cells(path, ys, rail_types, closed: bool = False) -> list[Cell]:
    n = len(path)
    cells = []
    for i in range(n):
        p, nx = _nbr_idx(n, i, closed)
        prev = path[p] if p is not None else path[i]
        nxt = path[nx] if nx is not None else path[i]
        yp = ys[p] if p is not None else ys[i]
        yn = ys[nx] if nx is not None else ys[i]
        shape = cell_shape(prev, path[i], nxt, yp, ys[i], yn, rail_types[i])
        x, z = path[i]
        cells.append(Cell(x, ys[i], z, shape, rail_types[i], rail_types[i] == "powered_rail"))
    return cells


# --------------------------------------------------------------------------- #
# booster planning (powered rail only on straights/climbs, never on/next to a curve)
# --------------------------------------------------------------------------- #
def plan_rail_types(path, ys, corner_idx, closed: bool, cfg: dict,
                    junction_idx=frozenset()) -> list[str]:
    n = len(path)
    rt = ["rail"] * n
    protected = set(junction_idx)
    for i in corner_idx:
        p, nx = _nbr_idx(n, i, closed)
        protected.update(j for j in (p, i, nx) if j is not None)
    climb = set()
    near_corner = set()
    for i in range(n):
        p, nx = _nbr_idx(n, i, closed)
        yp = ys[p] if p is not None else ys[i]
        yn = ys[nx] if nx is not None else ys[i]
        if yn - ys[i] == 1 or yp - ys[i] == 1:
            climb.add(i)
    for i in corner_idx:
        for d in (-2, -1, 1, 2):
            j = (i + d) % n if closed else i + d
            if 0 <= j < n:
                near_corner.add(j)
    every = max(1, cfg["booster_every"])
    for i in range(n):
        if i in protected:
            continue
        boost = (i % every == 0) or i in climb
        if cfg["curve_exit_boost"] and i in near_corner:
            boost = True
        if boost:
            rt[i] = "powered_rail"
    return rt


# --------------------------------------------------------------------------- #
# whole-network plan (main loop + branches + junction indices)
# --------------------------------------------------------------------------- #
def rail_cfg(layout: dict) -> dict:
    r = layout.get("rail", {})
    return {
        "booster_every": int(r.get("booster_every", 4)),
        "curve_exit_boost": bool(r.get("curve_exit_boost", True)),
        "climb_base_boosters": int(r.get("climb_base_boosters", 3)),
        "max_deviation": int(r.get("max_deviation", 24)),
    }


# a junction needs a straight, level run through it (the switch cell must be straight and the
# branch must depart perpendicular without the main line jogging onto the branch's cells).
_JUNCTION_RUN = 4


def _main_waypoints(layout: dict):
    """Main-loop waypoints with a short straight run forced through each junction, aligned to
    the station's track axis, so the switch geometry in `switches` is always realisable."""
    sinfo = route.station_info()
    wp = []
    for key, x, z in route.MAIN_LOOP:
        if key in switches.JUNCTIONS:
            r = _JUNCTION_RUN
            if sinfo[key][2] == "ew":
                wp += [(x - r, z), (x, z), (x + r, z)]
            else:
                wp += [(x, z - r), (x, z), (x, z + r)]
        else:
            wp.append((x, z))
    return wp


def plan_network(hf, layout: dict) -> dict:
    """Pure plan shared by the layer (Phase 3) and the validator: the resolved Cell lists for
    the main loop and each branch, plus the main-path index of each junction."""
    cfg = rail_cfg(layout)
    md = cfg["max_deviation"]

    main_wp = _main_waypoints(layout)
    main_xz = grid_path(main_wp, closed=True, max_dev=md)
    main_corners = corner_indices(main_xz, closed=True)
    n = len(main_xz)

    jidx = {name: main_xz.index(tuple(info["switch_xz"]))
            for name, info in switches.JUNCTIONS.items()
            if tuple(info["switch_xz"]) in main_xz}
    flat_extra = set()
    for idx in jidx.values():
        flat_extra.update((idx + d) % n for d in (-1, 0, 1))

    main_ys = compute_profile(hf, main_xz, main_corners | flat_extra, closed=True)
    main_rt = plan_rail_types(main_xz, main_ys, main_corners, True, cfg,
                              junction_idx=set(jidx.values()))
    main_cells = classify_cells(main_xz, main_ys, main_rt, closed=True)

    branch_jy = {info["branch"]: main_cells[jidx[name]].y
                 for name, info in switches.JUNCTIONS.items() if name in jidx}

    branches = {}
    for name in route.BRANCHES:
        bwp = [(x, z) for _, x, z in route.BRANCHES[name]]
        bxz = grid_path(bwp, closed=False, max_dev=md)
        bcorners = corner_indices(bxz, closed=False)
        anchors, bflat = {}, set(bcorners)
        jy = branch_jy.get(name)
        if jy is not None and len(bxz) >= 2:
            anchors = {0: jy, 1: jy}
            bflat |= {0, 1}
        bys = compute_profile(hf, bxz, bflat, closed=False, anchors=anchors)
        brt = plan_rail_types(bxz, bys, bcorners, False, cfg)
        branches[name] = classify_cells(bxz, bys, brt, closed=False)

    return {"main": main_cells, "branches": branches, "jidx": jidx, "cfg": cfg}
