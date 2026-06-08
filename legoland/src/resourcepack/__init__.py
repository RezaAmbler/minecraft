"""Resource pack (original, license-safe stand-ins).

Theming is realised as BLOCKS in-world (coloured concrete + blocky models in structures/
datapack), so it needs no textures and is fully regenerable. This pack provides a valid
pack.mcmeta (26.1.2 format 84), an original LEGO-brick pack icon, and CREDITS — a clean base
that richer textures/sounds can grow into later (post-MVP). All assets here are original.
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

LOG = logging.getLogger("legoland.resourcepack")


def _make_icon(path: Path) -> None:
    """An original 2x2-stud LEGO-style brick on sky — no third-party assets."""
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (128, 128), (120, 195, 235, 255))      # sky blue
    d = ImageDraw.Draw(img)
    d.rectangle([0, 104, 128, 128], fill=(95, 165, 80, 255))       # grass strip
    # brick body
    d.rectangle([24, 40, 104, 96], fill=(200, 45, 45, 255), outline=(120, 20, 20, 255), width=3)
    # four studs
    for sx in (40, 72):
        for sy in (30, 54):
            d.ellipse([sx, sy, sx + 16, sy + 14], fill=(225, 70, 70, 255),
                      outline=(120, 20, 20, 255), width=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def run(ctx) -> None:
    out = ctx.resourcepack_out
    out.mkdir(parents=True, exist_ok=True)
    v = ctx.version
    major, minor = v.resourcepack_format, v.resourcepack_minor
    meta = {"pack": {
        "pack_format": major,
        "min_format": [major, minor],
        "max_format": [major, minor],
        "description": "LEGOLAND California — family pack (original assets)",
    }}
    (out / "pack.mcmeta").write_text(json.dumps(meta, indent=2) + "\n")
    _make_icon(out / "pack.png")

    credits_src = Path("docs/CREDITS.md")
    if credits_src.exists():
        shutil.copy(credits_src, out / "CREDITS.md")

    LOG.info("resource pack: pack.mcmeta (format %d.%d) + icon -> %s", major, minor, out)
