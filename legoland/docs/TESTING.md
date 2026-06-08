# Testing — LEGOLAND California

We cannot launch Minecraft from the build environment, so validation is **structural** (`python -m
src.build validate`) plus a **human play-test loop** in the real 26.1.2 client. A play-test is REQUIRED
after Phase 1 and after each ridable land (CLAUDE.md).

## Structural checks (automated, after each phase)
- World opens in amulet; level.dat DataVersion = 4440; spawn is standable; kid-safe gamerules set.
- Rail: every cell's written shape matches its 4-connected neighbours; no diagonal adjacency; no Y>1
  step; no powered/detector/activator rail on a curve; switch-state-aware reachability (loop closes,
  each branch reachable in exactly one lever state); on-disk round-trip read-back. **No stubs.**
- Packs: datapack pack.mcmeta format 101.1; resource pack 84.0; all summon/menu functions present.
- `entities/` folder absent after `finalize`.
- Reproducibility: two clean rebuilds produce byte-identical world + datapack (mtime=0, seeded RNG).

## Phase 1 play-test checklist (Castle Hill / The Dragon)
1. **Load:** world opens in **26.1.2**; accept the one-time upgrade prompt; lands in Creative, bright,
   peaceful. No chunk-load crash (confirms the entities/ fix).
2. **Spawn:** you arrive on solid ground near Castle Hill, not in a hole or midair.
3. **Terrain:** Castle Hill reads as a hill (vertical exaggeration legible); no floating/holey ground.
4. **Castle:** towers/walls/gatehouse present and on the ground; queue/station beside the track.
5. **Ride:** `/function legoland:menu` → Ride **The Dragon**. You board the train on the track.
   - The train **completes the full loop without stalling** (note where it stops if it does — usually a
     missing booster on a straight/ascending cell, tune `booster_every` / boosters in config).
   - Rig **orientation** is correct (faces direction of travel; sits on the rail, not buried/floating).
   - Indoor section is dark/themed; outdoor drops feel like a coaster.
6. **Exit:** "Exit ride" stops cleanly and dismounts.

## How to report back
Drop `latest.log` (and a screenshot if useful) in the repo root, plus a note of:
- where the train stalled (coords/landmark), if anywhere;
- any rig orientation/scale/offset issues;
- anything that looks buried, floating, or missing.
The fix loop tunes config (boosters, rig offsets, structure heights) and regenerates.
