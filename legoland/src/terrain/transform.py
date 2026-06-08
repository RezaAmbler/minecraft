"""Real-world -> block COMPRESSED transform for LEGOLAND California.

Turns GPS (lat, lon, elevation) into Minecraft block coordinates by:
  1. equirectangular projection about the park centroid  ->  local metres,
  2. horizontal compression (metres / compression_factor)  ->  block X/Z,
  3. vertical mapping with exaggeration                    ->  block Y.

The USGS 3DEP elevation grid (references/dem_grid.csv, public domain) is bilinearly
interpolated so any block in the park footprint gets a real relative elevation. This
module is the single source of truth for the transform; Phase-1 terrain consumes
`heightfield()`. Run it directly to emit a preview PNG + sanity report:

    python -m src.terrain.transform
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .. import config as cfg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEM_GRID = REPO_ROOT / "references" / "dem_grid.csv"
PREVIEW = REPO_ROOT / "heightmaps" / "transform_preview.png"

M_PER_DEG_LAT = 111_320.0


@dataclass(frozen=True)
class Transform:
    centroid_lat: float
    centroid_lon: float
    m_per_deg_lon: float
    compression_factor: float          # m per block (horizontal)
    vertical_blocks_per_metre: float
    center_x: int
    center_z: int
    base_y: int
    elev_ref_m: float

    # --- forward projection -------------------------------------------------- #
    def to_metres(self, lat: float, lon: float) -> tuple[float, float]:
        east_m = (lon - self.centroid_lon) * self.m_per_deg_lon
        north_m = (lat - self.centroid_lat) * M_PER_DEG_LAT
        return east_m, north_m

    def block_xz(self, lat: float, lon: float) -> tuple[int, int]:
        east_m, north_m = self.to_metres(lat, lon)
        x = self.center_x + east_m / self.compression_factor
        z = self.center_z - north_m / self.compression_factor   # +Z is south
        return round(x), round(z)

    def block_y(self, elev_m: float) -> int:
        return round(self.base_y + (elev_m - self.elev_ref_m) * self.vertical_blocks_per_metre)

    def to_block(self, lat: float, lon: float, elev_m: float) -> tuple[int, int, int]:
        x, z = self.block_xz(lat, lon)
        return x, self.block_y(elev_m), z

    # --- inverse (block X/Z -> lat/lon, to sample the DEM) ------------------- #
    def to_latlon(self, x: float, z: float) -> tuple[float, float]:
        east_m = (x - self.center_x) * self.compression_factor
        north_m = -(z - self.center_z) * self.compression_factor
        lat = self.centroid_lat + north_m / M_PER_DEG_LAT
        lon = self.centroid_lon + east_m / self.m_per_deg_lon
        return lat, lon


def load_transform(config_dir: Path | str = cfg.DEFAULT_CONFIG_DIR) -> Transform:
    t = cfg.load_transform(config_dir)
    park, scale, frame = t["park"], t["scale"], t["frame"]
    lat0 = float(park["centroid_lat"])
    m_per_deg_lon = M_PER_DEG_LAT * math.cos(math.radians(lat0))
    return Transform(
        centroid_lat=lat0,
        centroid_lon=float(park["centroid_lon"]),
        m_per_deg_lon=m_per_deg_lon,
        compression_factor=float(scale["compression_factor"]),
        vertical_blocks_per_metre=float(scale["vertical_blocks_per_metre"]),
        center_x=int(frame["center_x"]),
        center_z=int(frame["center_z"]),
        base_y=int(frame["base_y"]),
        elev_ref_m=float(frame["elev_ref_m"]),
    )


# --------------------------------------------------------------------------- #
# DEM grid (regular lat/lon grid sampled from USGS 3DEP)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DEM:
    lats: np.ndarray   # ascending, shape (H,)
    lons: np.ndarray   # ascending, shape (W,)
    elev: np.ndarray   # shape (H, W), elev[i, j] at (lats[i], lons[j])

    def sample(self, lat, lon) -> np.ndarray:
        """Bilinear interpolation at (lat, lon) arrays; clamps to grid edges."""
        lat = np.asarray(lat, dtype=float)
        lon = np.asarray(lon, dtype=float)
        li = np.clip(np.searchsorted(self.lats, lat) - 1, 0, len(self.lats) - 2)
        lj = np.clip(np.searchsorted(self.lons, lon) - 1, 0, len(self.lons) - 2)
        lat0, lat1 = self.lats[li], self.lats[li + 1]
        lon0, lon1 = self.lons[lj], self.lons[lj + 1]
        ty = np.where(lat1 > lat0, (lat - lat0) / (lat1 - lat0), 0.0).clip(0, 1)
        tx = np.where(lon1 > lon0, (lon - lon0) / (lon1 - lon0), 0.0).clip(0, 1)
        e00 = self.elev[li, lj]; e01 = self.elev[li, lj + 1]
        e10 = self.elev[li + 1, lj]; e11 = self.elev[li + 1, lj + 1]
        top = e00 * (1 - tx) + e01 * tx
        bot = e10 * (1 - tx) + e11 * tx
        return top * (1 - ty) + bot * ty


def load_dem(path: Path = DEM_GRID) -> DEM:
    rows: list[tuple[float, float, float]] = []
    with path.open() as fh:
        for r in csv.DictReader(fh):
            rows.append((float(r["lat"]), float(r["lon"]), float(r["elev_m"])))
    lats = np.array(sorted({r[0] for r in rows}))
    lons = np.array(sorted({r[1] for r in rows}))
    idx = {(la, lo): e for la, lo, e in rows}
    elev = np.empty((len(lats), len(lons)), dtype=float)
    for i, la in enumerate(lats):
        for j, lo in enumerate(lons):
            elev[i, j] = idx[(la, lo)]
    return DEM(lats=lats, lons=lons, elev=elev)


# --------------------------------------------------------------------------- #
# Heightfield over the park footprint (block grid)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class HeightField:
    x0: int
    z0: int
    elev_m: np.ndarray   # shape (nz, nx) real elevation (metres)
    ground_y: np.ndarray # shape (nz, nx) block Y of the surface


def park_bounds(tr: Transform, config_dir: Path | str = cfg.DEFAULT_CONFIG_DIR) -> tuple[int, int, int, int]:
    """Block (x_min, x_max, z_min, z_max) covering the configured park bbox."""
    t = cfg.load_transform(config_dir)
    p = t["park"]
    corners = [
        (p["bbox_min_lat"], p["bbox_min_lon"]),
        (p["bbox_min_lat"], p["bbox_max_lon"]),
        (p["bbox_max_lat"], p["bbox_min_lon"]),
        (p["bbox_max_lat"], p["bbox_max_lon"]),
    ]
    xs, zs = zip(*(tr.block_xz(la, lo) for la, lo in corners))
    return min(xs), max(xs), min(zs), max(zs)


def heightfield(tr: Transform, dem: DEM,
                config_dir: Path | str = cfg.DEFAULT_CONFIG_DIR) -> HeightField:
    x_min, x_max, z_min, z_max = park_bounds(tr, config_dir)
    xs = np.arange(x_min, x_max + 1)
    zs = np.arange(z_min, z_max + 1)
    gx, gz = np.meshgrid(xs, zs)                       # shape (nz, nx)
    lat, lon = tr.to_latlon(gx.astype(float), gz.astype(float))
    elev = dem.sample(lat, lon)
    ground = np.round(tr.base_y + (elev - tr.elev_ref_m) * tr.vertical_blocks_per_metre).astype(int)
    return HeightField(x0=x_min, z0=z_min, elev_m=elev, ground_y=ground)


# --------------------------------------------------------------------------- #
# preview + sanity report (run as a module)
# --------------------------------------------------------------------------- #
def _colour(elev: np.ndarray) -> np.ndarray:
    """Simple terrain colour ramp (low=teal, mid=green, high=tan/white)."""
    lo, hi = float(elev.min()), float(elev.max())
    t = (elev - lo) / max(hi - lo, 1e-6)
    stops = np.array([
        [40, 90, 120],    # low
        [70, 130, 80],    # green
        [150, 160, 90],   # olive
        [180, 150, 110],  # tan
        [235, 235, 235],  # high
    ], dtype=float)
    pos = np.linspace(0, 1, len(stops))
    out = np.empty(t.shape + (3,), dtype=np.uint8)
    for c in range(3):
        out[..., c] = np.interp(t, pos, stops[:, c]).astype(np.uint8)
    return out


def write_preview(tr: Transform, hf: HeightField, anchors: list[dict],
                  out: Path = PREVIEW) -> Path:
    from PIL import Image, ImageDraw
    img = _colour(hf.elev_m)
    im = Image.fromarray(img, "RGB").resize(
        (img.shape[1] * 2, img.shape[0] * 2), Image.NEAREST)
    draw = ImageDraw.Draw(im)
    for a in anchors:
        x, z = tr.block_xz(float(a["lat"]), float(a["lon"]))
        px = (x - hf.x0) * 2
        pz = (z - hf.z0) * 2
        draw.ellipse([px - 4, pz - 4, px + 4, pz + 4], fill=(220, 30, 30), outline=(0, 0, 0))
        draw.text((px + 6, pz - 6), a["key"], fill=(0, 0, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def sanity(tr: Transform, anchors: list[dict]) -> None:
    """Assert the three anchors land in their real relative arrangement."""
    pos = {a["key"]: tr.to_block(float(a["lat"]), float(a["lon"]), float(a["elev_m"]))
           for a in anchors}
    dr, co, ga = pos["the_dragon"], pos["coastersaurus"], pos["galacticoaster"]
    # The Dragon: easternmost (max X) and northernmost (min Z) and highest (max Y).
    assert dr[0] > co[0] and dr[0] > ga[0], f"Dragon should be easternmost: {pos}"
    assert dr[2] < co[2], f"Dragon should be north of Coastersaurus: {pos}"
    assert ga[0] < co[0], f"Galacticoaster should be west of Coastersaurus: {pos}"
    assert dr[1] >= co[1] and dr[1] >= ga[1], f"Dragon should be highest: {pos}"
    print("sanity: anchor relative arrangement OK")
    for k, (x, y, z) in pos.items():
        print(f"  {k:16s} -> block ({x:4d}, y={y:3d}, {z:4d})")


def main() -> int:
    tr = load_transform()
    dem = load_dem()
    t = cfg.load_transform()
    anchors = t["anchor"]
    x_min, x_max, z_min, z_max = park_bounds(tr)
    print(f"park block footprint: X [{x_min}, {x_max}] ({x_max - x_min} wide), "
          f"Z [{z_min}, {z_max}] ({z_max - z_min} deep)")
    print(f"DEM elevation range : {dem.elev.min():.1f}..{dem.elev.max():.1f} m "
          f"-> ground Y {tr.block_y(dem.elev.min())}..{tr.block_y(dem.elev.max())}")
    sanity(tr, anchors)
    hf = heightfield(tr, dem)
    p = write_preview(tr, hf, anchors)
    print(f"preview written: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
