"""Phase 6 — Datapack mechanics (thin in-repo writer; beet not used — DECISIONS D3).

On top of the engine datapack (Phase 5) this adds: a load-time `setup` that re-asserts the
kid-safe settings (locked clear midday, peaceful, no damage), floating station-name labels
(text_display, also navigation), teleport hubs between stations, and a clickable master menu.
"""
from __future__ import annotations

import json
import logging

from .writer import Datapack
from ..rail import route
from ..terrain.heightfield import build_heightfield

LOG = logging.getLogger("sodor.datapack")


def _tellraw(target, comp) -> str:
    return f"tellraw {target} {json.dumps(comp)}"


def _axes(axis):
    return ((1, 0), (0, 1)) if axis == "ew" else ((0, 1), (1, 0))


def run(ctx) -> None:
    dp = Datapack(ctx.datapack_out, ctx, description="Island of Sodor — engines & mechanics")
    hf = build_heightfield(ctx)
    info = route.station_info()
    locs = {loc["key"]: loc for loc in ctx.layout.get("locations", [])}
    sea = int(ctx.layout["world"]["sea_level"])

    def hy(x, z, default):
        xi, zi = x - hf.west, z - hf.north
        return int(hf.height[zi, xi]) if (0 <= xi < hf.size and 0 <= zi < hf.size) else default

    # --- setup on load: re-assert kid-safe world settings ---
    setup = dp.function("sodor", "setup", [
        "gamerule doDaylightCycle false", "gamerule doWeatherCycle false",
        "gamerule doMobSpawning false", "gamerule doFireTick false", "gamerule mobGriefing false",
        "gamerule keepInventory true", "gamerule fallDamage false", "gamerule fireDamage false",
        "gamerule drowningDamage false", "gamerule doImmediateRespawn true",
        "gamerule sendCommandFeedback false", "gamerule doInsomnia false",
        "difficulty peaceful", "time set 6000", "weather clear 1000000",
    ])
    dp.add_load(setup)

    # --- floating station-name labels (navigation + flavour) ---
    label_lines = ["kill @e[tag=sodor.label]"]
    for key, (x, z, axis) in info.items():
        if key not in locs:
            continue
        comp = json.dumps({"text": locs[key]["name"], "color": "white", "bold": True})
        ty = hy(x, z, sea + 8) + 12
        label_lines.append(
            f"summon text_display {x} {ty} {z} "
            '{Tags:["sodor.label"],text:\'' + comp + "',billboard:\"center\","
            "transformation:{translation:[0f,0f,0f],scale:[2.5f,2.5f,2.5f],"
            "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]},"
            "brightness:{block:15,sky:15},background:0}"
        )
    # registry nameplates (e.g. the Thomas statue at spawn) — same text_display style
    from ..structures import resolve_placement
    for entry in ctx.layout.get("structures", []):
        if not entry.get("label"):
            continue
        bx, bz, _facing = resolve_placement(ctx, entry)
        comp = json.dumps({"text": entry["label"], "color": "aqua", "bold": True})
        ty = hy(bx, bz, sea + 8) + 15
        label_lines.append(
            f"summon text_display {bx} {ty} {bz} "
            '{Tags:["sodor.label"],text:\'' + comp + "',billboard:\"center\","
            "transformation:{translation:[0f,0f,0f],scale:[3f,3f,3f],"
            "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]},"
            "brightness:{block:15,sky:15},background:0}"
        )

    place_labels = dp.function("sodor", "labels/place", label_lines)
    dp.add_load(place_labels)

    # --- teleport hubs (one goto per MVP station) ---
    travel = []
    for key, (x, z, axis) in info.items():
        if key not in locs or not locs[key].get("mvp"):
            continue
        A, P = _axes(axis)
        ox, oz = x + P[0] * 3, z + P[1] * 3      # platform side, just off the track
        ty = hy(ox, oz, sea + 8) + 2
        fid = dp.function("sodor", f"travel/goto/{key}", [
            f"tp @s {ox + 0.5:.1f} {ty} {oz + 0.5:.1f} 0 0",
            _tellraw("@s", {"text": f"Welcome to {locs[key]['name']}!", "color": "green"}),
        ])
        travel.append((locs[key]["name"], fid))

    # travel menu
    tmenu = ["tellraw @s " + json.dumps({"text": "=== Travel to a station ===", "color": "gold", "bold": True})]
    for name, fid in travel:
        tmenu.append("tellraw @s " + json.dumps(["",
            {"text": "  ✈ ", "color": "gray"},
            {"text": name, "color": "aqua", "bold": True,
             "clickEvent": {"action": "run_command", "command": "/function " + fid}}]))
    dp.function("sodor", "travel/menu", tmenu)

    # master menu
    dp.function("sodor", "menu", [
        "tellraw @s " + json.dumps({"text": "====== Island of Sodor ======", "color": "gold", "bold": True}),
        "tellraw @s " + json.dumps(["", {"text": "  ▶ Ride an engine", "color": "aqua", "bold": True,
            "clickEvent": {"action": "run_command", "command": "/function sodor:engine/menu"}}]),
        "tellraw @s " + json.dumps(["", {"text": "  ✈ Travel to a station", "color": "green", "bold": True,
            "clickEvent": {"action": "run_command", "command": "/function sodor:travel/menu"}}]),
    ])

    LOG.info("Phase 6 mechanics: setup + %d travel hubs + %d labels", len(travel),
             sum(1 for k in info if k in locs))
