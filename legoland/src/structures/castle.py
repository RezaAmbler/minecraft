"""Castle Hill centerpiece — the LEGO-minifig medieval castle, its show-scene dragon,
and The Dragon coaster's station/queue.

Three PURE model functions, each returning a de-duplicated list of placement tuples
``(dx, dy, dz, block, props)`` in a local frame whose origin sits on the ground:

* ``dy == 0`` is the foundation top course (the ground the model rests on),
* ``dy == 1`` is the first block a player stands on,
* ``block`` is a namespace-less 1.21.8 block id, ``props`` is ``None`` or a small
  blockstate dict (e.g. ``{"facing": "north"}``).

No randomness, no I/O, no Minecraft/amulet imports — callers stamp these into the world.

Recommended origins (so the lands line up with the rail layer):
  * castle  : centre of Castle Hill; the keep straddles the coaster centreline.
  * dragon  : just inside the keep beside the track (e.g. castle origin + (8, 0, -4)).
  * station : west of the gatehouse where the boarding point is.

CRITICAL coaster tunnel: in :func:`castle_blocks` the east band ``dx in [2..14]``,
any ``dz``, ``dy in [1..5]`` is left fully OPEN so the rail layer can carve a clean
tunnel through the keep. The floor (dy=0) and the upper structure (dy>=6) may cross
that band; only dy 1..5 is kept clear.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Palette — LEGO-bright but medieval.
# ---------------------------------------------------------------------------
STONE = "stone_bricks"
COBBLE = "cobblestone"
CHISEL = "chiseled_stone_bricks"
ANDESITE = "polished_andesite"
MOSSY = "mossy_stone_bricks"
TIMBER = "dark_oak_log"
PLANK = "dark_oak_planks"
GOLD = "gold_block"
GLASS = "glass_pane"
RED = "red_wool"
BLUE = "blue_wool"
LANTERN = "lantern"

# Tower roof colours (heraldic, one per corner tower).
ROOF_COLOURS = ("red_terracotta", "blue_terracotta", "purple_terracotta",
                "lime_terracotta")

# Tower-roof stair block matching each colour above (for conical crenellation).
ROOF_STAIRS = {
    "red_terracotta": "polished_blackstone_brick_stairs",
    "blue_terracotta": "polished_blackstone_brick_stairs",
    "purple_terracotta": "polished_blackstone_brick_stairs",
    "lime_terracotta": "polished_blackstone_brick_stairs",
}

# Footprints (relative to each model's origin): (xmin, xmax, zmin, zmax).
CASTLE_FOOTPRINT = (-15, 15, -15, 15)
DRAGON_FOOTPRINT = (0, 10, -3, 3)
STATION_FOOTPRINT = (-6, 6, -7, 1)

# The open coaster band inside the castle (dx range, dy range) — keep clear of blocks.
TUNNEL_BAND_DX = (2, 14)
TUNNEL_BAND_DY = (1, 5)

Block = tuple[int, int, int, str, "dict | None"]


# ---------------------------------------------------------------------------
# Small geometry helpers — operate on a local list + de-dupe at the end so later
# writes win (decoration over structure), matching statue.py's approach.
# ---------------------------------------------------------------------------
def _emit(raw: list[Block]) -> dict[tuple[int, int, int], tuple[str, "dict | None"]]:
    merged: dict[tuple[int, int, int], tuple[str, "dict | None"]] = {}
    for x, y, z, blk, props in raw:
        merged[(x, y, z)] = (blk, props)
    return merged


def _finish(raw: list[Block]) -> list[Block]:
    merged = _emit(raw)
    return [(x, y, z, blk, props) for (x, y, z), (blk, props) in merged.items()]


def _in_tunnel(dx: int, dy: int) -> bool:
    """True if (dx, dy) falls in the reserved coaster band (must stay empty)."""
    return (TUNNEL_BAND_DX[0] <= dx <= TUNNEL_BAND_DX[1]
            and TUNNEL_BAND_DY[0] <= dy <= TUNNEL_BAND_DY[1])


# ---------------------------------------------------------------------------
# CASTLE
# ---------------------------------------------------------------------------
def castle_blocks() -> list[Block]:
    """A ~30x30 blocky medieval castle centred on its origin.

    Keep (central tower) straddles the coaster tunnel; the east band dy 1..5 is left
    open. West half is the solid decorative front (gatehouse + courtyard)."""
    raw: list[Block] = []

    def put(x: int, y: int, z: int, blk: str, props: "dict | None" = None,
            tunnel_ok: bool = False) -> None:
        # Respect the coaster tunnel unless the caller explicitly allows crossing
        # (floor at dy=0 and roof at dy>=6 may cross; never the 1..5 band).
        if not tunnel_ok and _in_tunnel(x, y):
            return
        raw.append((x, y, z, blk, props))

    def box(x0: int, x1: int, y0: int, y1: int, z0: int, z1: int, blk: str,
            props: "dict | None" = None, tunnel_ok: bool = False) -> None:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    put(x, y, z, blk, props, tunnel_ok)

    def crenellate(x0: int, x1: int, z0: int, z1: int, y: int, blk: str) -> None:
        """Alternating merlons around the perimeter rectangle at height y."""
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x not in (x0, x1) and z not in (z0, z1):
                    continue  # only the ring
                if (x + z) % 2 == 0:
                    put(x, y, z, blk)

    # --- Foundation slab (dy=0) — may cross the tunnel band (it's the floor). ---
    box(-15, 15, 0, 0, -15, 15, COBBLE, tunnel_ok=True)
    # Courtyard / interior floor one course up on the WEST (solid) half only.
    box(-14, 1, 1, 1, -14, 14, ANDESITE)

    # ----------------------------------------------------------------------
    # Curtain walls (~7 tall) around the perimeter, with a wall-walk + crenels.
    # The east wall (x=14) is part of the structure but kept solid only at the
    # floor/upper courses — the train passes THROUGH gaps in dy 1..5 there.
    # ----------------------------------------------------------------------
    wall_top = 7
    for (x0, x1, z0, z1) in (
        (-14, 14, -14, -14),  # north wall (low dz)
        (-14, 14, 14, 14),    # south wall (high dz)
        (-14, -14, -13, 13),  # west wall
        (14, 14, -13, 13),    # east wall (will be perforated by the tunnel band)
    ):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                for y in range(1, wall_top + 1):
                    blk = CHISEL if (y == wall_top) else STONE
                    put(x, y, z, blk)
        # wall-walk floor just inside the parapet
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                put(x, wall_top, z, "stone_brick_slab", {"type": "bottom"})
    crenellate(-14, 14, -14, 14, wall_top + 1, CHISEL)

    # ----------------------------------------------------------------------
    # Gatehouse — WEST side (toward -dx), archway facing the station.
    # ----------------------------------------------------------------------
    gate_h = 9
    for z in range(-3, 4):
        for y in range(1, gate_h + 1):
            put(-14, y, z, STONE)        # rebuild the west wall as the gate face
            put(-13, y, z, STONE)
    # carve the archway opening (3 wide, 4 tall) through the gate face
    for z in range(-1, 2):
        for y in range(1, 5):
            raw.append((-14, y, z, "air", None))  # explicit air -> overwritten? no:
    # (we DON'T emit air; instead simply skip placing the door cells)
    raw = [b for b in raw if b[3] != "air"]
    # timber portcullis frame + dark-oak gate doors at the back of the passage
    for y in range(1, 5):
        put(-13, y, -2, TIMBER, {"axis": "y"})
        put(-13, y, 2, TIMBER, {"axis": "y"})
    put(-13, 5, -2, TIMBER, {"axis": "x"})
    put(-13, 5, -1, TIMBER, {"axis": "x"})
    put(-13, 5, 0, TIMBER, {"axis": "x"})
    put(-13, 5, 1, TIMBER, {"axis": "x"})
    put(-13, 5, 2, TIMBER, {"axis": "x"})
    for z in range(-1, 2):
        for y in range(1, 5):
            put(-12, y, z, PLANK)        # closed gate doors (decorative)
    # gatehouse twin turrets flanking the arch, taller than the wall
    for z in (-4, 4):
        for y in range(1, 11):
            put(-14, y, z, CHISEL)
        put(-14, 11, z, GOLD)
    # heraldic banners either side of the gate
    put(-13, 6, -3, RED)
    put(-13, 6, 3, BLUE)
    put(-13, 7, -3, RED)
    put(-13, 7, 3, BLUE)

    # ----------------------------------------------------------------------
    # Central KEEP — 10x10, 14 tall, straddling the coaster tunnel.
    # Walls at x in [-3..6]; the east faces (x>=2) only exist at dy 0 and dy>=6,
    # so the train rolls straight through dy 1..5.
    # ----------------------------------------------------------------------
    kx0, kx1, kz0, kz1 = -3, 6, -5, 4
    keep_h = 14
    for x in range(kx0, kx1 + 1):
        for z in range(kz0, kz1 + 1):
            edge = x in (kx0, kx1) or z in (kz0, kz1)
            if not edge:
                continue
            for y in range(1, keep_h + 1):
                blk = CHISEL if y in (1, keep_h) else STONE
                # interior light bands + a gold belt course
                if y == 7 and (x + z) % 3 == 0:
                    blk = GOLD
                put(x, y, z, blk)  # tunnel band auto-skipped for x in 2..14
    # keep floors that DO cross the tunnel (dy=0 base, dy>=6 ceilings)
    box(kx0, kx1, 0, 0, kz0, kz1, ANDESITE, tunnel_ok=True)
    box(kx0, kx1, keep_h - 1, keep_h - 1, kz0, kz1, STONE, tunnel_ok=True)  # ceiling
    # keep crenellations + a gold-trimmed cap
    crenellate(kx0, kx1, kz0, kz1, keep_h + 1, CHISEL)
    for x in (kx0, kx1):
        for z in (kz0, kz1):
            put(x, keep_h + 2, z, GOLD)
    # keep windows (glass panes) on the WEST face only (solid side)
    for z in range(kz0 + 1, kz1, 2):
        for y in (4, 9):
            put(kx0, y, z, GLASS)
    # tall banner pole on the keep, flying the castle colours
    for y in range(keep_h + 1, keep_h + 5):
        put(0, y, kz0, TIMBER, {"axis": "y"})
    put(0, keep_h + 4, kz0, GOLD)
    put(1, keep_h + 3, kz0, RED)
    put(-1, keep_h + 3, kz0, BLUE)

    # ----------------------------------------------------------------------
    # Four corner towers — stepped-octagonal, taller than the walls, coloured tops.
    # NE/SE towers sit east of the tunnel band but their bodies are at the corners
    # (x=±13), clear of the dx 2..14 / dy 1..5 reservation only where dz is extreme;
    # to be safe the tower bodies are skipped inside the band like everything else.
    # ----------------------------------------------------------------------
    tower_h = 11
    corners = (
        (-13, -13, ROOF_COLOURS[0]),
        (-13, 13, ROOF_COLOURS[1]),
        (13, -13, ROOF_COLOURS[2]),
        (13, 13, ROOF_COLOURS[3]),
    )
    for cx, cz, roof in corners:
        _tower(put, box, crenellate, cx, cz, tower_h, roof)

    # ----------------------------------------------------------------------
    # Courtyard dressing on the solid WEST half: torches/lanterns + a well.
    # ----------------------------------------------------------------------
    for (lx, lz) in ((-10, -8), (-10, 8), (-6, 0)):
        put(lx, 2, lz, TIMBER, {"axis": "y"})
        put(lx, 3, lz, LANTERN, {"hanging": "false"})
    # small decorative well in the courtyard centre-west
    box(-8, -7, 1, 2, -1, 0, COBBLE)
    put(-8, 3, -1, "oak_fence")
    put(-7, 3, 0, "oak_fence")
    # interior wall-mounted torches lighting the keep (west wall, solid)
    for y in (3, 6):
        put(kx0 + 1, y, kz0, "wall_torch", {"facing": "north"})

    # strip any stray air placeholders and de-dupe (later writes win)
    raw = [b for b in raw if b[3] != "air"]
    return _finish(raw)


def _tower(put, box, crenellate, cx: int, cz: int, h: int, roof: str) -> None:
    """A stepped-square (octagon-ish) corner tower at (cx, cz), crenellated, with a
    coloured conical-ish roof and a heraldic banner."""
    r = 2  # tower half-width
    # body — chamfer the corners on the outer two courses to read as octagonal
    for y in range(1, h + 1):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if abs(dx) == r and abs(dz) == r:
                    continue  # clip corners -> octagon silhouette
                edge = abs(dx) == r or abs(dz) == r
                if not edge:
                    continue
                blk = CHISEL if y in (1, h) else STONE
                put(cx + dx, y, cz + dz, blk)
    # interior floor + lantern
    box(cx - 1, cx + 1, h - 1, h - 1, cz - 1, cz + 1, STONE)
    put(cx, h, cz, LANTERN, {"hanging": "true"})
    # crenellated parapet
    crenellate(cx - r, cx + r, cz - r, cz + r, h + 1, CHISEL)
    # conical-ish coloured roof: shrinking coloured rings topped with a gold finial
    roof_stair = ROOF_STAIRS.get(roof, "stone_brick_stairs")
    box(cx - r, cx + r, h + 2, h + 2, cz - r, cz + r, roof)
    box(cx - 1, cx + 1, h + 3, h + 3, cz - 1, cz + 1, roof)
    put(cx, h + 4, cz, roof)
    put(cx, h + 5, cz, GOLD)               # finial
    # peaked stair skirt around the lowest roof ring (suggests a cone)
    for dx, dz, facing in ((-r - 0, 0, "west"), (r, 0, "east"),
                           (0, -r, "north"), (0, r, "south")):
        put(cx + dx, h + 2, cz + dz, roof_stair, {"facing": facing})
    # banner down the tower face
    put(cx, h, cz - r, RED if (cx + cz) % 2 == 0 else BLUE)


# ---------------------------------------------------------------------------
# DRAGON — static, friendly green LEGO dragon, posed guarding the track.
# Local frame: body runs along +X, faces +X; ~10 long, ~6 tall.
# ---------------------------------------------------------------------------
GREEN = "green_concrete"
LIME = "lime_concrete"
GREEN_T = "green_terracotta"
GREEN_W = "green_wool"
BELLY = "lime_terracotta"
EYE = "sea_lantern"
SPIKE = "lime_wool"
FIRE_O = "orange_concrete"
FIRE_R = "red_concrete"
MAGMA = "magma_block"


def dragon_blocks() -> list[Block]:
    """A blocky, friendly green LEGO dragon (~10 long x ~6 tall) reared up to guard
    the track. Head has an open mouth with a magma/concrete 'fire-breath' (no fire
    blocks). Placed inside the castle beside the coaster."""
    raw: list[Block] = []

    def put(x: int, y: int, z: int, blk: str, props: "dict | None" = None) -> None:
        raw.append((x, y, z, blk, props))

    def box(x0: int, x1: int, y0: int, y1: int, z0: int, z1: int, blk: str,
            props: "dict | None" = None) -> None:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    put(x, y, z, blk, props)

    # --- haunches / tail (low, at the back, +X is the front) ---
    box(0, 1, 1, 2, -1, 1, GREEN_T)               # tail tip
    box(1, 3, 1, 3, -1, 1, GREEN)                 # rear body / haunches
    box(2, 3, 1, 1, -1, 1, BELLY)                 # belly underside

    # --- main body, rising toward the chest ---
    box(3, 5, 1, 4, -1, 1, GREEN)
    box(3, 5, 1, 1, -1, 1, BELLY)                 # belly
    # back spikes along the spine
    for x in (2, 4):
        put(x, 4, 0, SPIKE)
    put(3, 5, 0, SPIKE)

    # --- neck rearing up ---
    box(5, 6, 4, 6, -1, 0, GREEN)
    box(6, 6, 6, 7, -1, 0, GREEN)
    put(6, 7, 0, SPIKE)

    # --- head (open mouth faces +X) ---
    box(6, 8, 7, 9, -1, 1, GREEN)                 # skull
    box(7, 8, 7, 7, -1, 1, LIME)                  # lower jaw (open -> gap above)
    box(7, 9, 9, 9, -1, 1, GREEN_T)              # brow
    # eyes
    put(7, 8, -1, EYE)
    put(7, 8, 1, EYE)
    # snout / upper jaw extending forward, leaving the mouth open between y7 and y9
    box(9, 9, 8, 9, -1, 1, GREEN)
    box(9, 9, 7, 7, -1, 1, LIME)                  # lower front jaw
    # horns
    put(7, 10, -1, GREEN_T)
    put(7, 10, 1, GREEN_T)

    # --- fire breath from the open mouth (concrete + a magma 'ember'), no fire ---
    put(10, 8, 0, FIRE_O)
    put(11, 8, 0, FIRE_R)
    put(10, 7, 0, MAGMA)
    put(11, 7, -1, FIRE_O)
    put(11, 7, 1, FIRE_O)
    put(12, 7, 0, MAGMA)

    # --- wings (suggested, swept up from the shoulders, mixed greens) ---
    wing_cells = [(4, 5, -3), (4, 6, -4), (5, 6, -3), (5, 7, -4),
                  (4, 5, 3), (4, 6, 4), (5, 6, 3), (5, 7, 4)]
    for i, (x, y, z) in enumerate(wing_cells):
        blk = (GREEN_W, LIME, GREEN_T)[i % 3]
        put(x, y, z, blk)
    # wing struts back to the body
    put(4, 5, -2, GREEN_T)
    put(4, 5, 2, GREEN_T)

    # --- front legs / claws planted, guarding ---
    for z in (-1, 1):
        put(5, 1, z, GREEN_T)
        put(6, 1, z, GREEN_T)
    put(6, 1, 2, LIME)                            # splayed claw
    put(6, 1, -2, LIME)

    return _finish(raw)


# ---------------------------------------------------------------------------
# STATION — The Dragon coaster station + queue, off to one side of the track.
# Track passes along dz == 0; platform offset to dz in [-7..-2] (negative side).
# Boarding edge is at dz == -2, adjacent to the track at dz == 0.
# ---------------------------------------------------------------------------
SMOOTH = "smooth_stone"
SLAB = "smooth_stone_slab"


def station_blocks() -> list[Block]:
    """A ~12-long x ~4-wide raised platform on the NEGATIVE-dz side of the track,
    with a stone-brick + dark-oak roof on pillars, a fence queue railing leading in,
    and an open entrance/sign area (signs added elsewhere)."""
    raw: list[Block] = []

    def put(x: int, y: int, z: int, blk: str, props: "dict | None" = None) -> None:
        raw.append((x, y, z, blk, props))

    def box(x0: int, x1: int, y0: int, y1: int, z0: int, z1: int, blk: str,
            props: "dict | None" = None) -> None:
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    put(x, y, z, blk, props)

    px0, px1 = -6, 5          # 12 long along X
    pz0, pz1 = -6, -2         # 5 wide on the negative-dz side; -2 = boarding edge

    # --- foundation (dy=0) + platform floor (dy=1) ---
    box(px0, px1, 0, 0, pz0, pz1, COBBLE)
    box(px0, px1, 1, 1, pz0, pz1, ANDESITE)
    # boarding-edge trim (decorative warning strip beside the track)
    box(px0, px1, 1, 1, -2, -2, SMOOTH)
    # a one-block lip so riders step down onto the platform, not the track
    for x in range(px0, px1 + 1):
        put(x, 2, pz0, "stone_brick_wall")     # back safety rail along the far edge

    # --- roof pillars (dark-oak posts) at the four corners + midspans ---
    pillar_xs = (px0, -2, 1, px1)
    pillar_zs = (pz0, pz1)
    roof_y = 5
    for x in pillar_xs:
        for z in pillar_zs:
            for y in range(2, roof_y):
                put(x, y, z, TIMBER, {"axis": "y"})

    # --- roof (dy 5..6): stone-brick deck on a dark-oak frame, matching the castle ---
    box(px0, px1, roof_y, roof_y, pz0, pz1, PLANK)
    # raised ridge course + slab eaves for a pitched look
    box(px0, px1, roof_y + 1, roof_y + 1, -4, -4, STONE)
    for x in range(px0, px1 + 1):
        put(x, roof_y, pz0, "stone_brick_stairs", {"facing": "north"})
        put(x, roof_y, pz1, "stone_brick_stairs", {"facing": "south"})
    # gold trim + heraldic banners on the roofline (themed to the castle)
    put(px0, roof_y + 1, pz0, GOLD)
    put(px1, roof_y + 1, pz0, GOLD)
    put(-2, roof_y + 1, -4, RED)
    put(1, roof_y + 1, -4, BLUE)

    # --- platform lighting (lanterns hung under the roof) ---
    for x in (px0 + 1, -2, 1, px1 - 1):
        put(x, roof_y - 1, -4, LANTERN, {"hanging": "true"})

    # --- queue railing: a fenced switchback leading IN from the south/back ---
    # outer queue lane fences running south of the platform
    for x in range(px0, px1 + 1):
        put(x, 1, pz0 - 1, COBBLE)             # queue path foundation
        put(x, 2, pz0 - 1, "dark_oak_fence")   # far rail of the queue
    for z in range(pz0 - 1, pz0 + 1):
        put(px0, 2, z, "dark_oak_fence")
        put(px1, 2, z, "dark_oak_fence")
    # a short inner divider to make it read as a switchback queue
    box(-1, 3, 1, 1, pz0, pz0, COBBLE)
    for x in range(-1, 4):
        put(x, 2, pz0, "dark_oak_fence")

    # --- entrance / sign area (kept OPEN): a framed gateway at the queue mouth ---
    put(px0, 2, pz0 - 1, TIMBER, {"axis": "y"})
    put(px0, 3, pz0 - 1, TIMBER, {"axis": "y"})
    put(px0 + 1, 3, pz0 - 1, TIMBER, {"axis": "x"})
    put(px0 + 2, 3, pz0 - 1, TIMBER, {"axis": "x"})
    put(px0 + 2, 2, pz0 - 1, TIMBER, {"axis": "y"})
    put(px0 + 1, 3, pz0 - 1, GOLD)             # sign mount accent (sign added elsewhere)

    return _finish(raw)
