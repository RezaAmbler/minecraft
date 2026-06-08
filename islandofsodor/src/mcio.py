"""Shared Minecraft world I/O helpers (amulet) used by every chunk-writing phase.

World-creation strategy (validated in P1.1, see DECISIONS D10/D11):
  1. amulet `create_and_open` builds the region DB + a skeletal level.dat (no chunk writes),
  2. nbtlib writes the authoritative level.dat at DataVersion 4440 (src/world/level_dat.py),
  3. `open_level` (amulet) reads 4440 from level.dat and writes chunks stamped 4440.
Never write chunks before the level.dat is authored, or amulet stamps PyMCTranslate's 4439.
"""
from __future__ import annotations

import contextlib
import logging
from pathlib import Path

import amulet
from amulet.api.block import Block
from amulet.level.formats.anvil_world.format import AnvilFormat

LOG = logging.getLogger("sodor.mcio")

DIMENSION = "minecraft:overworld"


def version_id(ctx) -> tuple[str, tuple[int, ...]]:
    """The (platform, version) identifier amulet's set_version_block expects."""
    return (ctx.version.platform, tuple(ctx.version.game_version))


def block(name: str, properties: dict | None = None) -> Block:
    """Build an amulet Block from a 'namespace:base' (or 'base') id + optional properties.

    Property values must be amulet_nbt tags (e.g. StringTag('north_south')).
    """
    ns, sep, base = name.partition(":")
    if not sep:
        ns, base = "minecraft", ns
    return Block(ns, base, properties or {})


def create_skeleton(ctx, overwrite: bool = True) -> None:
    """Step 1: amulet creates the world skeleton (region DB + minimal level.dat).

    amulet's skeleton level.dat has no WorldGenSettings, so its loader logs transient
    'type was not a StringTag' errors about its own default — harmless, because we
    immediately overwrite level.dat. Silence that one logger during creation only.
    """
    world_dir = ctx.world_dir
    world_dir.parent.mkdir(parents=True, exist_ok=True)
    anvil_log = logging.getLogger("amulet.level.formats.anvil_world.format")
    prev = anvil_log.level
    anvil_log.setLevel(logging.CRITICAL)
    try:
        fmt = AnvilFormat(str(world_dir))
        fmt.create_and_open(ctx.version.platform, tuple(ctx.version.game_version), overwrite=overwrite)
        fmt.close()
    finally:
        anvil_log.setLevel(prev)
    LOG.debug("created world skeleton at %s", world_dir)


@contextlib.contextmanager
def open_level(ctx, save: bool = True):
    """Step 3: open the world for chunk writes; saves on clean exit, always closes."""
    level = amulet.load_level(str(ctx.world_dir))
    try:
        yield level
        if save:
            level.save()
    finally:
        level.close()


def world_data_version(ctx) -> int:
    """The DataVersion amulet currently reports for the on-disk world (read level.dat)."""
    level = amulet.load_level(str(ctx.world_dir))
    try:
        return int(level.level_wrapper.version)
    finally:
        level.close()


class WorldEditor:
    """Scattered-edit helper for rail/structures: caches universal blocks + the active chunk.

    Much faster than set_version_block (translates each block type once, not per call).
    """

    def __init__(self, level, ctx):
        self.level = level
        self.ver = version_id(ctx)
        self._tr = level.translation_manager.get_version(*self.ver).block
        self._uni: dict = {}
        self._cache_cx = self._cache_cz = None
        self._chunk = None

    def uni(self, name: str, props: dict | None = None):
        key = (name, tuple(sorted((props or {}).items())))
        b = self._uni.get(key)
        if b is None:
            import amulet_nbt
            p = {k: amulet_nbt.StringTag(v) for k, v in (props or {}).items()}
            b = self._tr.to_universal(block(name, p))[0]
            self._uni[key] = b
        return b

    def _chunk_at(self, cx, cz):
        from amulet.api.errors import ChunkDoesNotExist
        if cx != self._cache_cx or cz != self._cache_cz:
            try:
                self._chunk = self.level.get_chunk(cx, cz, DIMENSION)
            except ChunkDoesNotExist:
                self._chunk = self.level.create_chunk(cx, cz, DIMENSION)
            self._cache_cx, self._cache_cz = cx, cz
        return self._chunk

    def set(self, x, y, z, name, props=None):
        cx, cz = x >> 4, z >> 4
        ch = self._chunk_at(cx, cz)
        ch.set_block(x - (cx << 4), y, z - (cz << 4), self.uni(name, props))
        ch.changed = True

    def fill(self, x0, y0, z0, x1, y1, z1, name, props=None):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name, props)

    def name_at(self, x, y, z) -> str:
        blk = self.level.get_version_block(x, y, z, DIMENSION, self.ver)
        if isinstance(blk, tuple):
            blk = blk[0]
        return getattr(blk, "base_name", "")

    def surface_y(self, x, z, top=140, bottom=50) -> int | None:
        """Topmost non-air block y in the column (the terrain/track surface)."""
        for y in range(top, bottom, -1):
            if self.name_at(x, y, z) not in ("air", ""):
                return y
        return None

    def invalidate_cache(self):
        self._cache_cx = self._cache_cz = None

    # --- block entities (signs, lecterns) -------------------------------------
    # Written natively into the chunk's block-entity store (keyed on absolute coords); these
    # live in region chunks, so they SURVIVE the `entities/` finalize strip (DECISIONS D19).
    _SIGN_ROT = {"south": 0, "west": 4, "north": 8, "east": 12}  # standing-sign rotation

    def set_block_entity(self, x, y, z, base_name, compound, namespace="minecraft"):
        import amulet_nbt
        from amulet.api.block_entity import BlockEntity
        ch = self._chunk_at(x >> 4, z >> 4)
        be = BlockEntity(namespace, base_name, x, y, z, amulet_nbt.NamedTag(compound, ""))
        ch.block_entities.insert(be)   # keys on absolute (x,y,z); overwrites any prior BE there
        ch.changed = True

    def set_sign(self, x, y, z, lines, facing="north", kind="oak", wall=False,
                 color="black", glowing=False):
        """Place a real sign with engraved text. amulet stores block-entities in UNIVERSAL
        form and its sign converter reads `utags.<side>.java_nbt` (a list of NBT text-component
        compounds) — verified to round-trip to valid native 1.21.8 NBT (DECISIONS D19).
        `facing` = the direction the readable face points."""
        import amulet_nbt as N
        if wall:
            self.set(x, y, z, f"{kind}_wall_sign", {"facing": facing})
        else:
            self.set(x, y, z, f"{kind}_sign", {"rotation": str(self._SIGN_ROT.get(facing, 0))})

        def _face(strs):
            strs = (list(strs) + ["", "", "", ""])[:4]
            return N.CompoundTag({
                "java_nbt": N.ListTag([N.CompoundTag({"text": N.StringTag(str(s))}) for s in strs]),
                "color": N.StringTag(color),
                "has_glowing_text": N.ByteTag(1 if glowing else 0),
            })
        nbt = N.CompoundTag({"utags": N.CompoundTag({
            "front_text": _face(lines),
            "back_text": _face([]),
            "is_waxed": N.ByteTag(0),
        })})
        self.set_block_entity(x, y, z, "sign", nbt)

    def set_lectern_book(self, x, y, z, facing, title, author, pages):
        """Place a lectern holding a written book (1.21.8 item-component form). The pages text
        is plain (literal text components). Highest render risk across the 4440->26.1.2 upgrade
        (DECISIONS D19) — gated by a config switch with a text_display fallback."""
        import amulet_nbt as N
        self.set(x, y, z, "lectern", {"facing": facing, "has_book": "true", "powered": "false"})
        book = N.CompoundTag({
            "id": N.StringTag("minecraft:written_book"),
            "count": N.IntTag(1),
            "components": N.CompoundTag({
                "minecraft:written_book_content": N.CompoundTag({
                    "title": N.CompoundTag({"raw": N.StringTag(title)}),
                    "author": N.StringTag(author),
                    "pages": N.ListTag([N.CompoundTag({"raw": N.StringTag(str(p))}) for p in pages]),
                })
            }),
        })
        self.set_block_entity(x, y, z, "lectern", N.CompoundTag({"Book": book, "Page": N.IntTag(0)}))
