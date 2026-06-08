"""Phase 7 — Resource pack (original, license-safe stand-ins).

The engine faces/liveries are realised as BLOCKS in-world (coloured concrete + blocky faces
in datapack/rig.py), so they need no textures and are fully regenerable. This pack provides a
valid pack.mcmeta (26.1.2 format 84), an original pack icon, and CREDITS — a clean base that
richer textures/sounds can grow into later (post-MVP). All assets here are original.
"""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

LOG = logging.getLogger("sodor.resourcepack")


def _make_icon(path: Path) -> None:
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (128, 128), (120, 195, 235, 255))     # sky blue
    d = ImageDraw.Draw(img)
    d.rectangle([0, 96, 128, 128], fill=(95, 165, 80, 255))       # grass strip
    d.ellipse([26, 22, 102, 98], fill=(40, 110, 200, 255), outline=(20, 55, 115, 255), width=5)  # blue face
    for ex in (46, 72):                                           # eyes
        d.ellipse([ex, 46, ex + 12, 62], fill=(255, 255, 255, 255))
        d.ellipse([ex + 3, 50, ex + 9, 58], fill=(0, 0, 0, 255))
    d.arc([46, 56, 82, 88], start=20, end=160, fill=(0, 0, 0, 255), width=5)  # smile
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
        "description": "Island of Sodor — family pack (original assets)",
    }}
    (out / "pack.mcmeta").write_text(json.dumps(meta, indent=2) + "\n")
    _make_icon(out / "pack.png")

    credits_src = Path("resourcepack/CREDITS.md")
    if credits_src.exists():
        shutil.copy(credits_src, out / "CREDITS.md")

    LOG.info("Phase 7 resource pack: pack.mcmeta (format %d.%d) + icon -> %s", major, minor, out)
