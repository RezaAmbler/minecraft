"""Heightfield for the park, derived from the compressed real-world transform.

Unlike Sodor (which extracted an island mask from a reference image), the LEGOLAND terrain
is the real USGS 3DEP elevation surface, horizontally compressed and vertically exaggerated
by `src/terrain/transform.py`. Phase 1 produces a solid grassy hillside over the whole park
footprint; the central lake + paths are carved in a later phase.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import transform as T

# surface/material codes
AIR, GRASS, DIRT, STONE, WATER, SAND = 0, 1, 2, 3, 4, 5
CODE_TO_BLOCK = {
    AIR:   ("air", None),
    GRASS: ("grass_block", {"snowy": "false"}),
    DIRT:  ("dirt", None),
    STONE: ("stone", None),
    WATER: ("water", {"level": "0"}),
    SAND:  ("sand", None),
}

FLOOR_Y = 48        # bottom of the solid slab (everything below is void/air)
SUBSOIL = 3         # dirt thickness directly under the grass surface


@dataclass
class HeightField:
    x0: int                 # west-most block X (column 0)
    z0: int                 # north-most block Z (row 0)
    nx: int
    nz: int
    ground: np.ndarray      # [nz, nx] int16 surface (top solid) block Y
    water_y: int            # fill water on columns whose ground < water_y (FLOOR_Y-1 disables)


def build_heightfield(ctx) -> HeightField:
    tr = T.load_transform(ctx.config_dir)
    dem = T.load_dem()
    hf = T.heightfield(tr, dem, ctx.config_dir)     # x0, z0, elev_m, ground_y over park bounds
    ground = hf.ground_y.astype(np.int16)
    nz, nx = ground.shape
    # Phase 1: no lake yet -> water disabled. (Phase 2 sets water_y = tr.block_y(lake_elev_m).)
    return HeightField(x0=hf.x0, z0=hf.z0, nx=nx, nz=nz, ground=ground, water_y=FLOOR_Y - 1)


def ground_at(hf: HeightField, x: int, z: int) -> int | None:
    """Surface Y at world (x, z), or None if outside the park footprint."""
    ix, iz = x - hf.x0, z - hf.z0
    if 0 <= ix < hf.nx and 0 <= iz < hf.nz:
        return int(hf.ground[iz, ix])
    return None
