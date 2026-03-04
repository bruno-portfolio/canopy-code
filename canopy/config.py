from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from canopy import exceptions


@dataclass(frozen=True)
class LayerConfig:
    modules: list[str] = field(default_factory=list)
    label: str = ""


@dataclass(frozen=True)
class VultureConfig:
    min_confidence: int = 60
    exclude_types: list[str] = field(default_factory=lambda: ["attribute"])


@dataclass(frozen=True)
class GitConfig:
    churn_days: int = 30


@dataclass(frozen=True)
class ThresholdsConfig:
    mi_healthy: int = 40
    mi_moderate: int = 20
    churn_high: int = 20
    min_loc: int = 50


@dataclass(frozen=True)
class OutputConfig:
    path: str = "canopy.svg"
    width: int = 1000
    height: int = 800


@dataclass(frozen=True)
class Config:
    project: str | None = None
    source: str = "."
    module_depth: int = 2
    layers: dict[str, LayerConfig] = field(default_factory=dict)
    vulture: VultureConfig = field(default_factory=VultureConfig)
    git: GitConfig = field(default_factory=GitConfig)
    thresholds: ThresholdsConfig = field(default_factory=ThresholdsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    ignore: list[str] = field(default_factory=list)


def _field_names(cls: type) -> frozenset[str]:
    return frozenset(f.name for f in dataclasses.fields(cls))


_KNOWN_TOP_KEYS = _field_names(Config)
_KNOWN_VULTURE_KEYS = _field_names(VultureConfig)
_KNOWN_GIT_KEYS = _field_names(GitConfig)
_KNOWN_THRESHOLDS_KEYS = _field_names(ThresholdsConfig)
_KNOWN_OUTPUT_KEYS = _field_names(OutputConfig)
_KNOWN_LAYER_KEYS = _field_names(LayerConfig)


def _parse_sub(raw: dict, known_keys: frozenset[str]) -> dict:
    return {k: v for k, v in raw.items() if k in known_keys}


def _parse_layers(raw_layers: dict | None) -> dict[str, LayerConfig]:
    if not raw_layers:
        return {}
    result: dict[str, LayerConfig] = {}
    for name, value in raw_layers.items():
        if not value:
            result[name] = LayerConfig()
            continue
        filtered = _parse_sub(value, _KNOWN_LAYER_KEYS)
        modules = filtered.get("modules", [])
        if modules is None:
            modules = []
        result[name] = LayerConfig(
            modules=modules,
            label=filtered.get("label", ""),
        )
    return result


def _parse_config(raw: dict) -> Config:
    filtered = _parse_sub(raw, _KNOWN_TOP_KEYS)

    vulture_raw = filtered.get("vulture") or {}
    git_raw = filtered.get("git") or {}
    thresholds_raw = filtered.get("thresholds") or {}
    output_raw = filtered.get("output") or {}

    return Config(
        project=filtered.get("project"),
        source=filtered.get("source", "."),
        module_depth=filtered.get("module_depth", 2),
        layers=_parse_layers(filtered.get("layers")),
        vulture=VultureConfig(**_parse_sub(vulture_raw, _KNOWN_VULTURE_KEYS)),
        git=GitConfig(**_parse_sub(git_raw, _KNOWN_GIT_KEYS)),
        thresholds=ThresholdsConfig(**_parse_sub(thresholds_raw, _KNOWN_THRESHOLDS_KEYS)),
        output=OutputConfig(**_parse_sub(output_raw, _KNOWN_OUTPUT_KEYS)),
        ignore=filtered.get("ignore", []),
    )


def _load_from_path(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _parse_config(raw)


def load_config(config_path: str | None = None, *, project_dir: str = ".") -> Config:
    if config_path is not None:
        try:
            return _load_from_path(Path(config_path))
        except FileNotFoundError as err:
            raise exceptions.ConfigError(f"Config file not found: {config_path}") from err

    project = Path(project_dir)
    for name in ("canopy.yml", "canopy.yaml"):
        try:
            return _load_from_path(project / name)
        except FileNotFoundError:
            continue

    return Config()


def resolve_project_name(config: Config, project_dir: str) -> str:
    if config.project:
        return config.project
    return Path(project_dir).resolve().name


def validate_config(config: Config, project_dir: str) -> None:
    source_path = Path(project_dir) / config.source
    if not source_path.exists():
        raise exceptions.ConfigError(f"Source directory not found: {source_path}")

    if config.module_depth < 1:
        raise exceptions.ConfigError(f"module_depth must be >= 1, got {config.module_depth}")

    if config.thresholds.mi_healthy <= config.thresholds.mi_moderate:
        raise exceptions.ConfigError(
            f"mi_healthy ({config.thresholds.mi_healthy}) must be greater than "
            f"mi_moderate ({config.thresholds.mi_moderate})"
        )

    if config.output.width <= 0:
        raise exceptions.ConfigError(f"output.width must be > 0, got {config.output.width}")

    if config.output.height <= 0:
        raise exceptions.ConfigError(f"output.height must be > 0, got {config.output.height}")
