"""Coordinate helpers: location registry lookup, world bounds, map<->world transform.

Minecraft axes: +X east, +Z south, +Y up. The map<->world transform is used in Phase 2
to place the source-map's coastline/zones/rail polylines into world coordinates.
"""
from __future__ import annotations


def locations(layout: dict) -> list[dict]:
    return layout.get("locations", [])


def location(layout: dict, key: str) -> dict:
    for loc in locations(layout):
        if loc["key"] == key:
            return loc
    raise KeyError(f"no location with key {key!r}")


def world_bounds(layout: dict) -> tuple[int, int, int, int]:
    """(west_x, east_x, north_z, south_z) — approx landmass bounding box."""
    s = layout["scale"]
    return (int(s["west_x"]), int(s["east_x"]), int(s["north_z"]), int(s["south_z"]))


def map_to_world(px: float, pz: float, layout: dict) -> tuple[int, int]:
    """Source-map pixel (px, pz) -> world (x, z)."""
    m = layout["map"]
    bpp = float(m["blocks_per_pixel"])
    return (int(round(px * bpp + m["offset_x"])), int(round(pz * bpp + m["offset_z"])))


def in_border(x: float, z: float, layout: dict) -> bool:
    b = layout["world"]["border"]
    half = float(b["size"]) / 2.0
    return abs(x - float(b["center_x"])) <= half and abs(z - float(b["center_z"])) <= half
