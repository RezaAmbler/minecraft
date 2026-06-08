"""P2.2 — derive a clean Sodor land mask from the CC BY-SA reference railway map.

Hybrid approach (user choice): the map is the reference; the extraction logic is the
"coded coastline". The map shows Sodor (green) on sea (blue), plus the Isle of Man
(top-left) and England (top-right) as separate green masses that touch near the corners,
so we: green-threshold -> clear the two off-island corner regions -> flood-fill the
central island -> fill interior holes (labels/lines/legend). Output is reproducible from
the committed image + this code. A preview PNG is written for human (in-repo) verification.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

LOG = logging.getLogger("sodor.terrain.source_map")

# Off-island masses to remove, as (x0,y0,x1,y1) fractions of the working image.
# Tuned against heightmaps/source/sodor_railway_map.png (see ASCII analysis in commit log).
OFFISLAND_RECTS = [
    (0.00, 0.00, 0.15, 0.25),   # Isle of Man (top-left corner)
    (0.70, 0.00, 1.00, 0.35),   # England / mainland (top-right corner)
]


def _green(a: np.ndarray) -> np.ndarray:
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (g > 130) & (r > 120) & (b < 175) & (g >= r - 5)


def _find_land_seed(mask: np.ndarray) -> tuple[int, int]:
    h, w = mask.shape
    cy, cx = h // 2, w // 2
    if mask[cy, cx]:
        return (cx, cy)
    ys, xs = np.where(mask)
    i = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
    return (int(xs[i]), int(ys[i]))


def extract_sodor_mask(image_path: Path | str, work_width: int = 640,
                       offisland=OFFISLAND_RECTS, close_px: int = 5) -> np.ndarray:
    """Return a bool array (H x W) that is True over the Sodor landmass only."""
    im = Image.open(image_path).convert("RGB")
    if work_width and im.width != work_width:
        h = round(im.height * work_width / im.width)
        im = im.resize((work_width, h), Image.BILINEAR)
    a = np.asarray(im)
    land = _green(a)
    w, h = im.width, im.height
    for (x0, y0, x1, y1) in offisland:
        land[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = False

    # morphological closing (dilate then erode) seals the thin railway-line / text gaps
    # inside the green land so the island becomes solid (no canal-shaped trenches).
    if close_px >= 3:
        limg = Image.fromarray(np.where(land, 255, 0).astype("uint8"), "L")
        limg = limg.filter(ImageFilter.MaxFilter(close_px)).filter(ImageFilter.MinFilter(close_px))
        land = np.asarray(limg) > 127

    # fill interior holes: flood the border-connected sea, anything else non-land is a hole
    # (.copy() detaches from the numpy buffer so PIL owns it and floodfill writes persist)
    sea = Image.fromarray(np.where(land, 255, 0).astype("uint8"), "L").copy()
    ImageDraw.floodfill(sea, (0, 0), 128, thresh=0)
    filled = np.asarray(sea) != 128

    # keep only the central connected island
    isl = Image.fromarray(np.where(filled, 255, 0).astype("uint8"), "L").copy()
    ImageDraw.floodfill(isl, _find_land_seed(filled), 200, thresh=0)
    island = np.asarray(isl) == 200

    LOG.info("sodor mask: %d land px of %dx%d (%.1f%%)",
             int(island.sum()), w, h, 100 * island.mean())
    return island


def island_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))  # x0,y0,x1,y1


def save_preview(image_path: Path | str, mask: np.ndarray, out_png: Path | str) -> None:
    """Render the original map (resized to mask) with the extracted island tinted, for review."""
    im = Image.open(image_path).convert("RGB").resize(mask.shape[::-1], Image.BILINEAR)
    base = np.asarray(im).copy()
    # darken everything, then brighten the kept island green + outline its coast
    out = (base * 0.45).astype("uint8")
    out[mask] = (np.array([90, 200, 90]))  # kept land = bright green
    # coast outline = land pixels adjacent to non-land
    edge = mask & ~(
        np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1)
    )
    out[edge] = (np.array([255, 60, 60]))  # red coastline
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(out).save(out_png)
    LOG.info("wrote preview -> %s", out_png)
