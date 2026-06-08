"""P3.1 — rail route topology (waypoints in world coords).

The canon main line is point-to-point; for kid-friendly continuous running we close it
into a loop (decision D8): a "front" arc through the main-line stations along the southern
lowland, and a station-free return arc to the north (south of the mountain massif). Branches
spur south to Ffarquhar and Brendam Docks. Waypoints are authored on the island and verified
on land (rail.verify_routes); sea crossings become causeways via the rail-bed fill.
"""
from __future__ import annotations

# (key_or_None, x, z). key marks a station to be built in Phase 4.
MAIN_LOOP: list[tuple[str | None, int, int]] = [
    ("tidmouth",      -1400, 350),   # west terminus (+ sheds/turntable)
    ("knapford",       -850, 430),   # junction -> Ffarquhar branch
    ("wellsworth",     -250, 470),   # junction -> Brendam branch
    ("maron",           300, 440),
    ("crovans_gate",    800, 330),   # junction -> Skarloey (post-MVP)
    ("vicarstown",     1150, 200),   # east terminus
    (None,              700,  60),   # --- return arc (north, no stations) ---
    (None,              100,  20),
    (None,             -500,  30),
    (None,            -1050, 120),
]

BRANCHES: dict[str, list[tuple[str | None, int, int]]] = {
    "ffarquhar": [("knapford", -850, 430), ("elsbridge", -770, 580), ("ffarquhar", -700, 750)],
    "brendam":   [("wellsworth", -250, 470), (None, -280, 600), ("brendam_docks", -300, 720)],
}


def main_waypoints() -> list[tuple[int, int]]:
    """Main-loop waypoints (x, z) — snapped to a 4-connected grid path by rail.grid."""
    return [(x, z) for _, x, z in MAIN_LOOP]


def branch_waypoints(name: str) -> list[tuple[int, int]]:
    return [(x, z) for _, x, z in BRANCHES[name]]


def stations() -> dict[str, tuple[int, int]]:
    """All station keys -> (x,z) across the loop and branches."""
    out: dict[str, tuple[int, int]] = {}
    for key, x, z in MAIN_LOOP:
        if key:
            out[key] = (x, z)
    for seg in BRANCHES.values():
        for key, x, z in seg:
            if key:
                out[key] = (x, z)
    return out


def _axis(a: tuple[int, int], b: tuple[int, int]) -> str:
    return "ew" if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else "ns"


def station_info() -> dict[str, tuple[int, int, str]]:
    """key -> (x, z, axis) where axis ('ew'/'ns') is the track direction through the station."""
    info: dict[str, tuple[int, int, str]] = {}
    n = len(MAIN_LOOP)
    for i, (k, x, z) in enumerate(MAIN_LOOP):
        if not k:
            continue
        prv, nxt = MAIN_LOOP[i - 1], MAIN_LOOP[(i + 1) % n]
        info[k] = (x, z, _axis((prv[1], prv[2]), (nxt[1], nxt[2])))
    for seg in BRANCHES.values():
        for i, (k, x, z) in enumerate(seg):
            if not k or k in info:
                continue
            a, b = seg[max(0, i - 1)], seg[min(len(seg) - 1, i + 1)]
            info[k] = (x, z, _axis((a[1], a[2]), (b[1], b[2])))
    return info
