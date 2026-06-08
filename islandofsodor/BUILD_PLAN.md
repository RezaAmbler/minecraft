# BUILD_PLAN.md — Island of Sodor (source of truth for progress)

Work the lowest unchecked item in the lowest incomplete phase, top to bottom. Finish and
validate a phase before the next. Flip `- [ ]`→`- [x]` in the same commit that delivers it.
Full rationale: `/Users/reza/.claude/plans/you-are-building-a-zany-eclipse.md`.

MVP gate (definition of playable): island + coastline load cleanly · continuous main-line
loop rideable end to end · all 7 engines summon & drive · Tidmouth Sheds + Knapford +
Brendam Docks + main-line stops built and reachable · kid-safe settings.

---

## Phase 0 — Scaffolding  ✅ (exit: `build info`/`--help` run; deps import; version.toml matches wiki)
- [x] P0.1 Repo directory tree + `.gitignore`
- [x] P0.2 `pyproject.toml` + Python 3.12 `.venv` + pinned deps installed + `requirements.lock` (beet dropped — see DECISIONS D2)
- [x] P0.3 `config/version.toml` (data_version 4440, datapack 81, resourcepack 64) — verified vs wiki
- [x] P0.4 `config/layout.toml` (coords, 14 locations, line topology)
- [x] P0.5 `config/engines.toml` (classic 7 roster)
- [x] P0.6 `src/build.py` CLI + `src/config.py` + 8 phase-module stubs (info/all/clean/phase dispatch work)
- [x] P0.7 `CLAUDE.md`, `BUILD_PLAN.md`, `docs/DECISIONS.md`, `docs/SODOR_REFERENCE.md`, `resourcepack/CREDITS.md`
- [x] P0.8 Re-verify version values vs wiki; record toolchain decisions in DECISIONS
- [x] P0.9 `git init`, first commit

## Phase 1 — World foundation  (exit: amulet opens the void world cleanly; spot-checks pass)
- [x] P1.1 De-risk: confirm the amulet world-creation path (create vs nbtlib level.dat + amulet chunks); log in DECISIONS
- [x] P1.2 Generate `level.dat` via nbtlib: DataVersion 4440, Creative, allowCommands, peaceful, kid-safe gamerules (doDaylightCycle/doWeatherCycle false, fixed clear midday, doMobSpawning false, keepInventory true, doImmediateRespawn), LevelName, datapack enabled
- [x] P1.3 WorldGenSettings = void/superflat overworld (empty layers, no features/lakes)
- [x] P1.4 Spawn point + small safe spawn platform; generous centered world border
- [x] P1.5 Fill layout.toml world origin/bounds; master coordinate helpers in `src/world`
- [x] P1.6 Validation: amulet opens world; spawn-area chunk reads as air; level.dat fields correct (write→reopen smoke test)

## Phase 2 — Terrain  (exit: island landmass + coastline load cleanly AND reproducibly) *(MVP)*
- [x] P2.1 Source a reference Sodor map into `heightmaps/source/` (CC BY-SA 2.5; attributed in CREDITS)
- [x] P2.2 Pillow/numpy: extract Sodor land mask (green threshold + corner-clear + closing + flood-fill) → world-resolution land grid (3400×2504 blocks). Preview committed. (Zone masks/elevation folded into P2.3.)
- [x] P2.3 Deterministic terrain generator (seeded): coastline-aware elevation, sea + gravel/sand seabed, beaches, rolling hills, snow-capped mountain massif; bright palette. Fast numpy chunk writer.
- [x] P2.4 Region-batched (save+purge), resumable, logged writing via amulet — 45,369 chunks in ~31s
- [x] P2.5 Validation: amulet reopens; spawn-on-surface; per-zone spot-checks (grass/water/gravel/snow); heightfield determinism. 19/19. Preview: heightmaps/terrain_preview.png

## Phase 3 — Rail network  ✅ (exit: continuous main-line loop placed + ≥1 turntable) *(MVP)*
- [x] P3.1 Main-line topology re-derived onto the island + closed loop (route.py; stations on land)
- [x] P3.2 MVP branches: Ffarquhar (Knapford–Elsbridge–Ffarquhar), Brendam (Wellsworth–Brendam Docks)
- [x] P3.3 Rail placement engine: 3-wide bed, embankment/cut, rails, powered-rail boosters (hidden redstone)
- [x] P3.4 Turntable pad at Tidmouth (rotation wired by datapack in Phase 6 — see DECISIONS D15)
- [~] P3.5 Decorative signals — deferred to Phase 4 (placed with station structures)
- [x] P3.6 Validation: main loop sampled has continuous rail + closed; turntable present. 22/22.
- [x] P3.X CRITICAL: fixed 26.1.2 load (delete entities/, packs->26.1.2, spawn on grass) — DECISIONS D14
- [x] P3.7 RIDEABLE rail rewrite: 4-connected grid path + neighbour-derived curve/ascending shapes;
      booster planner (branches boosted); structures lay before rail so the corridor is never buried. D16
- [x] P3.8 Lever-operated switch junctions (Knapford→Ffarquhar, Wellsworth→Brendam): lever + lamp +
      both-exit boosters, polarity-agnostic geometry (in-game polarity confirm). D17
- [x] P3.9 Permanent rail validator: per-cell shape vs 4-connected neighbours, no diagonal/Y>1/powered-
      on-curve, switch-state-aware reachability (closed loop + each branch reachable in one lever state).

## Phase 4 — Structures  ✅ (exit: key MVP stations built and reachable on the loop) *(MVP)*
- [x] P4.1 Structure builders (src/structures/builders.py): generic platform+building station, Tidmouth roundhouse, Brendam dock pier; distinct accent colour + lit marker each
- [x] P4.2 Placement engine: build by route station_info (position + track axis), terrain-aware flatten
- [x] P4.3 Built 8 MVP locations: Tidmouth (roundhouse+turntable), Knapford, Wellsworth, Maron, Crovan's Gate, Vicarstown, Brendam Docks, Ffarquhar
- [x] P4.4 Validation: each MVP station's accent structure present. 23/23.
- [x] P4.5 Thomas statue at the Knapford spawn: blocky model (blue body/red lining/dark funnel/cheery
      face/№1/wheels on a quartz plinth) authored as code → reusable `schematics/thomas_statue.schem`,
      stamped via a `[[structures]]` registry, with a floating nameplate. D18

## Phase 5 — Engines  ✅ (exit: all 7 summonable; rigs + ride built + documented) *(MVP)*
- [x] P5.1 Rig generator (datapack/rig.py) → per-engine summon function (block_display parts: translation/scale, brightness 15, teleport_duration)
- [x] P5.2 Minecart↔rig follow tick (`tp @e[parts] @s` copies cart pos+yaw); board point at Knapford; one ride at a time
- [x] P5.3 Datapack writer + clickable /function sodor:menu + stop/load; in-game checklist in docs/TESTING.md
- [x] P5.4 All 7 engines generated (Thomas…Toby) with their liveries
- [x] P5.5 Validation: pack.mcmeta fmt 101, tick tag, all summon functions + tag targets exist. 29/29.
- [ ] P5.6 IN-GAME verify ride feel/orientation (needs play-test; tune from latest.log)

## Phase 6 — Datapack mechanics  ✅ (exit: datapack builds & validates; hubs + dialogue; settings locked)
- [x] P6.1 Load-time `setup`: re-asserts kid-safe gamerules + locked clear midday + peaceful
- [x] P6.2 Teleport hubs: clickable `/function sodor:travel/menu` + per-station goto (8 hubs)
- [x] P6.3 Station-name labels (text_display, navigation) + welcome dialogue + clickable master menu
- [x] P6.4 Datapack pack.mcmeta (format 101 for 26.1.2) + merged tick/load tags
- [x] P6.5 Validation: structure/JSON valid; all tag-referenced functions exist. 35/35.

## Phase 7 — Resource pack (original stand-ins)  ✅ (exit: pack validates)
- [x] P7.1 Resource `pack.mcmeta` (format 84 for 26.1.2) + original pack.png icon
- [x] P7.2 Engine liveries (coloured concrete) + cheery blocky FACES (eyes+smile from black blocks, in rig — no textures needed, regenerable). Richer textures/sounds deferred to polish.
- [x] P7.3 `CREDITS.md` — all original; reference map CC BY-SA attributed
- [x] P7.4 Validation: resourcepack pack.mcmeta valid + format 84 + icon present. 37/37.

## Phase 8 — Integration & packaging  ✅ (exit: one command regenerates + packages a validated, reproducible world)
- [x] P8.1 `build.py all` regenerates everything end to end into clean `build/` (~36s)
- [x] P8.2 Full validation suite (`src/validate`): **67 checks** — world/terrain/rail (P3.9
      shape/connectivity/switch-reachability)/structures/detailing (signs, props, docks, Wellsworth,
      welcome)/trees/datapack/resourcepack
- [x] P8.3 Reproducibility: level.dat + datapack + resourcepack BYTE-identical across rebuilds (fixed-mtime gzip); region block-content identical (only .mca header timestamps vary)
- [x] P8.4 Package: IslandOfSodor-world.zip (datapack inside) + IslandOfSodor-resourcepack.zip + INSTALL.md in build/dist/

## Phase 9 — MVP gate + iteration  (exit: MVP met & documented; polish backlog enumerated)
- [x] P9.1 MVP gate assessed (structural pass; in-game items pending the user's play-test):
  - [x] Island landmass + coastline exist & load (region chunks load in 26.1.2 after the entities/ fix)
  - [x] Continuous main-line LOOP placed AND genuinely vanilla-rideable (4-connected curve/ascending
        rail; validator proves connectivity + switch reachability — P3.7–P3.9) — *ride feel still in-game confirm*
  - [x] All 7 engines summonable (datapack functions + clickable menu) — *ride feel/orientation needs in-game confirm*
  - [x] Key stations built & reachable (Tidmouth+turntable, Knapford, Brendam, + main-line stops) + teleport hubs
  - [x] Kid-safe (Creative, locked clear midday, peaceful, no damage) in level.dat + load `setup`
  - [ ] P9.1a IN-GAME sign-off from a play-test (latest.log) — the only remaining MVP gate item
- [~] P9.2 Polish backlog (post-MVP): see docs/BACKLOG.md

## Phase 10 — Detailing pass  ✅ (exit: stations/island detailed; build reproducible; validation 67/67)
- [x] P10.1 Block-entity capability (`mcio.set_sign`/`set_lectern_book`) — real engraved signs +
      lectern books that survive the entities/ strip; text_display fallback switch. DECISIONS D19
- [x] P10.2 Reusable prop library (`src/structures/props.py`): water tower, coal stage, footbridge,
      canopy, signal box, bench, planter, phone box, picket fence, name board, warehouse/goods shed,
      crate/barrel, crane — authored as code → mtime=0 `.schem`. D21
- [x] P10.3 Declarative per-type detailing distribution (`src/structures/detailing.py` + `[detailing]`):
      a name sign per station + per-type prop kits, guarded off the rail corridor + switch cells. D21
- [x] P10.4 Brendam Docks build-out (quay, cranes, goods sheds, crates, lamps) + Wellsworth second
      flanking building, footbridge, signal box (junction kit) — switch stays operable.
- [x] P10.5 Deterministic LUSH trees (`src/trees`, ~23k): seeded jittered-grid, exclusion mask, never
      over the track or in water; runs after rail. D20
- [x] P10.6 Spawn welcome: lectern + written book + header sign beside the Thomas statue at Knapford.
- [x] P10.7 Validation 55→**67** (signs/props/docks/Wellsworth/welcome/trees) + byte-reproducible
      (seeded trees, mtime=0 schems, deterministic block-entity NBT). Repackaged build/dist/.
