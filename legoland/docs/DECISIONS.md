# Decisions — LEGOLAND California

Newest first. Each entry: **date · decision · why · consequences**. `LD#` = Legoland decision.
Pipeline-level decisions inherited from `../islandofsodor/docs/DECISIONS.md` (D2/D3 toolchain,
D10/D11 world-creation, D14 26.1.2 compat, D16/D17 rail, D18 schematics) still apply unless noted.

---

### LD8 · 2026-06-07 · Config schema = version + transform + lands + rides
**Decision:** Replace Sodor's `layout.toml`/`engines.toml` with four theme-park config files:
`version.toml` (unchanged), `transform.toml`, `lands.toml`, `rides.toml`; `src/config.py` gains
`load_transform/load_lands/load_rides` + helpers (`lands`, `mvp_lands`, `coasters`, `static_rides`).
**Why:** A park is lands + rides, not stations + engines; cleaner than overloading Sodor's schema.
**Consequences:** `build info` rewritten; Phase-1 phase modules read `ctx.transform/ctx.lands/ctx.rides`.

### LD7 · 2026-06-07 · Minifig aesthetic via vanilla blocks first
**Decision:** Bright concrete/terracotta palettes per land (in `lands.toml`), blocky display-entity
figures; custom textures deferred to a post-MVP backlog item.
**Why:** Matches Sodor's vanilla-first, original-assets approach; avoids texture/IP work blocking MVP.
**Consequences:** Resource pack starts as pack.mcmeta + icon only; theming comes from block choice.

### LD6 · 2026-06-07 · Namespace `legoland`, world name "LEGOLAND California"
**Consequences:** datapack at `world/datapacks/legoland`, functions `legoland:*`, sentinel
`.legoland-build`, zip names `LegolandCalifornia-*.zip`.

### LD5 · 2026-06-07 · Lands roster — include real-park corrections, flag them
**Decision:** The brief's land list was incomplete vs the real 2026 park. Added the missing real lands
**Imagination Zone**, **Land of Adventure**, **The LEGO Movie World** (marked `in_brief = false` in
`lands.toml`); confirmed **LEGO Galaxy** (opened Mar 2026) and **Dino Valley** (was Explorer Island,
2024). Also: the **Technic Coaster lives in Imagination Zone** (not an "Aquazone" land); **Cargo Ace**
is in Land of Adventure per Wikipedia (one source says Fun Town — minor uncertainty, noted in
`rides.toml`).
**Why:** Brief says "LEGOLAND-accurate" and "corrections logged, not silently changed."
**Consequences:** 11 lands total. Phase 1 is unaffected (Castle Hill only). **User to review** the
added lands and the Cargo Ace placement.

### LD4 · 2026-06-07 · Transform model (real-world → block)
**Decision:** Equirectangular projection about the park centroid (33.1275, -117.3115) → local metres;
horizontal compression **1.6 m/block** (~524×488-block footprint, ~500 across); vertical
**1.0 block/m** off an `elev_ref_m = 34.0 m` datum at `base_y = 64` → **1.6× vertical exaggeration**
relative to the compressed footprint (in the 1.5–2× window). DEM bilinearly interpolated.
Implemented in `src/terrain/transform.py`; params in `config/transform.toml`.
**Why:** Anchors give relative arrangement/orientation only; compression + exaggeration keep the
hillside legible after squashing. **Verified:** anchors land at Dragon (90, y87, -106), Galacticoaster
(-144, y81, -13), Coastersaurus (-48, y77, 83) — correct NE-high / west / south arrangement; preview
PNG matches the real hill-toward-lake slope.
**Consequences:** Single source of truth for all block placement; seed = 4790 (fixed) for determinism.

### LD3 · 2026-06-07 · Reference acquisition — real data path succeeded
**Decision:** Fetched **USGS 3DEP** elevation via the EPQS point service on a 15×15 grid (225 pts,
zero failures) + the 3 anchor points, and an **OSM** Overpass extract, into `references/`.
**Why:** Real, public-domain, reproducible inputs beat a hand-authored fallback.
**Consequences:** `references/dem_grid.csv` (relief 34–80 m; anchors 47.3/50.9/56.9 m),
`anchors_elev.csv`, `osm_legoland.json` are committed build inputs. Fallback (hand-authored profile)
not needed.

### LD2 · 2026-06-07 · Commit public geo data, NOT the copyrighted park map
**Decision:** USGS 3DEP (public domain) and OSM (ODbL — attributed in CREDITS) are committed under
`references/`. The official LEGOLAND park map is copyrighted → used only as a private viewing reference
to hand-author `lands.toml`; **not committed**.
**Why:** Reproducibility needs committed inputs; respect copyright; private/family build.
**Consequences:** Land centres other than the 3 coaster anchors are approximate (flagged in `lands.toml`).

### LD1 · 2026-06-07 · Copy-and-adapt the Sodor pipeline (no shared lib yet)
**Decision:** Copy `../islandofsodor/src` into `legoland/src` and adapt map-specific parts, rather than
refactoring a shared core.
**Why:** Keeps Sodor's validated, byte-reproducible build untouched; lets Legoland (theme park) diverge
from Sodor (railway) without coupling.
**Consequences:** Some duplication; a shared-core refactor is a future backlog item, not a prerequisite.

### LD0 · 2026-06-07 · Versions verified vs minecraft.wiki
1.21.8 → DataVersion **4440**; 26.1.2 (released 2026-04-09) → DataVersion **4790**; datapack
`pack_format` **101.1**; resource pack **84.0**; 4440→4790 upgrade-on-open is expected/safe. No change
from the inherited Sodor `version.toml`.
