from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from canopy.config import Config
from canopy.score import grade as score_grade

if TYPE_CHECKING:
    from canopy.models import Module


@dataclass(frozen=True)
class HealthColors:
    base: str
    dark: str
    light: str
    glow: str


@dataclass(frozen=True)
class Theme:
    # Canvas
    width: int = 1000
    height: int = 800

    # Background gradient stops
    bg_inner: str = "#111820"
    bg_mid: str = "#0a0e14"
    bg_outer: str = "#06080c"

    # Health palettes
    healthy: HealthColors = HealthColors(
        base="#2ea043", dark="#1a7f37", light="#56d364", glow="#2ea04355"
    )
    moderate: HealthColors = HealthColors(
        base="#d29922", dark="#9e6a03", light="#e3b341", glow="#d2992255"
    )
    complex: HealthColors = HealthColors(
        base="#da3633", dark="#b62324", light="#f85149", glow="#da363355"
    )

    # Thresholds
    score_healthy: int = 75
    score_moderate: int = 50
    risk_hotspot: float = 0.4

    # Ring
    ring_default: str = "#30363d"
    ring_infra: str = "#bc8cff"

    # Dependencies
    dep_core_infra: str = "#bc8cff"
    dep_light: str = "#21262d"
    dep_significant: str = "#58a6ff"
    dep_visible_count: int = 8
    dep_visible_opacity: float = 0.12
    cycle_stroke: str = "#f85149"

    # Hotspot (high churn x low health)
    hotspot_stroke: str = "#f0883e"

    # Dead code
    dead_fill: str = "#1b1f23"
    dead_opacity: float = 0.7

    # Stars
    star_fill: str = "#c9d1d9"
    star_count: int = 60
    star_min_r: float = 0.3
    star_max_r: float = 1.2
    star_min_opacity: float = 0.1
    star_max_opacity: float = 0.5

    # Text
    text_primary: str = "#c9d1d9"
    text_secondary: str = "#8b949e"
    text_muted: str = "#484f58"

    # Watermark
    watermark_fill: str = "#161b22"

    # Node glow
    ambient_opacity: float = 0.08
    ambient_opacity_core: float = 0.15

    # Core decoration
    core_ring_stroke: str = "#da3633"
    core_ring_radius: float = 50.0


def health_colors(theme: Theme, score: float) -> HealthColors:
    if score >= theme.score_healthy:
        return theme.healthy
    if score >= theme.score_moderate:
        return theme.moderate
    return theme.complex


@dataclass(frozen=True)
class ProjectStats:
    """Aggregated health stats computed once, shared by SVG and HTML renderers.

    Health percentages are weighted by lines of code, not module count —
    a healthy 5k-line module outweighs ten 50-line ones.
    """

    modules: int
    lines: int
    healthy_lines: int
    moderate_lines: int
    complex_lines: int
    dead_total: int
    score: float
    grade: str

    @property
    def healthy_pct(self) -> int:
        return round(self.healthy_lines * 100 / self.lines) if self.lines else 0

    @property
    def moderate_pct(self) -> int:
        return round(self.moderate_lines * 100 / self.lines) if self.lines else 0

    @property
    def complex_pct(self) -> int:
        return round(self.complex_lines * 100 / self.lines) if self.lines else 0


def compute_stats(modules: list[Module], theme: Theme) -> ProjectStats:
    """Compute LOC-weighted health stats from module list and theme thresholds."""
    total = len(modules)
    if total == 0:
        return ProjectStats(0, 0, 0, 0, 0, 0, 100.0, score_grade(100.0))
    total_lines = 0
    healthy_lines = moderate_lines = complex_lines = dead_total = 0
    score_weighted = 0.0
    for m in modules:
        total_lines += m.lines
        dead_total += m.dead
        score_weighted += m.score * m.lines
        if m.score >= theme.score_healthy:
            healthy_lines += m.lines
        elif m.score >= theme.score_moderate:
            moderate_lines += m.lines
        else:
            complex_lines += m.lines
    score = round(score_weighted / total_lines, 1) if total_lines else 100.0
    return ProjectStats(
        modules=total,
        lines=total_lines,
        healthy_lines=healthy_lines,
        moderate_lines=moderate_lines,
        complex_lines=complex_lines,
        dead_total=dead_total,
        score=score,
        grade=score_grade(score),
    )


def default_theme() -> Theme:
    return Theme()


def theme_from_config(cfg: Config) -> Theme:
    return Theme(
        width=cfg.output.width,
        height=cfg.output.height,
        score_healthy=cfg.thresholds.score_healthy,
        score_moderate=cfg.thresholds.score_moderate,
        risk_hotspot=cfg.thresholds.risk_hotspot,
    )
