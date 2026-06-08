"""Typed loaders for the TOML config files (config/*.toml).

Uses the stdlib `tomllib` (Python 3.11+), so no extra dependency. Keeping the
version/format values in one place satisfies the brief's hard constraint that
DataVersion + pack_formats live in config, verified against the wiki.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = REPO_ROOT / "config"


def _load_toml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing config file: {path}")
    with path.open("rb") as fh:
        return tomllib.load(fh)


@dataclass(frozen=True)
class VersionConfig:
    patch: str               # WORLD save patch (amulet output, 1.21.8)
    version_name: str
    data_version: int        # WORLD DataVersion (4440)
    platform: str
    game_version: tuple[int, int, int]
    client_patch: str        # version the family runs (26.1.2) — packs target this
    client_data_version: int
    datapack_format: int     # for datapack pack.mcmeta (26.1.2)
    resourcepack_format: int # for resource pack pack.mcmeta (26.1.2)
    datapack_minor: int
    resourcepack_minor: int
    raw: dict = field(repr=False)


def load_version(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> VersionConfig:
    d = _load_toml(Path(config_dir) / "version.toml")
    t = d["target"]
    a = t["amulet"]
    pf = d["pack_format"]
    client = d.get("client", {})
    return VersionConfig(
        patch=t["patch"],
        version_name=t["version_name"],
        data_version=int(t["data_version"]),
        platform=a["platform"],
        game_version=tuple(a["game_version"]),  # type: ignore[arg-type]
        client_patch=str(client.get("patch", t["patch"])),
        client_data_version=int(client.get("data_version", t["data_version"])),
        datapack_format=int(pf["datapack"]),
        resourcepack_format=int(pf["resourcepack"]),
        datapack_minor=int(pf.get("datapack_minor", 0)),
        resourcepack_minor=int(pf.get("resourcepack_minor", 0)),
        raw=d,
    )


def load_layout(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> dict:
    return _load_toml(Path(config_dir) / "layout.toml")


def load_engines(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> dict:
    return _load_toml(Path(config_dir) / "engines.toml")


def mvp_locations(layout: dict) -> list[dict]:
    return [loc for loc in layout.get("locations", []) if loc.get("mvp")]
