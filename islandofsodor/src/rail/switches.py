"""Lever-operated branch switches (P3.8).

A Minecraft rail connects to at most two neighbours, so a three-way split must be a single
redstone-switched rail: unpowered it runs straight along the main line, powered it curves
onto the branch (minecraft.wiki — the exact power->which-curve polarity is confirmed
in-game; this geometry is polarity-agnostic, see D17). Both branches leave their main-line
station heading SOUTH while the cart runs EAST, so the two junctions are geometrically
identical.

Layout at a junction (cart travels +X / east; branch departs +Z / south), all at rail Y `jy`:

        (jx, jz-2)  redstone_lamp        <- active-route indicator (north / platform side)
        (jx, jz-1)  polished_blackstone  <- switch stand; lever on top powers it
                      ^ lever             strongly powers the stand, which is adjacent to
        (jx-1,jz) -- (jx,jz) -- (jx+1,jz)   both the junction rail (south) and the lamp (north)
         slow       SWITCH      booster
                      |
                   (jx,jz+1)  branch tee (north_south)
                   (jx,jz+2)  branch booster

The switch stand sits on the main line's north shoulder (off the running line), so the lever
is reachable from the platform and a coasting cart slows on the unpowered `slow` cell, giving
a child time to throw it.
"""
from __future__ import annotations

# name -> junction definition. switch_xz is a main-line waypoint (route.MAIN_LOOP), so the
# gridded main path passes through it exactly. dirs: cart approaches from the west, continues
# east, branch departs south. branch = the branch key in route.BRANCHES.
JUNCTIONS: dict[str, dict] = {
    "knapford":   {"branch": "ffarquhar", "switch_xz": (-850, 430)},
    "wellsworth": {"branch": "brendam",   "switch_xz": (-250, 470)},
}

# direction vectors (layout.toml convention: +X=east, +Z=south)
_APPROACH = (-1, 0)   # west  — the slowing cell
_MAIN_OUT = (1, 0)    # east  — main continues
_BRANCH = (0, 1)      # south — branch departs


def exit_cells(name: str) -> dict:
    """Key (x,z) cells around the junction — shared by the layer and the validator so the
    switch-state reachability model and the stamped blocks agree."""
    jx, jz = JUNCTIONS[name]["switch_xz"]
    return {
        "switch": (jx, jz),
        "approach": (jx + _APPROACH[0], jz + _APPROACH[1]),     # (jx-1, jz)
        "main_out": (jx + _MAIN_OUT[0], jz + _MAIN_OUT[1]),     # (jx+1, jz)
        "branch_tee": (jx + _BRANCH[0], jz + _BRANCH[1]),       # (jx, jz+1)
        "branch_out": (jx + 2 * _BRANCH[0], jz + 2 * _BRANCH[1]),  # (jx, jz+2)
        "stand": (jx - _BRANCH[0], jz - _BRANCH[1]),            # (jx, jz-1) north shoulder
        "lamp": (jx - 2 * _BRANCH[0], jz - 2 * _BRANCH[1]),     # (jx, jz-2)
    }


def expected_rail(name: str, jy: int) -> dict:
    """The rail cells `stamp_junction` writes -> (y, type, shape). The validator overlays this
    over the plan so it checks what is actually on disk at the junction."""
    c = exit_cells(name)
    return {
        c["approach"]:   (jy, "rail", "east_west"),
        c["switch"]:     (jy, "rail", "east_west"),       # unpowered default = stay on main
        c["main_out"]:   (jy, "powered_rail", "east_west"),
        c["branch_tee"]: (jy, "rail", "north_south"),
        c["branch_out"]: (jy, "powered_rail", "north_south"),
    }


def stamp_junction(ed, name: str, jy: int) -> None:
    """Override the junction neighbourhood into a proper lever switch (run AFTER both the main
    line and the branch are laid; this is authoritative for the cells it owns)."""
    c = exit_cells(name)

    def rail(xz, shape, powered=False):
        x, z = xz
        ed.set(x, jy - 1, z, "redstone_block" if powered else "gravel")
        props = {"shape": shape}
        if powered:
            props["powered"] = "true"
        ed.set(x, jy, z, "powered_rail" if powered else "rail", props)
        for dy in range(1, 4):
            ed.set(x, jy + dy, z, "air")

    # main line through the switch: slow (plain) -> SWITCH (straight default) -> booster
    rail(c["approach"], "east_west")
    rail(c["switch"], "east_west")                 # unpowered default = stay on main
    rail(c["main_out"], "east_west", powered=True)
    # branch: tee (north_south) -> booster, both level with the junction
    rail(c["branch_tee"], "north_south")
    rail(c["branch_out"], "north_south", powered=True)

    # switch stand (powers the adjacent junction rail when the lever is on) + lever + lamp
    sx, sz = c["stand"]
    ed.set(sx, jy - 1, sz, "stone")
    ed.set(sx, jy, sz, "polished_blackstone")
    ed.set(sx, jy + 1, sz, "lever", {"face": "floor", "facing": "south", "powered": "false"})
    lx, lz = c["lamp"]
    ed.set(lx, jy - 1, lz, "stone")
    ed.set(lx, jy, lz, "redstone_lamp", {"lit": "false"})
    ed.set(lx, jy + 1, lz, "air")
