"""Phase 4 — structure builders (parametric, stamped via mcio.WorldEditor).

Kid-bright, blocky, readable. Each station gets a distinct accent colour + a tall lit
marker so young explorers can tell them apart from afar. Tidmouth also gets an engine
shed (roundhouse) by its turntable; Brendam gets a dock pier.
"""
from __future__ import annotations

# distinct accent concrete per station (navigation aid for kids)
ACCENTS = {
    "tidmouth": "blue_concrete",
    "knapford": "yellow_concrete",
    "wellsworth": "green_concrete",
    "maron": "orange_concrete",
    "crovans_gate": "light_blue_concrete",
    "vicarstown": "red_concrete",
    "brendam_docks": "cyan_concrete",
    "ffarquhar": "lime_concrete",
    "elsbridge": "magenta_concrete",
}


def _axes(axis: str):
    return ((1, 0), (0, 1)) if axis == "ew" else ((0, 1), (1, 0))


def _flatten(ed, x, z, ry, A, P, ta, sides):
    """Flatten strips beside the track to a grass pad at ry (track corridor left intact)."""
    for t in range(-ta, ta + 1):
        for sgn, d0, d1 in sides:
            for d in range(d0, d1 + 1):
                px = x + A[0] * t + P[0] * sgn * d
                pz = z + A[1] * t + P[1] * sgn * d
                sy = ed.surface_y(px, pz) or ry
                if sy < ry:
                    for yy in range(sy + 1, ry + 1):
                        ed.set(px, yy, pz, "dirt")
                ed.set(px, ry, pz, "grass_block", {"snowy": "false"})
                for yy in range(ry + 1, ry + 10):
                    ed.set(px, yy, pz, "air")


def build_station(ed, x, z, ry, axis, accent) -> None:
    A, P = _axes(axis)
    floor = ry + 1
    _flatten(ed, x, z, ry, A, P, 12, [(1, 2, 9), (-1, 2, 4)])

    # platforms both sides of the track (d=2,3), raised one above the rail
    for t in range(-10, 11):
        for sgn in (1, -1):
            for d in (2, 3):
                px = x + A[0] * t + P[0] * sgn * d
                pz = z + A[1] * t + P[1] * sgn * d
                ed.set(px, floor, pz, "smooth_stone")
                ed.set(px, floor + 1, pz, "polished_andesite_slab" if d == 2 else "air",
                       {"type": "bottom"} if d == 2 else None)

    # station building on +P side (d 4..8)
    b0, b1, bl = 4, 8, 6
    for t in range(-bl, bl + 1):
        for d in range(b0, b1 + 1):
            bx = x + A[0] * t + P[0] * d
            bz = z + A[1] * t + P[1] * d
            ed.set(bx, floor, bz, "smooth_stone")
            perim = t in (-bl, bl) or d in (b0, b1)
            for up in range(1, 4):
                ed.set(bx, floor + up, bz, accent if perim else "air")
            ed.set(bx, floor + 4, bz, "smooth_stone_slab", {"type": "bottom"})
    # windows along the back wall, door on the platform side
    for t in range(-bl + 1, bl, 2):
        bx = x + A[0] * t + P[0] * b1
        bz = z + A[1] * t + P[1] * b1
        ed.set(bx, floor + 2, bz, "glass")
    dx, dz = x + P[0] * b0, z + P[1] * b0
    ed.set(dx, floor + 1, dz, "air")
    ed.set(dx, floor + 2, dz, "air")

    # platform lamps
    for t in (-10, 0, 10):
        for sgn in (1, -1):
            px = x + A[0] * t + P[0] * sgn * 2
            pz = z + A[1] * t + P[1] * sgn * 2
            ed.set(px, floor + 1, pz, "oak_fence")
            ed.set(px, floor + 2, pz, "oak_fence")
            ed.set(px, floor + 3, pz, "sea_lantern")

    # tall lit accent marker behind the building (a from-afar landmark)
    mx, mz = x + P[0] * (b1 + 2), z + P[1] * (b1 + 2)
    ed.set(mx, ry, mz, accent)
    for up in range(1, 8):
        ed.set(mx, floor + up, mz, accent)
    ed.set(mx, floor + 8, mz, "glowstone")


def build_roundhouse(ed, x, z, ry, axis) -> None:
    """Tidmouth engine shed: a multi-stall brick shed set back from the turntable."""
    A, P = _axes(axis)
    floor = ry + 1
    # set the shed off to the -P side, clear a pad
    base_d = 6
    _flatten(ed, x, z, ry, A, P, 12, [(-1, base_d - 1, base_d + 9)])
    depth0, depth1 = base_d, base_d + 8
    half = 11
    for t in range(-half, half + 1):
        for d in range(depth0, depth1 + 1):
            bx = x + A[0] * t - P[0] * d
            bz = z + A[1] * t - P[1] * d
            ed.set(bx, floor, bz, "stone_bricks")
            back = d == depth1
            side = t in (-half, half)
            front = d == depth0
            for up in range(1, 6):
                solid = back or side or (front and (t % 4 != 0))  # front has stall openings every 4
                ed.set(bx, floor + up, bz, "brick_wall" if (front and up >= 4) else
                       ("bricks" if solid else "air"))
            ed.set(bx, floor + 6, bz, "deepslate_tile_slab", {"type": "bottom"})


def build_docks(ed, x, z, ry, axis) -> None:
    """Brendam Docks: a plank pier toward the sea + a warehouse + simple cranes."""
    A, P = _axes(axis)
    floor = ry + 1
    sea_level = ry  # pier sits just above the shoreline height
    # warehouse on land (+? side that is land): build on the -P side
    build_station(ed, x, z, ry, axis, ACCENTS["brendam_docks"])
    # pier extends along +P toward lower ground/water
    for t in range(-3, 4):
        for d in range(2, 16):
            px = x + A[0] * t + P[0] * d
            pz = z + A[1] * t + P[1] * d
            # support post down to whatever is below
            ed.set(px, floor, pz, "oak_planks")
            for up in range(1, 6):
                ed.set(px, floor + up, pz, "air")
            if t in (-3, 3) and d % 3 == 0:
                ed.set(px, floor + 1, pz, "oak_fence")  # railing posts
            # posts under the deck
            for yy in range(floor - 1, ry - 4, -1):
                ed.set(px, yy, pz, "stripped_oak_log", {"axis": "y"})
    # two simple cranes at the pier end
    for t in (-2, 2):
        cx = x + A[0] * t + P[0] * 14
        cz = z + A[1] * t + P[1] * 14
        for up in range(1, 6):
            ed.set(cx, floor + up, cz, "stripped_spruce_log", {"axis": "y"})
        for d in range(0, 4):
            ed.set(cx + P[0] * (-d), floor + 5, cz + P[1] * (-d), "stripped_spruce_log",
                   {"axis": "x" if axis == "ns" else "z"})
        ed.set(cx + P[0] * (-3), floor + 4, cz + P[1] * (-3), "chain")
