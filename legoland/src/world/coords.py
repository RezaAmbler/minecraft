"""Coordinate helpers: land registry lookup + world frame.

Minecraft axes: +X east, +Z south, +Y up. Real-world -> block projection lives in
`src/terrain/transform.py` (the single source of truth); this module just looks up lands
and the configured world frame (spawn, border) from config.
"""
from __future__ import annotations


def lands(land_cfg: dict) -> list[dict]:
    return land_cfg.get("lands", [])


def land(land_cfg: dict, key: str) -> dict:
    for ld in lands(land_cfg):
        if ld["key"] == key:
            return ld
    raise KeyError(f"no land with key {key!r}")


def land_center(land_cfg: dict, key: str) -> tuple[int, int]:
    c = land(land_cfg, key)["center"]
    return int(c[0]), int(c[1])


def spawn_xyz(transform_cfg: dict) -> tuple[int, int, int]:
    sp = transform_cfg["world"]["spawn"]
    return int(sp[0]), int(sp[1]), int(sp[2])


def border(transform_cfg: dict) -> tuple[int, int, int]:
    """(center_x, center_z, size) for the world border."""
    w = transform_cfg["world"]
    cx, cz = w["border_center"]
    return int(cx), int(cz), int(w["border_size"])


def in_border(x: float, z: float, transform_cfg: dict) -> bool:
    cx, cz, size = border(transform_cfg)
    half = size / 2.0
    return abs(x - cx) <= half and abs(z - cz) <= half
