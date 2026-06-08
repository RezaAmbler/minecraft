"""Author the authoritative level.dat via nbtlib (P1.2/P1.3).

A wrong DataVersion corrupts/!loads (brief hard constraint), so it comes from
config/version.toml (4440, verified). WorldGenSettings = void flat overworld so unbuilt
chunks are air; the_nether/the_end use standard noise generators (kids stay in overworld).
"""
from __future__ import annotations

import logging

import nbtlib
from nbtlib import Byte, Compound, Double, Int, List, Long, String

LOG = logging.getLogger("sodor.world.level_dat")

# Kid-safe gamerules. NBT stores all gamerule values as strings.
KID_SAFE_GAMERULES: dict[str, str] = {
    "doDaylightCycle": "false",      # locked time of day
    "doWeatherCycle": "false",       # locked clear weather
    "doMobSpawning": "false",        # no hostile pressure
    "doInsomnia": "false",           # no phantoms
    "doTraderSpawning": "false",
    "doPatrolSpawning": "false",
    "doFireTick": "false",           # fire never spreads
    "mobGriefing": "false",
    "keepInventory": "true",
    "doImmediateRespawn": "true",    # no death screen wait for little ones
    "fallDamage": "false",
    "fireDamage": "false",
    "drowningDamage": "false",
    "freezeDamage": "false",
    "naturalRegeneration": "true",
    "spawnRadius": "0",              # always spawn exactly at world spawn
    "showDeathMessages": "false",
    "announceAdvancements": "false",
    "commandBlockOutput": "false",
    "sendCommandFeedback": "false",
}


def _void_overworld_generator() -> Compound:
    """minecraft:flat generator producing pure air (a single air layer) = void."""
    return Compound({
        "type": String("minecraft:flat"),
        "settings": Compound({
            "biome": String("minecraft:plains"),
            "layers": List[Compound]([
                Compound({"block": String("minecraft:air"), "height": Int(1)}),
            ]),
            "lakes": Byte(0),
            "features": Byte(0),
        }),
    })


def _dimensions() -> Compound:
    return Compound({
        "minecraft:overworld": Compound({
            "type": String("minecraft:overworld"),
            "generator": _void_overworld_generator(),
        }),
        "minecraft:the_nether": Compound({
            "type": String("minecraft:the_nether"),
            "generator": Compound({
                "type": String("minecraft:noise"),
                "settings": String("minecraft:nether"),
                "biome_source": Compound({
                    "type": String("minecraft:multi_noise"),
                    "preset": String("minecraft:nether"),
                }),
            }),
        }),
        "minecraft:the_end": Compound({
            "type": String("minecraft:the_end"),
            "generator": Compound({
                "type": String("minecraft:noise"),
                "settings": String("minecraft:end"),
                "biome_source": Compound({"type": String("minecraft:the_end")}),
            }),
        }),
    })


def build_level_dat(ctx, spawn: tuple[int, int, int] | None = None) -> nbtlib.File:
    v = ctx.version
    w = ctx.transform["world"]
    sp = w["spawn"]
    spawn = spawn if spawn is not None else (int(sp[0]), int(sp[1]), int(sp[2]))
    spawn = {"x": spawn[0], "y": spawn[1], "z": spawn[2]}
    bcx, bcz = w["border_center"]
    border = {"center_x": int(bcx), "center_z": int(bcz), "size": int(w["border_size"])}
    dv = int(v.data_version)

    gamerules = Compound({k: String(val) for k, val in KID_SAFE_GAMERULES.items()})

    data = Compound({
        # --- identity / version ---
        "version": Int(19133),                       # Anvil level format version
        "DataVersion": Int(dv),                       # 4440 (authoritative; see DECISIONS D11)
        "Version": Compound({
            "Id": Int(dv), "Name": String(v.version_name),
            "Snapshot": Byte(0), "Series": String("main"),
        }),
        "LevelName": String(w["world_name"]),
        "initialized": Byte(1),
        "LastPlayed": Long(0),                        # fixed (0) for reproducible output
        "DataVersionTag": Int(dv),                    # harmless extra; ignored by MC

        # --- gameplay: Creative, peaceful, cheats on ---
        "GameType": Int(1),                           # Creative
        "allowCommands": Byte(1),                     # cheats on (needed for /tp hubs + functions)
        "Difficulty": Byte(0),                        # peaceful
        "DifficultyLocked": Byte(1),
        "hardcore": Byte(0),

        # --- locked clear midday ---
        "Time": Long(6000), "DayTime": Long(6000),
        "clearWeatherTime": Int(2_000_000_000),
        "raining": Byte(0), "rainTime": Int(2_000_000_000),
        "thundering": Byte(0), "thunderTime": Int(2_000_000_000),

        # --- spawn ---
        "SpawnX": Int(int(spawn["x"])), "SpawnY": Int(int(spawn["y"])), "SpawnZ": Int(int(spawn["z"])),
        "SpawnAngle": nbtlib.Float(0.0),

        # --- world border (no damage; gentle for kids) ---
        "BorderCenterX": Double(float(border["center_x"])),
        "BorderCenterZ": Double(float(border["center_z"])),
        "BorderSize": Double(float(border["size"])),
        "BorderSizeLerpTarget": Double(float(border["size"])),
        "BorderSizeLerpTime": Long(0),
        "BorderSafeZone": Double(5.0),
        "BorderWarningBlocks": Double(5.0),
        "BorderWarningTime": Double(15.0),
        "BorderDamagePerBlock": Double(0.0),          # kid-safe: no border damage

        # --- generation ---
        "GameRules": gamerules,
        "WorldGenSettings": Compound({
            "seed": Long(int(w["seed"])),
            "generate_features": Byte(0),
            "bonus_chest": Byte(0),
            "dimensions": _dimensions(),
        }),

        # --- datapacks: a datapack present in world/datapacks/ auto-enables; don't list
        #     file/sodor here until it exists (avoids "Missing data pack" warning) ---
        "DataPacks": Compound({
            "Enabled": List[String]([String("vanilla")]),
            "Disabled": List[String]([]),
        }),
        "WasModded": Byte(0),
    })

    f = nbtlib.File({"Data": data})
    f.root_name = ""        # vanilla level.dat root tag is unnamed
    return f


def write_level_dat(ctx, spawn: tuple[int, int, int] | None = None) -> None:
    import gzip

    path = ctx.world_dir / "level.dat"
    f = build_level_dat(ctx, spawn=spawn)
    # write raw NBT, then gzip with a FIXED mtime=0 so level.dat is byte-reproducible
    f.save(str(path), gzipped=False)
    raw = path.read_bytes()
    with gzip.GzipFile(str(path), "wb", mtime=0) as g:
        g.write(raw)
    LOG.info("wrote level.dat (DataVersion %d, Creative, void worldgen, spawn=%s) -> %s",
             ctx.version.data_version, spawn or "config", path)


def patch_spawn_y(ctx, y: int) -> None:
    """Update only SpawnY in an existing level.dat (e.g. after terrain sets the surface)."""
    path = ctx.world_dir / "level.dat"
    f = nbtlib.load(str(path))
    f["Data"]["SpawnY"] = Int(int(y))
    f.save(str(path), gzipped=True)
    LOG.info("patched SpawnY -> %d", y)


def patch_spawn_xyz(ctx, x: int, y: int, z: int) -> None:
    path = ctx.world_dir / "level.dat"
    f = nbtlib.load(str(path))
    f["Data"]["SpawnX"] = Int(int(x))
    f["Data"]["SpawnY"] = Int(int(y))
    f["Data"]["SpawnZ"] = Int(int(z))
    f.save(str(path), gzipped=True)
    LOG.info("patched spawn -> (%d, %d, %d)", x, y, z)
