"""Phase 5 — Engines (datapack-driven rideable display-entity rigs).

Each engine = a rig of block_display parts (datapack/rig.py) that follow a player-ridden
minecart via a per-tick `tp @e[parts] @s` (copies the cart's position + yaw). A kid clicks
an engine in /function sodor:menu -> teleported onto the track in that engine -> rides the
loop (powered-rail boosters keep it rolling). One engine at a time (summon despawns the prior).

NOTE: ride feel / orientation can only be verified in-game (see docs/TESTING.md + the
play-test log loop). Structure here is validated; tuning happens from play-test feedback.
"""
from __future__ import annotations

import json
import logging

from ..datapack.writer import Datapack
from ..datapack import rig
from ..rail import grid, route
from ..terrain.heightfield import build_heightfield

LOG = logging.getLogger("sodor.entities")


def _tellraw(target: str, component) -> str:
    return f"tellraw {target} {json.dumps(component)}"


def run(ctx) -> None:
    dp = Datapack(ctx.datapack_out, ctx, description="Island of Sodor — engines & mechanics")

    # boarding point: the main-loop rail cell nearest Knapford (kid spawns here)
    hf = build_heightfield(ctx)
    cells = grid.plan_network(hf, ctx.layout)["main"]
    kx, kz = route.stations()["knapford"]
    b = min(cells, key=lambda c: (c.x - kx) ** 2 + (c.z - kz) ** 2)
    board = f"{b.x + 0.5:.1f} {b.y + 0.2:.1f} {b.z + 0.5:.1f}"

    engines = ctx.engines["roster"]
    summon_ids = []
    for e in engines:
        # SNBT CustomName is a single-quoted JSON text component, e.g. CustomName:'"Thomas"'
        cart_nbt = "{Tags:[\"sodor.cart\"],CustomName:'" + json.dumps(e["name"]) + "'}"
        lines = [
            f"# summon {e['name']} (#{e['number']})",
            "kill @e[tag=sodor.part]",
            "kill @e[tag=sodor.cart]",
            f"tp @s {board}",
            f"summon minecart {board} {cart_nbt}",
            *rig.summon_lines(e, []),
            "execute as @e[tag=sodor.cart,limit=1] at @s run tp @e[tag=sodor.part] @s",
            "ride @s mount @e[tag=sodor.cart,limit=1,sort=nearest]",
            _tellraw("@s", {"text": f"All aboard {e['name']}! Enjoy the ride around Sodor.",
                            "color": "aqua"}),
        ]
        fid = dp.function("sodor", f"engine/summon/{e['key']}", lines)
        summon_ids.append((e, fid))

    # per-tick: each rig follows its cart (position + yaw)
    tick = dp.function("sodor", "engine/tick", [
        "# engine rig follows its minecart (copies position + yaw)",
        "execute as @e[tag=sodor.cart,limit=1] at @s run tp @e[tag=sodor.part] @s",
    ])
    dp.add_tick(tick)

    # stop / put away
    dp.function("sodor", "engine/stop", [
        "ride @s dismount",
        "kill @e[tag=sodor.part]",
        "kill @e[tag=sodor.cart]",
        _tellraw("@s", {"text": "Engine put away. Type /function sodor:menu to ride again.",
                        "color": "yellow"}),
    ])

    # clickable engine menu (master menu added by the mechanics phase)
    dp.function("sodor", "engine/menu", rig.engine_menu_lines(engines))

    # load: objective + greeting (mechanics phase adds more)
    load = dp.function("sodor", "engine/load", [
        "scoreboard objectives add sodor.tmp dummy",
        _tellraw("@a", {"text": "Welcome to the Island of Sodor! Type ",
                        "color": "green"}),
        _tellraw("@a", ["", {"text": "/function sodor:menu", "color": "aqua", "bold": True},
                        {"text": " to pick an engine and ride!", "color": "green"}]),
    ])
    dp.add_load(load)

    LOG.info("Phase 5 engines complete: %d engines, board point %s", len(engines), board)
