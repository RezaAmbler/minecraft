# datapack/

Hand-authored datapack **source fragments** (if any) — e.g. static `.mcfunction` snippets or
JSON templates that are easier to write by hand than to generate.

The datapack is assembled by `src/datapack/` (a thin in-repo writer; beet is intentionally
not used — see DECISIONS D3) and emitted to `build/world/datapacks/sodor/` with
`pack_format` 81. Most content (engine summon/tick functions, teleport hubs, dialogue,
gamerule setup, tick/load tags) is generated, so this directory may stay nearly empty.
