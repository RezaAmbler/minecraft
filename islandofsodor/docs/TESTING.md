# TESTING.md — in-game manual test checklist

We **cannot launch Minecraft from the build environment**, so structural checks
(`python -m src.build validate`) cover file/coord/format correctness, and the items below
must be verified **in the real client (Java 26.1.2)**. After testing, drop `latest.log`
(and the session JSON) in the repo root — the build assistant reads them for feedback.

## Install (one time)
1. Copy `build/world` into your Minecraft `saves/` folder (rename if you like).
2. (Resource pack, once Phase 7 ships) copy `build/resourcepack` zip into `resourcepacks/`
   and enable it in Options → Resource Packs.
3. Open the world in **1.21.8 will upgrade → 26.1.2** (it upgrades on first load; this is expected).

## World / terrain
- [ ] World opens with **no "Failed to load chunk"** errors (check latest.log).
- [ ] You spawn standing on grass near **Knapford** (central hub), not falling/suffocating.
- [ ] The island looks right: green land, blue sea coastline, a snow-capped mountain to the north.
- [ ] It is always **bright midday**, **clear weather**, **Creative**, no hostile mobs.
- [ ] Flying to the world border: it hugs the island (no endless void to fall into).

## Rail + stations
- [ ] A continuous **rail loop** runs through the stations; you can walk/fly along it unbroken.
- [ ] Branch lines spur to **Ffarquhar** and **Brendam Docks**.
- [ ] Each station has a platform, a building, and a tall coloured marker (Tidmouth=blue,
      Knapford=yellow, Wellsworth=green, Maron=orange, Crovan's Gate=light blue,
      Vicarstown=red, Brendam=cyan, Ffarquhar=lime).
- [ ] Tidmouth has the engine shed (roundhouse) + a turntable apron.

## Rideability (the rail rewrite — P3.7) — **most important this pass**
- [ ] Ride an engine (or place a plain minecart) and confirm the cart **completes the entire
      main loop** and returns to the start **without stalling** — especially on **curves** and on
      **grades** (the climbs near the hills). If it stalls somewhere, note **where** (a station
      name or rough coords) so booster density can be tuned there.
- [ ] The track visibly **curves and ramps** smoothly (no offset/floating/disconnected rail).

## Branch switches (lever-operated — P3.8), at Knapford and Wellsworth
- [ ] At the junction there is an obvious **lever** on a stand beside the line (north/platform side)
      and a **redstone lamp** indicator.
- [ ] With the lever in one position the cart **stays on the main line** through the junction; flip
      the lever and the cart **diverts onto the branch** (Ffarquhar at Knapford, Brendam at Wellsworth).
- [ ] The cart **keeps moving** through the junction either way (boosters on both exits).
- [ ] **If the lever direction is reversed** vs. what you expect (lever "on" should = divert to branch),
      tell the assistant — it's a one-line polarity flip in `src/rail/switches.py` (see DECISIONS D17).

## Thomas statue (at spawn — P4 polish)
- [ ] On arrival at Knapford a blocky **Thomas statue** greets you: blue body, red lining, dark
      funnel, the cheery face (eyes + smile), a "1" on the side, wheels, on a quartz plinth.
- [ ] The statue **faces the spawn point** and **does not block** the platform, station doors, or
      the running line. A floating **"Thomas the Tank Engine"** nameplate hovers above it.

## Engines (the big one — datapack)
- [ ] On load you see the green welcome message.
- [ ] Run `/function sodor:menu` → a clickable list of the 7 engines appears.
- [ ] Click **Thomas** → you are teleported onto the track in a Thomas-shaped engine.
- [ ] The engine **moves along the loop** (powered-rail boosters push the minecart).
- [ ] The engine **model follows** the cart and turns with the track (report jitter/offset/orientation).
- [ ] Each of the 7 engines summons with its own colours (Thomas blue, James red, Henry green, …).
- [ ] Click **Put engine away** (or `/function sodor:engine/stop`) → you dismount, model removed.

## Detailing pass — signs, props, trees, docks, welcome (P-detail)
- [ ] **Name signs render** — every station platform has a readable name board (Knapford, Tidmouth,
      Wellsworth, Brendam Docks, Maron, Crovan's Gate, Vicarstown, Ffarquhar). Confirm the **engraved
      sign shows the name** (not blank, not boxes) and faces the track. *This is the new block-entity
      path — if a sign is blank/garbled, flip `config [detailing].signs = "text_display"` and rebuild.*
- [ ] **Spawn welcome** — beside the Thomas statue at Knapford there's a **lectern**; right-click it to
      read the welcome book (3 pages). *If the book is blank/broken, flip `[detailing].welcome =
      "text_display"`; the WELCOME header sign should read regardless.*
- [ ] **Props look sensible + clear of the track** — water towers, signal boxes, covered footbridges
      (you can walk over them; they clear the track), platform canopies, benches, planters, white
      fencing, red phone boxes. Nothing sits **on** the rails; the footbridges don't block trains.
- [ ] **Trees don't block the line** — ride the **full loop + both branches**: no leaves or trunks over
      the track, no tree on the rails. The island should look lushly wooded with open fields between.
- [ ] **Brendam Docks** reads like a working dock — quay edge, several cranes, goods sheds, crates/
      barrels — and the branch is **still rideable to the terminus**.
- [ ] **Wellsworth** reads like a classic main-line station — **two buildings flanking** the track, a
      footbridge, a signal box — and the **Brendam junction still throws** (the lever still works).

## Things likely to need tuning from your feedback
- Engine model **orientation** (which way is "forward") and **scale/offset** vs the minecart.
- Whether the minecart **keeps rolling** the whole loop (booster spacing in `config/layout.toml [rail]`).
- **Switch polarity** (lever-on should divert to the branch) — one constant in `src/rail/switches.py`.
- **Statue** placement/facing at spawn (offset in the `[[structures]]` entry in `config/layout.toml`).
- Menu **click-to-run** working (clickEvent format) in 26.1.2.
- Spawn position; station look; mountain shape.

Tell the assistant what you saw (or just leave latest.log) and it will adjust.
