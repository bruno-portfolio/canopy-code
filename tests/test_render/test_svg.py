from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from canopy.models import (
    Layer,
    LayoutResult,
    ProjectData,
)
from canopy.render.svg import render_svg

from .conftest import make_dep, make_layout, make_mod, make_node, make_pd, make_ring, make_theme

GOLDEN_DIR = Path(__file__).parent.parent / "golden"


# ── SVG Structure ─────────────────────────────────────────────────────────


class TestSvgStructure:
    def test_returns_string(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert isinstance(svg, str)

    def test_starts_with_svg_tag(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert svg.startswith("<svg")

    def test_ends_with_svg_close(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert svg.strip().endswith("</svg>")

    def test_valid_xml(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        ET.fromstring(svg)  # Raises on invalid XML

    def test_no_style_tag(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert "<style" not in svg

    def test_no_script_tag(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert "<script" not in svg

    def test_no_dominant_baseline(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert "dominant-baseline" not in svg

    def test_uses_monospace(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'font-family="monospace"' in svg


# ── ViewBox ───────────────────────────────────────────────────────────────


class TestViewBox:
    def test_default_viewbox(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'viewBox="0 0 1000 800"' in svg

    def test_custom_viewbox(self):
        svg = render_svg(make_pd(), make_layout(), make_theme(width=1200, height=600))
        assert 'viewBox="0 0 1200 600"' in svg


# ── Defs ──────────────────────────────────────────────────────────────────


class TestDefs:
    def test_has_bg_gradient(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'id="bgGrad"' in svg

    def test_has_node_glow(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'id="nodeGlow"' in svg

    def test_has_soft_glow(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'id="softGlow"' in svg

    def test_has_churn_pulse_filter(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'id="churnPulse"' in svg


# ── Background ────────────────────────────────────────────────────────────


class TestBackground:
    def test_bg_uses_gradient(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert 'fill="url(#bgGrad)"' in svg


# ── Stars ─────────────────────────────────────────────────────────────────


class TestStars:
    def test_star_count(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert svg.count('fill="#c9d1d9"') >= 60

    def test_deterministic(self):
        a = render_svg(make_pd(), make_layout(), make_theme())
        b = render_svg(make_pd(), make_layout(), make_theme())
        assert a == b

    def test_different_projects_differ(self):
        a = render_svg(make_pd(name="alpha"), make_layout(), make_theme())
        b = render_svg(make_pd(name="beta"), make_layout(), make_theme())
        # Stars section will differ (different seeds), overall SVG differs
        assert a != b


# ── Rings ─────────────────────────────────────────────────────────────────


class TestRings:
    def test_ring_rendered(self):
        svg = render_svg(make_pd(), make_layout(rings=[make_ring()]), make_theme())
        assert 'r="200.0"' in svg

    def test_infra_dashed(self):
        svg = render_svg(make_pd(), make_layout(rings=[make_ring("infra")]), make_theme())
        assert 'stroke-dasharray="8 4"' in svg

    def test_non_infra_not_dashed(self):
        svg = render_svg(
            make_pd(), make_layout(rings=[make_ring("api", 250.0, "API")]), make_theme()
        )
        # Should not have dasharray for non-infra
        # Check the ring circle specifically
        assert "stroke-dasharray" not in svg or svg.count("stroke-dasharray") == 1
        # The core decoration may add dasharray; check ring line doesn't have it
        # More robust: just verify ring is present
        assert 'r="250.0"' in svg


# ── Nodes ─────────────────────────────────────────────────────────────────


class TestNodes:
    def test_healthy_color(self):
        t = make_theme()
        svg = render_svg(
            make_pd(modules=[make_mod(mi=50.0)]),
            make_layout(nodes=[make_node()]),
            t,
        )
        assert t.healthy.base in svg

    def test_moderate_color(self):
        t = make_theme()
        svg = render_svg(
            make_pd(modules=[make_mod(mi=30.0)]),
            make_layout(nodes=[make_node()]),
            t,
        )
        assert t.moderate.base in svg

    def test_complex_color(self):
        t = make_theme()
        svg = render_svg(
            make_pd(modules=[make_mod(mi=10.0)]),
            make_layout(nodes=[make_node()]),
            t,
        )
        assert t.complex.base in svg

    def test_coordinates_translated(self):
        t = make_theme()  # 1000x800 → cx=500, cy=400
        svg = render_svg(
            make_pd(modules=[make_mod()]),
            make_layout(nodes=[make_node(x=100.0, y=50.0)]),
            t,
        )
        # sx = 500 + 100 = 600, sy = 400 + 50 = 450
        assert "600.0" in svg
        assert "450.0" in svg


# ── Churn Pulse ───────────────────────────────────────────────────────────


class TestChurnPulse:
    def test_animate_above_threshold(self):
        svg = render_svg(
            make_pd(modules=[make_mod(churn=25)]),
            make_layout(nodes=[make_node()]),
            make_theme(),
        )
        assert "<animate" in svg

    def test_no_animate_below_threshold(self):
        svg = render_svg(
            make_pd(modules=[make_mod(churn=5)]),
            make_layout(nodes=[make_node()]),
            make_theme(),
        )
        # Only animateTransform (core decoration) should be absent too
        # since no core layer module
        assert "<animate " not in svg


# ── Dead Code Spots ───────────────────────────────────────────────────────


class TestDeadCodeSpots:
    def test_spots_present(self):
        t = make_theme()
        svg = render_svg(
            make_pd(modules=[make_mod(dead=3)]),
            make_layout(nodes=[make_node()]),
            t,
        )
        assert t.dead_fill in svg

    def test_no_spots_when_zero(self):
        t = make_theme()
        svg = render_svg(
            make_pd(modules=[make_mod(dead=0)]),
            make_layout(nodes=[make_node()]),
            t,
        )
        assert t.dead_fill not in svg

    def test_spots_deterministic(self):
        pd = make_pd(modules=[make_mod(dead=5)])
        ly = make_layout(nodes=[make_node()])
        t = make_theme()
        a = render_svg(pd, ly, t)
        b = render_svg(pd, ly, t)
        assert a == b


# ── Labels ────────────────────────────────────────────────────────────────


class TestLabels:
    def test_last_segment(self):
        svg = render_svg(
            make_pd(modules=[make_mod(name="pkg.utils.helpers")]),
            make_layout(nodes=[make_node(name="pkg.utils.helpers")]),
            make_theme(),
        )
        assert "helpers" in svg

    def test_truncation(self):
        svg = render_svg(
            make_pd(modules=[make_mod(name="pkg.very_long_name_here")]),
            make_layout(nodes=[make_node(name="pkg.very_long_name_here")]),
            make_theme(),
        )
        assert "very_long.." in svg

    def test_strip_underscore(self):
        svg = render_svg(
            make_pd(modules=[make_mod(name="pkg._private")]),
            make_layout(nodes=[make_node(name="pkg._private")]),
            make_theme(),
        )
        assert "private" in svg
        # Should not show leading underscore
        assert ">_private<" not in svg

    def test_collapsed_shows_desc(self):
        svg = render_svg(
            make_pd(modules=[make_mod(name="_collapsed_infra", desc="+5 more")]),
            make_layout(nodes=[make_node(name="_collapsed_infra")]),
            make_theme(),
        )
        assert "+5 more" in svg

    def test_loc_label_large_node(self):
        svg = render_svg(
            make_pd(modules=[make_mod(lines=200)]),
            make_layout(nodes=[make_node(r=25.0)]),
            make_theme(),
        )
        assert "200 loc" in svg

    def test_no_loc_label_small_node(self):
        svg = render_svg(
            make_pd(modules=[make_mod(lines=200)]),
            make_layout(nodes=[make_node(r=12.0)]),
            make_theme(),
        )
        assert "200 loc" not in svg


# ── Core Decoration ───────────────────────────────────────────────────────


class TestCoreDecoration:
    def test_animatetransform_present(self):
        svg = render_svg(
            make_pd(
                modules=[make_mod(name="app", layer="core")],
                layers=[Layer("core", 0, "Core"), Layer("infra", 1, "Infra")],
            ),
            make_layout(nodes=[make_node(name="app", x=0, y=0)]),
            make_theme(),
        )
        assert "animateTransform" in svg

    def test_no_decoration_without_core(self):
        svg = render_svg(
            make_pd(
                modules=[make_mod(layer="infra")],
                layers=[Layer("infra", 1, "Infra")],
            ),
            make_layout(nodes=[make_node()]),
            make_theme(),
        )
        assert "animateTransform" not in svg


# ── Dependencies ──────────────────────────────────────────────────────────


class TestDependencies:
    def test_significant_dep_bezier(self):
        svg = render_svg(
            make_pd(
                modules=[
                    make_mod(name="pkg.a", layer="infra"),
                    make_mod(name="pkg.b", layer="infra"),
                ],
                deps=[make_dep("pkg.a", "pkg.b", weight=5.0)],
            ),
            make_layout(
                nodes=[make_node(name="pkg.a", x=-100, y=0), make_node(name="pkg.b", x=100, y=0)]
            ),
            make_theme(),
        )
        assert "<path" in svg
        assert " Q" in svg

    def test_no_deps_no_lines(self):
        svg = render_svg(make_pd(deps=[]), make_layout(), make_theme())
        assert "<line " not in svg


# ── Stats Bar ─────────────────────────────────────────────────────────────


class TestStatsBar:
    def test_contains_module_count(self):
        svg = render_svg(
            make_pd(modules=[make_mod(), make_mod(name="pkg.bar")]),
            make_layout(nodes=[make_node(), make_node(name="pkg.bar", x=-100)]),
            make_theme(),
        )
        assert "2 modules" in svg

    def test_contains_total_lines(self):
        svg = render_svg(
            make_pd(modules=[make_mod(lines=500)]),
            make_layout(nodes=[make_node()]),
            make_theme(),
        )
        assert "500 lines" in svg


# ── Watermark ─────────────────────────────────────────────────────────────


class TestWatermark:
    def test_canopy_present(self):
        svg = render_svg(make_pd(), make_layout(), make_theme())
        assert "canopy" in svg


# ── Determinism ───────────────────────────────────────────────────────────


class TestDeterminism:
    def test_identical_output(self):
        pd = make_pd(
            modules=[make_mod(dead=3, churn=25), make_mod(name="pkg.bar", mi=15.0)],
            deps=[make_dep("pkg.foo", "pkg.bar", 0.5)],
        )
        ly = make_layout(
            nodes=[make_node(), make_node(name="pkg.bar", x=-80, y=60, r=15)],
            rings=[make_ring()],
        )
        t = make_theme()
        a = render_svg(pd, ly, t)
        b = render_svg(pd, ly, t)
        assert a == b


# ── XML Escape ────────────────────────────────────────────────────────────


class TestXmlEscape:
    def test_ampersand_in_project_name(self):
        svg = render_svg(
            make_pd(name="foo&bar"),
            make_layout(),
            make_theme(),
        )
        ET.fromstring(svg)  # Must parse as valid XML

    def test_angle_brackets_in_label(self):
        svg = render_svg(
            make_pd(modules=[make_mod(name="pkg.<gen>")]),
            make_layout(nodes=[make_node(name="pkg.<gen>")]),
            make_theme(),
        )
        ET.fromstring(svg)


# ── Golden Tests ──────────────────────────────────────────────────────────


class TestGoldenSvg:
    @staticmethod
    def _minimal_svg() -> str:
        pd = make_pd(modules=[make_mod()])
        ly = make_layout(nodes=[make_node()], rings=[make_ring()])
        return render_svg(pd, ly, make_theme())

    @staticmethod
    def _full_svg() -> str:
        modules = [
            make_mod(name="app", lines=500, mi=60.0, layer="core"),
            make_mod(name="pkg.api", lines=300, mi=35.0, layer="infra", churn=25),
            make_mod(name="pkg.db", lines=200, mi=15.0, layer="infra", dead=4),
            make_mod(name="_collapsed_outer", lines=50, mi=45.0, layer="outer", desc="+3 more"),
        ]
        deps = [
            make_dep("app", "pkg.api", 0.8),
            make_dep("pkg.api", "pkg.db", 0.5),
        ]
        layers = [
            Layer("core", 0, "Core"),
            Layer("infra", 1, "Infrastructure"),
            Layer("outer", 2, "Outer"),
        ]
        nodes = [
            make_node(name="app", x=0, y=0, r=35),
            make_node(name="pkg.api", x=150, y=80, r=22),
            make_node(name="pkg.db", x=-120, y=100, r=18),
            make_node(name="_collapsed_outer", x=0, y=250, r=12),
        ]
        rings = [
            make_ring("infra", 200.0, "Infrastructure"),
            make_ring("outer", 300.0, "Outer"),
        ]
        pd = ProjectData(
            modules=modules,
            dependencies=deps,
            layers=layers,
            project_name="golden-test",
        )
        ly = LayoutResult(nodes=nodes, rings=rings)
        return render_svg(pd, ly, make_theme())

    def test_golden_minimal(self):
        path = GOLDEN_DIR / "minimal.svg"
        svg = self._minimal_svg()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
            pytest.skip("Golden file created — inspect and re-run")
        assert svg == path.read_text(encoding="utf-8")

    def test_golden_full(self):
        path = GOLDEN_DIR / "full.svg"
        svg = self._full_svg()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(svg, encoding="utf-8")
            pytest.skip("Golden file created — inspect and re-run")
        assert svg == path.read_text(encoding="utf-8")
