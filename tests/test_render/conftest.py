"""Shared test builders for render tests."""

from __future__ import annotations

from canopy.models import (
    Dependency,
    Layer,
    LayoutResult,
    Module,
    NodePosition,
    ProjectData,
    RingPosition,
)
from canopy.render.theme import Theme


def make_theme(**kw) -> Theme:
    return Theme(**kw)


def make_mod(
    name: str = "pkg.foo",
    lines: int = 100,
    mi: float = 50.0,
    *,
    layer: str = "infra",
    dead: int = 0,
    churn: int = 0,
    desc: str = "",
) -> Module:
    return Module(
        name=name,
        lines=lines,
        funcs=3,
        mi=mi,
        cc=2.0,
        dead=dead,
        churn=churn,
        layer=layer,
        desc=desc,
    )


def make_dep(src: str = "pkg.a", tgt: str = "pkg.b", weight: float = 1.0) -> Dependency:
    return Dependency(from_module=src, to_module=tgt, weight=weight)


def make_node(
    name: str = "pkg.foo",
    x: float = 100.0,
    y: float = 50.0,
    r: float = 20.0,
) -> NodePosition:
    return NodePosition(name=name, x=x, y=y, radius=r)


def make_ring(layer: str = "infra", radius: float = 200.0, label: str = "Infra") -> RingPosition:
    return RingPosition(layer_name=layer, radius=radius, label=label)


def make_pd(
    modules: list[Module] | None = None,
    deps: list[Dependency] | None = None,
    layers: list[Layer] | None = None,
    name: str = "testproj",
) -> ProjectData:
    if modules is None:
        modules = [make_mod()]
    if layers is None:
        layers = [Layer("core", 0, "Core"), Layer("infra", 1, "Infra")]
    return ProjectData(
        modules=modules,
        dependencies=deps or [],
        layers=layers,
        project_name=name,
    )


def make_layout(
    nodes: list[NodePosition] | None = None,
    rings: list[RingPosition] | None = None,
) -> LayoutResult:
    if nodes is None:
        nodes = [make_node()]
    return LayoutResult(nodes=nodes, rings=rings or [make_ring()])
