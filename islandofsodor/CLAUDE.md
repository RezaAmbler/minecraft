# CLAUDE.md — Island of Sodor build pipeline

Persistent context for working in this repo. Read **BUILD_PLAN.md** first each session.

## Current state (2026-06-07)
All phases are **built, validated (67/67 structural checks), and packaged** (`build/dist/`).
The world generates from scratch in ~70s (incl. ~23k seeded trees) and is byte-reproducible. **Client is Minecraft
26.1.2** (not 1.21.8 — see memory): the world is written at 1.21.8/4440 (amulet's reliable
output) and 26.1.2 upgrades it on load; packs target 26.1.2 (datapack 101, resource 84).
The amulet `entities/` chunks that crashed 26.1.2 are stripped by the `finalize` step.
The rail is now **genuinely vanilla-rideable** (P3.7–P3.9, DECISIONS D16–D17): a 4-connected
grid path with neighbour-derived curve/ascending shapes, lever-operated branch switches, and a
permanent validator that proves connectivity + switch reachability. Structures lay **before**
rail so the corridor is never buried. A **Thomas statue** greets the player at the Knapford
spawn (P4.5, D18: code → `.schem` + registry). **Phase 10 detailing** (D19–D21): real
block-entity **name signs** at every station + a **lectern/welcome book** at spawn (a new `mcio`
block-entity capability, with a `[detailing].signs`/`.welcome` text_display fallback); a reusable
**prop library** (`src/structures/props.py`) distributed per station type by `src/structures/detailing.py`;
built-out **Brendam Docks** + enhanced **Wellsworth** (2nd building, footbridge); and ~23k **deterministic
lush trees** (`src/trees`, seeded). **Remaining: in-game play-test sign-off** (engine ride
*feel*/orientation; does the cart clear the whole loop without stalling; lever polarity matches the
sign; **do the block-entity signs/book render in 26.1.2** — else flip the fallback switches; statue
+ detailing look right). After the user tests, read `latest.log` (memory:
playtest-log-feedback-loop) and tune. Polish backlog: `docs/BACKLOG.md`.

## What this is
A **fully regenerable** Minecraft **Java Edition 1.21.8** singleplayer **Creative** world
of the **Island of Sodor** (Thomas & Friends), built from source by a Python pipeline.
Deliverables: a world save + a datapack + a resource pack. Kid-friendly, guided, bright.
Signature feature: a functional, rideable railway with the classic 7-engine roster as
display-entity models. Private/family-only (see IP note below).

## Verified target values (config/version.toml — never hardcode from memory)
| Thing | Value | Source (verified 2026-06-07) |
|---|---|---|
| Patch | 1.21.8 | — |
| DataVersion | **4440** | minecraft.wiki/w/Data_version |
| Datapack pack_format | **81** | minecraft.wiki/w/Pack_format |
| Resourcepack pack_format | **64** | minecraft.wiki/w/Pack_format |
| amulet game_version | `("java",(1,21,8))` | PyMCTranslate-confirmed |

## Toolchain (see docs/DECISIONS.md for the why)
- **Python 3.12 only** (brew `python@3.12`). amulet-core 1.9.40 needs numpy<2, which has no
  3.13/3.14 wheels. `build.py` refuses other interpreters.
- Deps pinned in `pyproject.toml`, locked in `requirements.lock`:
  amulet-core 1.9.40, numpy 1.26.4, Pillow 12.2.0, mcschematic 11.4.4, nbtlib 2.0.4.
- **No beet** (it requires Python 3.14, incompatible with the stack). The datapack is
  emitted by a thin in-repo writer (`src/datapack`).

## Run it
```bash
python3.12 -m venv .venv && ./.venv/bin/pip install -r requirements.lock   # one-time
./.venv/bin/python -m src.build info        # show resolved config
./.venv/bin/python -m src.build all         # regenerate everything into build/
./.venv/bin/python -m src.build <phase>     # world|terrain|rail|structures|engines|datapack|resourcepack|package|validate
./.venv/bin/python -m src.build validate    # structural checks
./.venv/bin/python -m src.build clean       # remove build/
```

## Repo map
- `config/` — version.toml (pins), layout.toml (coords/locations/lines), engines.toml (roster)
- `src/` — pipeline: `world terrain rail structures entities(=engines) datapack resourcepack validate` + `build.py`, `config.py`
- `schematics/` — exported `.schem` library  · `datapack/`,`resourcepack/` — authored asset sources
- `heightmaps/` — source map + derived masks  · `build/` — generated output (gitignored)
- `docs/` — DECISIONS, SODOR_REFERENCE, INSTALL, TESTING

## Working protocol
1. Read `BUILD_PLAN.md`; work the **lowest unchecked item in the lowest incomplete phase**. No jumping ahead.
2. One phase at a time; meet its **exit criterion** before the next.
3. Flip `- [ ]`→`- [x]` in `BUILD_PLAN.md` in the **same commit** that delivers the work.
4. Commit per coherent unit; message references phase+task (e.g. `P3.2: powered rail along main line`).
5. Validate after each phase (amulet load + assert-open + coordinate spot-checks; pack JSON valid). Log results.
6. Regenerate into a clean `build/` regularly to confirm reproducibility; a non-reproducing rerun is a bug.
7. Record decisions/workarounds in `docs/DECISIONS.md`.
8. If a task is infeasible or the plan is wrong, **stop and flag it**; don't silently redesign scope.

## Validation reality
We **cannot launch Minecraft** here. Validate structurally only (world opens in amulet,
coords correct, rail continuity, entity NBT present, pack formats match config). Ride feel
and in-client visuals are covered by a **manual checklist** in `docs/TESTING.md`.

## IP note (internal)
Thomas & Friends is Mattel IP. This project is **private/family-only — keep it unpublished**.
We use **original, license-safe stand-in assets** only (no community-pack adaptation). The
reference Sodor map is a private layout input, not redistributed. See `resourcepack/CREDITS.md`.
