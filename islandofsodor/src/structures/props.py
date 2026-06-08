"""Reusable lineside/station prop library (detailing pass).

Each prop is a pure `<name>(facing="south") -> [(dx,dy,dz,block,props)]` model authored in a
local frame whose front faces local +Z, with dy=0 at the ground — exactly the `statue.py`
pattern. `build(name, facing)` dispatches by name; `export_schem(name)` writes a reusable,
byte-reproducible `schematics/<name>.schem` (re-gzipped mtime=0). The detailing pass
(`detailing.py`) computes per-station offsets/facing and stamps these via `WorldEditor.set`.

All original, blocky, kid-bright; palette consistent with the station builders. Props sit on
the platform apron / lineside — never on the running line (the detailing guard enforces that).
"""
from __future__ import annotations

# palette
PLANK, LOG, SLOG = "oak_planks", "oak_log", "stripped_oak_log"
SPLANK, SSLOG = "spruce_planks", "stripped_spruce_log"
BRICK, STONE, SSTONE = "bricks", "stone_bricks", "smooth_stone"
GLASS, PANE = "glass", "glass_pane"
FENCE, SLAB = "oak_fence", "oak_slab"
LAMP, RED, WHITE = "sea_lantern", "red_concrete", "white_concrete"
QUARTZ = "smooth_quartz"


def _rot(x, z, facing):
    if facing == "north":
        return (-x, -z)
    if facing == "east":
        return (z, -x)
    if facing == "west":
        return (-z, x)
    return (x, z)


def _finish(raw, facing):
    merged = {}
    for x, y, z, blk, props in raw:
        merged[(x, y, z)] = (blk, props)
    out = []
    for (x, y, z), (blk, props) in merged.items():
        rx, rz = _rot(x, z, facing)
        out.append((rx, y, rz, blk, props))
    return out


def _builder(fn):
    """Wrap a model fn(box, put) into a `<name>(facing)` returning rotated, de-duped blocks."""
    def make(facing="south"):
        raw: list = []

        def box(x0, x1, y0, y1, z0, z1, blk, props=None):
            for x in range(x0, x1 + 1):
                for y in range(y0, y1 + 1):
                    for z in range(z0, z1 + 1):
                        raw.append((x, y, z, blk, props))

        def put(x, y, z, blk, props=None):
            raw.append((x, y, z, blk, props))

        fn(box, put)
        return _finish(raw, facing)
    return make


# --------------------------------------------------------------------------- #
# props  (front = +Z; for station kit, +Z usually points toward the track)
# --------------------------------------------------------------------------- #
@_builder
def water_tower(box, put):
    # four log legs, a plank tank, a slab roof, a spout toward the track
    for cx in (-2, 2):
        for cz in (-2, 2):
            box(cx, cx, 0, 4, cz, cz, LOG, {"axis": "y"})
    box(-2, 2, 4, 4, -2, 2, SLOG, {"axis": "x"})        # frame ring
    box(-2, 2, 5, 7, -2, 2, SPLANK)                      # tank
    box(-1, 1, 5, 6, -1, 1, "water", {"level": "0"})    # (hidden) water core
    box(-2, 2, 8, 8, -2, 2, "spruce_slab", {"type": "bottom"})
    put(0, 4, 3, "chain", {"axis": "y"})                # spout
    put(0, 3, 3, "cauldron")


@_builder
def coal_stage(box, put):
    box(-2, 2, 0, 2, -1, 2, STONE)                      # bunker base
    box(-1, 1, 3, 3, 0, 1, "coal_block")               # coal pile
    box(-2, 2, 3, 3, -1, 2, FENCE)                      # rim rail (over base perimeter)
    box(-1, 1, 3, 3, 0, 1, "coal_block")
    put(0, 4, 0, LAMP)


@_builder
def footbridge(box, put):
    # crosses the track along local Z (deck at dy5, clears rail headroom y+1..3); towers at z=+-3
    for tz in (-3, 3):
        box(-1, 1, 0, 5, tz, tz, PLANK)
        box(-1, 1, 1, 4, tz, tz, "air")                 # hollow tower
        # access stairs facing outward
        put(0, 0, tz + (1 if tz > 0 else -1), "oak_stairs",
            {"facing": "south" if tz > 0 else "north", "half": "bottom"})
    box(-1, 1, 5, 5, -4, 4, PLANK)                       # deck
    box(-2, 2, 6, 6, -3, 3, SLAB, {"type": "bottom"})    # roof
    for dz in range(-4, 5):                               # railings
        put(-2, 6, dz, FENCE)
        put(2, 6, dz, FENCE)


@_builder
def canopy(box, put):
    # awning over the platform edge; posts on the platform, roof leaning toward the track (+Z)
    for tx in (-4, 0, 4):
        box(tx, tx, 1, 3, 2, 2, FENCE)
    box(-4, 4, 4, 4, 0, 2, SLAB, {"type": "bottom"})
    box(-4, 4, 4, 4, -1, -1, "oak_trapdoor", {"facing": "south", "half": "top", "open": "false"})


@_builder
def signal_box(box, put):
    box(-1, 2, 0, 2, -1, 2, BRICK)                       # ground floor (brick)
    box(0, 1, 1, 1, 0, 1, "air")
    box(-1, 2, 3, 4, -1, 2, GLASS)                       # operating floor (glass)
    box(0, 1, 3, 3, 0, 1, "air")
    box(-2, 3, 5, 5, -2, 3, "deepslate_tile_slab", {"type": "bottom"})  # eaved roof
    for yy in range(1, 5):                               # external stair rail
        put(3, yy, 0, "ladder", {"facing": "west"})


@_builder
def bench(box, put):
    for tx in (-1, 0, 1):
        put(tx, 1, 0, "oak_stairs", {"facing": "south", "half": "bottom"})
    put(-1, 1, 0, FENCE)
    put(1, 1, 0, FENCE)
    put(-1, 2, 0, FENCE)
    put(1, 2, 0, FENCE)


_FLOWERS = ["poppy", "dandelion", "cornflower", "oxeye_daisy", "azure_bluet"]


def planter(facing="south", idx=0):
    raw = []
    for z in (-1, 0, 1):
        raw.append((-1, 1, z, "spruce_trapdoor", {"facing": "east", "half": "bottom", "open": "false"}))
        raw.append((1, 1, z, "spruce_trapdoor", {"facing": "west", "half": "bottom", "open": "false"}))
        raw.append((0, 1, z, "grass_block", {"snowy": "false"}))
        raw.append((0, 2, z, _FLOWERS[(idx + z) % len(_FLOWERS)], None))
    raw.append((0, 1, -2, "spruce_trapdoor", {"facing": "south", "half": "bottom", "open": "false"}))
    raw.append((0, 1, 2, "spruce_trapdoor", {"facing": "north", "half": "bottom", "open": "false"}))
    return _finish(raw, facing)


@_builder
def phone_box(box, put):
    box(-1, 1, 0, 3, -1, 1, RED)                         # red shell
    box(-1, 1, 1, 2, 0, 0, PANE)                         # windows (front)
    box(0, 0, 1, 2, -1, -1, PANE)
    box(0, 0, 1, 2, 1, 1, PANE)
    box(0, 0, 1, 2, 0, 0, "air")                         # interior/doorway
    box(-1, 1, 4, 4, -1, 1, "red_concrete_slab", {"type": "bottom"})
    put(0, 5, 0, LAMP)


@_builder
def picket_fence(box, put):
    box(-3, 3, 0, 0, 0, 0, QUARTZ)                       # curb
    for tx in range(-3, 4):
        put(tx, 1, 0, "birch_fence")                     # pale pickets


@_builder
def name_board(box, put):
    # two log posts + a plank backing; the SIGN is stamped by the detailing pass on the front
    for tx in (-2, 2):
        box(tx, tx, 0, 3, 0, 0, SLOG, {"axis": "y"})
    box(-2, 2, 3, 3, 0, 0, SLOG, {"axis": "x"})          # header beam
    box(-2, 2, 1, 2, 0, 0, PLANK)                        # backing board (sign mounts on +Z face)


@_builder
def warehouse(box, put):
    box(-3, 3, 0, 0, -4, 4, SSTONE)                      # floor
    box(-3, 3, 1, 4, -4, 4, BRICK)                       # walls
    box(-2, 2, 1, 3, -3, 3, "air")                       # interior
    box(-3, 3, 1, 3, 4, 4, "spruce_trapdoor", {"facing": "south", "half": "bottom", "open": "false"})  # doors
    box(-4, 4, 5, 5, -5, 5, "deepslate_tile_slab", {"type": "bottom"})  # roof
    for tz in (-2, 2):                                   # windows
        put(-3, 2, tz, GLASS)
        put(3, 2, tz, GLASS)


@_builder
def goods_shed(box, put):
    box(-2, 2, 0, 0, -3, 3, PLANK)
    box(-2, 2, 1, 3, -3, 3, SPLANK)
    box(-1, 1, 1, 2, -2, 2, "air")
    box(-2, 2, 1, 2, 3, 3, "spruce_trapdoor", {"facing": "south", "half": "bottom", "open": "false"})
    box(-3, 3, 4, 4, -4, 4, "spruce_slab", {"type": "bottom"})


@_builder
def crate_stack(box, put):
    put(0, 0, 0, SPLANK); put(1, 0, 0, SPLANK); put(0, 0, 1, SPLANK)
    put(0, 1, 0, SPLANK)
    put(2, 0, 0, "barrel", {"facing": "up"})
    put(2, 0, 1, "barrel", {"facing": "up"})
    put(2, 1, 0, "barrel", {"facing": "up"})
    put(0, 0, 2, "barrel", {"facing": "up"})


@_builder
def crane(box, put):
    box(0, 0, 0, 5, 0, 0, SSLOG, {"axis": "y"})          # mast
    box(0, 0, 5, 5, -3, 0, SSLOG, {"axis": "z"})         # jib
    put(0, 4, -3, "chain", {"axis": "y"})
    put(0, 3, -3, "chain", {"axis": "y"})


# --------------------------------------------------------------------------- #
# dispatch + schematic export
# --------------------------------------------------------------------------- #
PROPS = {
    "water_tower": water_tower, "coal_stage": coal_stage, "footbridge": footbridge,
    "canopy": canopy, "signal_box": signal_box, "bench": bench, "planter": planter,
    "phone_box": phone_box, "picket_fence": picket_fence, "name_board": name_board,
    "warehouse": warehouse, "goods_shed": goods_shed, "crate_stack": crate_stack,
    "crane": crane,
}


def build(name, facing="south"):
    return PROPS[name](facing)


def _blockstate(blk, props):
    s = f"minecraft:{blk}"
    if props:
        s += "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
    return s


def export_schem(name, out_dir="schematics"):
    """Write a byte-reproducible schematics/<name>.schem from the canonical (south) model."""
    import gzip
    from pathlib import Path
    from mcschematic import MCSchematic, Version
    s = MCSchematic()
    for dx, dy, dz, blk, props in build(name, "south"):
        s.setBlock((dx, dy, dz), _blockstate(blk, props))
    s.save(out_dir, name, Version.JE_1_21_5)
    p = Path(out_dir) / f"{name}.schem"
    p.write_bytes(gzip.compress(gzip.decompress(p.read_bytes()), mtime=0))
