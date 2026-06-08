"""Rides phase — datapack-driven rideable display-entity coaster trains.

Each coaster = a rig of block_display parts (datapack/rig.py) that follow a player-ridden
minecart via a per-tick `tp @e[parts] @s` (copies the cart's position + yaw). A kid clicks a
coaster in /function legoland:menu -> teleported into the train on the track -> rides the loop
(powered-rail boosters keep it rolling). One ride at a time (summon despawns the prior).

NOTE: ride feel / orientation can only be verified in-game (docs/TESTING.md + play-test loop).
Phase 1 prototypes ONE rig end-to-end: The Dragon.
"""
from __future__ import annotations

import json
import logging

from ..datapack import rig
from ..datapack.writer import Datapack
from ..rail import coaster
from ..terrain.heightfield import build_heightfield

LOG = logging.getLogger("legoland.rides")


def _tellraw(target: str, component) -> str:
    return f"tellraw {target} {json.dumps(component)}"


def run(ctx) -> None:
    dp = Datapack(ctx.datapack_out, ctx, description="LEGOLAND California — rides & mechanics")
    hf = build_heightfield(ctx)

    coasters = coaster.mvp_coasters(ctx.rides)
    if not coasters:
        LOG.warning("no MVP coaster with a route — no ride functions generated")
        return

    for ride in coasters:
        plan = coaster.plan_coaster(hf, ride, ctx.transform)
        b = plan.cells[plan.boarding_idx]
        board = f"{b.x + 0.5:.1f} {b.y + 0.2:.1f} {b.z + 0.5:.1f}"
        cart_nbt = '{Tags:["legoland.cart"],CustomName:\'' + json.dumps(ride["name"]) + "'}"
        lines = [
            f"# board {ride['name']}",
            "kill @e[tag=legoland.part]",
            "kill @e[tag=legoland.cart]",
            f"tp @s {board}",
            f"summon minecart {board} {cart_nbt}",
            *rig.summon_lines(ride, []),
            "execute as @e[tag=legoland.cart,limit=1] at @s run tp @e[tag=legoland.part] @s",
            "ride @s mount @e[tag=legoland.cart,limit=1,sort=nearest]",
            _tellraw("@s", {"text": f"All aboard {ride['name']}! Hold on tight!", "color": "aqua"}),
        ]
        dp.function("legoland", f"ride/summon/{ride['key']}", lines)

    # per-tick: each train rig follows its cart (position + yaw)
    tick = dp.function("legoland", "ride/tick", [
        "# coaster train rig follows its minecart (copies position + yaw)",
        "execute as @e[tag=legoland.cart,limit=1] at @s run tp @e[tag=legoland.part] @s",
    ])
    dp.add_tick(tick)

    # exit / put away
    dp.function("legoland", "ride/stop", [
        "ride @s dismount",
        "kill @e[tag=legoland.part]",
        "kill @e[tag=legoland.cart]",
        _tellraw("@s", {"text": "Ride over! Type /function legoland:menu to ride again.",
                        "color": "yellow"}),
    ])

    # clickable coaster menu (master menu added by the mechanics phase)
    dp.function("legoland", "ride/menu", rig.coaster_menu_lines(coasters))

    # load greeting
    load = dp.function("legoland", "ride/load", [
        "scoreboard objectives add legoland.tmp dummy",
        _tellraw("@a", {"text": "Welcome to LEGOLAND California!", "color": "green"}),
        _tellraw("@a", ["", {"text": "/function legoland:menu", "color": "aqua", "bold": True},
                        {"text": " to ride a coaster!", "color": "green"}]),
    ])
    dp.add_load(load)

    LOG.info("rides complete: %d rideable coaster(s)", len(coasters))
