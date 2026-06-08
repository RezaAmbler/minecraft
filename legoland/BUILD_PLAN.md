# LEGOLAND California — Build Plan

Phased, checkbox-driven. Flip `- [ ]` → `- [x]` in the SAME COMMIT as the work. Full plan + rationale:
`/Users/reza/.claude/plans/here-is-a-plan-zesty-ullman.md`. Constraints: `CLAUDE.md`. Decisions:
`docs/DECISIONS.md`.

## Phase 0 — Config + references + compressed transform  ✅
*Exit: `build info` runs on 3.12; versions wiki-verified; transform yields a sane ~500-block footprint.*
- [x] P0.1 Scaffold tree; copy pyproject + requirements.lock; py3.12 `.venv`; deps import.
- [x] P0.2 Copy & adapt `build.py`/`config.py`/`mcio.py` (sodor→legoland namespace/sentinel); `build info` runs.
- [x] P0.3 `config/version.toml` (1.21.8/4440, datapack 101.1, resourcepack 84.0, client 26.1.2/4790); verified vs minecraft.wiki 2026-06-07.
- [x] P0.4 Reference acquisition: real USGS 3DEP DEM (`references/dem_grid.csv`, `anchors_elev.csv`) + OSM (`osm_legoland.json`). Network path succeeded (LD3).
- [x] P0.5 `config/transform.toml` + `src/terrain/transform.py`: anchors→metres→squash→DEM→1.6× vertical exaggeration→block coords. Preview PNG + anchor sanity assert pass.
- [x] P0.6 `config/lands.toml` — 11 real lands (3 added as LD5 corrections), block centres, palettes, MVP=Castle Hill.
- [x] P0.7 `config/rides.toml` — 5 coasters (Dragon detailed) + 9 static rides.
- [x] P0.8 Seed docs: CLAUDE.md, BUILD_PLAN.md, DECISIONS.md, LEGOLAND_REFERENCE.md, CREDITS.md, TESTING.md.
- [x] P0.9 Commit Phase 0.

## Phase 1 — CASTLE HILL: full vertical slice
*Prove the entire pipeline on ONE land. Exit: Castle Hill terrain + castle + The Dragon coaster
generate, validate, and package; **HUMAN PLAY-TEST GATE** before Phase 2.*
- [x] P1.1 Terrain (compressed) for Castle Hill — adapt `src/terrain` to consume the transform + DEM (replace Sodor green-mask). Vertical exaggeration so the hill reads. Heightfield determinism check.
- [x] P1.2 World foundation — adapt `src/world` (level.dat via nbtlib, DV 4440, Creative + kid-safe gamerules, void gen, spawn near Castle Hill). amulet opens cleanly.
- [x] P1.3 Structures BEFORE rail — adapt `src/structures`: castle (towers/gatehouse/walls, minifig palette) + Dragon station/queue as code models; export `.schem` (mtime=0); terrain-aware flatten leaves the coaster corridor intact.
- [x] P1.4 The Dragon as a rail coaster — adapt `src/rail`: route→4-connected grid→neighbour-derived shapes→booster planner (straights/climbs only)→boarding cell. Reuse `rail/grid.py cell_shape()`. No diagonals, max Y±1.
- [ ] P1.5 Datapack runtime — adapt `src/datapack`+`src/entities`: kid-safe load setup; summon The Dragon display-entity rig bound to a ridden minecart via per-tick `tp`; clickable `/function legoland:menu`. Prototype this ONE rig end-to-end.
- [ ] P1.6 Theming — Castle Hill palette, themed queue/station, a cheap visual-motion accent; resource pack pack.mcmeta (84.0) + icon.
- [ ] P1.7 Validation (REAL validator) — adapt `src/validate`: rail per-cell shape vs neighbours, no diagonal, no Y>1, no powered rail on curves, switch-state reachability, on-disk round-trip; world/DataVersion/spawn/pack-JSON. No stubs.
- [ ] P1.8 Finalize + package — delete `entities/`; byte-reproducible; zip world + resourcepack + INSTALL.md.
- [ ] P1.9 **HUMAN PLAY-TEST GATE** — load in 26.1.2, ride The Dragon, send `latest.log` + notes; tune. Do NOT start Phase 2 until this passes.

## Phases 2+ — Remaining lands (outline; reuse the Castle Hill pipeline)
Each ridable land repeats P1.1–P1.9. Order: The Beginning, Miniland USA, Fun Town, Imagination Zone
(Technic Coaster), NINJAGO World, The LEGO Movie World, Pirate Shores, Land of Adventure (Cargo Ace),
Dino Valley (Coastersaurus), LEGO Galaxy (Galacticoaster). Then park-wide terrain knit + paths +
central lake; full-park validation + reproducibility; package.

## MVP gate (playable)
Castle Hill loads cleanly; The Dragon rideable end-to-end; castle built & reachable; kid-safe settings;
one display-entity rig proven.
