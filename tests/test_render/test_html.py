from __future__ import annotations

from canopy.render.html import render_html
from canopy.render.svg import render_svg

from .conftest import make_layout, make_mod, make_node, make_pd, make_theme


def _render(**kw) -> str:
    pd = kw.get("pd", make_pd())
    ly = kw.get("ly", make_layout())
    t = kw.get("t", make_theme())
    svg = render_svg(pd, ly, t)
    return render_html(pd, t, svg)


# ── Tests ─────────────────────────────────────────────────────────────────


class TestRenderHtmlBasic:
    def test_render_html_returns_string(self):
        html = _render()
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_html_valid_structure(self):
        html = _render()
        assert "<!DOCTYPE html>" in html
        assert "<svg" in html
        assert "</html>" in html

    def test_render_html_contains_module_data(self):
        pd = make_pd(modules=[make_mod(name="pkg.alpha"), make_mod(name="pkg.beta")])
        ly = make_layout(nodes=[make_node(name="pkg.alpha"), make_node(name="pkg.beta", x=-100)])
        html = _render(pd=pd, ly=ly)
        assert '"pkg.alpha"' in html
        assert '"pkg.beta"' in html

    def test_render_html_contains_tooltip(self):
        html = _render()
        assert 'class="tooltip"' in html

    def test_render_html_self_contained(self):
        html = _render()
        assert "<link" not in html
        assert 'src="http' not in html

    def test_render_html_contains_theme_colors(self):
        t = make_theme()
        html = _render(t=t)
        assert t.healthy.base in html
        assert t.moderate.base in html
        assert t.complex.base in html

    def test_render_html_svg_responsive(self):
        t = make_theme()
        html = _render(t=t)
        assert 'width="100%"' in html
        # The <svg> root tag should not have fixed dimensions,
        # but child elements like <rect> may still have width/height
        import re

        svg_tag = re.search(r"<svg\b[^>]*>", html).group(0)
        assert f'width="{t.width}"' not in svg_tag
