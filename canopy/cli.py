from __future__ import annotations

import dataclasses
from pathlib import Path

import click

from canopy import __version__, exceptions
from canopy.aggregator import aggregate
from canopy.collectors.coverage import collect_coverage
from canopy.collectors.git import collect_churn
from canopy.collectors.imports import collect_imports
from canopy.collectors.radon import collect_radon
from canopy.collectors.vulture import collect_vulture
from canopy.config import load_config, resolve_project_name, validate_config
from canopy.cycles import cycle_groups
from canopy.history import history_path_for, record_run
from canopy.layout import assign_layers, collapse_small, compute_layout
from canopy.layout.layers import UNCATEGORIZED
from canopy.render import render_html, render_svg
from canopy.render.theme import compute_stats, theme_from_config


def _build_config(project_dir, config_path, output_override):
    cfg = load_config(config_path, project_dir=project_dir)
    validate_config(cfg, project_dir)
    if output_override:
        cfg = dataclasses.replace(
            cfg,
            output=dataclasses.replace(cfg.output, path=output_override),
        )
    return cfg


def _run_collectors(source_path, project_dir, cfg):
    radon = collect_radon(source_path)
    vulture = collect_vulture(source_path, min_confidence=cfg.vulture.min_confidence)
    churn = collect_churn(project_dir, days=cfg.git.churn_days)
    imports = collect_imports(source_path)
    coverage = collect_coverage(project_dir)
    return radon, vulture, churn, imports, coverage


def _warn_uncategorized(project_data, cfg):
    if not cfg.layers:
        return
    names = [m.name for m in project_data.modules if m.layer == UNCATEGORIZED]
    if names:
        click.echo(
            f"Warning: {len(names)} module(s) not matched by any layer: {', '.join(names)}",
            err=True,
        )


def _warn_cycles(project_data):
    for group in cycle_groups(project_data.dependencies):
        click.echo(f"Warning: import cycle: {' <-> '.join(group)}", err=True)


def _run_pipeline(cfg, source_path, project_dir, radon, vulture, churn, imports, coverage):
    project_data = aggregate(
        cfg=cfg,
        source_path=source_path,
        imports=imports,
        radon=radon,
        vulture=vulture,
        churn=churn,
        coverage=coverage,
    )
    project_name = resolve_project_name(cfg, project_dir)
    project_data = dataclasses.replace(project_data, project_name=project_name)
    project_data = assign_layers(project_data, cfg)
    _warn_uncategorized(project_data, cfg)
    _warn_cycles(project_data)
    project_data = collapse_small(project_data, cfg.thresholds.min_loc)
    layout = compute_layout(project_data, cfg)
    return project_data, layout


def _write_output(cfg, project_data, layout, html_path=None):
    theme = theme_from_config(cfg)
    stats = compute_stats(project_data.modules, theme)
    delta = record_run(
        history_path_for(cfg.output.path),
        score=stats.score,
        grade=stats.grade,
        modules=stats.modules,
        lines=stats.lines,
    )
    svg = render_svg(project_data, layout, theme, delta=delta)
    out = Path(cfg.output.path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    delta_note = f", {'+' if delta > 0 else ''}{delta} vs last run" if delta else ""
    click.echo(
        f"{out} written ({stats.modules} modules, {stats.lines} lines, "
        f"grade {stats.grade} {stats.score}/100{delta_note})"
    )

    if html_path:
        html_content = render_html(project_data, theme, svg)
        html_out = Path(html_path)
        html_out.parent.mkdir(parents=True, exist_ok=True)
        html_out.write_text(html_content, encoding="utf-8")
        click.echo(f"{html_out} written (interactive HTML)")


@click.group()
@click.version_option(version=__version__, prog_name="canopy")
def main():
    """Canopy — orbital SVG visualizations of codebase health."""


@main.command()
@click.argument("path", default=".")
@click.option("--config", "config_path", default=None, help="Path to canopy.yml")
@click.option("--output", "output_override", default=None, help="Override output path")
@click.option("--html", "html_path", default=None, help="Generate interactive HTML viewer")
def run(path, config_path, output_override, html_path):
    """Analyse a project and generate an SVG diagram."""
    try:
        project_dir = str(Path(path).resolve())
        cfg = _build_config(project_dir, config_path, output_override)
        source_path = str(Path(project_dir) / cfg.source)
        radon, vulture, churn, imports, coverage = _run_collectors(source_path, project_dir, cfg)
        project_data, layout = _run_pipeline(
            cfg,
            source_path,
            project_dir,
            radon,
            vulture,
            churn,
            imports,
            coverage,
        )
        _write_output(cfg, project_data, layout, html_path=html_path)
    except exceptions.ConfigError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
    except exceptions.CollectorError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(2) from exc
    except exceptions.CanopyError as exc:
        click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1) from exc
