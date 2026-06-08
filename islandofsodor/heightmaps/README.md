# heightmaps/

Inputs and derived data for terrain generation (Phase 2).

- `source/` — the reference Sodor map image (a **private build input**; not redistributed
  with any deliverable — see CREDITS / IP note). Used to trace coastline, zone masks, and
  rail-route polylines. NOTE: the canon map is stylized/cartoon, **not topographic** — it
  drives 2-D layout; elevation is authored per-zone with deterministic seeded noise.
- derived masks (coastline, zones, rail polylines) are produced by `src/terrain/` and may be
  cached under `_cache/` (gitignored).
