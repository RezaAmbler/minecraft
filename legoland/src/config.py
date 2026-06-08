"""Typed loaders for the TOML config files (config/*.toml).

Uses the stdlib `tomllib` (Python 3.11+), so no extra dependency. Keeping the
version/format values in one place satisfies the brief's hard constraint that
DataVersion + pack_formats live in config, verified against the wiki.

LEGOLAND uses four config files (the theme-park analogue of Sodor's
version/layout/engines):
  * version.toml   — Minecraft version + pack-format pins (shared, unchanged)
  * transform.toml — GPS anchors, bbox, real-world -> block compression, world frame
  * lands.toml     — the park's lands (the "locations" of the build)
  * rides.toml     — coasters (rail rides) + static rides + display-entity rigs
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


def load_transform(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> dict:
    """Anchors, bbox, compression factor, vertical exaggeration, world frame, seed."""
    return _load_toml(Path(config_dir) / "transform.toml")


def load_lands(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> dict:
    """The park's lands registry."""
    return _load_toml(Path(config_dir) / "lands.toml")


def load_rides(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> dict:
    """Coasters (rail rides) + static rides + display-entity rigs."""
    return _load_toml(Path(config_dir) / "rides.toml")


def lands(land_cfg: dict) -> list[dict]:
    return land_cfg.get("lands", [])


def mvp_lands(land_cfg: dict) -> list[dict]:
    return [land for land in land_cfg.get("lands", []) if land.get("mvp")]


def coasters(ride_cfg: dict) -> list[dict]:
    """Rail rides only (tracked coasters)."""
    return [r for r in ride_cfg.get("rides", []) if r.get("kind") == "coaster"]


def static_rides(ride_cfg: dict) -> list[dict]:
    """Non-rideable themed structures (spinning/drop/flat rides)."""
    return [r for r in ride_cfg.get("rides", []) if r.get("kind") != "coaster"]
