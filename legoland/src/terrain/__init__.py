"""Terrain phase — write the park heightfield into the world.

Fast, vectorized chunk writer: each material is translated to a universal block ONCE, then
per-chunk numpy [x, y, z] volumes are filled from heightfield slices. Region-batched
(save+purge) and resumable. The heightfield is the compressed real DEM (heightfield.py).
"""
from __future__ import annotations

import logging
import time

import numpy as np

from .. import mcio
from . import heightfield as hfmod

LOG = logging.getLogger("legoland.terrain")
DIM = mcio.DIMENSION
SAVE_EVERY = 1024
PROGRESS_FILE = ".legoland_terrain_progress"


def _universal_blocks(level):
    import amulet_nbt
    tr = level.translation_manager.get_version("java", (1, 21, 8)).block
    U = {}
    for code, (name, props) in hfmod.CODE_TO_BLOCK.items():
        p = {k: amulet_nbt.StringTag(v) for k, v in (props or {}).items()}
        U[code] = tr.to_universal(mcio.block(name, p))[0]
    return U


def _fill_chunk(level, hf, U, cx, cz) -> bool:
    """Fill one chunk from the heightfield. Returns False if fully outside the park."""
    ox, oz = cx * 16, cz * 16
    hx0, hz0 = ox - hf.x0, oz - hf.z0
    lx0, lx1 = max(0, -hx0), min(16, hf.nx - hx0)
    lz0, lz1 = max(0, -hz0), min(16, hf.nz - hz0)
    if lx1 <= lx0 or lz1 <= lz0:
        return False

    # local [z, x] surface height; present mask = inside the park footprint
    present = np.zeros((16, 16), bool)
    Hc = np.full((16, 16), hfmod.FLOOR_Y, np.int16)
    present[lz0:lz1, lx0:lx1] = True
    Hc[lz0:lz1, lx0:lx1] = hf.ground[hz0 + lz0:hz0 + lz1, hx0 + lx0:hx0 + lx1]
    if not present.any():
        return False

    ch = level.create_chunk(cx, cz, DIM)
    pal = {code: ch.block_palette.get_add_block(b) for code, b in U.items()}

    top = int(max(Hc.max(), hf.water_y)) + 1            # exclusive top
    yspan = top - hfmod.FLOOR_Y
    absy = np.arange(hfmod.FLOOR_Y, top, dtype=np.int16)[None, :, None]   # [1, y, 1]
    Hx = Hc.T[:, None, :]                                # [x, 1, z]
    presentx = present.T[:, None, :]

    vol = np.full((16, yspan, 16), pal[hfmod.AIR], np.uint32)
    solid = presentx & (absy <= Hx)
    vol = np.where(solid, pal[hfmod.STONE], vol)                         # stone slab up to surface
    vol = np.where(solid & (absy > Hx - hfmod.SUBSOIL) & (absy < Hx),
                   pal[hfmod.DIRT], vol)                                 # dirt subsoil under grass
    vol = np.where(presentx & (absy == Hx), pal[hfmod.GRASS], vol)       # grass surface
    if hf.water_y >= hfmod.FLOOR_Y:                                      # optional lake fill
        vol = np.where(presentx & (absy > Hx) & (absy <= hf.water_y),
                       pal[hfmod.WATER], vol)

    air = pal[hfmod.AIR]
    for cy in range(hfmod.FLOOR_Y // 16, (top + 15) // 16):
        y_lo = cy * 16 - hfmod.FLOOR_Y
        sub = vol[:, y_lo:y_lo + 16, :]
        if sub.shape[1] < 16:                            # pad the top sub-chunk to 16 high
            sub = np.concatenate([sub, np.full((16, 16 - sub.shape[1], 16), air, np.uint32)], axis=1)
        if not (sub != air).any():
            continue
        ch.blocks.add_sub_chunk(cy, np.ascontiguousarray(sub))
    ch.changed = True
    level.put_chunk(ch, DIM)
    return True


def run(ctx) -> None:
    hf = hfmod.build_heightfield(ctx)
    cx_min, cx_max = hf.x0 // 16, (hf.x0 + hf.nx - 1) // 16
    cz_min, cz_max = hf.z0 // 16, (hf.z0 + hf.nz - 1) // 16
    total = (cx_max - cx_min + 1) * (cz_max - cz_min + 1)
    LOG.info("generating %d chunks: cx[%d..%d] cz[%d..%d]", total, cx_min, cx_max, cz_min, cz_max)

    progress_path = ctx.world_dir / PROGRESS_FILE
    start_cz = cz_min
    if ctx.resume and progress_path.exists():
        start_cz = int(progress_path.read_text().strip() or cz_min) + 1
        LOG.info("resuming at cz=%d", start_cz)

    written = done = 0
    t0 = time.time()
    with mcio.open_level(ctx, save=False) as level:
        U = _universal_blocks(level)
        for cz in range(start_cz, cz_max + 1):
            for cx in range(cx_min, cx_max + 1):
                if _fill_chunk(level, hf, U, cx, cz):
                    written += 1
                done += 1
                if done % SAVE_EVERY == 0:
                    level.save()
                    level.purge()
            progress_path.write_text(str(cz))
            if (cz - cz_min) % 8 == 0:
                pct = 100 * (cz - cz_min + 1) / (cz_max - cz_min + 1)
                LOG.info("  …cz=%d (%.0f%%), %d chunks, %.1fs", cz, pct, written, time.time() - t0)
        level.save()
    if progress_path.exists():
        progress_path.unlink()

    # land spawn on the terrain surface at the spawn column
    sp = ctx.transform["world"]["spawn"]
    g = hfmod.ground_at(hf, int(sp[0]), int(sp[2]))
    if g is not None:
        from ..world.level_dat import patch_spawn_y
        patch_spawn_y(ctx, g + 1)

    LOG.info("terrain complete: %d chunks written in %.1fs", written, time.time() - t0)
