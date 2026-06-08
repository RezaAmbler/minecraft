"""Validation suite — structural checks (we cannot launch Minecraft here).

Loads the output world with amulet and asserts it opens; checks level.dat, terrain, rail
geometry (the real check — every cell's written shape vs its 4-connected neighbours, no
diagonal, no Y>1, no powered rail on a curve, loop-closure reachability, on-disk round-trip),
structures, and the packs. Ride feel + in-client visuals are covered by docs/TESTING.md.
Run via `python -m src.build validate`; exits non-zero if any check fails. No stubs.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from .. import mcio

LOG = logging.getLogger("legoland.validate")


@dataclass
class Report:
    results: list = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, bool(ok), detail))
        LOG.info("[%s] %s%s", "PASS" if ok else "FAIL", name, f" — {detail}" if detail else "")

    @property
    def failures(self) -> list:
        return [r for r in self.results if not r[1]]

    def summary(self) -> str:
        n, f = len(self.results), len(self.failures)
        return f"{n - f}/{n} checks passed"


def _block_name(level, x: int, y: int, z: int, ver) -> str:
    blk = level.get_version_block(x, y, z, mcio.DIMENSION, ver)
    if isinstance(blk, tuple):
        blk = blk[0]
    return getattr(blk, "full_blockstate", str(blk))


# ----------------------------------------------------------------------------- #
def validate_world(ctx, rep: Report) -> None:
    import amulet
    import nbtlib

    world_dir = ctx.world_dir
    if not (world_dir / "level.dat").exists():
        rep.check("world exists", False, f"no level.dat at {world_dir}")
        return

    ver = mcio.version_id(ctx)
    w = ctx.transform["world"]
    d = nbtlib.load(str(world_dir / "level.dat"))["Data"]
    sx, sz = int(d["SpawnX"]), int(d["SpawnZ"])
    sy = int(d["SpawnY"])

    level = amulet.load_level(str(world_dir))
    try:
        dv = int(level.level_wrapper.version)
        rep.check("world opens in amulet", True)
        rep.check("DataVersion == config", dv == ctx.version.data_version,
                  f"on-disk {dv} vs config {ctx.version.data_version}")
        foot = _block_name(level, sx, sy - 1, sz, ver)
        rep.check("spawn stands on solid ground",
                  not foot.startswith(("minecraft:air", "minecraft:water")), f"@y{sy-1} {foot}")
        head = _block_name(level, sx, sy, sz, ver)
        rep.check("spawn has headroom (air)", head.startswith("minecraft:air"), f"@y{sy} {head}")
    finally:
        level.close()
    rep.check("GameType == Creative(1)", int(d["GameType"]) == 1, str(int(d["GameType"])))
    rep.check("allowCommands (cheats)", int(d["allowCommands"]) == 1)
    rep.check("Difficulty == peaceful(0)", int(d["Difficulty"]) == 0)
    gr = d["GameRules"]
    rep.check("gamerule doDaylightCycle=false", str(gr["doDaylightCycle"]) == "false")
    rep.check("gamerule doMobSpawning=false", str(gr["doMobSpawning"]) == "false")
    dims = d["WorldGenSettings"]["dimensions"]
    rep.check("WorldGenSettings has 3 dimensions",
              all(k in dims for k in ("minecraft:overworld", "minecraft:the_nether", "minecraft:the_end")),
              ", ".join(dims.keys()))
    gen_type = str(dims["minecraft:overworld"]["generator"]["type"])
    rep.check("overworld generator is flat(void)", gen_type == "minecraft:flat", gen_type)
    rep.check("world border set", float(d["BorderSize"]) == float(w["border_size"]),
              str(float(d["BorderSize"])))


def validate_terrain(ctx, rep: Report) -> None:
    """Heightfield determinism + the written surface matches it on pristine park columns.

    Samples a grid across the park footprint, EXCLUDING a radius around any built land (where
    structures/rail legitimately replace grass with their own blocks), and requires grass with
    air above — proving the DEM terrain was written correctly where nothing overbuilt it."""
    import amulet
    import numpy as np
    from ..terrain.heightfield import build_heightfield, ground_at

    hf = build_heightfield(ctx)
    hf2 = build_heightfield(ctx)
    rep.check("heightfield deterministic", bool(np.array_equal(hf.ground, hf2.ground)))

    built = [(int(ld["center"][0]), int(ld["center"][1]), int(ld.get("footprint", 120)))
             for ld in ctx.lands.get("lands", []) if ld.get("mvp")]

    def overbuilt(x, z):
        return any((x - cx) ** 2 + (z - cz) ** 2 <= (fp // 2 + 6) ** 2 for cx, cz, fp in built)

    ver = mcio.version_id(ctx)
    level = amulet.load_level(str(ctx.world_dir))
    try:
        ok = bad = 0
        sample_bad = []
        for x in range(hf.x0 + 8, hf.x0 + hf.nx - 8, 40):
            for z in range(hf.z0 + 8, hf.z0 + hf.nz - 8, 40):
                if overbuilt(x, z):
                    continue
                g = ground_at(hf, x, z)
                surf = _block_name(level, x, g, z, ver)
                above = _block_name(level, x, g + 1, z, ver)
                if surf.startswith("minecraft:grass_block") and above.startswith("minecraft:air"):
                    ok += 1
                else:
                    bad += 1
                    if len(sample_bad) < 3:
                        sample_bad.append(f"({x},{g},{z}):{surf.split('[')[0].split(':')[-1]}")
        rep.check("terrain surface is grass on pristine park columns (air above)",
                  bad == 0 and ok >= 20, f"{ok} ok, {bad} bad {sample_bad}")
    finally:
        level.close()


# rail shape -> its two cardinal (dx,dz) connection offsets
_RAIL_CONN = {
    "east_west": [(1, 0), (-1, 0)], "north_south": [(0, 1), (0, -1)],
    "north_east": [(0, -1), (1, 0)], "north_west": [(0, -1), (-1, 0)],
    "south_east": [(0, 1), (1, 0)], "south_west": [(0, 1), (-1, 0)],
    "ascending_east": [(1, 0), (-1, 0)], "ascending_west": [(1, 0), (-1, 0)],
    "ascending_north": [(0, -1), (0, 1)], "ascending_south": [(0, -1), (0, 1)],
}


def _rail_at(level, x, y, z, ver):
    s = _block_name(level, x, y, z, ver)
    if "rail" not in s:
        return None
    base = s.split("[", 1)[0].split(":")[-1]
    shape = s.split("shape=", 1)[1].split("]")[0].split(",")[0].strip('"') if "shape=" in s else None
    return (base, shape)


def validate_rail(ctx, rep: Report) -> None:
    """The real rideability proof for every MVP coaster: ordered-plan geometry guarantees
    (4-connected, no Y>1, no powered/detector/activator rail on a curve), shape-connectivity,
    on-disk round-trip of type+shape, and loop-closure reachability (BFS over the rail graph).
    Uses the same `coaster.plan_coaster` the layer used, so checked == built."""
    import amulet
    from ..rail import coaster, grid
    from ..terrain.heightfield import build_heightfield

    hf = build_heightfield(ctx)
    rides = coaster.mvp_coasters(ctx.rides)
    if not rides:
        rep.check("at least one MVP coaster", False, "no coaster with a route in rides.toml")
        return

    ver = mcio.version_id(ctx)
    level = amulet.load_level(str(ctx.world_dir))
    try:
        for ride in rides:
            plan = coaster.plan_coaster(hf, ride, ctx.transform)
            cells = plan.cells
            n = len(cells)
            label = ride["name"]

            # geometric guarantees on the ordered loop (no world reads)
            diag = ystep = curvetype = None
            for i in range(n):
                c, d = cells[i], cells[(i + 1) % n]
                if abs(c.x - d.x) + abs(c.z - d.z) != 1:
                    diag = diag or (c.xz, d.xz)
                if abs(c.y - d.y) > 1:
                    ystep = ystep or (c.xz, d.xz)
                if c.shape in grid.CURVE_SHAPES and c.rail_type != "rail":
                    curvetype = curvetype or (c.xz, c.rail_type)
            rep.check(f"{label}: 4-connected (no diagonal step)", diag is None, str(diag or ""))
            rep.check(f"{label}: no Y step >1 between cells", ystep is None, str(ystep or ""))
            rep.check(f"{label}: no powered rail on a curve", curvetype is None, str(curvetype or ""))

            # connectivity from shapes (closed loop: every connection lands on a rail cell)
            keys = {c.xz for c in cells}
            disc = []
            for c in cells:
                for dx, dz in _RAIL_CONN.get(c.shape, []):
                    if (c.x + dx, c.z + dz) not in keys:
                        disc.append((c.x, c.z, c.shape, (dx, dz)))
                        break
            rep.check(f"{label}: every rail shape connects to a neighbour", not disc,
                      f"{len(disc)} dangling e.g. {disc[:3]}")

            # on-disk round-trip: world holds exactly the planned (type, shape) at each cell
            bad = []
            for c in cells:
                if _rail_at(level, c.x, c.y, c.z, ver) != (c.rail_type, c.shape):
                    bad.append((c.x, c.y, c.z, _rail_at(level, c.x, c.y, c.z, ver), (c.rail_type, c.shape)))
                    if len(bad) >= 5:
                        break
            rep.check(f"{label}: rail written correctly on disk (round-trip)", not bad,
                      f"{len(bad)}+ mismatch e.g. {bad[:2]}")

            # loop-closure reachability: BFS the rail adjacency from the boarding cell
            adj = defaultdict(set)
            xz = [c.xz for c in cells]
            for i in range(n):
                a, b = xz[i], xz[(i + 1) % n]
                adj[a].add(b); adj[b].add(a)
            seen, stack = {xz[plan.boarding_idx]}, [xz[plan.boarding_idx]]
            while stack:
                u = stack.pop()
                for v in adj[u]:
                    if v not in seen:
                        seen.add(v); stack.append(v)
            rep.check(f"{label}: loop closed & fully traversable from boarding cell",
                      len(seen) == n, f"{n - len(seen)} cells unreachable")
    finally:
        level.close()


def validate_structures(ctx, rep: Report) -> None:
    """Confirm Castle Hill's structures exist (scan around the land centre for key blocks)."""
    import amulet
    from ..world.coords import land_center

    try:
        cx, cz = land_center(ctx.lands, "castle_hill")
    except KeyError:
        rep.check("castle_hill land defined", False)
        return
    ver = mcio.version_id(ctx)
    level = amulet.load_level(str(ctx.world_dir))
    try:
        ed = mcio.WorldEditor(level, ctx)
        counts = defaultdict(int)
        for dx in range(-22, 23, 2):
            for dz in range(-22, 23, 2):
                for y in range(82, 108):
                    counts[ed.name_at(cx + dx, y, cz + dz)] += 1
        castle = counts.get("stone_bricks", 0) + counts.get("chiseled_stone_bricks", 0)
        gold = counts.get("gold_block", 0)
        dragon = counts.get("lime_concrete", 0) + counts.get("green_concrete", 0) + counts.get("green_terracotta", 0)
        rep.check("castle present (stone-brick mass)", castle >= 30, f"{castle} stone-brick samples")
        rep.check("castle heraldry present (gold)", gold >= 1, f"{gold} gold samples")
        rep.check("dragon show-scene present (green)", dragon >= 1, f"{dragon} green samples")
        # station near the boarding cell
        from ..rail import coaster
        from ..terrain.heightfield import build_heightfield
        plan = coaster.plan_coaster(build_heightfield(ctx), coaster.mvp_coasters(ctx.rides)[0], ctx.transform)
        b = plan.cells[plan.boarding_idx]
        st = any(ed.name_at(b.x + dx, b.y, b.z + dz) in ("polished_andesite", "smooth_stone", "dark_oak_planks")
                 for dx in range(-6, 7) for dz in range(-8, 3))
        rep.check("coaster station present near boarding cell", st)
    finally:
        level.close()


def validate_datapack(ctx, rep: Report) -> None:
    import json
    root = ctx.datapack_out
    mc = root / "pack.mcmeta"
    if not mc.exists():
        rep.check("datapack built", False, "no pack.mcmeta (run `datapack`)")
        return
    try:
        meta = json.loads(mc.read_text())
    except Exception as e:
        rep.check("pack.mcmeta valid JSON", False, str(e))
        return
    fmt = meta.get("pack", {}).get("pack_format")
    rep.check("datapack pack_format == client", fmt == ctx.version.datapack_format,
              f"{fmt} vs {ctx.version.datapack_format}")
    tickjson = root / "data" / "minecraft" / "tags" / "function" / "tick.json"
    rep.check("tick tag -> legoland:ride/tick",
              tickjson.exists() and "legoland:ride/tick" in tickjson.read_text())

    from ..rail import coaster
    fn = root / "data" / "legoland" / "function"
    bad = []
    for c in coaster.mvp_coasters(ctx.rides):
        f = fn / "ride" / "summon" / f"{c['key']}.mcfunction"
        if not f.exists() or "summon block_display" not in f.read_text():
            bad.append(c["key"])
    rep.check("all coaster summon functions present", not bad, str(bad))
    for name in ("menu", "ride/menu", "ride/stop", "travel/menu", "setup"):
        rep.check(f"function present: {name}", (fn / f"{name}.mcfunction").exists())
    hubs_missing = [ld["key"] for ld in ctx.lands.get("lands", [])
                    if not (fn / "travel" / "goto" / f"{ld['key']}.mcfunction").exists()]
    rep.check("teleport hub per land", not hubs_missing, str(hubs_missing))
    # every tick/load-tagged function must exist
    for tag in ("tick", "load"):
        tj = root / "data" / "minecraft" / "tags" / "function" / f"{tag}.json"
        if tj.exists():
            for fid in json.loads(tj.read_text()).get("values", []):
                ns, _, p = fid.partition(":")
                rep.check(f"{tag}-tagged function exists: {fid}",
                          (root / "data" / ns / "function" / f"{p}.mcfunction").exists())


def validate_resourcepack(ctx, rep: Report) -> None:
    import json
    out = ctx.resourcepack_out
    mc = out / "pack.mcmeta"
    if not mc.exists():
        rep.check("resource pack built", False, "no pack.mcmeta (run `resourcepack`)")
        return
    try:
        meta = json.loads(mc.read_text())
    except Exception as e:
        rep.check("resourcepack pack.mcmeta valid JSON", False, str(e))
        return
    fmt = meta.get("pack", {}).get("pack_format")
    rep.check("resourcepack pack_format == client", fmt == ctx.version.resourcepack_format,
              f"{fmt} vs {ctx.version.resourcepack_format}")
    rep.check("resourcepack icon present", (out / "pack.png").exists())


def validate_finalize(ctx, rep: Report) -> None:
    """After finalize the entities/ folder must be gone (26.1.2 rejects amulet's entity chunks)."""
    rep.check("entities/ folder removed", not (ctx.world_dir / "entities").exists())


def run(ctx) -> None:
    rep = Report()
    validate_world(ctx, rep)
    validate_terrain(ctx, rep)
    validate_rail(ctx, rep)
    validate_structures(ctx, rep)
    validate_datapack(ctx, rep)
    validate_resourcepack(ctx, rep)
    validate_finalize(ctx, rep)
    LOG.info("validation: %s", rep.summary())
    if rep.failures:
        names = ", ".join(n for n, _, _ in rep.failures)
        raise SystemExit(f"VALIDATION FAILED ({len(rep.failures)}): {names}")
