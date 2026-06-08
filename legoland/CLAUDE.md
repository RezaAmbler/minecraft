# LEGOLAND California — code-generated Minecraft map

A **singleplayer, datapack-only, PRIVATE/FAMILY (unpublished)** Minecraft Java map of LEGOLAND
California (Carlsbad). Sibling to `../islandofsodor` and built by reusing its proven, fully-validated
pipeline (copy-and-adapt — see DECISIONS LD1).

## Current state (2026-06-07)
Phase 0 + Phase 1 (Castle Hill) complete through structural validation. `python -m src.build all`
regenerates the world + datapack + resource pack in ~2s, **40/40 validation checks pass**, and the
output is byte-reproducible. Castle Hill has DEM terrain, a blocky castle, The Dragon as a rideable
coaster (display-entity train), and the kid-safe datapack menu. **NEXT: P1.9 human play-test gate**
(load in 26.1.2, ride The Dragon, send `latest.log` — see `docs/TESTING.md`) before Phase 2. See
`BUILD_PLAN.md` for the live checklist.

## Hard constraints — never hardcode from memory; values live in `config/` and are wiki-verified
- **World save:** Java **1.21.8**, DataVersion **4440** (amulet output; the 26.1.2 client upgrades it
  on first load — expected & verified for Sodor).
- **Client:** **26.1.2**, DataVersion 4790 — datapack & resource pack target this.
- **Datapack `pack_format` 101.1; resource pack `pack_format` 84.0.** (verified vs minecraft.wiki 2026-06-07)
- **Python 3.12 only** (amulet-core 1.9.40 pins numpy<2; no 3.13/3.14 wheels). `build.py` enforces.
- **Toolchain (pinned in `requirements.lock`):** amulet-core 1.9.40, numpy 1.26.4, Pillow 12.2.0,
  mcschematic 11.4.4, nbtlib 2.0.4. **No beet** (needs 3.14).
- Generate into a **CLEAN** output dir (`build/`), never a live save (sentinel `.legoland-build`).

## Capability rules (bake in; do NOT attempt the "no" items)
- Tracked coasters (Dragon, Coastersaurus, Technic Coaster, Galacticoaster, Cargo Ace) = **rail rides**:
  axis-aligned only, **NO diagonals**, **max 1 block Y per cell**, **NO powered rail on curves**,
  boosters only on straight/ascending cells. Compute each cell's shape from its 4-connected neighbours
  (amulet does NOT recompute rail shape on direct write). 3-way splits use a **lever switch** with BOTH
  states forming valid connected rail (polarity confirmed in-game).
- Ride vehicles = **display-entity rigs bound to a ridden minecart** via a per-tick datapack function.
  Prototype ONE rig end-to-end (The Dragon) before any roster.
- Spinning/drop/free-drive rides = **STATIC themed structures** with visual-only display-entity motion
  where cheap. Do NOT attempt rideable rotation or rideable vertical drop.
- All entities summoned at **RUNTIME** via datapack; **pre-place NONE** (amulet writes entities/*.mca
  the 26.1.2 client rejects → the `finalize` phase deletes `entities/`).

## Scale & geography (LOCKED)
- COMPRESSED real layout: ~**500 blocks** across the whole park, ~100–150 per land. Relative land
  positions + relative elevation from real data; **1.5–2× vertical exaggeration** (configured 1.6×).
- Inputs are real & public-domain, committed under `references/`: USGS 3DEP elevation
  (`dem_grid.csv`, `anchors_elev.csv`) + OSM extract (`osm_legoland.json`). The official LEGOLAND park
  map is copyrighted → used only as a *viewing reference*, **never committed** (see LD2).
- Transform: `src/terrain/transform.py` (single source of truth). Anchors, bbox, compression,
  exaggeration, world frame, seed live in `config/transform.toml`.

## Theming & IP
LEGOLAND-accurate (real land/ride names, minifig aesthetic; bright concrete/terracotta, blocky figures —
custom textures are post-MVP). **LEGO® and LEGOLAND® are trademarks of the LEGO Group.** This is a
private family build; **keep it unpublished.** Original / license-safe assets only; confirm licenses
before adapting any community asset.

## Validation (non-negotiable; we cannot launch Minecraft from here)
Structural only + a human play-test loop. Rails: per-cell shape vs 4-connected neighbours; no diagonal;
no Y>1 step; no powered rail on curves; switch-state-aware reachability; on-disk round-trip read-back.
**No substring-sampling stubs.** Plus world-opens / DataVersion / spawn / pack-JSON checks. A human
play-test gate is REQUIRED after Phase 1 and each ridable land.

## Working protocol
1. Read `BUILD_PLAN.md`; work the lowest unchecked item in the lowest incomplete phase.
2. One phase at a time; meet the exit criterion before the next.
3. Flip `- [ ]` → `- [x]` in `BUILD_PLAN.md` in the SAME COMMIT as the work.
4. Commit per coherent unit; message references phase+task (e.g. `P1.4: The Dragon rail route`).
5. Validate after each phase; regenerate into a clean `build/` regularly to confirm reproducibility
   (schematic mtime=0, level.dat mtime=0, all randomness seeded from `config`).
6. Record non-obvious decisions/workarounds in `docs/DECISIONS.md`.
7. If something is infeasible or wrong: STOP and flag it; don't silently redesign scope.

## Layout
`config/` version·transform·lands·rides · `references/` committed public geo inputs ·
`src/` pipeline (build·config·mcio · world·terrain·rail·structures·entities·datapack·resourcepack·validate) ·
`docs/` DECISIONS·LEGOLAND_REFERENCE·CREDITS·TESTING·INSTALL · `heightmaps/`·`schematics/` derived/exported.
Run everything from `legoland/` inside `./.venv` (`./.venv/bin/python -m src.build …`).
