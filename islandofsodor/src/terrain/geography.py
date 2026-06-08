"""P2.2 — fit the extracted Sodor mask into world coordinates and produce a
world-resolution land grid that terrain generation samples directly.

The island is scaled (preserving aspect) to `map.island_width_blocks` and centred on
`world.border`. Returns a bool grid indexed [z - north, x - west].
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from . import source_map

LOG = logging.getLogger("sodor.terrain.geography")


@dataclass(frozen=True)
class WorldGeometry:
    land: np.ndarray      # bool grid [z_idx, x_idx]; True = land
    west_x: int           # world X of column 0
    north_z: int          # world Z of row 0
    width: int            # E-W extent in blocks (== land.shape[1])
    height: int           # N-S extent in blocks (== land.shape[0])

    @property
    def east_x(self) -> int:
        return self.west_x + self.width

    @property
    def south_z(self) -> int:
        return self.north_z + self.height

    def is_land(self, x: int, z: int) -> bool:
        xi, zi = x - self.west_x, z - self.north_z
        if 0 <= zi < self.height and 0 <= xi < self.width:
            return bool(self.land[zi, xi])
        return False


def map_path(ctx) -> Path:
    return source_map.Path(ctx.layout["map"]["source_image"])  # repo-relative


def build_geometry(ctx) -> WorldGeometry:
    mask = source_map.extract_sodor_mask(ctx.layout["map"]["source_image"])
    x0, y0, x1, y1 = source_map.island_bbox(mask)
    pw, ph = (x1 - x0 + 1), (y1 - y0 + 1)

    width = int(ctx.layout["map"]["island_width_blocks"])
    height = int(round(width * ph / pw))
    cx = float(ctx.layout["world"]["border"]["center_x"])
    cz = float(ctx.layout["world"]["border"]["center_z"])
    west = int(round(cx - width / 2.0))
    north = int(round(cz - height / 2.0))

    crop = mask[y0:y1 + 1, x0:x1 + 1]
    img = Image.fromarray(np.where(crop, 255, 0).astype("uint8"), "L").resize(
        (width, height), Image.NEAREST)
    land = np.asarray(img) > 127

    LOG.info("world geometry: island %dx%d blocks at world x[%d..%d] z[%d..%d], %.1f%% land",
             width, height, west, west + width, north, north + height, 100 * land.mean())
    return WorldGeometry(land=land, west_x=west, north_z=north, width=width, height=height)
