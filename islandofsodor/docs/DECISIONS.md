# DECISIONS.md — running log of technical decisions + rationale

Newest first. Each entry: date · decision · why · consequences.

## 2026-06-07 — Rail rideability rewrite + Thomas statue (P3.7–P3.9, P4 polish)

### D16. Rails are now genuinely vanilla-rideable (supersedes the geometry half of D15)
**Why:** A play-test found the main line was not continuously rideable — a minecart ran a short
way then hit an offset, disconnected section. Root cause (confirmed in source): `route.densify`
interpolated waypoints **diagonally** (both X and Z change per step) and `_lay_track` wrote every
cell as a flat `east_west`/`north_south` straight — never a curve or ascending shape. Minecraft
rails only connect orthogonally, so the line was disconnected from the start of every diagonal run.
**Fix (`src/rail/grid.py` + `pathing.py`):** snap each route to a strictly **4-connected grid path**
(one cardinal step per cell, an axis-aligned staircase with long straights + batched corners), then
derive every cell's `shape` from its **immediate** neighbours (straight / curve / ascending). The Y
profile flattens corner + junction neighbourhoods and removes width-1 valleys so curves stay flat and
grades land on straights (where `ascending_*` is legal). Booster planner: only plain `rail` curves;
powered rail lands on straights/climbs/curve-exits (denser, `booster_every=4`, **branches boosted too**).
**Corridor is sacred:** structures now run **before** rail in `ALL_SEQUENCE` so a station's flatten/
platform can never bury or erase the line (incl. branch departures through the platform).
**Consequence:** the laid rail is the real running line again; the datapack-driven cart (D15) is kept
as the documented fallback if vanilla momentum ever stalls. Ride feel still confirmed in-game.

### D17. Branch junctions are lever-operated redstone switches; power polarity confirmed in-game
**Why:** A rail connects to ≤2 neighbours, so a 3-way split (main + branch) must be a redstone-switched
rail: unpowered = straight on the main line, powered = divert to the branch (minecraft.wiki; the exact
default-curve polarity is unstated for 26.1.2). `src/rail/switches.py` forces a short straight run through
each junction (Knapford→Ffarquhar, Wellsworth→Brendam), then stamps a switch cell + a kid-reachable lever
on a stand that powers it, a redstone-lamp indicator, a slowing approach cell, and powered rails on **both**
exits. The geometry is **polarity-agnostic** — both exits are laid as real connected rail, so whichever
power state vanilla uses for "divert", the cart always lands on valid track; a single constant flips it if
the lever reads backward in-game. The validator models each junction as a toggle and asserts both states.
**Consequence:** one in-game tweak at most (the polarity constant). Switch *rotation*/visual signals later.

### D18. Statue authored as code → `.schem` library artifact + in-memory replay placement
**Why:** The Thomas spawn statue is defined once as a block model (`src/structures/statue.py`), exported to
`schematics/thomas_statue.schem` (mcschematic) **and** replayed block-by-block into the world by a new
`[[structures]]` registry (`config/layout.toml` + the loader in `src/structures`). Replaying the in-memory
model — rather than reading the `.schem` back — keeps one source of truth and avoids a second translation
path. mcschematic embeds the current timestamp in the gzip, so `export_schem` **re-gzips with `mtime=0`**
(the level_dat.py trick) to stay byte-reproducible. **Consequence:** the `.schem` is the reusable library
artifact (not shipped in the world zip); the world placement is regenerable from the same source.

## 2026-06-07 — Phase 3 rail + CRITICAL play-test findings (26.1.2)

### D14. Client is 26.1.2; world stays 1.21.8 (+upgrade); delete entities/; packs target 26.1.2
**Why:** The user play-tested (latest.log + session JSON in repo root — see memory) and the
client is **Java 26.1.2** (DataVersion 4790, datapack fmt 101.1, resource fmt 84.0), NOT
1.21.8. Findings + fixes:
- The 1.21.8 world (4440) DID load in 26.1.2 — **region/block chunks upgrade cleanly**. But
  **`entities/*.mca` crashed** (`EntityStorage.loadEntities` → `NoSuchElementException: No value
  present` = missing chunk `Position`), failing 180 spawn-area chunks. amulet writes entity
  chunks 26.1.2 rejects. We place **zero** pre-placed entities (engines are datapack-summoned),
  so a new **`finalize` step deletes `entities/`** (MC recreates empty ones). Fixes the crash.
- amulet-core 1.9.40 **cannot cleanly write a native 26.1 world** (`DimensionDoesNotExist` on a
  fresh 26.1 create; PyMCTranslate max java = (26,1,0)=4786). So the **world stays 1.21.8/4440**
  (amulet's reliable output) and 26.1.2 upgrades it on first load. The **datapack + resource
  pack target 26.1.2** (config [client] + [pack_format] datapack 101 / resource 84).
- Removed premature `file/sodor` from level.dat `DataPacks.Enabled` (caused "Missing data pack"
  warning); a datapack present in world/datapacks/ auto-enables once Phase 6 creates it.
- `finalize` also re-places spawn on real **grass** near Knapford (the rail bed had cleared the
  configured spawn column to air).

### D15. Rail = visual bed + datapack-driven ride (not vanilla rail physics) — *geometry superseded by D16*
**Why:** Routes are diagonal; vanilla rails are orthogonal-with-curves (ugly staircases). The
engine ride (Phase 5) interpolates along the route polyline (pathing.compute_path) via per-tick
teleport, so the laid rails are a coherent 3-wide gravel **bed + rails for looks**; smoothed,
slope-limited height shared between bed-laying and the ride. Boosters (powered rail on hidden
redstone blocks) give vanilla rideability as a backup. Turntable: a pad at Tidmouth now;
datapack rotation in Phase 6.

## 2026-06-07 — Phase 2 terrain (P2.1/P2.2)

### D12. Island shape from a **CC BY-SA reference map** + coded extraction (no scipy)
**Why:** User chose the "hybrid" route. The reference is Wikimedia Commons
"Maps-sodor-railways-amoswolfe.svg" (**CC BY-SA 2.5** — license-clean, attributed in
CREDITS). Extraction (`src/terrain/source_map.py`): green-threshold the land, clear the
two off-island corner masses (Isle of Man, England) via parametric rectangles, **morphological
closing** (PIL MaxFilter→MinFilter, `close_px=5`) to seal railway-line/text gaps so the
island is solid, flood-fill the central component, fill interior holes. Pure Pillow+numpy —
**scipy not needed** (PIL MaxFilter/MinFilter give dilation/erosion; PIL floodfill gives
fill, but note: `Image.fromarray(...).copy()` is required or floodfill writes don't persist).
Reproducible from the committed image + code; a preview PNG is committed for verification.
**Consequence:** `src/terrain/geography.py` fits the mask to `map.island_width_blocks=3400`
centred on the world border → 3400×2504-block island. Coastline is slightly smoothed (kid-legible).

### D13. Placeholder station coords need re-deriving from the island (Phase 3)
**Why:** layout.toml station coords were rough guesses; against the real island some fall in
sea (e.g. Tidmouth). Phase 3 re-derives station positions onto the landmass (and snaps to
coast where appropriate) when laying rail. Terrain (Phase 2) only needs the landmass, which is correct.

## 2026-06-07 — Phase 1 world creation (P1.1 de-risk)

### D10. World creation = amulet `create_and_open` + nbtlib-authored `level.dat`, **level.dat written before chunks**
**Why / how (empirically validated, /tmp probes):**
amulet's `AnvilFormat._create` writes only a skeletal `level.dat`
(`version=19133`, `DataVersion`, `LastPlayed`, `LevelName`) — no GameType, gamerules,
WorldGenSettings, spawn, border, or DataPacks. On open it loads `level.dat` into
`root_tag`; on save it does `root_tag.save_to()` with **no normalization**, so fields it
doesn't understand are preserved across round-trips. Chosen flow:
1. `AnvilFormat(path).create_and_open("java",(1,21,8), overwrite=True)`; close. *(no chunk writes yet)*
2. **nbtlib writes the authoritative complete `level.dat`** (DataVersion 4440, Creative,
   kid-safe gamerules, void flat WorldGenSettings, spawn, border, DataPacks).
3. `amulet.load_level(path)` → write all chunks via `set_version_block(x,y,z,"minecraft:overworld",("java",(1,21,8)),block)` → `save()`/`close()`.
Block round-trip verified (stone/concrete read back); fields survive.
**Consequence:** later phases just `load_level` + write chunks; level.dat is owned by `src/world`.

### D11. **DataVersion 4440 is authoritative for 1.21.8** (not PyMCTranslate's 4439)
**Why:** PyMCTranslate (amulet's table) maps `("java",(1,21,8))→4439` internally (likely
registered at a pre-release). The true release DataVersion is **4440**, confirmed by THREE
sources: minecraft.wiki/w/Data_version, PrismarineJS `minecraft-data` protocolVersions.json,
and search consensus (4440 = 1.21.8-rc1/release). Because we author `level.dat=4440` BEFORE
writing chunks, amulet reads 4440 from level.dat and **stamps on-disk chunks at 4440** too
(verified: `on-disk chunk DataVersion: 4440`). If we had let amulet pick, chunks would be 4439.
**Consequence:** keep `config/version.toml data_version = 4440`; never write chunks before level.dat is set.

## 2026-06-07 — Phase 0 toolchain & target

### D1. Target Minecraft Java **1.21.8** (DataVersion 4440)
**Why:** User choice. 1.21.8 is mature and is the last patch *before* the
`min_format`/`max_format` minor-version pack system (introduced 1.21.9), so pack
formats are plain integers (datapack **81**, resourcepack **64**). All values verified
against minecraft.wiki on 2026-06-07 and stored in `config/version.toml`.
**Consequence:** Players select the 1.21.8 profile in their launcher.

### D2. Python **3.12 only**; reject 3.13/3.14 and amulet-core 2.x
**Why:** `amulet-core` 1.9.40 (the stable, documented 1.x API) pins `numpy~=1.17`
(<2.0). numpy 1.x has **no wheels for Python 3.13/3.14** (only numpy 2.x exists there),
so the stable amulet stack is uninstallable on the machine's preinstalled 3.13/3.14.
`amulet-core` 2.0.9a0 *does* install on 3.14 but is an **alpha** pulling numpy 2.5.0rc1
and a stack of alpha sub-packages — too fragile for a long-lived, reproducible family
project. Installed `python@3.12` via Homebrew; numpy 1.26.4 + amulet-core 1.9.40 resolve
cleanly. `build.py` refuses other interpreters (`--allow-any-python` to override).
**Consequence:** Build env is pinned to 3.12 (`requires-python = ">=3.12,<3.13"`).

### D3. **Drop beet**; emit the datapack with a thin in-repo writer
**Why:** `beet` 0.115.0 requires Python **>=3.14**, incompatible with the 3.12 amulet
stack (D2). The brief explicitly allows preferring raw output over fighting an
abstraction. A datapack is just `.mcfunction` text + JSON tags + `pack.mcmeta`; a small
writer in `src/datapack` gives full control with zero cross-Python complexity.
**Consequence:** No beet dependency. `src/datapack` owns datapack assembly.

### D4. **nbtlib 2.0.4** (not 1.12.1)
**Why:** `mcschematic` 11.4.4 requires `nbtlib>=2.0.4`. amulet uses its **own**
`amulet-nbt` (2.1.8) internally, so nbtlib is only used by mcschematic and by us for
`level.dat`/map/entity NBT — no conflict. We adapt to the nbtlib 2.x API.
**Consequence:** Use nbtlib 2.x idioms when hand-editing `level.dat`.

### D5. mcschematic max JE enum is **JE_1_21_5**; accepted
**Why:** mcschematic 11.4.4's newest Java 1.21 version is 1.21.5 (no 1.21.6–8). Block
states for our palette (stone, planks, rails, glass, stairs, slabs, concrete, wool, …)
are **identical** across 1.21.x, and the **world's** DataVersion (4440) is written by
`level.dat` + amulet — not by mcschematic. So `.schem` metadata at 1.21.5 is cosmetic.
**Consequence:** `.schem` files carry a 1.21.5 DataVersion; harmless for our use.

### D6. amulet block writes target `("java", (1, 21, 8))`
**Why:** PyMCTranslate 1.2.43 (bundled with amulet) confirms Java `(1,21,8)` is a known
version; `set_version_block` accepts the `(platform, version_tuple)` form. Stored in
`config/version.toml [target.amulet]`.

### D7. Rideable engine = **minecart physics + display rig, per-tick teleport, smoothed** (architecture; prototype in Phase 5)
**Why:** Display entities don't ride rails. Established community pattern (Solar's Block
Display Vehicles; "On A Rail"): minecart carries the player + provides physics; a rig of
item/block_display entities is teleported to the cart's position+yaw each tick, with
`teleport_duration` (≈2) so motion interpolates instead of jittering. Prototype **one**
engine (Thomas) before scaling.
**Consequence:** Highest-risk item; ride *feel* is only verifiable in-game (TESTING.md).

### D8. Main line **closed into a loop** (vs canon point-to-point) (architecture; Phase 3)
**Why:** Canon main line is Vicarstown↔Tidmouth (not a loop). Continuous riding is far
friendlier for young children, so the MVP adds return/balloon loops at the ends.
**Consequence:** A deliberate, documented stylization; canon ordering preserved along the run.

### D9. **Original, license-safe assets only**
**Why:** User choice; avoids all IP/license risk (Mattel IP; community packs often
derivative). No community-asset adaptation. Reference Sodor map used privately for layout,
not redistributed. See `resourcepack/CREDITS.md`.
