"""Spawn welcome: a lectern + written book (and a header sign) beside the Thomas statue at the
Knapford spawn, greeting the player on arrival. Real block-entities (DECISIONS D19) — gated by
`[detailing].welcome`; the header sign is always placed, the written book only in "lectern" mode.
"""
from __future__ import annotations

import logging

LOG = logging.getLogger("sodor.welcome")

_PAGES = [
    "Welcome to the\nIsland of Sodor!\n\nHop aboard at\nKnapford and ride\nthe railway across\nthe whole island.",
    "Visit the docks at\nBrendam, climb to\nthe mountains, and\nmeet the engines\nat Tidmouth Sheds.",
    "Open the menu with\n/function sodor:menu\nto pick an engine\nto ride.\n\nHave fun!",
]
_SIGN = ["WELCOME TO", "THE ISLAND", "OF SODOR", "All aboard!"]


def place_welcome(ctx, ed) -> None:
    mode = ctx.layout.get("detailing", {}).get("welcome", "lectern")
    sp = ctx.layout["world"]["spawn"]
    sea = int(ctx.layout["world"]["sea_level"])
    # a small plaza just EAST of the Thomas statue (statue spans spawn.x +-4), facing the spawn
    wx, wz = int(sp["x"]) + 8, int(sp["z"]) - 14
    base = ed.surface_y(wx, wz) or (sea + 6)

    for fx in range(wx - 2, wx + 3):              # tidy quartz plaza + headroom
        for fz in range(wz - 2, wz + 3):
            ed.set(fx, base, fz, "smooth_quartz")
            for yy in range(base + 1, base + 5):
                ed.set(fx, yy, fz, "air")

    # header name-board (two posts + a backing) with a real wall sign facing the spawn (+Z)
    for px in (wx - 1, wx + 1):
        for dy in (1, 2, 3):
            ed.set(px, base + dy, wz - 1, "stripped_oak_log", {"axis": "y"})
    for px in range(wx - 1, wx + 2):
        ed.set(px, base + 2, wz - 1, "oak_planks")
        ed.set(px, base + 3, wz - 1, "oak_planks")
    ed.set_sign(wx, base + 2, wz, _SIGN, facing="south", wall=True)

    if mode == "lectern":
        ed.set(wx, base, wz, "polished_andesite")
        ed.set_lectern_book(wx, base + 1, wz, "south", "Welcome to Sodor",
                            "The Controller", _PAGES)
    LOG.info("welcome placed at (%d,%d) y=%d (mode=%s)", wx, wz, base, mode)
