"""Thomas the Tank Engine statue — a blocky landmark for the Knapford spawn (P4 polish).

The model is defined ONCE as a list of (dx, dy, dz, block, props) in a local frame whose
front (the cheery face) points to local +Z. That single source is both exported to a reusable
`schematics/thomas_statue.schem` (mcschematic) and replayed block-by-block into the world by
the structure registry (`structures.run`) — replaying the in-memory model, rather than reading
the .schem back, keeps one source of truth and preserves byte-reproducibility (see D18).
Palette + the 2-eyes/3-piece smile match Thomas in engines.toml + the engine rig (datapack/rig).
"""
from __future__ import annotations

BLUE = "light_blue_concrete"   # Thomas's NWR blue (engines.toml block_main)
RED = "red_concrete"           # lining (block_trim)
BLACK = "black_concrete"       # face + wheels
DARK = "polished_blackstone"   # funnel
WHITE = "white_concrete"       # face plate + number
QB, QS, QC = "quartz_block", "smooth_quartz", "chiseled_quartz_block"   # plinth


def thomas_statue_blocks(facing: str = "south"):
    """Return [(dx, dy, dz, block, props)] for the statue, rotated so the face points `facing`.
    dy=0 is the plinth base (placed at the ground); the model is ~12 blocks tall."""
    raw: list[tuple] = []

    def box(x0, x1, y0, y1, z0, z1, blk, props=None):
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    raw.append((x, y, z, blk, props))

    def put(x, y, z, blk, props=None):
        raw.append((x, y, z, blk, props))

    # plinth (2 tall, oversized) with a chiseled front course under the face
    box(-4, 4, 0, 0, -2, 12, QS)
    box(-4, 4, 1, 1, -2, 12, QB)
    box(-4, 4, 1, 1, 11, 12, QC)

    # underframe + side wheels
    box(-2, 2, 2, 2, 1, 10, BLACK)
    for dz in (2, 4, 7, 9):
        for side in (-3, 3):
            put(side, 2, dz, BLACK)
            put(side, 3, dz, BLACK)
    # red running board / footplate (the lining)
    box(-3, 3, 3, 3, 1, 10, RED)

    # boiler — full width low, tapering to a rounded top
    box(-3, 3, 4, 6, 2, 9, BLUE)
    box(-2, 2, 7, 7, 2, 9, BLUE)
    box(-2, 2, 8, 8, 3, 8, BLUE)
    box(-3, 3, 4, 7, 4, 4, RED)        # boiler bands (lining)
    box(-3, 3, 4, 7, 7, 7, RED)

    # cab at the back (low dz) + red roof, with a back window opening
    box(-3, 3, 4, 7, 0, 1, BLUE)
    box(-2, 2, 5, 6, 0, 0, "air")
    box(-3, 3, 8, 8, 0, 2, RED)

    # front face plate + the cheery face (2 eyes + 3-piece smile, like the rig)
    box(-2, 2, 4, 8, 10, 10, WHITE)
    put(-2, 7, 11, BLACK); put(-1, 7, 11, BLACK)        # left eye
    put(1, 7, 11, BLACK); put(2, 7, 11, BLACK)          # right eye
    put(-2, 5, 11, BLACK)                               # smile up-left
    put(-1, 4, 11, BLACK); put(0, 4, 11, BLACK); put(1, 4, 11, BLACK)   # smile centre
    put(2, 5, 11, BLACK)                                # smile up-right

    # buffer beam + funnel + steam dome
    box(-3, 3, 3, 3, 11, 11, RED)
    box(-1, 1, 9, 11, 7, 8, DARK)                       # funnel
    box(-1, 1, 9, 9, 4, 5, RED)                         # dome

    # number "1" on both boiler sides (white, inset into the blue)
    for side in (-3, 3):
        for yy in (4, 5, 6):
            put(side, yy, 5, WHITE)                     # vertical stroke
        put(side, 4, 4, WHITE); put(side, 4, 6, WHITE)  # base serifs
        put(side, 6, 4, WHITE)                          # top flag

    # de-dupe (later writes win — face plate over boiler, etc.)
    merged: dict[tuple[int, int, int], tuple] = {}
    for x, y, z, blk, props in raw:
        merged[(x, y, z)] = (blk, props)
    out = []
    for (x, y, z), (blk, props) in merged.items():
        rx, rz = _rot(x, z, facing)
        out.append((rx, y, rz, blk, props))   # (dx, dy, dz, block, props)
    return out


def _rot(x: int, z: int, facing: str):
    """Rotate local (x,z) so the model's +Z front points `facing` -> returns (x', z')."""
    if facing == "north":
        return (-x, -z)
    if facing == "east":
        return (z, -x)
    if facing == "west":
        return (-z, x)
    return (x, z)   # south (front +Z) — identity


def _blockstate(blk: str, props: dict | None) -> str:
    s = f"minecraft:{blk}"
    if props:
        s += "[" + ",".join(f"{k}={v}" for k, v in sorted(props.items())) + "]"
    return s


def export_schem(out_dir: str = "schematics", name: str = "thomas_statue") -> None:
    """Write the reusable library schematic from the same model the world placement replays.
    Re-gzips with mtime=0 so the artifact is byte-reproducible (mcschematic embeds the current
    timestamp otherwise — the same fix world/level_dat.py uses)."""
    import gzip
    from pathlib import Path
    from mcschematic import MCSchematic, Version
    s = MCSchematic()
    for dx, dy, dz, blk, props in thomas_statue_blocks("south"):
        s.setBlock((dx, dy, dz), _blockstate(blk, props))
    s.save(out_dir, name, Version.JE_1_21_5)   # newest JE_1_21 enum (DECISIONS D5)
    path = Path(out_dir) / f"{name}.schem"
    payload = gzip.decompress(path.read_bytes())
    path.write_bytes(gzip.compress(payload, mtime=0))
