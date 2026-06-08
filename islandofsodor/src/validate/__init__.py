"""Validation suite — structural checks (we cannot launch Minecraft here).

Loads the output world with amulet and asserts it opens; spot-checks coordinates and
reads level.dat fields back. Ride feel + in-client visuals are covered by docs/TESTING.md.
Run via `python -m src.build validate`; exits non-zero if any check fails.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .. import mcio

LOG = logging.getLogger("sodor.validate")


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


def validate_world(ctx, rep: Report) -> None:
    import amulet
    import nbtlib

    world_dir = ctx.world_dir
    if not (world_dir / "level.dat").exists():
        rep.check("world exists", False, f"no level.dat at {world_dir}")
        return

    ver = mcio.version_id(ctx)
    w = ctx.layout["world"]
    d = nbtlib.load(str(world_dir / "level.dat"))["Data"]
    sx, sz = int(d["SpawnX"]), int(d["SpawnZ"])
    sy = int(d["SpawnY"])  # terrain may have patched this onto the surface

    # amulet opens + DataVersion + spawn standability
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
    rep.check("gamerule doWeatherCycle=false", str(gr["doWeatherCycle"]) == "false")
    rep.check("gamerule doMobSpawning=false", str(gr["doMobSpawning"]) == "false")
    dims = d["WorldGenSettings"]["dimensions"]
    rep.check("WorldGenSettings has 3 dimensions",
              all(k in dims for k in ("minecraft:overworld", "minecraft:the_nether", "minecraft:the_end")),
              ", ".join(dims.keys()))
    gen_type = str(dims["minecraft:overworld"]["generator"]["type"])
    rep.check("overworld generator is flat(void)", gen_type == "minecraft:flat", gen_type)
    border = float(d["BorderSize"])
    rep.check("world border set", border == float(w["border"]["size"]), str(border))


def validate_terrain(ctx, rep: Report) -> None:
    """Predict surface blocks from the heightfield and verify them in the world."""
    import amulet
    import numpy as np
    from ..terrain.heightfield import build_heightfield, CODE_TO_BLOCK, SNOW_Y

    hf = build_heightfield(ctx)

    # determinism: a second build must match (seeded + image-derived)
    hf2 = build_heightfield(ctx)
    rep.check("heightfield deterministic", bool(np.array_equal(hf.height, hf2.height)
                                                and np.array_equal(hf.surf, hf2.surf)))

    ver = mcio.version_id(ctx)
    level = amulet.load_level(str(ctx.world_dir))
    try:
        # detect terrain: a sea corner should be water at sea level
        scx, scz = hf.west + 8, hf.north + 8
        sea_top = _block_name(level, scx, hf.sea_level, scz, ver)
        if not sea_top.startswith("minecraft:water"):
            rep.check("terrain generated", False, f"sea corner @y{hf.sea_level} = {sea_top}")
            return
        rep.check("terrain generated (sea corner is water)", True)

        # land sample: island centre (inland, off the thin rail loop)
        cx = int(round(float(ctx.layout["world"]["border"]["center_x"])))
        cz = int(round(float(ctx.layout["world"]["border"]["center_z"])))
        xi, zi = cx - hf.west, cz - hf.north
        h = int(hf.height[zi, xi])
        exp = CODE_TO_BLOCK[int(hf.surf[zi, xi])][0]
        got = _block_name(level, cx, h, cz, ver)
        rep.check("land surface block matches heightfield",
                  got.startswith(f"minecraft:{exp}"), f"@({cx},{h},{cz}) got {got}, want {exp}")
        above = _block_name(level, cx, h + 1, cz, ver)
        rep.check("air above land surface", above.startswith("minecraft:air"), above)

        # sea sample: seabed solid + water column
        bed = int(hf.height[8, 8])  # corner seabed
        bed_blk = _block_name(level, scx, bed, scz, ver)
        rep.check("seabed is solid", not bed_blk.startswith(("minecraft:air", "minecraft:water")), bed_blk)

        # mountain sample: highest land column should be snow-capped
        flat = np.where(hf.land, hf.height, -9999)
        mzi, mxi = np.unravel_index(int(np.argmax(flat)), flat.shape)
        mh = int(hf.height[mzi, mxi])
        mx, mz = hf.west + int(mxi), hf.north + int(mzi)
        peak = _block_name(level, mx, mh, mz, ver)
        rep.check(f"mountain peak y={mh} is snow", mh >= SNOW_Y and peak.startswith("minecraft:snow"),
                  f"@({mx},{mh},{mz}) {peak}")
    finally:
        level.close()


# rail shape -> the two cardinal (dx,dz) neighbour offsets it connects (ascending connects
# along its axis: the lower end level, the higher end one block up — found by scanning y +-1).
_RAIL_CONN = {
    "east_west": [(1, 0), (-1, 0)], "north_south": [(0, 1), (0, -1)],
    "north_east": [(0, -1), (1, 0)], "north_west": [(0, -1), (-1, 0)],
    "south_east": [(0, 1), (1, 0)], "south_west": [(0, 1), (-1, 0)],
    "ascending_east": [(1, 0), (-1, 0)], "ascending_west": [(1, 0), (-1, 0)],
    "ascending_north": [(0, -1), (0, 1)], "ascending_south": [(0, -1), (0, 1)],
}


def _rail_at(level, x, y, z, ver):
    """(rail_type, shape) at the cell, or None if it is not a rail block."""
    s = _block_name(level, x, y, z, ver)
    if "rail" not in s:
        return None
    base = s.split("[", 1)[0].split(":")[-1]
    shape = s.split("shape=", 1)[1].split("]")[0].split(",")[0].strip('"') if "shape=" in s else None
    return (base, shape)


def validate_rail(ctx, rep: Report) -> None:
    """Structural proof that the line is rideable (we cannot launch Minecraft): every rail
    cell's written shape is read back and checked against its 4-connected neighbours, with no
    diagonal-only adjacency, no Y step >1, no powered/detector/activator rail on a curve, and a
    switch-state-aware reachability model (closed loop + each branch reachable in one lever
    state, on-main in the other). Uses the same `rail.grid` plan the layer used, so the checked
    geometry cannot drift from the written geometry."""
    import amulet
    from collections import defaultdict
    from ..terrain.heightfield import build_heightfield
    from ..rail import grid, route, switches

    hf = build_heightfield(ctx)
    net = grid.plan_network(hf, ctx.layout)
    main_cells, branches, jidx = net["main"], net["branches"], net["jidx"]
    ver = mcio.version_id(ctx)

    # expected on-disk rail: plan cells, with junction-owned cells overlaid (stamp is
    # authoritative for the 3 head cells of each branch + the approach/switch/main_out).
    expected = {c.xz: (c.y, c.rail_type, c.shape) for c in main_cells}
    for cells in branches.values():
        for c in cells[3:]:
            expected[c.xz] = (c.y, c.rail_type, c.shape)
    for name, idx in jidx.items():
        expected.update(switches.expected_rail(name, main_cells[idx].y))
    keys = set(expected)

    # geometric guarantees on the ordered plan (no world reads needed)
    def geom(cells, label, closed):
        n = len(cells)
        diag = ystep = curvetype = None
        for i in range(n):
            c = cells[i]
            if i + 1 < n or closed:
                d = cells[(i + 1) % n]
                if abs(c.x - d.x) + abs(c.z - d.z) != 1:
                    diag = diag or (c.xz, d.xz)
                if abs(c.y - d.y) > 1:
                    ystep = ystep or (c.xz, d.xz)
            if c.shape in grid.CURVE_SHAPES and c.rail_type != "rail":
                curvetype = curvetype or (c.xz, c.rail_type)
        rep.check(f"{label}: 4-connected (no diagonal step)", diag is None, str(diag or ""))
        rep.check(f"{label}: no Y step >1 between cells", ystep is None, str(ystep or ""))
        rep.check(f"{label}: no powered/detector/activator rail on a curve",
                  curvetype is None, str(curvetype or ""))

    geom(main_cells, "main loop", True)
    for name, cells in branches.items():
        geom(cells, f"{name} branch", False)

    # connectivity from the shapes (each shape's two ends must land on another rail cell),
    # except a branch terminus legitimately dead-ends with one open side.
    termini_xz = {cells[-1].xz for cells in branches.values()}
    disc = []
    for (x, z), (y, typ, shape) in expected.items():
        if (x, z) in termini_xz:
            continue
        for dx, dz in _RAIL_CONN.get(shape, []):
            if (x + dx, z + dz) not in keys:
                disc.append((x, y, z, shape, (dx, dz)))
                break
    rep.check("every rail shape connects to its neighbours", not disc,
              f"{len(disc)} dangling e.g. {disc[:3]}")

    level = amulet.load_level(str(ctx.world_dir))
    try:
        # round-trip: the world holds exactly the planned type + shape at each cell
        bad = []
        for (x, z), (y, typ, shape) in expected.items():
            if _rail_at(level, x, y, z, ver) != (typ, shape):
                bad.append((x, y, z, _rail_at(level, x, y, z, ver), (typ, shape)))
                if len(bad) >= 5:
                    break
        rep.check("rail shapes written correctly on disk", not bad,
                  f"{len(bad)}+ mismatch(es) e.g. {bad[:3]}")

        # each lever switch: both exits are real rail, and the lever + lamp are present
        for name, idx in jidx.items():
            c = switches.exit_cells(name)
            jy = main_cells[idx].y
            both = (_rail_at(level, *(c["main_out"][0], jy, c["main_out"][1]), ver)
                    and _rail_at(level, *(c["branch_tee"][0], jy, c["branch_tee"][1]), ver))
            rep.check(f"{name} junction: both exits are connected rail", bool(both))
            ed = mcio.WorldEditor(level, ctx)
            sx, sz = c["stand"]
            lvr = ed.name_at(sx, jy + 1, sz)
            rep.check(f"{name} junction: lever present", lvr == "lever", lvr)

        # turntable rail at Tidmouth (the loop now runs across the apron)
        tx, tz = route.stations()["tidmouth"]
        found = any("rail" in _block_name(level, tx, ty, tz, ver) for ty in range(60, 90))
        rep.check("turntable rail at Tidmouth", found, "no rail in y[60,90) at Tidmouth")
    finally:
        level.close()

    # switch-state-aware reachability: model each junction as a toggle and BFS the rail graph
    adj = defaultdict(set)
    M = [c.xz for c in main_cells]
    for i in range(len(M)):
        a, b = M[i], M[(i + 1) % len(M)]
        adj[a].add(b); adj[b].add(a)
    for cells in branches.values():
        B = [c.xz for c in cells]
        for i in range(len(B) - 1):
            adj[B[i]].add(B[i + 1]); adj[B[i + 1]].add(B[i])

    def reach(drop_edges, start):
        drop = set()
        for a, b in drop_edges:
            drop.add((a, b)); drop.add((b, a))
        seen, stack = {start}, [start]
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if (u, v) not in drop and v not in seen:
                    seen.add(v); stack.append(v)
        return seen

    start = M[0]
    jc = {name: switches.exit_cells(name) for name in jidx}
    termini = {name: branches[switches.JUNCTIONS[name]["branch"]][-1].xz for name in jidx}

    # all switches straight -> main loop is one closed traversable ring, no branch diverted
    seen = reach([(jc[n]["switch"], jc[n]["branch_tee"]) for n in jidx], start)
    rep.check("main loop closed & fully traversable (switches straight)",
              all(c.xz in seen for c in main_cells),
              f"{sum(1 for c in main_cells if c.xz not in seen)} cells unreachable")
    for name in jidx:
        rep.check(f"{name} junction: cart stays on main when lever=straight",
                  termini[name] not in seen)
        # divert at this junction (others straight) -> the branch terminus becomes reachable
        drop = [(jc[name]["switch"], jc[name]["main_out"])]
        drop += [(jc[o]["switch"], jc[o]["branch_tee"]) for o in jidx if o != name]
        rep.check(f"{name} junction: branch reachable when lever=divert",
                  termini[name] in reach(drop, start))


def validate_structures(ctx, rep: Report) -> None:
    """Confirm each MVP station's accent structure exists (scan a coarse grid for its colour)."""
    import amulet
    from ..rail import route
    from ..structures.builders import ACCENTS

    info = route.station_info()
    mvp = {loc["key"] for loc in ctx.layout.get("locations", []) if loc.get("mvp")}
    level = amulet.load_level(str(ctx.world_dir))
    try:
        ed = mcio.WorldEditor(level, ctx)
        ok, total, missing = 0, 0, []
        for key, (x, z, axis) in info.items():
            if key not in mvp:
                continue
            total += 1
            ry = ed.surface_y(x, z) or 68
            accent = ACCENTS.get(key, "white_concrete")
            found = any(
                ed.name_at(x + dx, y, z + dz) == accent
                for dx in range(-14, 15, 2) for dz in range(-14, 15, 2) for y in (ry + 3, ry + 6)
            )
            ok += found
            if not found:
                missing.append(key)
        if ok == 0:
            rep.check("structures built", False, "no station structures found (run `structures`)")
        else:
            rep.check("all MVP stations built", ok == total,
                      f"{ok}/{total} built" + (f"; missing {missing}" if missing else ""))
    finally:
        level.close()


def validate_datapack(ctx, rep: Report) -> None:
    import json
    root = ctx.datapack_out
    mc = root / "pack.mcmeta"
    if not mc.exists():
        rep.check("datapack built", False, "no pack.mcmeta (run `engines`)")
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
    rep.check("tick tag -> engine/tick",
              tickjson.exists() and "sodor:engine/tick" in tickjson.read_text())
    # every engine summon function present + non-trivial
    bad = []
    for e in ctx.engines["roster"]:
        f = root / "data" / "sodor" / "function" / "engine" / "summon" / f"{e['key']}.mcfunction"
        if not f.exists() or "summon block_display" not in f.read_text():
            bad.append(e["key"])
    rep.check("all engine summon functions present", not bad, str(bad))
    fn = root / "data" / "sodor" / "function"
    for name in ("menu", "engine/menu", "travel/menu", "setup"):
        rep.check(f"function present: {name}", (fn / f"{name}.mcfunction").exists())
    # teleport hub per MVP station
    from ..rail import route
    mvp = {loc["key"] for loc in ctx.layout.get("locations", []) if loc.get("mvp")}
    hubs_missing = [k for k in route.station_info() if k in mvp
                    and not (fn / "travel" / "goto" / f"{k}.mcfunction").exists()]
    rep.check("teleport hub per MVP station", not hubs_missing, str(hubs_missing))
    # every function the tick/load tags reference must exist
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


def run(ctx) -> None:
    rep = Report()
    validate_world(ctx, rep)
    validate_terrain(ctx, rep)
    validate_rail(ctx, rep)
    validate_structures(ctx, rep)
    validate_datapack(ctx, rep)
    validate_resourcepack(ctx, rep)
    LOG.info("validation: %s", rep.summary())
    if rep.failures:
        names = ", ".join(n for n, _, _ in rep.failures)
        raise SystemExit(f"VALIDATION FAILED ({len(rep.failures)}): {names}")
