# BACKLOG — post-MVP polish

The MVP (Phases 0–8) is built, validated structurally, and packaged. These are the
next-up improvements, roughly in priority order. Many depend on **in-game play-test
feedback** (drop `latest.log` in the repo root; see docs/playtest loop in memory).

## First, from play-test feedback (highest priority)
- ✅ **Rideable rail** (was #1): the diagonal-track problem is fixed — `src/rail` now lays a
  4-connected path with proper curve/ascending shapes and a validator proves connectivity
  (P3.7–P3.9, DECISIONS D16). Remaining is **in-game momentum/feel tuning only**: confirm the
  cart clears the whole loop + branches without stalling; if a spot stalls, raise booster density
  in `config/layout.toml [rail]`, or fall back to the datapack-driven cart along the route (D15).
- **Ride tuning (engine model):** orientation (forward axis), scale, and offset vs the minecart.
- **Spawn / station look**, mountain shape, coastline detail — adjust from screenshots.
- Confirm `clickEvent` menu format works in 26.1.2 (else adjust).

## Geography / coverage
- More canonical locations (currently 8 MVP): Crosby, Kellsthorpe Road, Great Waterton,
  Ulfstead Castle, Sodor Steamworks, Skarloey/Rheneas, Misty Island, Arlesburgh.
- More branch lines: Skarloey narrow-gauge (Crovan's Gate→Blue Mountain Quarry), the Little
  Western (Tidmouth→Arlesburgh), Culdee Fell, Norramby, Peel Godred.
- Bridges/viaducts + tunnels as distinct structures (currently embankments/cuttings).

## Rail
- Turntable **rotation** (datapack-driven block_display deck + rail reconnect) — apron exists.
- Real **signals** (P3.5, deferred) at stations/junctions.
- ✅ Proper rail curve/ascending shapes for vanilla minecart traversal — done (P3.7, D16).
- Lever-switch **visual polish**: in-game polarity confirm + signpost text on the switch stand (P3.8).

## Engines / mechanics
- Richer engine models (more parts, number plates) and per-engine personalities in dialogue.
- Multiple simultaneous engines (per-engine id matching, not one-at-a-time).
- "Sir Topham Hatt" NPC with branching dialogue; per-station flavour text.
- A whistle sound on board (vanilla sound now; custom sound in the resource pack later).

## Resource pack
- Custom textures via item_display + the 26.1 item-model system (faces, liveries, number
  plates), themed station/building textures, custom sky, whistle sounds.

## Engineering
- `.schem` export of the structure library (mcschematic): ✅ infrastructure done — the
  `[[structures]]` registry + `export_schem` ship the Thomas statue (P4.5, D18); still TODO to
  export the parametric station builders (roundhouse/docks/station) through the same path.
- Optional: target a native 26.1 world if a future amulet build writes it cleanly
  (avoids the 1.21.8→26.1.2 upgrade-on-load).
