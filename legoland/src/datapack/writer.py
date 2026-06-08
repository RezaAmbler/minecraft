"""Thin datapack writer (beet intentionally not used — see DECISIONS D3).

Writes pack.mcmeta + .mcfunction files + function tags into build/world/datapacks/sodor.
Tag writes merge (read-modify-write) so multiple phases (engines, mechanics) can each
register tick/load functions. Targets the 26.1.2 client (datapack format 101.1).
"""
from __future__ import annotations

import json
from pathlib import Path


class Datapack:
    def __init__(self, root: Path, ctx, description: str = "Island of Sodor"):
        self.root = Path(root)
        v = ctx.version
        major, minor = v.datapack_format, v.datapack_minor
        self.root.mkdir(parents=True, exist_ok=True)
        meta = {"pack": {
            "pack_format": major,
            "min_format": [major, minor],
            "max_format": [major, minor],
            "description": description,
        }}
        (self.root / "pack.mcmeta").write_text(json.dumps(meta, indent=2) + "\n")

    def function(self, namespace: str, path: str, lines: list[str]) -> str:
        p = self.root / "data" / namespace / "function" / f"{path}.mcfunction"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(lines) + "\n")
        return f"{namespace}:{path}"

    def _merge_tag(self, namespace: str, kind: str, name: str, values: list[str]) -> None:
        p = self.root / "data" / namespace / "tags" / kind / f"{name}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        existing: list = []
        if p.exists():
            existing = json.loads(p.read_text()).get("values", [])
        merged = list(dict.fromkeys([*existing, *values]))
        p.write_text(json.dumps({"values": merged}, indent=2) + "\n")

    def add_tick(self, function_id: str) -> None:
        self._merge_tag("minecraft", "function", "tick", [function_id])

    def add_load(self, function_id: str) -> None:
        self._merge_tag("minecraft", "function", "load", [function_id])
