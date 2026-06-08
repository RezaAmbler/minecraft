# SODOR_REFERENCE.md — canon geography, locations, line topology, roster

A working reference for the build. Fan sources vary in detail; our world is a **stylized,
kid-legible adaptation**, not a survey-accurate replica. Coordinates live in
`config/layout.toml` and are refined from the source map in Phase 2.

Sources: en.wikipedia.org/wiki/Island_of_Sodor · ttte.fandom.com (Thomas Wiki) ·
The Railway Series (Rev. W. Awdry) canon maps. Verified spot-checks 2026-06-07.

## Island overview
- Roughly an east–west island off the north-west coast of England, joined to the mainland
  at **Barrow-in-Furness** via a bridge to **Vicarstown** (the island's eastern gateway).
- The **Main Line** runs west across the island from Vicarstown to **Tidmouth** on the
  west coast (Tidmouth Sheds = the engines' home).
- North-west is mountainous (**Culdee Fell**, the highest point; the **Skarloey Railway**
  narrow-gauge slate country). South coast has **Brendam** (docks) and the Little Western
  coastal run toward **Arlesburgh**.
- Our axis convention: +X = east, +Z = south. Vicarstown at large +X (east), Tidmouth at
  large −X (west).

## Main Line (our ordering, east → west)
`Vicarstown → Crovan's Gate → Kellsthorpe Road → Maron → Wellsworth → Crosby → Knapford → Tidmouth`
- Canon ordering varies slightly between sources; this is a faithful-enough stylization.
- **Junctions:** Crovan's Gate (Skarloey Railway + Sodor Steamworks), Wellsworth
  (Brendam branch), Knapford (Ffarquhar branch), Tidmouth (Little Western).
- Closed into a continuous **loop** for kid-friendly riding (decision D8).

## Branch lines
| Branch | Route | Notes / engines |
|---|---|---|
| **Ffarquhar** (Thomas's Branch) | Knapford – Elsbridge – Ffarquhar | Thomas, Toby, Percy; Anopha Quarry at the end. *MVP* |
| **Brendam** (Edward's Branch) | Wellsworth – Suddery – Brendam Docks | Edward, Bill & Ben. *MVP* |
| **The Little Western** | Tidmouth – Arlesburgh (Harwick) | Duck, Oliver. *post-MVP* |
| **Skarloey Railway** (narrow gauge) | Crovan's Gate – Skarloey – Rheneas – Blue Mountain Quarry | Skarloey, Rheneas; slate. *post-MVP* |
| **Culdee Fell Railway** (mountain rack) | Kirk Machan – Culdee Fell summit | *post-MVP* |
| **Peel Godred** (electrified) | Killdane/Kellsthorpe – Peel Godred | only electrified line. *post-MVP* |
| **Norramby** | Vicarstown – Ballahoo – Norramby | *post-MVP* |

## Locations (build registry — see config/layout.toml)
**MVP (Phase 4):** Tidmouth (+ Sheds & turntable), Knapford, Wellsworth, Maron,
Crovan's Gate, Vicarstown, Brendam Docks, Ffarquhar.
**Phase-0 stubs / post-MVP:** Crosby, Kellsthorpe Road, Elsbridge, Sodor Steamworks,
Ulfstead Castle, Blue Mountain Quarry.
**Future polish candidates:** Great Waterton, Arlesburgh, Skarloey & Rheneas stations,
Misty Island, Suddery, Kirk Ronan, Lakeside, Callan Castle.

## Classic engine roster (config/engines.toml)
North Western Railway (NWR). All are steam; "type" drives the display-rig silhouette.

| # | Name | Type | Wheels | Livery | Personality cue (for dialogue/faces) |
|---|---|---|---|---|---|
| 1 | **Thomas** | tank | 0-6-0T | NWR blue, red lining | cheeky, eager |
| 2 | **Edward** | tender | 4-4-0 | blue, red/yellow lining | kind, wise, older |
| 3 | **Henry** | tender | 4-6-0 | green, red lining | gentle, a worrier |
| 4 | **Gordon** | tender | 4-6-2 | (express) blue, red lining | proud, big & fast |
| 5 | **James** | tender | 2-6-0 | red, black/yellow lining | vain, splendid |
| 6 | **Percy** | tank | 0-4-0ST | green, red lining | happy, small, mail |
| 7 | **Toby** | tram | 0-6-0T | brown, yellow stripes | wise tram, side plates |

Notes for modelling (Phase 5/7): tank engines have no separate tender; Gordon is the
largest (long boiler, 4-6-2); Toby is boxy with side plates + cowcatchers; faces go on the
smokebox front (tender/tank) or front plate (tram). Number plates on the side tank/cab.
