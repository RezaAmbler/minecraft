"""Datapack mechanics (thin in-repo writer; beet not used — DECISIONS LD1/Sodor D3).

On top of the rides datapack this adds: a load-time `setup` that re-asserts the kid-safe
settings (locked clear midday, peaceful, no damage), floating land-name labels (text_display,
also navigation), teleport hubs to each land, and a clickable master menu.
"""
from __future__ import annotations

import json
import logging

from ..terrain.heightfield import build_heightfield, ground_at
from .writer import Datapack

LOG = logging.getLogger("legoland.datapack")


def _tellraw(target, comp) -> str:
    return f"tellraw {target} {json.dumps(comp)}"


def run(ctx) -> None:
    dp = Datapack(ctx.datapack_out, ctx, description="LEGOLAND California — rides & mechanics")
    hf = build_heightfield(ctx)
    lands = ctx.lands.get("lands", [])
    built = [ld for ld in lands if ld.get("mvp")]      # Phase 1: Castle Hill only

    def gy(x, z, default=80):
        g = ground_at(hf, x, z)
        return g if g is not None else default

    # --- setup on load: re-assert kid-safe world settings ---
    setup = dp.function("legoland", "setup", [
        "gamerule doDaylightCycle false", "gamerule doWeatherCycle false",
        "gamerule doMobSpawning false", "gamerule doFireTick false", "gamerule mobGriefing false",
        "gamerule keepInventory true", "gamerule fallDamage false", "gamerule fireDamage false",
        "gamerule drowningDamage false", "gamerule doImmediateRespawn true",
        "gamerule sendCommandFeedback false", "gamerule doInsomnia false",
        "difficulty peaceful", "time set 6000", "weather clear 1000000",
    ])
    dp.add_load(setup)

    # --- floating land-name labels (navigation + flavour) ---
    label_lines = ["kill @e[tag=legoland.label]"]
    for ld in built:
        x, z = int(ld["center"][0]), int(ld["center"][1])
        comp = json.dumps({"text": ld["name"], "color": "gold", "bold": True})
        ty = gy(x, z, 88) + 24
        label_lines.append(
            f"summon text_display {x} {ty} {z} "
            '{Tags:["legoland.label"],text:\'' + comp + "',billboard:\"center\","
            "transformation:{translation:[0f,0f,0f],scale:[4f,4f,4f],"
            "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]},"
            "brightness:{block:15,sky:15},background:0}"
        )
    place_labels = dp.function("legoland", "labels/place", label_lines)
    dp.add_load(place_labels)

    # --- teleport hubs (one goto per land; Phase 1 has Castle Hill, others come online later) ---
    travel = []
    for ld in lands:
        x, z = int(ld["center"][0]), int(ld["center"][1])
        ty = gy(x, z, 80) + 1
        fid = dp.function("legoland", f"travel/goto/{ld['key']}", [
            f"tp @s {x + 0.5:.1f} {ty} {z + 0.5:.1f} 0 0",
            _tellraw("@s", {"text": f"Welcome to {ld['name']}!", "color": "green"}),
        ])
        travel.append((ld["name"], fid, bool(ld.get("mvp"))))

    # travel menu (built lands first, the rest greyed but reachable)
    tmenu = ["tellraw @s " + json.dumps({"text": "=== Travel to a land ===", "color": "gold", "bold": True})]
    for name, fid, is_built in sorted(travel, key=lambda t: (not t[2], t[0])):
        tmenu.append("tellraw @s " + json.dumps(["",
            {"text": "  ✦ ", "color": "gray"},
            {"text": name, "color": "aqua" if is_built else "gray", "bold": is_built,
             "clickEvent": {"action": "run_command", "command": "/function " + fid}}]))
    dp.function("legoland", "travel/menu", tmenu)

    # master menu
    dp.function("legoland", "menu", [
        "tellraw @s " + json.dumps({"text": "===== LEGOLAND California =====", "color": "gold", "bold": True}),
        "tellraw @s " + json.dumps(["", {"text": "  ▶ Ride a coaster", "color": "aqua", "bold": True,
            "clickEvent": {"action": "run_command", "command": "/function legoland:ride/menu"}}]),
        "tellraw @s " + json.dumps(["", {"text": "  ✦ Travel to a land", "color": "green", "bold": True,
            "clickEvent": {"action": "run_command", "command": "/function legoland:travel/menu"}}]),
    ])

    LOG.info("mechanics: setup + %d travel hubs + %d labels", len(travel), len(built))
