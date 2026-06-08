"""P2.3 — deterministic, vectorized heightfield for the island.

The canon map is not topographic, so elevation is AUTHORED (per decision in the plan):
gentle rolling hills everywhere, a snow-capped mountain massif, beaches that taper to the
coast, and a seabed that deepens offshore. All numpy + a seeded RNG => reproducible.
Produces 2-D arrays over a square region (side = island_width) centred on the world border.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image

from .geography import WorldGeometry, build_geometry

LOG = logging.getLogger("sodor.terrain.heightfield")

# --- vertical model (blocks) ---
BASE_Y = 48          # bottom of the solid terrain slab (below = void); 16-aligned
YMAX = 176           # top of the fill window (16-aligned); mountains stay below this
HILL_AMP = 12        # rolling-hill amplitude
MTN_AMP = 84         # mountain massif amplitude
ROCK_Y = 104         # bare stone above this height
SNOW_Y = 122         # snow above this height
TAPER = 18           # blocks over which land height tapers down to the shore
BEACH_CD = 3         # land within this many blocks of sea = sandy beach

# surface/solid-top block codes
AIR, GRASS, SAND, STONE, SNOW, GRAVEL, DIRT, WATER = range(8)
CODE_TO_BLOCK = {
    GRASS: ("grass_block", {"snowy": "false"}),
    SAND: ("sand", None),
    STONE: ("stone", None),
    SNOW: ("snow_block", None),
    GRAVEL: ("gravel", None),
    DIRT: ("dirt", None),
    WATER: ("water", {"level": "0"}),
    AIR: ("air", None),
}


@dataclass(frozen=True)
class HeightField:
    west: int
    north: int
    size: int
    land: np.ndarray      # bool [z,x]
    height: np.ndarray    # int16 [z,x]: land surface y, or seabed y for sea
    surf: np.ndarray      # uint8 [z,x]: top solid block code
    sea_level: int = 62


def _shift_or(m: np.ndarray) -> np.ndarray:
    out = m.copy()
    out[1:, :] |= m[:-1, :]
    out[:-1, :] |= m[1:, :]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out


def _distance_into(target: np.ndarray, source: np.ndarray, cap: int) -> np.ndarray:
    """Distance (1..cap) of each `target` cell from the `source` region; 0 outside target."""
    d = np.zeros(target.shape, np.int16)
    frontier = source.copy()
    for k in range(1, cap + 1):
        nb = _shift_or(frontier) & target & (d == 0)
        if not nb.any():
            break
        d[nb] = k
        frontier = nb
    d[target & (d == 0)] = cap  # interior beyond cap clamps to cap
    return d


def _octave(rng, cells: int, size: int) -> np.ndarray:
    base = (rng.random((cells, cells)) * 255).astype("uint8")
    img = Image.fromarray(base, "L").resize((size, size), Image.BICUBIC)
    return np.asarray(img).astype("float32") / 255.0


def _square_land(geo: WorldGeometry, west: int, north: int, size: int) -> np.ndarray:
    """Place the island bbox land grid into a size×size square at (west,north)."""
    land = np.zeros((size, size), bool)
    x_lo, x_hi = max(west, geo.west_x), min(west + size, geo.east_x)
    z_lo, z_hi = max(north, geo.north_z), min(north + size, geo.south_z)
    if x_hi > x_lo and z_hi > z_lo:
        land[z_lo - north:z_hi - north, x_lo - west:x_hi - west] = \
            geo.land[z_lo - geo.north_z:z_hi - geo.north_z, x_lo - geo.west_x:x_hi - geo.west_x]
    return land


def build_heightfield(ctx) -> HeightField:
    geo = build_geometry(ctx)
    w = ctx.layout["world"]
    sea_level = int(w["sea_level"])
    ground = int(w["ground_base"])
    size = int(ctx.layout["map"]["island_width_blocks"])
    cx = int(round(float(w["border"]["center_x"])))
    cz = int(round(float(w["border"]["center_z"])))
    west, north = cx - size // 2, cz - size // 2

    land = _square_land(geo, west, north, size)
    sea = ~land
    LOG.info("heightfield %dx%d, %.1f%% land; computing distances + noise…",
             size, size, 100 * land.mean())

    coast = _distance_into(land, sea, TAPER + 4)     # land->coast distance
    seadist = _distance_into(sea, land, 14)           # sea->shore distance

    rng = np.random.default_rng(int(w["seed"]))
    noise = 0.6 * _octave(rng, max(4, size // 64), size) + 0.4 * _octave(rng, max(8, size // 16), size)
    noise = (noise - noise.min()) / (noise.ptp() + 1e-6)

    # mountain massif (north-central), radial falloff, land only
    zz, xx = np.mgrid[0:size, 0:size]
    wx, wz = west + xx, north + zz
    mtn_cx, mtn_cz, mtn_r = cx, cz - 880, 560     # massif in the far north; southern lowland stays clear for rail
    dist = np.sqrt((wx - mtn_cx) ** 2 + (wz - mtn_cz) ** 2)
    dist = dist * (0.72 + 0.56 * noise)              # noisy radius -> irregular, non-circular massif
    mtn = np.clip(1.0 - dist / mtn_r, 0.0, 1.0) ** 1.7
    mtn = mtn * (0.78 + 0.44 * noise)                # ridged height variation across the range

    # land height: base + hills + mountains, then taper to the shore near the coast
    H = ground + noise * HILL_AMP + mtn * MTN_AMP
    shore = sea_level + 1
    t = np.clip(coast / TAPER, 0.0, 1.0)
    H_land = shore + t * (H - shore)

    # seabed: shallow at shore, deepening offshore
    seabed = sea_level - 1 - np.minimum(seadist, 12)

    height = np.where(land, np.rint(H_land), seabed).astype(np.int16)
    height = np.where(land, np.maximum(height, shore), height).astype(np.int16)

    # surface block codes
    surf = np.full((size, size), AIR, np.uint8)
    surf[land] = GRASS
    surf[land & (height >= ROCK_Y)] = STONE
    surf[land & (height >= SNOW_Y)] = SNOW
    surf[land & (coast <= BEACH_CD)] = SAND          # beaches override
    surf[sea] = np.where(seadist[sea] <= 5, SAND, GRAVEL)

    LOG.info("height range land: %d..%d", int(height[land].min()) if land.any() else 0,
             int(height[land].max()) if land.any() else 0)
    return HeightField(west=west, north=north, size=size, land=land,
                       height=height, surf=surf, sea_level=sea_level)
