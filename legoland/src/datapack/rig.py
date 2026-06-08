"""Generate an engine's display-entity rig as /summon commands (block_display parts).

The rig is built in the entity's local frame with forward = local +Z. The per-tick follow
(`tp @e[parts] @s` to the cart) copies the cart's yaw, so the loco rotates with travel.
Each part is a scaled, translated block_display; transformation.translation is the bottom
corner, centred in X/Z. Resource-pack faces come in Phase 7; here a white face plate stands in.
"""
from __future__ import annotations

import json


def engine_menu_lines(engines: list[dict]) -> list[str]:
    """Clickable tellraw list of the engines (used by the master menu)."""
    out = ["tellraw @s " + json.dumps({"text": "=== Ride an engine ===", "color": "gold", "bold": True})]
    for e in engines:
        fid = f"sodor:engine/summon/{e['key']}"
        out.append("tellraw @s " + json.dumps(["",
            {"text": "  ▶ ", "color": "gray"},
            {"text": e["name"], "color": "aqua", "bold": True,
             "clickEvent": {"action": "run_command", "command": "/function " + fid}},
            {"text": f"  (#{e['number']} — {e['color_name']})", "color": "dark_gray"}]))
    out.append("tellraw @s " + json.dumps(["",
        {"text": "  ■ Put engine away", "color": "red",
         "clickEvent": {"action": "run_command", "command": "/function sodor:engine/stop"}}]))
    return out


def _part(block, cx, by, cz, sx, sy, sz):
    """(block, center_x, bottom_y, center_z, size...) -> (block, translation, scale)."""
    return (block, (cx - sx / 2, by, cz - sz / 2), (sx, sy, sz))


def engine_parts(engine: dict):
    main = engine["block_main"]
    trim = engine["block_trim"]
    typ = engine.get("type", "tank")
    parts = [
        _part(trim, 0, -0.1, 0.0, 2.0, 0.5, 6.0),     # chassis / wheels
        _part(trim, 0, 0.1, -3.0, 2.2, 0.5, 0.4),     # front buffer beam
    ]
    if typ == "tram":  # Toby — boxy tram with side plates + roof
        parts += [
            _part(main, 0, 0.3, 0.0, 2.2, 2.2, 5.2),
            _part(trim, 0, 2.5, 0.0, 2.4, 0.4, 5.4),  # roof
            _part("white_concrete", 0, 0.6, -2.7, 1.6, 1.4, 0.3),  # face plate (front)
        ]
    else:  # tank / tender steam loco
        parts += [
            _part(main, 0, 0.4, -1.0, 1.8, 1.7, 4.0),   # boiler
            _part("white_concrete", 0, 0.6, -2.95, 1.5, 1.4, 0.3),  # face plate
            _part(trim, 0, 2.0, -2.1, 0.8, 0.9, 0.8),   # funnel
            _part(trim, 0, 2.0, -0.5, 0.8, 0.5, 0.8),   # dome
            _part(main, 0, 0.4, 1.7, 2.0, 1.9, 2.0),    # cab
            _part(trim, 0, 2.3, 1.7, 2.2, 0.4, 2.2),    # cab roof
        ]
        if typ == "tender":
            parts += [
                _part(trim, 0, 0.0, 3.4, 2.2, 0.4, 2.8),
                _part(main, 0, 0.3, 3.4, 2.0, 1.4, 2.6),  # tender
            ]

    # cheery blocky face on the front plate (eyes + a smile) — the signature Thomas look,
    # built from blocks so it needs no resource pack textures.
    face_cz = -2.7 if typ == "tram" else -2.95
    fz = face_cz - 0.18                     # just in front of the white plate
    eye_y = 1.2 if typ == "tram" else 1.05
    parts += [
        _part("black_concrete", -0.42, eye_y, fz, 0.34, 0.34, 0.16),   # left eye
        _part("black_concrete", 0.42, eye_y, fz, 0.34, 0.34, 0.16),    # right eye
        _part("black_concrete", -0.45, eye_y - 0.55, fz, 0.32, 0.16, 0.16),  # smile (up-left)
        _part("black_concrete", 0.0, eye_y - 0.68, fz, 0.42, 0.16, 0.16),    # smile (centre)
        _part("black_concrete", 0.45, eye_y - 0.55, fz, 0.32, 0.16, 0.16),   # smile (up-right)
    ]
    return parts


def _f(v: float) -> str:
    return f"{v:.3f}f"


def summon_lines(engine: dict, extra_tags: list[str]) -> list[str]:
    key = engine["key"]
    tags = ['"sodor.part"', f'"sodor.{key}"', *[f'"{t}"' for t in extra_tags]]
    tagstr = ",".join(tags)
    lines = []
    for block, (tx, ty, tz), (sx, sy, sz) in engine_parts(engine):
        nbt = (
            "{Tags:[" + tagstr + "],"
            f'block_state:{{Name:"minecraft:{block}"}},'
            "transformation:{translation:[" + ",".join(_f(v) for v in (tx, ty, tz)) + "],"
            "scale:[" + ",".join(_f(v) for v in (sx, sy, sz)) + "],"
            "left_rotation:[0f,0f,0f,1f],right_rotation:[0f,0f,0f,1f]},"
            "brightness:{block:15,sky:15},teleport_duration:2,interpolation_duration:2,"
            'billboard:"fixed"}'
        )
        lines.append(f"summon block_display ~ ~ ~ {nbt}")
    return lines
