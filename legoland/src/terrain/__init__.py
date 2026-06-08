"""Phase 2 — Terrain.

Builds the heightfield (heightfield.py) then writes the island into the world with a fast,
vectorized chunk writer: each block type is translated to universal ONCE, then per-chunk
numpy sub-chunk arrays are filled from heightfield slices. Region-batched (save+purge),
logged, and resumable. Performance validated in P2.3 (~ms/chunk; full island ~1-2 min).
"""
from __future__ import annotations

import logging
import time

import numpy as np

from .. import mcio
from . import heightfield as hfmod

LOG = logging.getLogger("sodor.terrain")
DIM = mcio.DIMENSION
SAVE_EVERY = 1024            # chunks between save+purge (bounds memory)
PROGRESS_FILE = ".sodor_terrain_progress"


def _universal_blocks(level):
    """Translate each terrain block type to a universal Block exactly once."""
    import amulet_nbt
    tr = level.translation_manager.get_version("java", (1, 21, 8)).block
    U = {}
    for code, (name, props) in hfmod.CODE_TO_BLOCK.items():
        p = {k: amulet_nbt.StringTag(v) for k, v in (props or {}).items()}
        U[code] = tr.to_universal(mcio.block(name, p))[0]
    return U


def _fill_chunk(level, hf, U, cx, cz) -> bool:
    """Fill one chunk from the heightfield. Returns False if fully outside the region."""
    ox, oz = cx * 16, cz * 16
    hx0, hz0 = ox - hf.west, oz - hf.north
    lx0, lx1 = max(0, -hx0), min(16, hf.size - hx0)
    lz0, lz1 = max(0, -hz0), min(16, hf.size - hz0)
    if lx1 <= lx0 or lz1 <= lz0:
        return False  # entirely outside the generated square

    # local [z,x] arrays (air/void outside the overlap)
    Hc = np.zeros((16, 16), np.int16)
    surfc = np.full((16, 16), hfmod.AIR, np.uint8)
    landc = np.zeros((16, 16), bool)
    Hc[lz0:lz1, lx0:lx1] = hf.height[hz0 + lz0:hz0 + lz1, hx0 + lx0:hx0 + lx1]
    surfc[lz0:lz1, lx0:lx1] = hf.surf[hz0 + lz0:hz0 + lz1, hx0 + lx0:hx0 + lx1]
    landc[lz0:lz1, lx0:lx1] = hf.land[hz0 + lz0:hz0 + lz1, hx0 + lx0:hx0 + lx1]
    has_terrain = surfc != hfmod.AIR
    if not has_terrain.any():
        return False

    ch = level.create_chunk(cx, cz, DIM)
    pal = {code: ch.block_palette.get_add_block(b) for code, b in U.items()}
    surf_pal = np.full((16, 16), pal[hfmod.AIR], np.uint32)
    for code in (hfmod.GRASS, hfmod.SAND, hfmod.STONE, hfmod.SNOW, hfmod.GRAVEL):
        surf_pal[surfc == code] = pal[code]

    # transpose to [x,z]; build a [x, y, z] volume over [BASE_Y, top)
    Hx = Hc.T[:, None, :]
    landx = landc.T[:, None, :]
    surf3 = surf_pal.T[:, None, :]
    top = int(min(hfmod.YMAX, ((max(int(Hc.max()), hf.sea_level) + 16) // 16) * 16))
    yspan = top - hfmod.BASE_Y
    absy = np.arange(hfmod.BASE_Y, top, dtype=np.int16)[None, :, None]

    vol = np.full((16, yspan, 16), pal[hfmod.AIR], np.uint32)
    below = absy < Hx
    vol = np.where(below, pal[hfmod.STONE], vol)                         # solid base (land & seabed)
    vol = np.where(landx & (absy >= Hx - 3) & below, pal[hfmod.DIRT], vol)  # land subsoil
    vol = np.where(absy == Hx, surf3, vol)                              # land top / sea seabed
    vol = np.where((~landx) & (absy > Hx) & (absy <= hf.sea_level),
                   pal[hfmod.WATER], vol)                               # sea water column

    air = pal[hfmod.AIR]
    for cy in range(hfmod.BASE_Y // 16, top // 16):
        sub = vol[:, cy * 16 - hfmod.BASE_Y: cy * 16 - hfmod.BASE_Y + 16, :]
        if not (sub != air).any():
            continue
        ch.blocks.add_sub_chunk(cy, np.ascontiguousarray(sub))
    ch.changed = True
    level.put_chunk(ch, DIM)
    return True


def run(ctx) -> None:
    hf = hfmod.build_heightfield(ctx)
    cx_min, cx_max = hf.west // 16, (hf.west + hf.size - 1) // 16
    cz_min, cz_max = hf.north // 16, (hf.north + hf.size - 1) // 16
    total = (cx_max - cx_min + 1) * (cz_max - cz_min + 1)
    LOG.info("generating %d chunks: cx[%d..%d] cz[%d..%d]", total, cx_min, cx_max, cz_min, cz_max)

    progress_path = ctx.world_dir / PROGRESS_FILE
    start_cz = cz_min
    if ctx.resume and progress_path.exists():
        start_cz = int(progress_path.read_text().strip() or cz_min) + 1
        LOG.info("resuming at cz=%d", start_cz)

    written = 0
    done = 0
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
            if (cz - cz_min) % 16 == 0:
                pct = 100 * (cz - cz_min + 1) / (cz_max - cz_min + 1)
                LOG.info("  …cz=%d (%.0f%%), %d chunks written, %.1fs",
                         cz, pct, written, time.time() - t0)
        level.save()
    if progress_path.exists():
        progress_path.unlink()

    # put spawn on the terrain surface at the spawn column (kid lands on ground, not in a hill)
    sp = ctx.layout["world"]["spawn"]
    xi, zi = int(sp["x"]) - hf.west, int(sp["z"]) - hf.north
    if 0 <= xi < hf.size and 0 <= zi < hf.size and hf.land[zi, xi]:
        from ..world.level_dat import patch_spawn_y
        patch_spawn_y(ctx, int(hf.height[zi, xi]) + 1)  # feet on top of the surface block

    LOG.info("Phase 2 terrain complete: %d chunks written in %.1fs", written, time.time() - t0)
