"""Generate a coaster train's display-entity rig as /summon commands (block_display parts).

The rig is built in the train's local frame with forward = local -Z (nose at most-negative Z).
The per-tick follow (`tp @e[parts] @s` to the cart) copies the cart's position + yaw, so the
train rotates with travel. Each part is a scaled, translated block_display;
transformation.translation is the bottom corner, centred in X/Z. Phase 1 prototypes ONE rig
end-to-end (The Dragon); ride feel / orientation are tuned from the play-test log.
"""
from __future__ import annotations

import json


def coaster_menu_lines(coasters: list[dict]) -> list[str]:
    """Clickable tellraw list of the rideable coasters (used by the master menu)."""
    out = ["tellraw @s " + json.dumps({"text": "=== Ride a coaster ===", "color": "gold", "bold": True})]
    for c in coasters:
        fid = f"legoland:ride/summon/{c['key']}"
        out.append("tellraw @s " + json.dumps(["",
            {"text": "  ▶ ", "color": "gray"},
            {"text": c["name"], "color": "aqua", "bold": True,
             "clickEvent": {"action": "run_command", "command": "/function " + fid}},
            {"text": "  (" + c.get("land", "").replace("_", " ") + ")", "color": "dark_gray"}]))
    out.append("tellraw @s " + json.dumps(["",
        {"text": "  ■ Exit ride", "color": "red",
         "clickEvent": {"action": "run_command", "command": "/function legoland:ride/stop"}}]))
    return out


def _part(block, cx, by, cz, sx, sy, sz):
    """(block, center_x, bottom_y, center_z, size...) -> (block, translation, scale)."""
    return (block, (cx - sx / 2, by, cz - sz / 2), (sx, sy, sz))


def coaster_parts(ride: dict):
    """A blocky LEGO coaster train: a dragon-headed lead car + two passenger cars.
    Forward is local -Z (nose forward)."""
    main = ride.get("train_main", "red_concrete")
    trim = ride.get("train_trim", "gold_block")
    acc = ride.get("train_accent", "lime_concrete")     # dragon green
    parts = [
        _part(trim, 0, -0.1, 0.0, 2.0, 0.4, 7.2),       # chassis / frame
        # --- lead car: the dragon ---
        _part(main, 0, 0.3, -2.2, 1.8, 1.2, 2.4),       # lead car body
        _part(trim, 0, 1.45, -2.2, 1.9, 0.2, 2.5),      # lead car rim
        _part(acc, 0, 1.0, -3.3, 1.4, 1.1, 1.4),        # dragon head
        _part(acc, -0.5, 2.0, -3.1, 0.35, 0.8, 0.35),   # left horn
        _part(acc, 0.5, 2.0, -3.1, 0.35, 0.8, 0.35),    # right horn
        _part("yellow_concrete", -0.42, 1.35, -3.95, 0.26, 0.26, 0.16),  # left eye
        _part("yellow_concrete", 0.42, 1.35, -3.95, 0.26, 0.26, 0.16),   # right eye
        _part("orange_concrete", 0, 0.85, -4.0, 1.0, 0.45, 0.2),         # mouth / fire glow
        _part(acc, -1.15, 0.9, -2.0, 0.8, 0.45, 1.8),   # left wing
        _part(acc, 1.15, 0.9, -2.0, 0.8, 0.45, 1.8),    # right wing
        # --- passenger cars ---
        _part(main, 0, 0.3, 0.2, 1.8, 1.0, 1.8),        # car 2
        _part(trim, 0, 1.15, 0.2, 1.9, 0.2, 1.9),       # car 2 rim
        _part(main, 0, 0.3, 2.4, 1.8, 1.0, 1.8),        # car 3
        _part(trim, 0, 1.15, 2.4, 1.9, 0.2, 1.9),       # car 3 rim
    ]
    return parts


def _f(v: float) -> str:
    return f"{v:.3f}f"


def summon_lines(ride: dict, extra_tags: list[str]) -> list[str]:
    key = ride["key"]
    tags = ['"legoland.part"', f'"legoland.{key}"', *[f'"{t}"' for t in extra_tags]]
    tagstr = ",".join(tags)
    lines = []
    for block, (tx, ty, tz), (sx, sy, sz) in coaster_parts(ride):
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
